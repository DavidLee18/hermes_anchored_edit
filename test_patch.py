"""Tests for the patch tools — anchoring, atomicity, offset-shift, overlap."""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hermes_anchored_edit.patch import smart_patch, smart_patch_batch  # noqa: E402


def _mk(content):
    f = tempfile.NamedTemporaryFile("w", suffix=".rs", delete=False)
    f.write(content)
    f.close()
    return f.name


SRC = 'use anyhow::{Context, Result};\n\nfn greet(name: &str) -> String {\n    format!("Hello, {}!", name)\n}\n'


def test_single_exact_multiline():
    f = _mk(SRC)
    r = json.loads(smart_patch({"path": f, "find": 'fn greet(name: &str) -> String {\n    format!("Hello, {}!", name)\n}',
                                "replace": 'fn greet(n: &str) -> String {\n    format!("Hi", n)\n}'}))
    assert r["success"]
    os.unlink(f)


def test_single_escape_tolerant():
    f = _mk(SRC)
    # find uses backslash-escaped quotes the file does not literally contain
    r = json.loads(smart_patch({"path": f, "find": 'format!(\\"Hello, {}!\\", name)',
                                "replace": 'format!("Hey", name)'}))
    assert r["success"], r
    os.unlink(f)


def test_single_indent_tolerant():
    f = _mk(SRC)
    r = json.loads(smart_patch({"path": f, "find": 'format!("Hello, {}!", name)',
                                "replace": 'format!("Yo", name)'}))
    assert r["success"]
    assert "Yo" in open(f).read()
    os.unlink(f)


def test_single_ambiguous_rejected():
    f = _mk("let x = 1;\nlet x = 1;\n")
    r = json.loads(smart_patch({"path": f, "find": "let x = 1;", "replace": "let x = 2;"}))
    assert not r["success"] and "MORE THAN ONCE" in r["error"]
    os.unlink(f)


def test_single_missing_field():
    f = _mk(SRC)
    r = json.loads(smart_patch({"path": f, "find": "x"}))
    assert not r["success"] and "replace required" in r["error"]
    os.unlink(f)


def test_batch_offset_shift():
    f = _mk("let a = 1;\nlet b = 2;\nlet c = 3;\n")
    r = json.loads(smart_patch_batch({"edits": [
        {"path": f, "find": "let a = 1;", "replace": "let alpha = 100000;"},
        {"path": f, "find": "let c = 3;", "replace": "let gamma = 3;"},
    ]}))
    out = open(f).read()
    assert r["success"]
    assert "let alpha = 100000;" in out and "let gamma = 3;" in out and "let b = 2;" in out
    os.unlink(f)


def test_batch_atomic_abort_leaves_file_untouched():
    f = _mk("let a = 1;\nlet b = 2;\n")
    before = open(f).read()
    r = json.loads(smart_patch_batch({"edits": [
        {"path": f, "find": "let a = 1;", "replace": "CHANGED"},
        {"path": f, "find": "does not exist", "replace": "x"},
    ]}))
    assert not r["success"]
    assert open(f).read() == before  # nothing written
    assert any(e.get("index") == 1 for e in r["failed"])
    os.unlink(f)


def test_batch_overlap_rejected():
    f = _mk("foobar baz\n")
    r = json.loads(smart_patch_batch({"edits": [
        {"path": f, "find": "foobar", "replace": "X"},
        {"path": f, "find": "foobar baz", "replace": "Y"},
    ]}))
    assert not r["success"]
    assert any("overlap" in e.get("error", "") for e in r["failed"])
    os.unlink(f)


def test_batch_multi_file():
    fa, fb = _mk("alpha\n"), _mk("beta\n")
    r = json.loads(smart_patch_batch({"edits": [
        {"path": fa, "find": "alpha", "replace": "ALPHA"},
        {"path": fb, "find": "beta", "replace": "BETA"},
    ]}))
    assert r["success"]
    assert open(fa).read().strip() == "ALPHA" and open(fb).read().strip() == "BETA"
    os.unlink(fa); os.unlink(fb)


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
