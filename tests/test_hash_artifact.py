from pathlib import Path

from scripts.hash_artifact import file_hash, tree_hash


def test_artifact_hash_is_deterministic_and_detects_content_change(tmp_path: Path):
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    first = artifact / "a.txt"
    second = artifact / "nested" / "b.txt"
    second.parent.mkdir()
    first.write_text("one", encoding="utf-8")
    second.write_text("two", encoding="utf-8")

    before = tree_hash(artifact)
    assert before == tree_hash(artifact)
    assert file_hash(first) != file_hash(second)

    second.write_text("changed", encoding="utf-8")
    assert tree_hash(artifact) != before
