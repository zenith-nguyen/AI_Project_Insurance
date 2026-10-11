"""Metrics shared by document baseline notebooks and reports."""
from __future__ import annotations

from collections import Counter
from typing import Iterable


def edit_distance(left: list[str], right: list[str]) -> int:
    previous = list(range(len(right) + 1))
    for row, left_item in enumerate(left, start=1):
        current = [row]
        for column, right_item in enumerate(right, start=1):
            current.append(min(current[-1] + 1, previous[column] + 1, previous[column - 1] + (left_item != right_item)))
        previous = current
    return previous[-1]


def character_error_rate(references: Iterable[str], predictions: Iterable[str]) -> float:
    edits = total = 0
    for reference, prediction in zip(references, predictions, strict=True):
        ref = list(reference)
        edits += edit_distance(ref, list(prediction))
        total += len(ref)
    return edits / total if total else 0.0


def word_error_rate(references: Iterable[str], predictions: Iterable[str]) -> float:
    edits = total = 0
    for reference, prediction in zip(references, predictions, strict=True):
        ref = reference.split()
        edits += edit_distance(ref, prediction.split())
        total += len(ref)
    return edits / total if total else 0.0


def field_micro_scores(expected: Iterable[tuple[str, str]], predicted: Iterable[tuple[str, str]]) -> dict[str, float]:
    expected_counts = Counter(expected)
    predicted_counts = Counter(predicted)
    true_positive = sum((expected_counts & predicted_counts).values())
    false_positive = sum(predicted_counts.values()) - true_positive
    false_negative = sum(expected_counts.values()) - true_positive
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}
