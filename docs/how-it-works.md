# How it works

`vsc-sync` is essentially a thin Python wrapper around a Git repository that knows how to translate between VS Code’s on-disk format and a portable, human-readable representation.

```none
┌──────────────┐   read   ┌────────────────┐
│ VS Code app  │ ───────▶ │    parsers     │
└──────────────┘          └──────┬─────────┘
                                 │
                                 ▼
                       ┌────────────────────┐  commit  ┌─────────────┐
                       │ dot-files repo     │ ◀──────── │ git backend │
                       └────────────────────┘           └─────────────┘
```

## Storage layout

The repository created by `vsc-sync init` looks like this:

```
.vsc-sync/
├── extensions.txt   # frozen extension list
├── settings.json    # base settings
└── snippets/
    ├── python.json
    └── javascript.json
```

All files live under a single directory so your home folder stays tidy.

## Security

No credentials ever touch disk.  Tokens are stored in your OS’s credential store using the [`keyring`](https://pypi.org/project/keyring/) library.

## Under the hood

* **File operations** – `vsc_sync.core.file_ops`
* **Git plumbing** – `vsc_sync.core.git_ops`
* **Config management** – `vsc_sync.core.config_manager`

Dive into the [API reference](reference/vsc_sync.md) if you’d like to use these building blocks programmatically.

!!! warning "Pull overwrites repository files"
    The `vsc-sync pull` command writes *into* your `vscode-configs` repository.
    Any existing files in the target layer will be replaced (after a prompt,
    unless you pass `--overwrite`).  Make sure you commit or back-up before
    pulling large changes.
