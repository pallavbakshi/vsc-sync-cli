# Usage Guide

This guide covers the day-to-day commands and workflows for vsc-sync CLI after [installation](installation.md) and [initial setup](tutorials/quick-start.md).

---

## 🎯 Core Philosophy: Opt-In Control

vsc-sync uses an **opt-in approach** - you specify exactly what you want to apply. No more accidental overwrites!

```bash
# ❌ Old way: Everything by default, exclusions required
vsc-sync apply vscode --no-extensions --no-snippets

# ✅ New way: Only apply what you specify
vsc-sync apply vscode --settings --keybindings
```

---

## 📋 Command Overview

| Command | Purpose |
|---------|---------|
| `init`  | **Enhanced setup** with guided TOML configuration and intelligent layer resolution |
| `apply` | **Opt-in application** of specific components (settings, keybindings, extensions, etc.) |
| `status`| Show diff between local configuration and repository layers |
| `pull`  | Pull configurations **from** an editor **into** the repository |
| `edit`  | Open and edit layer configurations with sorting options |
| `config`| **NEW**: Manage TOML configuration (aliases, presets, defaults) |
| `setup-project` | Create per-project workspace configurations |

---

## 🚀 The Apply Command (Most Important)

The `apply` command is where vsc-sync shines. It's been completely redesigned for precision and flexibility.

### Component Selection

Specify exactly what you want to apply:

```bash
# Individual components
vsc-sync apply vscode --settings          # Only settings.json
vsc-sync apply vscode --keybindings       # Only keybindings.json  
vsc-sync apply vscode --extensions        # Only extensions
vsc-sync apply vscode --snippets          # Only snippets directory
vsc-sync apply vscode --tasks            # Only tasks.json

# Multiple components
vsc-sync apply vscode --settings --keybindings --extensions

# Convenience flags
vsc-sync apply vscode --all               # All components
vsc-sync apply vscode --config            # settings + keybindings + tasks (no extensions/snippets)
```

### Safe Preview with `--dry-run`

Unsure about the outcome?  Append `--dry-run` to **any** apply command:

```
vsc-sync apply cursor --all --layer base --layer cursor --layer python --remove-extra --dry-run
```

What you get:

* A coloured diff/preview of the final **settings.json**, **keybindings.json**,
  **tasks.json**, and which snippet files would be copied.  
* An extension summary (to-install / to-uninstall / already present).  
* **Nothing is written** – ideal for PR reviews or first-time rolls-outs.

Pair this with the interactive extension prompt for maximum safety.

### Layer System

#### Standard Layers (Traditional)
```bash
# Apply with tech stacks
vsc-sync apply vscode --settings --stack python --stack web
```

### How settings are merged  *(new)*

`settings.json` from **all** layers are _deep-merged_.  Every key that appears in
any layer ends up in the final file; when the same key exists in multiple
layers the value from the _later_ layer overrides those before it.  The final
file is written so that higher-precedence keys appear **later in the file** –
exactly how VS Code itself resolves duplicates (“last key wins”).

Keybindings are still concatenated (base first → top layer) and extensions are
union-deduplicated.

#### Custom Layers (New & Powerful)
```bash
# Explicit layer ordering with simple names
vsc-sync apply vscode --settings \
  --layer base \
  --layer python \
  --layer vscode \
  --layer personal

# Mix simple names and full paths
vsc-sync apply cursor --all \
  --layer base \
  --layer /custom/path/typescript-config
```

#### Layer Presets (Ultimate Convenience)
```bash
# Define once in config.toml
python-dev = ["base", "python", "personal"]
web-dev = ["base", "web", "vscode", "personal"]

# Use everywhere
vsc-sync apply vscode --all --preset python-dev
vsc-sync apply cursor --config --preset web-dev
```

### Extension Management

Crystal-clear extension handling with three distinct modes:

```bash
# Default: Incremental (install missing, keep existing)
vsc-sync apply vscode --extensions

# Remove extras: Install missing + remove extensions not in config
vsc-sync apply vscode --extensions --remove-extra

# Nuclear option: Remove ALL extensions, then reinstall from config
vsc-sync apply vscode --extensions --replace-all
```

