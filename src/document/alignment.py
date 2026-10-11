"""Conservative weak alignment for SROIE line-level OCR tokens.

The jsdnrs SROIE mirror stores OCR output as line-like strings rather than
single words.  Ground-truth values therefore need field-aware matching before
they can be converted to BIO labels for token classification.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from typing import Any, Iterable, Mapping, Sequence


DATE_LABEL_WORDS = ("date", "dated", "tarikh")
TOTAL_LABEL_WORDS = ("total", "amount", "grandtotal", "jumlah")


@dataclass(frozen=True)
class Alignment:
    """A matched consecutive token span and its audit information."""

    field: str
    start: int
    end: int
    score: float
    method: str
    target: str
    matched_text: str


def entity_text(value: Any) -> str:
    """Flatten common mirror representations without stringifying brackets."""

    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        for key in ("text", "value", "answer"):
            if value.get(key):
                return entity_text(value[key])
        return " ".join(entity_text(item) for item in value.values() if item)
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        return " ".join(entity_text(item) for item in value if item)
    return str(value).strip()


def compact(value: Any) -> str:
    text = unicodedata.normalize("NFKC", entity_text(value)).casefold()
    return "".join(character for character in text if character.isalnum())


def _amounts(value: Any) -> set[Decimal]:
    text = unicodedata.normalize("NFKC", entity_text(value))
    candidates = re.findall(r"(?<!\d)[+-]?\d[\d., ]*(?!\d)", text)
    parsed: set[Decimal] = set()
    for candidate in candidates:
        token = candidate.replace(" ", "").strip(".,")
        if not token:
            continue
        if "," in token and "." in token:
            if token.rfind(".") > token.rfind(","):
                token = token.replace(",", "")
            else:
                token = token.replace(".", "").replace(",", ".")
        elif "," in token:
            tail = token.rsplit(",", 1)[-1]
            token = token.replace(",", ".") if len(tail) in (1, 2) else token.replace(",", "")
        try:
            parsed.add(Decimal(token))
        except InvalidOperation:
            continue
    return parsed


def _date_digits(value: Any) -> str:
    return "".join(re.findall(r"\d", entity_text(value)))


def _dates(value: Any) -> set[date]:
    text = unicodedata.normalize("NFKC", entity_text(value))
    candidates: set[tuple[int, int, int]] = set()
    for first, second, third in re.findall(r"(?<!\d)(\d{1,4})[./-](\d{1,2})[./-](\d{1,4})(?!\d)", text):
        if len(first) == 4:
            candidates.add((int(first), int(second), int(third)))
        elif len(third) == 4:
            candidates.add((int(third), int(second), int(first)))
    for digits in re.findall(r"(?<!\d)(\d{8})(?!\d)", text):
        if digits[:2] in {"19", "20"}:
            candidates.add((int(digits[:4]), int(digits[4:6]), int(digits[6:])))
        else:
            candidates.add((int(digits[4:]), int(digits[2:4]), int(digits[:2])))
    parsed: set[date] = set()
    for year, month, day in candidates:
        try:
            parsed.add(date(year, month, day))
        except ValueError:
            continue
    return parsed


def _context_bonus(words: Sequence[str], start: int, field: str) -> float:
    context = compact(" ".join(words[max(0, start - 2) : start + 1]))
    labels = DATE_LABEL_WORDS if field == "date" else TOTAL_LABEL_WORDS
    return 0.20 if any(label in context for label in labels) else 0.0


def _candidate_score(field: str, target: str, candidate: str) -> tuple[float, str]:
    wanted = compact(target)
    observed = compact(candidate)
    if not wanted or not observed:
        return 0.0, "empty"

    if wanted == observed:
        return 1.0, "exact_compact"

    if field == "date":
        wanted_dates = _dates(target)
        observed_dates = _dates(candidate)
        if wanted_dates and wanted_dates.intersection(observed_dates):
            return 0.995, "equal_date"
        wanted_digits = _date_digits(target)
        observed_digits = _date_digits(candidate)
        if len(wanted_digits) >= 6 and wanted_digits in observed_digits:
            return 0.99, "date_digits"
    elif field == "total":
        wanted_amounts = _amounts(target)
        observed_amounts = _amounts(candidate)
        if wanted_amounts and wanted_amounts.intersection(observed_amounts):
            return 0.99, "equal_amount"

    if wanted in observed:
        return 0.96, "target_contained"
    if observed in wanted and len(observed) / len(wanted) >= 0.75:
        return 0.93, "candidate_contained"

    similarity = SequenceMatcher(None, wanted, observed).ratio()
    return similarity, "fuzzy"


def align_entity(
    words: Sequence[str],
    field: str,
    value: Any,
    *,
    max_window: int = 3,
    minimum_score: float = 0.84,
) -> Alignment | None:
    """Match one entity to a consecutive OCR span.

    Context is only a tie-breaker.  A candidate must independently pass the
    similarity threshold, so a nearby ``TOTAL`` label cannot manufacture a
    match for an unrelated number.
    """

    target = entity_text(value)
    if not target:
        return None

    ranked: list[tuple[float, float, int, int, str, str]] = []
    for start in range(len(words)):
        for end in range(start + 1, min(len(words), start + max_window) + 1):
            candidate = " ".join(str(word) for word in words[start:end])
            base_score, method = _candidate_score(field, target, candidate)
            if base_score < minimum_score:
                continue
            rank_score = base_score + _context_bonus(words, start, field)
            ranked.append((rank_score, base_score, start, end, method, candidate))

    if not ranked:
        return None
    _, score, start, end, method, candidate = max(
        ranked,
        key=lambda item: (item[0], item[1], -(item[3] - item[2]), item[2]),
    )
    return Alignment(field, start, end, score, method, target, candidate)


def align_entities(
    words: Sequence[str],
    entities: Mapping[str, Any] | None,
    fields: Sequence[str] = ("date", "total"),
) -> dict[str, Alignment | None]:
    values = entities if isinstance(entities, Mapping) else {}
    return {field: align_entity(words, field, values.get(field)) for field in fields}


def bio_labels(
    words: Sequence[str],
    entities: Mapping[str, Any] | None,
    field_map: Mapping[str, str],
) -> tuple[list[str], dict[str, Alignment | None]]:
    """Return BIO labels plus auditable span matches."""

    labels = ["O"] * len(words)
    alignments = align_entities(words, entities, tuple(field_map))
    occupied: set[int] = set()
    for field, label_name in field_map.items():
        match = alignments[field]
        if match is None or any(index in occupied for index in range(match.start, match.end)):
            continue
        labels[match.start] = f"B-{label_name}"
        for index in range(match.start + 1, match.end):
            labels[index] = f"I-{label_name}"
        occupied.update(range(match.start, match.end))
    return labels, alignments

