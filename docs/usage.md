# Usage

After [installing](installation.md) the CLI there are six high-level commands you’ll use regularly.

| Command | Purpose |
|---------|---------|
| `init`  | Bootstrap a fresh machine by cloning the dot-files repository |
| `status`| Show diff between local VS Code config and repository |
| `apply` | Pull remote changes **and** write them into your local VS Code profile |
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

## Advanced flags

* `--diff` – print patch instead of writing files.
* `--only <component>` – restrict operation to `extensions`, `settings`, `snippets`.
* `--force` – overwrite local changes even if conflict detected.

See `vsc-sync <command> --help` for all options.