**What each mode does:**

- **Default**: Safest option - only installs missing extensions
- **--remove-extra**: Cleans up unwanted extensions while keeping configured ones
- **--replace-all**: Fresh start - removes everything and reinstalls from scratch

### Local Extension Fallback

When marketplace installation fails, vsc-sync automatically searches `~/Documents/vscode-extension/` for local VSIX files:

```
~/Documents/vscode-extension/
├── ms-python.python.vsix
├── ms-python.python-2023.1.0.vsix
└── publisher.extension-1.2.3.vsix
```

Supported filename patterns:
- `publisher.extension.vsix`
- `publisher.extension-version.vsix`

**Installation Timeouts:**
- **Marketplace**: 30 seconds (download only)  
  (increased from 10 s to accommodate slower connections and large extensions)
- **Local VSIX**: 2 minutes (includes compilation and installation)

**Interactive safety prompt**  *(new in vsc-sync ≥ x.y.z)*

After showing the planned install/uninstall list vsc-sync now asks:

```
Proceed with installing/uninstalling these extensions? (Y/n)
```

• Reply **Y** (default) → extensions are managed as usual.  
• Reply **n** → extension step is skipped, while all other components
  (settings, keybindings, snippets, tasks) remain applied.  
• Use `--force` to bypass the prompt in automation/CI.

---

## 🧠 Intelligent Layer Resolution

vsc-sync automatically finds layers in your vscode-configs directory:

### Directory Structure
```
~/vscode-configs/
├── base/                   # "base" → auto-discovered
├── apps/
│   ├── vscode/            # "vscode" → auto-discovered  
│   ├── cursor/            # "cursor" → auto-discovered
│   └── windsurf/          # "windsurf" → auto-discovered
├── stacks/
│   ├── python/            # "python" → auto-discovered
│   ├── javascript/        # "javascript" → auto-discovered
│   └── web-dev/           # "web-dev" → auto-discovered
└── projects/
    ├── react-app/         # "react-app" → auto-discovered
    └── api-backend/       # "api-backend" → auto-discovered
```

### Resolution Strategy
vsc-sync uses a three-tier resolution strategy:

1. **Intelligent name resolution**: Searches standard directories
2. **Alias resolution**: Uses aliases from config.toml
3. **Literal path resolution**: Falls back to treating input as file path

```bash
# All of these work automatically:
vsc-sync apply vscode --settings --layer base           # Found in ~/vscode-configs/base/
vsc-sync apply vscode --settings --layer python         # Found in ~/vscode-configs/stacks/python/
vsc-sync apply vscode --settings --layer personal       # Alias from config.toml
vsc-sync apply vscode --settings --layer /custom/path   # Literal path
```

---

## 🔧 Configuration Management

### The Config Command

Manage your TOML configuration easily:

```bash
# View current configuration  
vsc-sync config --show

# Edit configuration in your default editor
vsc-sync config --edit

# Show config file location
vsc-sync config --path

# Initialize/recreate config.toml
vsc-sync config --init
```

### TOML Configuration Structure

Your `~/.config/vsc-sync/config.toml` contains:

```toml
# Path for intelligent layer resolution
vscode_configs_path = "~/vscode-configs"

[defaults]
components = ["settings", "keybindings", "extensions"]
backup = true
extension_mode = "add"

[layer_aliases.personal]
name = "personal"
path = "~/my-configs/personal-settings.json"
description = "Personal preference overrides"

[layer_presets]
python-dev = ["base", "python", "personal"]
web-dev = ["base", "web", "vscode", "personal"]
minimal = ["base"]
```

---

## 📊 Status and Monitoring

### Check Configuration Status
```bash
# Check all apps
vsc-sync status

# Check specific app
vsc-sync status vscode

# Check with specific stacks
vsc-sync status vscode --stack python --stack web
```

---

## 📤 Pull Command (Repository Updates)

Pull configurations **from** an editor **into** your repository:

