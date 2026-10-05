import json

from scripts.inspect_cardd import annotation_summary, sample_records
from scripts.audit_cardd_alignment import audit


def test_fiftyone_detection_labels_and_format_are_discovered():
    payload = {
        "samples": [
            {
                "filepath": "data/example.jpg",
                "ground_truth": {
                    "_cls": "fiftyone.core.labels.Detections",
                    "detections": [
                        {"_cls": "fiftyone.core.labels.Detection", "label": "dent", "bounding_box": [0.1, 0.2, 0.3, 0.4]},
                        {"_cls": "fiftyone.core.labels.Detection", "label": "scratch", "mask": [[0, 1], [1, 0]]},
                    ],
                },
            }
        ]
    }
    records = sample_records(payload)
    labels, annotation_types, geometry_counts = annotation_summary(records)
    assert labels == ["dent", "scratch"]
    assert "fiftyone.core.labels.Detection" in annotation_types
    assert "fiftyone.core.labels.Detections" in annotation_types
    assert geometry_counts == {"bounding_box": 1, "mask": 1}


def test_cardd_alignment_reports_missing_and_unreferenced_images(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "present.jpg").write_bytes(b"image")
    (data / "unreferenced.jpg").write_bytes(b"image")
    payload = {
        "samples": [
            {"filepath": "data/present.jpg"},
            {"filepath": "/export/data/missing.jpg"},
            {"filepath": "data/present.jpg"},
            {},
        ]
    }
    (tmp_path / "samples.json").write_text(json.dumps(payload), encoding="utf-8")

    result = audit(tmp_path)

    assert result["sample_records"] == 4
    assert result["image_files"] == 2
    assert result["records_without_filepath"] == 1
    assert result["missing_referenced_images_first_100"] == ["missing.jpg"]
    assert result["unreferenced_downloaded_images_first_100"] == ["unreferenced.jpg"]
    assert result["duplicate_sample_references"] == {"present.jpg": 2}
    assert result["ready_for_conversion"] is False
