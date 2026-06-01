# hermes_anchored_edit

Content-anchored file tools for [Hermes Agent](https://github.com/NousResearch/hermes-agent) — robust editing and frugal reading that cut failed tool calls, round-trips, and wasted context.

Three tools, registered under the `file` toolset:

- **`smart_patch`** — replace a snippet in a file. Matching is whitespace- and escape-tolerant, so the model doesn't have to reproduce indentation or quote-escaping byte-for-byte.
- **`smart_patch_batch`** — apply many edits in one call, atomically. Validate-all-then-apply; same-file edits applied bottom-up so offsets never drift; nothing is written if any edit fails.
- **`read_relevant`** — return only the regions of a file matching a query (plus context), instead of loading the whole file into context.

## Why

These tools were built to fix three concrete failure modes observed when an LLM agent edits code through a generic patch tool:

1. **Malformed multi-mode tool calls.** Tools that overload several operations behind one name (with different required fields per mode) get called with the wrong fields. The fix here: flat, single-purpose schemas where every field is required — nothing to get wrong.
2. **Escape-drift.** A diff round-tripped through tool-call JSON can arrive with doubled escaping (`\\"` where the file has `"`), so an exact-string match silently fails and the agent loops. The fix: match on a *normalised* form (escaping and per-line whitespace ignored) to locate the span, then mutate the *original* bytes — so matching is robust but content stays exact.
3. **Whole-file reads.** Reading an entire file to change three lines wastes context (and tokens). `read_relevant` returns only the matching slices.

`smart_patch_batch` additionally collapses N single-edit round-trips into one, which is the larger token saving on multi-edit tasks.

## Credit

The editing approach — content/anchor-based edits and multi-edit batching — is **inspired by [Dirac](https://dirac.run)**, which popularised these mechanics for token-efficient coding agents. This project is an independent implementation of those ideas as a Hermes plugin; it does not use, wrap, depend on, or affiliate with Dirac.

## Install

Copy the package into your Hermes plugins directory:

```sh
cp -r hermes_anchored_edit ~/.hermes/plugins/
hermes plugins enable hermes_anchored_edit
# restart the gateway / agent to load it
```

Verify:

```sh
hermes tools list --verbose | grep -E 'smart_patch|read_relevant'
```

To steer the agent toward these tools over the built-ins, add to `SOUL.md`:

```
- For all file edits use smart_patch; for two or more edits use smart_patch_batch in one call.
- To read files, use read_relevant with a query for what you need, not whole-file reads.
```

## Tools

### smart_patch
```json
{ "path": "src/foo.rs", "find": "<unique existing snippet>", "replace": "<new text>" }
```
`replace: ""` deletes the matched region. If `find` is not unique or not found, the tool returns candidate locations — adjust and retry rather than repeating the same call.

### smart_patch_batch
```json
{ "edits": [
  { "path": "src/a.rs", "find": "...", "replace": "..." },
  { "path": "src/b.rs", "find": "...", "replace": "..." }
] }
```
Atomic: if any edit fails to locate uniquely, none are applied and a per-edit report is returned.

### read_relevant
```json
{ "path": "src/foo.rs", "query": "fn target", "context_lines": 8, "max_matches": 20 }
```
`query` is matched literally first, then as a regex. Returns matching regions with line numbers, overlapping windows merged.

## Tests

```sh
python3 tests/test_patch.py
python3 tests/test_read.py
```

The tests cover the tricky guarantees: escape/indentation tolerance, ambiguity rejection, batch atomicity (a failed batch leaves files untouched), same-file offset-shift correctness, overlap detection, and literal-vs-regex read matching.

## AI-Assisted Development

This project was built collaboratively with **Anthropic's Claude Opus 4.8**.

The AI's contribution: drafting and iterating the tool implementations (the content-anchoring matcher, the atomic batch logic, the targeted reader), writing the unit tests, and helping diagnose the editing failure modes — escape-drift, malformed multi-mode tool calls, and whole-file-read waste — that motivated the design.

The direction, architecture, and all decisions were human-led: the choice to extract these mechanics as a Hermes plugin rather than adopt another agent, the design constraints, and the naming and structure. Every change was reviewed, deployed, and tested by the author in a live environment; bugs surfaced during that testing were fed back and fixed in iteration.

In short: the human set the goals and made the judgments; the AI accelerated the implementation and testing under that direction.

## License

MIT — see [LICENSE](LICENSE).
