from scripts.inspect_cardd import annotation_summary, sample_records


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
