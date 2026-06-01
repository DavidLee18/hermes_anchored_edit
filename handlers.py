"""Single and atomic-batch file editing, anchored on content.

smart_patch        — replace one snippet, tolerant of whitespace/escape drift.
smart_patch_batch  — apply many edits in one call, atomically (validate-all-
                     then-apply), with same-file edits applied bottom-up so
                     offset shifts never corrupt later edits.

Handlers always return a JSON string and never raise.
"""

import json
import os

from ..common import normalise, find_span, candidates


def smart_patch(args: dict, **kwargs) -> str:
    path = (args.get("path") or "").strip()
    find = args.get("find")
    replace = args.get("replace")

    if not path:
        return json.dumps({"success": False, "error": "path required: provide the file to edit."})
    if find is None:
        return json.dumps({"success": False, "error": "find required: provide the existing text to replace."})
    if replace is None:
        return json.dumps({"success": False, "error": "replace required: provide replacement text ('' to delete)."})
    if not os.path.isfile(path):
        return json.dumps({"success": False, "error": f"file not found: {path}"})

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return json.dumps({"success": False, "error": f"could not read {path}: {e}"})

    span = find_span(content, find)
    if span is None:
        return json.dumps({"success": False,
                           "error": "find text not located (even after whitespace/escape-tolerant match). "
                                    "Adjust `find` to match the current file.",
                           "candidates": candidates(content, find)})
    if span == "AMBIGUOUS":
        return json.dumps({"success": False,
                           "error": "find text matched MORE THAN ONCE. Add surrounding lines to make it unique.",
                           "candidates": candidates(content, find)})

    start, end = span
    new_content = content[:start] + replace + content[end:]
    if new_content == content:
        return json.dumps({"success": False, "error": "no change: replacement identical to matched text."})

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
    except Exception as e:
        return json.dumps({"success": False, "error": f"could not write {path}: {e}"})

    return json.dumps({"success": True, "path": path,
                       "replaced_chars": end - start, "new_size": len(new_content)})


def smart_patch_batch(args: dict, **kwargs) -> str:
    edits = args.get("edits")
    if not isinstance(edits, list) or not edits:
        return json.dumps({"success": False,
                           "error": "edits required: a non-empty list of {path, find, replace} objects."})

    file_cache = {}
    resolved = []
    errors = []

    for i, e in enumerate(edits):
        if not isinstance(e, dict):
            errors.append({"index": i, "error": "edit must be an object with path, find, replace."})
            continue
        path = (e.get("path") or "").strip()
        find = e.get("find")
        replace = e.get("replace")
        if not path:
            errors.append({"index": i, "error": "path required."}); continue
        if find is None:
            errors.append({"index": i, "error": "find required."}); continue
        if replace is None:
            errors.append({"index": i, "error": "replace required ('' to delete)."}); continue

        if path not in file_cache:
            if not os.path.isfile(path):
                errors.append({"index": i, "path": path, "error": "file not found."}); continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    file_cache[path] = f.read()
            except Exception as ex:
                errors.append({"index": i, "path": path, "error": f"could not read: {ex}"}); continue

        span = find_span(file_cache[path], find)
        if span is None:
            errors.append({"index": i, "path": path, "error": "find not located.",
                           "candidates": candidates(file_cache[path], find)}); continue
        if span == "AMBIGUOUS":
            errors.append({"index": i, "path": path,
                           "error": "find matched more than once; add surrounding lines.",
                           "candidates": candidates(file_cache[path], find)}); continue
        start, end = span
        resolved.append({"path": path, "start": start, "end": end, "replace": replace, "index": i})

    by_file = {}
    for r in resolved:
        by_file.setdefault(r["path"], []).append(r)
    for path, items in by_file.items():
        ordered = sorted(items, key=lambda r: r["start"])
        for a, b in zip(ordered, ordered[1:]):
            if a["end"] > b["start"]:
                errors.append({"index": b["index"], "path": path,
                               "error": f"overlaps edit index {a['index']} in the same file."})

    if errors:
        return json.dumps({"success": False,
                           "error": "batch aborted; no files written. Fix the listed edits and resend the whole batch.",
                           "failed": errors, "validated_ok": len(resolved), "total": len(edits)})

    written = []
    try:
        for path, items in by_file.items():
            content = file_cache[path]
            for r in sorted(items, key=lambda r: r["start"], reverse=True):
                content = content[: r["start"]] + r["replace"] + content[r["end"]:]
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            written.append({"path": path, "edits_applied": len(items), "new_size": len(content)})
    except Exception as ex:
        for w in written:
            try:
                with open(w["path"], "w", encoding="utf-8") as f:
                    f.write(file_cache[w["path"]])
            except Exception:
                pass
        return json.dumps({"success": False,
                           "error": f"write failed mid-batch: {ex}. Rolled back {len(written)} file(s)."})

    return json.dumps({"success": True, "files": written, "total_edits": len(resolved)})
