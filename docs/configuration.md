# Configuration

This guide covers vsc-sync's TOML configuration system, which enables intelligent layer resolution, layer aliases, presets, and default settings.

---

## 📁 Configuration Files

vsc-sync uses two configuration files:

1. **Main Configuration** (`~/.config/vsc-sync/config.json`)
   - Stores vscode-configs repository path
   - Lists discovered/registered applications
   - Created by `vsc-sync init`

2. **TOML Configuration** (`~/.config/vsc-sync/config.toml`)  
   - Enables intelligent layer resolution
   - Defines layer aliases and presets
   - Sets default behaviors
   - **NEW**: Created during enhanced `vsc-sync init`

---

## 🚀 TOML Configuration Overview

The TOML configuration supercharges vsc-sync with:

- **🧠 Intelligent Layer Resolution**: Use `base`, `python`, `vscode` instead of full paths
- **🔗 Layer Aliases**: Define custom shortcuts for any configuration path
- **📦 Layer Presets**: Common layer combinations in a single flag
- **⚙️ Default Settings**: Customize default behaviors

---

## 📝 Complete TOML Reference

### Basic Structure

```toml
# ~/.config/vsc-sync/config.toml

# Path to vscode-configs repository for intelligent layer resolution
vscode_configs_path = "~/vscode-configs"

[defaults]
components = ["settings", "keybindings", "extensions"]
backup = true
extension_mode = "add"

[layer_aliases.alias_name]
name = "alias_name"
path = "/path/to/config"
description = "Human-readable description"

[layer_presets]
preset_name = ["layer1", "layer2", "layer3"]

[editor_settings.editor_name]
auto_backup = true
extension_timeout = 10
```

### Detailed Sections

#### `vscode_configs_path`
```toml
# Enables intelligent layer resolution
vscode_configs_path = "~/vscode-configs"

# Can be absolute or relative path
vscode_configs_path = "/Users/pb/development/vscode-configs"
vscode_configs_path = "./configs"
```

**What it enables:**
```bash
# Without vscode_configs_path: Must use full paths
vsc-sync apply vscode --settings \
  --layer0 ~/vscode-configs/base \
  --layer1 ~/vscode-configs/stacks/python

# With vscode_configs_path: Use simple names  
vsc-sync apply vscode --settings \
  --layer0 base \
  --layer1 python
```

#### `[defaults]` Section
```toml
[defaults]
# Components applied when using --all or no component flags specified
components = ["settings", "keybindings", "extensions"]

# Create backup before applying changes
backup = true

# Default extension management mode: "add", "remove-extra", "replace-all"
extension_mode = "add"
```

**Usage:**
```bash
# These defaults are used when no specific flags given
vsc-sync apply vscode --all
# Equivalent to: vsc-sync apply vscode --settings --keybindings --extensions
```

#### `[layer_aliases.*]` Section
Define custom shortcuts for any configuration path:

```toml
[layer_aliases.work]
name = "work"
path = "/company/shared/vscode-config"
description = "Company-wide development standards"

[layer_aliases.personal]
name = "personal"  
path = "~/my-configs/personal-settings.json"
description = "Personal preference overrides"

[layer_aliases.legacy]
name = "legacy"
path = "~/old-projects/legacy-config"
description = "Legacy project compatibility settings"

[layer_aliases.client-a]
name = "client-a"
path = "~/clients/client-a/.vscode-config"
description = "Client A specific requirements"
```

**Usage:**
```bash
# Use aliases like any other layer name
vsc-sync apply vscode --settings \
  --layer0 base \
  --layer1 work \      # Resolves to /company/shared/vscode-config
  --layer2 personal    # Resolves to ~/my-configs/personal-settings.json

# Mix aliases with intelligent names and literal paths
vsc-sync apply cursor --all \
  --layer0 base \               # Intelligent: ~/vscode-configs/base/
  --layer1 client-a \           # Alias: ~/clients/client-a/.vscode-config
  --layer2 /custom/project      # Literal path
```

#### `[layer_presets]` Section
Define common layer combinations:

```toml
[layer_presets]
# Development environments
python-dev = ["base", "python", "personal"]
web-dev = ["base", "javascript", "web", "personal"]
fullstack = ["base", "python", "javascript", "web", "personal"]
data-science = ["base", "python", "jupyter", "data-science"]

# Project types  
startup = ["base", "startup", "fast-iteration", "personal"]
enterprise = ["base", "work", "security", "compliance"]
open-source = ["base", "community", "documentation", "personal"]

# Specialized workflows
debugging = ["base", "debugging", "logging", "personal"]
testing = ["base", "testing", "ci-cd", "personal"] 
presentation = ["base", "presentation", "clean-ui", "minimal"]

# Editor-specific
vscode-power = ["base", "vscode", "extensions-heavy", "personal"]
cursor-ai = ["base", "cursor", "ai-enhanced", "personal"]
minimal-setup = ["base", "minimal"]

# Complex combinations with aliases
work-python = ["base", "work", "python", "personal"]
client-project = ["base", "work", "client-a", "python", "personal"]
```

