# Template configuration repository

Below is a **fully-featured example** of how you can organise your VS Code
configuration repository when using **VSC Sync CLI**.  Feel free to clone this
layout and trim whatever you don’t need – the tool works fine with only the
`base/` directory if that’s all you care about.

```text
.
├── base/                 # Settings & snippets applied everywhere
│   ├── settings.json
│   ├── keybindings.json
│   ├── extensions.json
│   ├── tasks.json
│   └── snippets/
│       └── global.code-snippets
│
├── stacks/               # Language-specific overlays (Python, JS, Go…)
│   ├── python/
│   │   ├── settings.json
│   │   ├── keybindings.json
│   │   ├── extensions.json
│   │   ├── tasks.json
│   │   └── snippets/python.code-snippets
│   └── javascript/
│       ├── settings.json
│       ├── extensions.json
│       └── snippets/javascript.code-snippets
│
├── apps/                 # Editor-flavoured overrides (VS Code, VSCodium…)
│   ├── vscode/
│   │   ├── settings.json
│   │   ├── keybindings.json
│   │   └── extensions.json
│   │   └── tasks.json
│   └── vscodium/
│       ├── settings.json
│       └── extensions.json
│
├── projects/             # Per-project configs (workspaceSettingsPath)
│   ├── react-app/
│   │   ├── settings.json
│   │   └── extensions.json
│   └── generic-python-api/
│       ├── settings.json
│       └── extensions.json
│
└── README.md             # Explain how to consume the repo
```

## How merging works

`vsc-sync apply` assembles the final configuration for a machine in four steps:

1. Start with **base/** files.
2. Overlay the relevant **stacks/** directory if `--stack` is provided
   (e.g. `python`).
3. Overlay the **apps/** directory that matches the running editor
   (auto-detected or via `--app vscodium`).
4. If inside a repo that has a matching directory under **projects/**, those
   files win last.

Each overlay can override or extend keys.  Lists (like extensions) are merged
uniquely so duplicates are removed.

`tasks.json` follows the same *winner-takes-all* rule as `keybindings.json` –
only the file from the highest-priority layer is copied.


