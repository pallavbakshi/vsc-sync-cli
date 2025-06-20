# Quick Start

Get up and running with vsc-sync's enhanced layer system and intelligent configuration in under 5 minutes!

---

## 🚀 Installation

```bash
# 1. Install from source
git clone https://github.com/your-org/vsc-sync-cli.git
cd vsc-sync-cli

# (optional but recommended)
python -m venv .venv && source .venv/bin/activate

# Editable install
pip install -e .[cli]
```

---

## 📁 Prepare Your Configuration Repository

You'll need a repository to store your configurations. Two options:

### Option A: Create Empty Repository
```bash
# Create a new empty private repository on GitHub/GitLab
# We'll set up the structure during init
```

### Option B: Use Template Structure
```bash
# Clone or create with recommended structure
mkdir ~/vscode-configs && cd ~/vscode-configs
git init

# Create standard directories
mkdir -p base apps/vscode apps/cursor stacks/python stacks/web projects

# Add example settings
echo '{"editor.fontSize": 14}' > base/settings.json
echo '[]' > base/keybindings.json
echo '["ms-python.python"]' > stacks/python/extensions.json

git add . && git commit -m "Initial structure"
```

---

## ⚡ Enhanced Initialization

The new `init` command provides a complete guided setup:

```bash
# Initialize with local repository
vsc-sync init --repo ~/vscode-configs

# OR initialize with remote repository
vsc-sync init --repo git@github.com:your-user/vscode-configs.git
```

### What happens during init:

1. **Repository Setup**
   ```
   Would you like to clone a repository? [y/N]: n
   Enter path to vscode-configs directory: ~/vscode-configs
   ```

2. **Application Discovery**
   ```
   Auto-discovering applications...
   ✓ Found: vscode at ~/.config/Code/User
   ✓ Found: cursor at ~/.config/Cursor/User  
   ✓ Found: windsurf at ~/.config/Windsurf/User
   ```

3. **🆕 Intelligent Layer Resolution Setup**
   ```
   Setting up intelligent layer resolution...
   
   Do you want to set up intelligent layer resolution? 
   This allows you to use simple names like 'base', 'python', 'vscode' 
   instead of full paths [Y/n]: y
   
   ✓ Created TOML config at ~/.config/vsc-sync/config.toml
   ✓ Intelligent layer resolution enabled
   
   What this enables:
   • Use short names: --layer base --layer python
   • Instead of full paths: --layer ~/vscode-configs/base
   • Automatic discovery in: base/, apps/, stacks/, projects/
   ```

**Result**: You're ready to use simple names immediately!

---

## 🎯 Start Using vsc-sync

### Apply Configurations (Opt-In Approach)

No more accidental overwrites! Specify exactly what you want:

```bash
# Start simple - apply settings only
vsc-sync apply vscode --settings

# Add keybindings
vsc-sync apply vscode --settings --keybindings

# Apply everything
vsc-sync apply vscode --all
```

### Use the Layer System

```bash
# Traditional approach (still works)
vsc-sync apply vscode --settings --stack python

# 🆕 New custom layers with simple names
vsc-sync apply vscode --settings \
  --layer base \
  --layer python \
  --layer vscode

# 🆕 Use layer presets (defined in config.toml)
vsc-sync apply vscode --all --preset python-dev
```

### Extension Management Made Clear

```bash
# Install missing extensions only (safest)
vsc-sync apply vscode --extensions

# Remove extras + install missing
vsc-sync apply vscode --extensions --remove-extra

# Nuclear option: remove all, reinstall from config
vsc-sync apply vscode --extensions --replace-all
```

---

## 🔧 Configuration Management

### View Your Setup
```bash
# See current configuration
vsc-sync config --show

# Show applications
vsc-sync list-apps

# Check status
vsc-sync status vscode
```

### Edit Configuration
```bash
# Edit TOML config for aliases and presets
vsc-sync config --edit

# Edit layer files directly
vsc-sync edit base --settings
vsc-sync edit stack python --extensions
```

---

## 🌟 Complete Workflow Example

Here's a typical workflow for a Python developer:

### 1. Initial Setup (First Machine)
```bash
# Install and initialize
vsc-sync init --repo ~/vscode-configs

# Apply basic configuration
vsc-sync apply vscode --all --layer base --layer python

# Make adjustments in VSCode, then pull them back
vsc-sync pull vscode --to stack python --settings --keybindings
```

### 2. Set Up Layer Preset
```bash
# Edit TOML config to add preset
vsc-sync config --edit

# Add this to config.toml:
# [layer_presets]
# python-dev = ["base", "python", "personal"]
```

### 3. Daily Usage
```bash
# On any machine, apply your full Python setup
vsc-sync apply vscode --all --preset python-dev

# Or selectively apply components
vsc-sync apply cursor --config --preset python-dev  # No extensions
vsc-sync apply windsurf --extensions --layer base --layer python
```

### 4. Iteration and Updates
```bash
# Make changes in your editor
# Pull them back to repository
vsc-sync pull vscode --to stack python --settings --extensions

# Apply to other editors/machines
vsc-sync apply cursor --settings --preset python-dev
```

---

## 🔄 Multi-Editor Workflow

Sync the same configuration across different editors:

```bash
# Apply identical setup to different editors
vsc-sync apply vscode --all --preset web-dev
vsc-sync apply cursor --all --preset web-dev  
vsc-sync apply windsurf --all --preset web-dev

# Or target specific editor configurations
vsc-sync apply vscode --config --layer base --layer vscode --layer web
vsc-sync apply cursor --config --layer base --layer cursor --layer web
```

---

## ⚠️ Migration from Old Version

If you were using vsc-sync before the enhancements:

### Your existing configs still work:
```bash
# These commands remain unchanged
vsc-sync apply vscode --stack python --stack web
vsc-sync pull vscode --to base --settings
vsc-sync edit base --keybindings
```

### Upgrade to new features:
```bash
# Run init again to set up TOML config
vsc-sync init  # Will detect existing setup

# Start using new opt-in approach
vsc-sync apply vscode --settings --keybindings  # Instead of --no-extensions --no-snippets

# Set up layer presets for convenience
vsc-sync config --edit
```

---

## 🎁 What You Get

After following this quick start, you have:

✅ **Complete Configuration Management**: All editors discovered and ready
✅ **Intelligent Layer Resolution**: Use simple names instead of paths  
✅ **Layer Presets**: Common workflows accessible via single flag
✅ **Opt-In Safety**: Only apply what you explicitly specify
✅ **Multi-Editor Support**: Same configs across VSCode, Cursor, Windsurf, etc.
✅ **Local Extension Fallback**: VSIX installation when marketplace fails
✅ **Smart Keybinding Merging**: Combines all layers instead of overwriting

---

## 🆘 Quick Troubleshooting

**Layer resolution not working?**
```bash
vsc-sync config --show  # Check vscode_configs_path
```

**Extensions failing to install?**
```bash
ls ~/Documents/vscode-extension/  # Check local VSIX files
vsc-sync apply vscode --extensions --dry-run  # Preview what will happen
```

**Want to see what would change?**
```bash
vsc-sync apply vscode --all --preset python-dev --dry-run
```

You're now ready to use vsc-sync's powerful layer system! Check the [Usage Guide](../usage.md) for detailed command documentation.
