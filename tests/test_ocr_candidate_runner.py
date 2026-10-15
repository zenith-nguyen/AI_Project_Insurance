import argparse
import json

import pytest

from scripts.run_vietnamese_ocr_candidate import _metadata_path, _prepare_run, _read_completed
from src.document.ocr_benchmark import sha256_file


def _args(tmp_path, *, resume=False, force=False, profile="robust"):
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text("{}\n", encoding="utf-8")
    return argparse.Namespace(
        manifest=manifest,
        output=tmp_path / "predictions.jsonl",
        lang="vi",
        profile=profile,
        max_side=None,
        resume=resume,
        force=force,
    )


def test_new_candidate_run_writes_locked_metadata(tmp_path):
    args = _args(tmp_path)
    contract, completed = _prepare_run(args)
    metadata = json.loads(_metadata_path(args.output).read_text(encoding="utf-8"))
    assert completed == set()
    assert metadata["manifest_sha256"] == sha256_file(args.manifest)
    assert contract["profile"] == "robust"


def test_resume_rejects_configuration_change(tmp_path):
    initial = _args(tmp_path)
    _prepare_run(initial)
    initial.output.write_text(json.dumps({"sample_id": "A", "predicted_text": "x"}) + "\n", encoding="utf-8")
    changed = _args(tmp_path, resume=True, profile="fast_upright")
    with pytest.raises(ValueError, match="profile changed"):
        _prepare_run(changed)


def test_resume_reads_completed_rows(tmp_path):
    args = _args(tmp_path)
    _prepare_run(args)
    args.output.write_text(
        json.dumps({"sample_id": "A", "predicted_text": "x"}) + "\n"
        + json.dumps({"sample_id": "B", "predicted_text": "y"}) + "\n",
        encoding="utf-8",
    )
    resumed = _args(tmp_path, resume=True)
    _, completed = _prepare_run(resumed)
    assert completed == {"A", "B"}
    assert _read_completed(args.output) == {"A", "B"}


def test_existing_output_requires_explicit_resume_or_force(tmp_path):
    args = _args(tmp_path)
    args.output.write_text("", encoding="utf-8")
    with pytest.raises(FileExistsError):
        _prepare_run(args)
