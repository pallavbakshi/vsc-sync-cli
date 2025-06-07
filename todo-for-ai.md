# TODO – keybindings sorting feature

Goal
----
Add an option to sort `keybindings.json` when editing it via the *edit* command:

```
vsc-sync edit <layer-type> [layer-name] --file-type keybindings --sort
```

Behaviour
1. Operates **only** on the file specified by the CLI invocation (no bulk sort).
2. Sort algorithm
   • Primary key: if the "key" string starts with `-`, it precedes non-dash keys.
   • Then case-insensitive alphabetical order of the "key" value.
3. Duplicate handling
   • If two objects have identical `key` *and* `when` values, keep **the last
     one in the original array** (mirrors VS Code runtime behaviour).
   • Emit a Rich console warning listing discarded duplicates.
4. The file is completely rewritten with pretty-printed 2-space indentation.
5. Before writing, print a confirmation message: “This will overwrite
   keybindings.json. Make sure you have a backup if needed.”; proceed only on
   user confirmation (Yes/No prompt).  Skipped when `--yes` flag is supplied.

Checklist
---------

- [ ] **Design / CLI plumbing**
  - [X] Extend `edit` command with a `--sort` boolean flag and `--yes` for confirmation.

- [ ] **Sorting implementation** (`src/vsc_sync/commands/edit_cmd.py`)
  - [X] Sorting/deduplication implemented with confirmation prompt.

- [ ] **Unit tests**
  - [X] Sorting order & duplicate logic.

- [ ] **CLI integration tests**
  - [ ] Typer integration test (optional).

- [ ] **Documentation**
  - [X] usage.md updated.
  - [X] layer-precedence tip.
