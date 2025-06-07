# VSC Sync CLI

Synchronise your VS Code settings, extensions and snippets across multiple workstations with a single command-line tool.

---

## Key features

* **One-command bootstrap** – `vsc-sync init`
* Cross-platform secrets storage (Keychain, Credential Manager, Gnome Keyring)
* Handles settings.json, keybindings, user snippets and more
* Dry-run / diff mode so nothing ever clobbers your local setup by accident

---

## What is it?

`vsc-sync` is a lightweight wrapper around Git that stores your personal VS Code configuration in a private repository.  Unlike Settings Sync it works completely offline, integrates with existing dot-files, and can be fully automated inside CI scripts or bootstrap shells.

```bash
$ vsc-sync status
✔ settings.json         in sync
✔ extensions            in sync
✘ snippets/python.json  local has changes
```

## Quick links

* [Installation](installation.md) – clone & editable install
* [Usage](usage.md) – day-to-day commands
* [API reference](reference/vsc_sync.md) – Python import-level docs

Need help? Open an issue or chat with us on the `#vsc-sync` Discord channel!
