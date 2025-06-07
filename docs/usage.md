# Usage

After [installing](installation.md) the CLI there are six high-level commands you’ll use regularly.

| Command | Purpose |
|---------|---------|
| `init`  | Bootstrap a fresh machine by cloning the dot-files repository |
| `status`| Show diff between local VS Code config and repository |
| `apply` | Pull remote changes **and** write them into your local VS Code profile (settings, keybindings, **tasks**, snippets, extensions) |
| `edit`  | Push your current VS Code config to the repository |
| `pull`  | Pull remote repository without touching local VS Code files |
| `setup-project` | Create a per-project sync config (workspaces) |

Run any command with `-h/--help` for detailed flags, e.g.:

```bash
vsc-sync edit --dry-run --verbose
```

---

## Typical workflow

1. Set up the first machine:

   ```bash
   vsc-sync init git@github.com:pb/dotfiles-vscode.git
   ```

2. Make changes in VS Code (install extensions, tweak settings).

3. Persist those changes:

   ```bash
   vsc-sync edit -m "Enable Ruff linter"
   ```

4. On another machine:

   ```bash
   vsc-sync apply   # pulls and writes config locally
   ```

---

## Pulling changes back into the repo

`vsc-sync pull` copies configuration *from* an editor (or project) *into* your
`vscode-configs` repository layer. Existing files in the target layer are
overwritten after a confirmation prompt—use `--overwrite` to skip the prompt
if you’re scripting.

Examples

```bash
# pull settings.json only (default behaviour)
vsc-sync pull vscode --to base

# pull keybindings but leave settings.json untouched
vsc-sync pull vscodium --to base --no-settings --keybindings

# pull everything and overwrite without asking (dangerous!)
vsc-sync pull vscode --to base \
  --keybindings --extensions --snippets \
  --overwrite
```

Always inspect the diff and commit your repository after a pull so that you
can revert unintended changes.

---

## Advanced flags

* `--diff` – print patch instead of writing files.
* `--no-tasks` – skip syncing tasks.json (enabled by default).
* `--force` – overwrite local changes even if conflict detected.

### Sorting keybindings

Need a tidy, alphabetised keybindings list?

```bash
vsc-sync edit base --keybindings --sort --yes
```

The command will:
1. Remove duplicate entries (same `key` + `when` – last one wins),
2. Sort so chords starting with `-` are listed first, then everything else in
   alphabetical order,
3. Rewrite the file with 2-space indentation.

If you omit `--yes` you’ll be prompted before the file is overwritten.

### Applying selectively

By default `vsc-sync apply` writes **all** components (settings, keybindings,
extensions, snippets, tasks).  Use the additive flags below to restrict what
gets applied:

| Flag | Effect |
|------|--------|
| `--settings` | Include `settings.json`. If **no** component flag is provided, settings are included by default. |
| `--keybindings` | Include `keybindings.json`. |
| `--extensions` | Manage extensions (install and—if `--prune-extensions` is also given—uninstall). |
| `--snippets` | Copy the `snippets` directory. |
| `--tasks / --no-tasks` | Include or skip `tasks.json` (tasks are synced by default). |

Examples

```bash
# Only apply keybindings.json (nothing else will be touched)
vsc-sync apply vscode --keybindings

# Apply settings and extensions, leave snippets & keybindings untouched
vsc-sync apply vscode --settings --extensions --no-tasks
```

If none of the component flags are specified, the command behaves as before
and syncs everything.

See `vsc-sync <command> --help` for all options.
