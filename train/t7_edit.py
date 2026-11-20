"""T7 weight edits as pure functions over plain lists. Never loads or downloads a model.

Matrix = list of rows (list of float). Spec = {"columns": [j, ...], "values": [[v_row0, v_row1, ...], ...]}
where values[k] is the new column for columns[k] (length = number of rows).
"""
import copy
import hashlib
import math
import struct


def checksum(w):
    h = hashlib.sha256()
    for row in w:
        h.update(struct.pack("<%dd" % len(row), *row))
    return h.hexdigest()


def apply_column_edit(w, spec, expected_base_sha256):
    """Return (edited_copy, report). Raises ValueError, before editing, unless checksum(w) equals the
    caller's recorded expected sha256 (from the download manifest). Base is never mutated."""
    before = checksum(w)
    if before != expected_base_sha256:
        raise ValueError("base sha256 mismatch: got %s, expected %s" % (before, expected_base_sha256))
    if any(len(r) != len(w[0]) for r in w):
        raise ValueError("ragged base matrix")
    cols, vals = spec["columns"], spec["values"]
    if len(cols) != len(vals):
        raise ValueError("columns and values differ in length")
    n, m = len(w), len(w[0]) if w else 0
    for j, v in zip(cols, vals):
        if not 0 <= j < m:
            raise IndexError("column %d out of range 0..%d" % (j, m - 1))
        if len(v) != n:
            raise ValueError("column %d needs %d values, got %d" % (j, n, len(v)))
    out = copy.deepcopy(w)
    for j, v in zip(cols, vals):
        for i in range(n):
            out[i][j] = v[i]
    return out, {"base_sha256": before, "edited_sha256": checksum(out),
                 "columns": list(cols), "base_verified": True}


def diff_of_means(pos, neg):
    """Unit vector mean(pos) - mean(neg) over lists of equal-length vectors (arm D direction)."""
    d = [sum(c) / len(pos) - sum(x) / len(neg) for c, x in zip(zip(*pos), zip(*neg))]
    n = math.sqrt(sum(x * x for x in d))
    if n == 0:
        raise ValueError("zero difference of means")
    return [x / n for x in d]
