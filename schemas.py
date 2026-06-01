"""LLM-facing schemas for the patch tools. Flat, minimal, all-required fields."""

SMART_PATCH = {
    "name": "smart_patch",
    "description": (
        "Replace an exact snippet of text in a file with new text. Use this for ALL "
        "single code edits instead of other patch tools. It locates `find` using "
        "whitespace- and escape-tolerant matching, so you do NOT need to reproduce "
        "indentation or escaping byte-for-byte. ALWAYS provide all three fields: `path`, "
        "`find` (a unique snippet currently in the file — several lines is best for "
        "uniqueness), and `replace` (the new text; empty string deletes). If `find` is "
        "not unique or not found, the tool returns a clear error with candidate locations "
        "— read it and adjust `find`, do not repeat the same call."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file to edit."},
            "find": {"type": "string", "description": "Existing text to replace; provide enough lines to be unique."},
            "replace": {"type": "string", "description": "Replacement text ('' deletes the matched region)."},
        },
        "required": ["path", "find", "replace"],
    },
}

SMART_PATCH_BATCH = {
    "name": "smart_patch_batch",
    "description": (
        "Apply MANY edits in ONE call — use whenever you have two or more edits (across one "
        "or several files) instead of calling smart_patch repeatedly. Atomic: if ANY edit "
        "fails to locate uniquely, NONE are applied and you get a per-edit error report; fix "
        "the listed ones and resend the whole batch. Provide `edits` as a list of objects, "
        "each {path, find, replace}, with the same rules as smart_patch. Batching is faster "
        "and cheaper than many single calls and is strongly preferred for multi-edit work."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "edits": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File to edit."},
                        "find": {"type": "string", "description": "Unique existing snippet to replace."},
                        "replace": {"type": "string", "description": "Replacement ('' deletes)."},
                    },
                    "required": ["path", "find", "replace"],
                },
                "description": "List of edits to apply atomically.",
            }
        },
        "required": ["edits"],
    },
}
