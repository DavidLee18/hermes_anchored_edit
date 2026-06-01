"""Tests for read_relevant — slicing, multi-match, no-match, literal vs regex, window merge."""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hermes_anchored_edit.read import read_relevant  # noqa: E402


def _mk(content):
    f = tempfile.NamedTemporaryFile("w", suffix=".rs", delete=False)
    f.write(content)
    f.close()
    return f.name


def _big():
    lines = [f"line {i}" for i in range(200)]
    lines[50] = "fn target_function() -> Result<()> {"
    lines[51] = "    do_the_thing();"
    lines[120] = "fn another_target() {}"
    return _mk("\n".join(lines))


def test_returns_slice_not_whole_file():
    f = _big()
    r = json.loads(read_relevant({"path": f, "query": "target_function", "context_lines": 3}))
    assert r["success"] and r["matches"] == 1 and len(r["regions"]) == 1
    assert "51\t" in r["regions"][0] and "do_the_thing" in r["regions"][0]
    os.unlink(f)


def test_multiple_matches():
    f = _big()
    r = json.loads(read_relevant({"path": f, "query": "target"}))
    assert r["matches"] == 2
    os.unlink(f)


def test_no_match_clean_error():
    f = _big()
    r = json.loads(read_relevant({"path": f, "query": "nonexistent_xyz"}))
    assert not r["success"] and "no lines matched" in r["error"]
    os.unlink(f)


def test_literal_with_regex_metachars():
    f = _big()
    # contains ( ) < > — valid regex but meant literally; literal-first handles it
    r = json.loads(read_relevant({"path": f, "query": "fn target_function() -> Result<()> {"}))
    assert r["success"] and r["matches"] == 1
    os.unlink(f)


def test_regex_fallback():
    f = _big()
    r = json.loads(read_relevant({"path": f, "query": r"fn \w+_target"}))
    assert r["success"] and r["matches"] == 1
    os.unlink(f)


def test_overlapping_windows_merge():
    lines = ["x"] * 30
    lines[10] = "hit"
    lines[12] = "hit"
    f = _mk("\n".join(lines))
    r = json.loads(read_relevant({"path": f, "query": "hit", "context_lines": 5}))
    assert len(r["regions"]) == 1
    os.unlink(f)


def test_missing_query():
    f = _big()
    r = json.loads(read_relevant({"path": f}))
    assert not r["success"] and "query required" in r["error"]
    os.unlink(f)


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn(); print(f"PASS {fn.__name__}"); passed += 1
        except Exception:
            print(f"FAIL {fn.__name__}"); traceback.print_exc()
    print(f"\n{passed}/{len(fns)} passed")
