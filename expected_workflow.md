# Expected Workflow

This file shows practical examples of how someone can use this MCP server from a local LLM setup.

## Example 1: Safe Edit with Dry Run + Approval

Use this when you want confidence before changing code.

### Situation
You want to rename a value in one line, but only if the exact match exists.

### Typical local setup flow
1. Start the MCP server (pointed at your project folder).
2. Ask your LLM assistant to run `edit_file_lines` with `dryRun: true`.
3. Review the returned diff.
4. If correct, ask your assistant to run `approve_edit` with the returned `stateId`.

### Example tool call (dry run)
```json
{
  "p": "src/components/App.tsx",
  "e": [
    {
      "startLine": 2,
      "endLine": 2,
      "content": "\"green\"",
      "strMatch": "\"blue\""
    }
  ],
  "dryRun": true
}
```

### What to expect
- You get a unified diff.
- You get a `State ID`.
- No file is changed yet.

Then approve:
```json
{
  "stateId": "<state-id-from-dry-run>"
}
```

---

## Example 2: Search First, Then Targeted Regex Edit

Use this when you need to find exact locations before updating structured text.

### Situation
You want to find all places where a config key appears, then update one match safely.

### Typical local setup flow
1. Ask your LLM assistant to run `search_file` for text or regex.
2. Inspect returned line numbers and context.
3. Ask it to run `edit_file_lines` against the specific line range using `regexMatch`.
4. Use dry run + approval when edits are risky.

### Example search call
```json
{
  "path": "src/config/settings.ts",
  "pattern": "timeout",
  "type": "text",
  "caseSensitive": false,
  "contextLines": 2,
  "maxMatches": 20,
  "wholeWord": true,
  "multiline": false
}
```

### Example targeted edit call
```json
{
  "p": "src/config/settings.ts",
  "e": [
    {
      "startLine": 18,
      "endLine": 18,
      "content": "15000",
      "regexMatch": "(?<=timeout:\\s)\\d+"
    }
  ],
  "dryRun": true
}
```

### What to expect
- `search_file` returns line/column + context so the LLM can edit precisely.
- `edit_file_lines` updates only the matched segment, not the whole line.
- You can approve only after validating diff output.

---

## Notes for Local LLM Usage

- Keep the MCP server restricted to allowed directories only.
- Prefer `dryRun: true` for non-trivial edits.
- Use `get_file_lines` before editing if line numbers may have shifted.
- If an edit fails because no match is found, run `search_file` again and refine the pattern.
