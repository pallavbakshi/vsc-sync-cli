# Layer Precedence & Conflict Resolution

VSC Sync CLI has two distinct layer systems for maximum flexibility:

1. **Standard Layer System** (traditional) - for `--stack` flags
2. **Custom Layer System** (new) - for `--layer0`, `--layer1`, etc. and `--preset` flags

This page explains how both systems handle precedence and conflict resolution.

---

## Standard Layer System (Traditional)

### Precedence Order
```
base   ← lowest priority
app
stack(s)  ← highest priority (last one wins if multiple)
```

1. **base/** – settings/snippets/extensions that apply everywhere
2. **apps/<alias>/** – overrides specific to the running editor (VSCode, Cursor, etc.)
3. **stacks/<name>/** – language/framework-specific tweaks (python, web-dev, etc.)

Multiple stacks are applied in command-line order:
```bash
vsc-sync apply vscode --settings --stack python --stack web
# Order: base → app → python → web (web wins conflicts)
```

### Projects
`projects/<repo-name>/` layers sit outside automatic merge - they're copied verbatim into workspace folders rather than global user profiles.

---

## Custom Layer System (Enhanced)

### Explicit Layer Ordering
The custom layer system gives you complete control over layer ordering:

```bash
vsc-sync apply vscode --settings \
  --layer0 base \       # Applied first (lowest priority)
  --layer1 python \     # Applied second
  --layer2 vscode \     # Applied third  
  --layer3 personal     # Applied last (highest priority)
```

### Layer Presets
Presets are resolved to explicit layer ordering:
```bash
# config.toml: python-dev = ["base", "python", "personal"]
vsc-sync apply vscode --settings --preset python-dev

# Equivalent to:
vsc-sync apply vscode --settings \
  --layer0 base --layer1 python --layer2 personal
```

---

## Configuration File Merging

### Settings.json (Deep Merge)
Settings are deeply merged across all layers. The merge algorithm in `vsc_sync/core/config_manager.py` handles conflicts:

• **Duplicate keys**: Later layer value replaces earlier layer value
• **Nested objects**: Merged recursively (only conflicting subtrees replaced)
• **Arrays**: Concatenated and deduplicated

#### Example: Settings Merge
```json
// base/settings.json
{
  "editor.tabSize": 2,
  "editor.fontSize": 12,
  "python.linting": {
    "enabled": true,
    "pylintEnabled": false
  }
}

// python/settings.json  
{
  "editor.tabSize": 4,
  "python.linting": {
    "pylintEnabled": true,
    "flake8Enabled": true
  }
}

// Result after merge:
{
  "editor.tabSize": 4,           // python layer wins
  "editor.fontSize": 12,         // from base layer
  "python.linting": {
    "enabled": true,             // from base layer
    "pylintEnabled": true,       // python layer wins
    "flake8Enabled": true        // from python layer
  }
}
```

---

## Keybindings Behavior (CHANGED)

**🎯 Major Change**: Keybindings now merge from all layers instead of using "last layer wins".

### New Behavior: Merge All Layers
```bash
vsc-sync apply vscode --keybindings --layer0 base --layer1 python --layer2 personal
```

**Result**: Keybindings from all layers are combined:
```json
[
  // All keybindings from base/keybindings.json
  {"key": "ctrl+shift+p", "command": "workbench.action.showCommands"},
  
  // All keybindings from python/keybindings.json  
  {"key": "f5", "command": "python.debugCurrentFile"},
  
  // All keybindings from personal/keybindings.json
  {"key": "ctrl+`", "command": "workbench.action.terminal.toggle"}
]
```

### Why We Changed This
1. **More Intuitive**: Users expect layers to combine, not override
2. **Better Composability**: Build complex keybinding sets from simple layers
3. **Preserves User Intent**: Each layer's keybindings are preserved
4. **Easier Management**: Edit keybindings in focused, single-purpose layers

### Conflict Resolution
If multiple layers define the same keystroke, **all entries are preserved**. VSCode's own conflict resolution determines which one takes effect (last entry in array wins).

### Migration from Old Behavior
**Old way** (single authoritative file):
```bash
# Only one keybindings.json would be used
vsc-sync apply vscode --keybindings --stack python --stack web
```

**New way** (all layers combined):
```bash
# All keybindings.json files are merged
vsc-sync apply vscode --keybindings --layer0 base --layer1 python --layer2 web
```

---

## Extensions & Snippets

### Extensions.json (List Concatenation)
Extensions from all layers are combined and deduplicated:
```json
// base/extensions.json: ["ms-python.python"]
// web/extensions.json: ["esbenp.prettier-vscode", "ms-python.python"]
// Result: ["ms-python.python", "esbenp.prettier-vscode"]
```

### Snippets (Directory Union)
Snippet directories from all layers are combined:
```
base/snippets/global.json       → copied
python/snippets/python.json    → copied  
web/snippets/javascript.json   → copied
```

---

## Conflict Resolution Examples

### Settings Conflicts
```bash
vsc-sync apply vscode --settings \
  --layer0 base \      # "editor.tabSize": 2
  --layer1 python \    # "editor.tabSize": 4  
  --layer2 personal    # "editor.fontSize": 16

# Result: tabSize=4 (python wins), fontSize=16 (personal only)
```

### Keybinding Conflicts
```bash
vsc-sync apply vscode --keybindings \
  --layer0 base \      # [{"key": "f5", "command": "workbench.action.debug.start"}]
  --layer1 python      # [{"key": "f5", "command": "python.debugCurrentFile"}]

# Result: Both entries preserved, python wins due to array order
```

### Extension Conflicts
```bash
vsc-sync apply vscode --extensions \
  --layer0 base \      # ["ms-python.python", "ms-vscode.vscode-json"]
  --layer1 python      # ["ms-python.python", "ms-python.pylint"]

# Result: ["ms-python.python", "ms-vscode.vscode-json", "ms-python.pylint"]
# (duplicates removed automatically)
```

---

## Best Practices

### Layer Organization
1. **Keep base minimal**: Essential settings that apply everywhere
2. **Use focused layers**: Each layer should have a clear, single purpose  
3. **Order by specificity**: General → specific → personal
4. **Document conflicts**: Use `--dry-run` to preview merges

### Keybinding Management
1. **Avoid duplicate keys across layers**: Prevents conflicts
2. **Use layer-specific prefixes**: e.g., python layer uses `ctrl+p` prefix
3. **Sort for clarity**: Use `vsc-sync edit --keybindings --sort` to organize
4. **Test combinations**: Preview with `--dry-run` before applying

### Debugging Conflicts
```bash
# Preview what will be merged
vsc-sync apply vscode --all --preset python-dev --dry-run

# Check individual layers
vsc-sync edit base --settings
vsc-sync edit stack python --settings

# Sort keybindings to spot conflicts
vsc-sync edit base --keybindings --sort --yes
```

---

## Layer Resolution Priority

When using custom layers, resolution follows this priority:

1. **Intelligent name resolution**: Search in vscode-configs directories
2. **TOML alias resolution**: Match against config.toml aliases  
3. **Literal path resolution**: Treat as file/directory path

```bash
# These all work:
--layer0 base           # Found in ~/vscode-configs/base/
--layer1 python         # Found in ~/vscode-configs/stacks/python/
--layer2 personal       # Alias from config.toml
--layer3 /custom/path   # Literal path
```

---

## Mental Model

> **Standard layers**: Automatic precedence (base → app → stacks)
> **Custom layers**: Explicit precedence (--layer0 → --layer1 → --layer2...)
> **All systems**: Later layers win conflicts, keybindings merge instead of override

Understanding these precedence rules helps you design layer structures that behave predictably and meet your specific configuration needs.

---

## Handy Tips

### Sort Keybindings for Conflict Detection
```bash
vsc-sync edit base --keybindings --sort --yes
```
Creates alphabetized keybindings grouped by key and `when` clause, making conflicts easy to spot.

### Preview Merges
```bash
vsc-sync apply vscode --all --preset python-dev --dry-run
```
Shows exactly what would be applied without making changes.

### Check Layer Resolution
```bash
vsc-sync config --show  # Verify your vscode_configs_path and aliases
```

## Take-away

> When two layers disagree, ask “which one is applied last?” — that layer wins.

Keeping this mental model in mind makes it easy to reason about the final
configuration, even with many stacks and editor variants in play.

## Handy tip – sort your keybindings

Run:

```bash
vsc-sync edit base --keybindings --sort --yes
```

to get an alphabetised `keybindings.json` grouped by key and `when` clause so
you can quickly spot overlaps or conflicts.  The command keeps *all* entries –
even exact duplicates – because sometimes two identical shortcuts are
deliberately defined in different extensions or contexts.

Entries starting with a leading dash (`-`) naturally appear near the top
because `-` sorts before letters in ASCII, making it easy to inspect chord
prefixes (`-ctrl+k`, `-ctrl+w`, …).