```bash
# Pull settings.json only (default)
vsc-sync pull vscode --to base

# Pull specific components
vsc-sync pull vscode --to base --keybindings --extensions

# Pull from project .vscode directory
vsc-sync pull --from-project ./my-project --to project my-project

# Dangerous: overwrite without confirmation
vsc-sync pull vscode --to base --keybindings --extensions --overwrite
```

**⚠️ Warning**: Pull operations overwrite existing files in your repository. Always review changes and commit after pulling.

---

## ✏️ Edit Command (Layer Editing)

Open and edit layer configurations:

```bash
# Edit settings.json (default)
vsc-sync edit base

# Edit specific file types
vsc-sync edit base --keybindings
vsc-sync edit stack python --extensions  
vsc-sync edit app vscode --tasks

# Sort keybindings while editing
vsc-sync edit base --keybindings --sort --yes
```

### Keybinding Sorting

The `--sort` flag provides intelligent keybinding organization:

1. **Primary sort**: By `key` string (case-insensitive)
2. **Secondary sort**: General shortcuts (no `when` clause) before specific ones
3. **Specificity heuristic**: Fewer logical operators = more general
4. **Preserves duplicates**: So you can spot conflicts

---

## 🛠️ Advanced Workflows

### Multi-Editor Development
```bash
# Apply same config to different editors
vsc-sync apply vscode --all --preset python-dev
vsc-sync apply cursor --all --preset python-dev  
vsc-sync apply windsurf --all --preset python-dev
```

### Project-Specific Configurations
```bash
# Set up project workspace
vsc-sync setup-project ./my-react-app --stack web --stack react

# Apply project-specific settings
vsc-sync apply vscode --config --layer base --layer web --layer react-app
```

### Extension Development Workflow
```bash
# Clean slate for testing
vsc-sync apply vscode --extensions --replace-all

# Add specific extensions for testing
vsc-sync apply vscode --extensions --layer base --layer extension-dev
```

### Configuration Iteration
```bash
# 1. Make changes in editor
# 2. Pull changes back to repository
vsc-sync pull vscode --to stack python --settings --keybindings

# 3. Test on another editor
vsc-sync apply cursor --config --stack python

# 4. Fine-tune and repeat
```

---

## 🔍 Troubleshooting Common Issues

### Layer Resolution Not Working
```bash
# Check your TOML config
vsc-sync config --show

# Verify vscode_configs_path is correct
ls ~/vscode-configs/

# Use full paths as fallback
vsc-sync apply vscode --settings --layer /full/path/to/base
```

### Extension Installation Failures
```bash
# Check local VSIX directory
ls ~/Documents/vscode-extension/

# Use --replace-all for clean reinstall
vsc-sync apply vscode --extensions --replace-all

# Check with dry-run first
vsc-sync apply vscode --extensions --dry-run
```

### Keybinding Conflicts
```bash
# Sort keybindings to see duplicates
vsc-sync edit base --keybindings --sort

# Check merged result
vsc-sync apply vscode --keybindings --dry-run
```

---

## ⚡ Quick Reference

### Essential Commands
```bash
# Complete setup (first time)
vsc-sync init --repo ~/vscode-configs

# Daily usage - apply what you need
vsc-sync apply vscode --settings --keybindings

# Use presets for complex setups
vsc-sync apply cursor --all --preset python-dev

# Manage configuration
vsc-sync config --show
vsc-sync config --edit
```

### Component Flags
| Flag | What it applies |
|------|----------------|
| `--settings` | settings.json |
| `--keybindings` | keybindings.json |
| `--extensions` | Extension management |
| `--snippets` | snippets/ directory |
| `--tasks` | tasks.json |
| `--all` | Everything |
| `--config` | settings + keybindings + tasks |

### Extension Modes
| Flag | Behavior |
|------|----------|
| (default) | Install missing only |
| `--remove-extra` | + Remove unlisted extensions |
| `--replace-all` | Remove all + reinstall from config |

### Layer Options
| Option | Usage |
|--------|-------|
| `--stack python` | Standard stack-based layers |
| `--layer base --layer python` | Custom layer ordering |
| `--preset python-dev` | Predefined layer combinations |

Run any command with `--help` for detailed options and examples!