**Usage:**
```bash
# Apply entire preset
vsc-sync apply vscode --all --preset python-dev

# Combine presets with other flags
vsc-sync apply cursor --config --preset web-dev
vsc-sync apply windsurf --extensions --preset testing
```

#### `[editor_settings.*]` Section
Editor-specific configuration:

```toml
[editor_settings.vscode]
auto_backup = true
extension_timeout = 10
marketplace_fallback = true

[editor_settings.cursor]
auto_backup = true
extension_timeout = 15
ai_features = true

[editor_settings.windsurf]
auto_backup = false
extension_timeout = 5
```

**Currently supported settings:**
- `auto_backup`: Whether to create backups before applying
- `extension_timeout`: Seconds to wait for marketplace extension installs
- Other settings are reserved for future features

---

## 🧠 Intelligent Layer Resolution

### How It Works

When you specify a layer name, vsc-sync uses this resolution strategy:

1. **Intelligent name resolution**: Search standard directories
2. **Alias resolution**: Check config.toml aliases
3. **Literal path resolution**: Treat as file/directory path

### Directory Search Order

For intelligent name resolution, vsc-sync searches:

```
{vscode_configs_path}/
├── {name}/                 # Direct match (for "base")
├── apps/{name}/           # Application-specific  
├── stacks/{name}/         # Technology stacks
└── projects/{name}/       # Project-specific
```

### Examples

Given this directory structure:
```
~/vscode-configs/
├── base/
├── apps/
│   ├── vscode/
│   └── cursor/
├── stacks/
│   ├── python/
│   └── web/
└── projects/
    └── my-app/
```

And this TOML configuration:
```toml
vscode_configs_path = "~/vscode-configs"

[layer_aliases.personal]
name = "personal"
path = "~/my-configs/personal.json"
```

Resolution examples:
```bash
# Intelligent resolution
--layer0 base      # → ~/vscode-configs/base/
--layer1 python    # → ~/vscode-configs/stacks/python/
--layer2 vscode    # → ~/vscode-configs/apps/vscode/
--layer3 my-app    # → ~/vscode-configs/projects/my-app/

# Alias resolution  
--layer4 personal  # → ~/my-configs/personal.json

# Literal path resolution
--layer5 /custom   # → /custom (as-is)
```

---

## 🛠️ Managing TOML Configuration

### The Config Command

```bash
# Show current configuration
vsc-sync config --show

# Edit configuration in your default editor
vsc-sync config --edit

# Show config file location
vsc-sync config --path

# Initialize/recreate config.toml with examples
vsc-sync config --init
```

### Example: config --show Output

```
vsc-sync Configuration
File: ~/.config/vsc-sync/config.toml

VSCode Configs Path:
  ~/vscode-configs
  (Used for intelligent layer name resolution)

Defaults:
  Components: settings, keybindings, extensions
  Backup: true
  Extension mode: add

Layer Aliases:
  work: /company/shared/vscode-config
    Company-wide development standards
  personal: ~/my-configs/personal-settings.json
    Personal preference overrides

Layer Presets:
  python-dev: base, python, personal
  web-dev: base, web, vscode, personal
```

### Creating/Updating Configuration

#### During Init (Recommended)
```bash
vsc-sync init --repo ~/vscode-configs
# Follow prompts to set up TOML configuration
```

#### Manual Setup
```bash
# Create example configuration
vsc-sync config --init

# Edit to customize
vsc-sync config --edit
```

#### Editing Existing Configuration
```bash
# Open in editor
vsc-sync config --edit

# Or edit directly
nano ~/.config/vsc-sync/config.toml
```

---

## 📚 Configuration Examples

### Basic Setup
```toml
vscode_configs_path = "~/vscode-configs"

[defaults]
components = ["settings", "keybindings"]
backup = true
extension_mode = "add"

[layer_presets]
minimal = ["base"]
python = ["base", "python"]
web = ["base", "web"]
```

### Advanced Setup
```toml
vscode_configs_path = "~/development/vscode-configs"

[defaults]
components = ["settings", "keybindings", "extensions"]
backup = true
extension_mode = "remove-extra"

[layer_aliases.company]
name = "company"
path = "/company/shared/vscode-standards"
description = "Company development standards"

[layer_aliases.personal]
name = "personal"
path = "~/personal-configs/vscode.json"
description = "Personal preferences and shortcuts"

[layer_aliases.client-x]
name = "client-x"
path = "~/clients/client-x/.vscode-config"
description = "Client X specific requirements"

[layer_presets]
# Development environments
python-work = ["base", "company", "python", "personal"]
web-work = ["base", "company", "web", "personal"]
fullstack-work = ["base", "company", "python", "web", "personal"]

# Client projects
client-x-python = ["base", "company", "client-x", "python", "personal"]
client-x-web = ["base", "company", "client-x", "web", "personal"]

# Personal projects
python-personal = ["base", "python", "personal"]
web-personal = ["base", "web", "personal"]

# Specialized workflows
debugging = ["base", "debugging", "verbose-logging"]
testing = ["base", "testing", "ci-cd", "coverage"]
demo = ["base", "presentation", "clean", "minimal"]

[editor_settings.vscode]
auto_backup = true
extension_timeout = 10

[editor_settings.cursor]
auto_backup = true
extension_timeout = 15
```

