"""Shared content-anchoring logic used by both the patch and read tools.

The core idea (inspired by Dirac's content-anchored editing): locate a snippet
in a file by its NORMALISED content rather than by exact byte match or line
number. Normalisation undoes JSON escape-drift and ignores per-line whitespace,
so an edit or read anchors correctly even when the model's quoting or
indentation differs from the file. The actual file mutation always uses the
ORIGINAL bytes of the matched span, so normalisation never corrupts content.
"""


def normalise(text: str) -> str:
    """Canonical form for tolerant matching.

    - iteratively undo double-escaping artefacts ('\\"' -> '"', '\\\\' -> '\\')
    - strip leading/trailing whitespace per line
    - drop blank lines
    Used ONLY to locate spans; never to write.
    """
    prev = None
    while prev != text:
        prev = text
        text = text.replace('\\"', '"').replace("\\\\", "\\")
    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln != ""]
    return "\n".join(lines)


def find_span(haystack: str, needle: str):
    """Locate needle in haystack.

    Returns:
        (start, end)  char offsets of a unique match
        None          no match
        "AMBIGUOUS"   more than one match
    Tries exact match first (fast path), then a whitespace/escape-tolerant
    window scan that accounts for blank-line-dropping in normalisation.
    """
    idx = haystack.find(needle)
    if idx != -1 and haystack.find(needle, idx + 1) == -1:
        return (idx, idx + len(needle))

    hay_lines = haystack.split("\n")
    norm_needle = normalise(needle)
    if norm_needle == "":
        return None
    needle_norm_lines = len(norm_needle.split("\n"))

    offsets = []
    pos = 0
    for ln in hay_lines:
        offsets.append(pos)
        pos += len(ln) + 1

    matches = []
    n = len(hay_lines)
    for i in range(n):
        non_blank = 0
        j = i
        while j < n and non_blank < needle_norm_lines:
            if hay_lines[j].strip() != "":
                non_blank += 1
            j += 1
        if non_blank < needle_norm_lines:
            break
        window = "\n".join(hay_lines[i:j])
        if normalise(window) == norm_needle:
            start = offsets[i]
            end = offsets[j - 1] + len(hay_lines[j - 1])
            matches.append((start, end))

    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return "AMBIGUOUS"
    return None


def candidates(haystack: str, needle: str, k: int = 3):
    """Best-effort location hints when a match fails or is ambiguous."""
    first = normalise(needle).split("\n")[0][:60]
    hints = []
    for n, line in enumerate(haystack.split("\n"), 1):
        if first and first[:20] in normalise(line):
            hints.append(f"  line {n}: {line.strip()[:80]}")
            if len(hints) >= k:
                break
    return hints
