# VSC Sync CLI

Synchronize your VSCode-like configurations across multiple editors (VSCode, Cursor, Windsurf, VSCodium, etc.) with intelligent layer management and a powerful command-line interface.

---

## ✨ Key Features

* **🚀 Enhanced One-Command Setup** – `vsc-sync init` with guided TOML configuration
* **🧠 Intelligent Layer Resolution** – Use simple names like `base`, `python`, `vscode` instead of full paths
* **🎯 Opt-In Component Control** – Apply only what you specify: `--settings`, `--keybindings`, `--extensions`
* **🔄 Custom Layer System** – Stack layers in order with `--layer base --layer python --layer personal`
* **📦 Layer Presets** – Common workflows in a single `--preset` flag
* **💾 Local Extension Fallback** – Auto-install from `~/Documents/vscode-extension/` when marketplace fails
* **🔗 Smart Keybinding Merging** – Combine keybindings from all layers instead of overwriting
* **⚡ Multi-Editor Support** – Works with VSCode, Cursor, Windsurf, VSCodium, Void, PearAI
* **🛡️ Safe by Design** – Opt-in components, backup before changes, dry-run mode

---

## 🎮 What's New

### Opt-In Architecture
No more accidental changes! Specify exactly what you want to sync:
```bash
# Only apply settings and keybindings
vsc-sync apply vscode --settings --keybindings

# Apply everything
vsc-sync apply cursor --all

# Config files only (settings + keybindings + tasks)
vsc-sync apply windsurf --config
```

### Intelligent Layer Resolution
Use simple names that automatically resolve to the right paths:
```bash
# Before: Full paths required
vsc-sync apply vscode --settings \
  --layer ~/vscode-configs/base \
  --layer ~/vscode-configs/stacks/python

# Now: Simple names work
vsc-sync apply vscode --settings \
  --layer base \
  --layer python
```

### Layer Presets for Common Workflows
```bash
# Define once in config.toml
python-dev = ["base", "python", "personal"]

# Use everywhere
vsc-sync apply vscode --all --preset python-dev
```

---

## 🛠️ What is it?

`vsc-sync` is a sophisticated configuration management tool built around Git that:

- **Stores configurations in layers** (base → app → stack → project)
- **Works completely offline** - no cloud dependency
- **Supports multiple editors** - not just VSCode
- **Provides intelligent merging** - especially for keybindings
- **Offers flexible layer combinations** - mix and match as needed
- **Includes robust extension management** - with local fallback support

```bash
$ vsc-sync status
✔ settings.json         in sync (3 layers applied)
✔ extensions            in sync (12 installed)
✔ keybindings.json      in sync (merged from 2 layers)
✘ snippets/python.json  local has changes
```

---

## 🚀 Quick Start

1. **Initialize with guided setup**:
   ```bash
   vsc-sync init --repo ~/vscode-configs
   # Follow the interactive prompts for complete setup
   ```

2. **Apply configurations selectively**:
   ```bash
   # Start simple
   vsc-sync apply vscode --settings --keybindings
   
   # Use layer presets for complex setups
   vsc-sync apply cursor --all --preset python-dev
   ```

3. **Manage your configuration**:
   ```bash
   # View current setup
   vsc-sync config --show
   
   # Edit layer aliases and presets
   vsc-sync config --edit
   ```

---

## 📚 Documentation

### Getting Started
* [Installation](installation.md) – Setup and requirements
* [Quick Start](tutorials/quick-start.md) – Get running in 5 minutes
* [Usage Guide](usage.md) – Day-to-day commands and workflows

### Advanced Features
* [Advanced Usage](advanced-usage.md) – Layer system, presets, and custom workflows
* [Configuration](configuration.md) – TOML config and intelligent resolution
* [Template Config](template-config.md) – Setting up your vscode-configs repository

### Reference
* [Layer Precedence](behind-the-scenes/layer-precedence.md) – How layers merge and override
* [How It Works](how-it-works.md) – Architecture and design principles
* [API Reference](reference/vsc_sync.md) – Python module documentation

---

## 💡 Common Use Cases

**Python Developer**:
```bash
vsc-sync apply vscode --all --preset python-dev
```

**Web Developer with TypeScript**:
```bash
vsc-sync apply cursor --config \
  --layer base --layer web --layer typescript
```

**Extension Management**:
```bash
# Add missing extensions only
vsc-sync apply vscode --extensions

# Remove extra extensions not in config
vsc-sync apply vscode --extensions --remove-extra

# Fresh install (remove all, reinstall from config)
vsc-sync apply vscode --extensions --replace-all
```

**Multi-Editor Workflow**:
```bash
# Same config across different editors
vsc-sync apply vscode --all --preset web-dev
vsc-sync apply cursor --all --preset web-dev
vsc-sync apply windsurf --all --preset web-dev
```

Need help? Check our [Usage Guide](usage.md) or open an issue on GitHub!