### Team Collaboration Setup
```toml
vscode_configs_path = "~/shared/team-vscode-configs"

[defaults]
components = ["settings", "keybindings", "extensions"]
backup = true
extension_mode = "remove-extra"

[layer_aliases.team-base]
name = "team-base"
path = "~/shared/team-vscode-configs/team-base"
description = "Team-wide base configuration"

[layer_aliases.personal]
name = "personal"
path = "~/my-personal-configs/overrides.json"
description = "Personal overrides (not shared)"

[layer_presets]
# Standard team environments
backend = ["team-base", "python", "api", "personal"]
frontend = ["team-base", "javascript", "react", "personal"]
fullstack = ["team-base", "python", "javascript", "react", "personal"]

# Role-specific
lead = ["team-base", "leadership", "code-review", "personal"]
intern = ["team-base", "learning", "guided", "personal"]

# Project-specific
project-alpha = ["team-base", "project-alpha", "personal"]
project-beta = ["team-base", "project-beta", "personal"]
```

---

## 🔧 Configuration Validation

### Checking Your Configuration

```bash
# Verify configuration is valid
vsc-sync config --show

# Test layer resolution
vsc-sync apply vscode --settings --layer0 base --dry-run

# Test preset resolution  
vsc-sync apply vscode --all --preset python-dev --dry-run
```

### Common Issues

#### vscode_configs_path Not Found
```toml
# ❌ This path doesn't exist
vscode_configs_path = "~/nonexistent-configs"
```

**Solution:**
```bash
# Check the path exists
ls ~/vscode-configs

# Fix in TOML config
vsc-sync config --edit
```

#### Layer Alias Path Invalid
```toml
# ❌ This path doesn't exist
[layer_aliases.broken]
path = "~/nonexistent/config.json"
```

**Solution:**
```bash
# Verify alias paths exist
ls ~/my-configs/personal.json

# Remove or fix broken aliases
vsc-sync config --edit
```

#### Preset References Unknown Layers
```toml
# ❌ "unknown-layer" can't be resolved
[layer_presets]
broken-preset = ["base", "unknown-layer", "personal"]
```

**Solution:**
```bash
# Test preset resolution
vsc-sync apply vscode --all --preset broken-preset --dry-run

# Fix preset definition
vsc-sync config --edit
```

---

## 🎯 Best Practices

### TOML Configuration
1. **Use descriptive names**: `python-dev` not `p1`
2. **Document aliases**: Include helpful descriptions
3. **Test presets**: Validate with `--dry-run` before using
4. **Keep it simple**: Start basic, add complexity gradually

### Layer Organization
1. **Consistent naming**: Use clear, consistent layer names
2. **Logical grouping**: Group related configurations together
3. **Minimal base**: Keep base layer essential-only
4. **Personal last**: Always apply personal overrides last

### Team Collaboration
1. **Shared base**: Common foundation for team consistency
2. **Personal overrides**: Allow individual customization
3. **Document conventions**: Clear naming and usage guidelines
4. **Version control**: Keep TOML configs in version control

### Maintenance
1. **Regular cleanup**: Remove unused aliases and presets
2. **Path validation**: Periodically check paths still exist
3. **Preset testing**: Verify presets work after repository changes
4. **Documentation**: Keep descriptions up-to-date

---

## 🔄 Migration and Upgrades

### Migrating from Pre-TOML Version

If you were using vsc-sync before TOML configuration:

#### Your existing setup still works:
```bash
# These commands remain unchanged
vsc-sync apply vscode --stack python --stack web
vsc-sync pull vscode --to base --settings
```

#### Upgrade to TOML features:
```bash
# Run init again to set up TOML config
vsc-sync init  # Will detect existing setup and add TOML

# Start using intelligent resolution
vsc-sync apply vscode --settings --layer0 base --layer1 python

# Create presets for common workflows
vsc-sync config --edit
```

### Adding TOML to Existing Installation

```bash
# Initialize TOML configuration  
vsc-sync config --init

# Edit to match your setup
vsc-sync config --edit

# Test intelligent resolution
vsc-sync apply vscode --settings --layer0 base --dry-run
```

---

## 📖 Related Documentation

- [Usage Guide](usage.md) - Using TOML configuration in daily workflows
- [Advanced Usage](advanced-usage.md) - Complex layer and preset patterns
- [Quick Start](tutorials/quick-start.md) - Setting up TOML during initialization
- [Layer Precedence](behind-the-scenes/layer-precedence.md) - How layer resolution and merging works

The TOML configuration system makes vsc-sync significantly more powerful and user-friendly. Start with the basic setup and gradually add aliases and presets as your workflows become more sophisticated.