import base64
import io
import zlib

import numpy as np

from scripts.convert_cardd_fiftyone_to_yolo import assign_groups, decode_mask


def test_cardd_binary_mask_decodes_without_pickle():
    expected = np.array([[False, True], [True, False]], dtype=bool)
    buffer = io.BytesIO()
    np.save(buffer, expected, allow_pickle=False)
    payload = base64.b64encode(zlib.compress(buffer.getvalue())).decode("ascii")

    actual = decode_mask({"$binary": {"base64": payload, "subType": "00"}})

    assert actual.dtype == np.uint8
    assert np.array_equal(actual, expected)


def test_grouped_split_keeps_duplicate_group_together_and_near_target_sizes():
    vectors = np.tile(np.array([[1, 0], [0, 1], [1, 1]]), (100, 1))
    groups = [[0, 1, 2]] + [[index] for index in range(3, len(vectors))]

    assignments = assign_groups(groups, vectors, (0.70, 0.15, 0.15), seed=42)
    counts = {name: list(assignments.values()).count(name) for name in ("train", "val", "test")}

    assert len({assignments[index] for index in groups[0]}) == 1
    assert abs(counts["train"] - 210) <= 3
    assert abs(counts["val"] - 45) <= 3
    assert abs(counts["test"] - 45) <= 3
