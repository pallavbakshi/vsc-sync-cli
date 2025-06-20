# Advanced Usage

This guide covers advanced features of vsc-sync including the custom layer system, TOML configuration, layer presets, and sophisticated workflows.

---

## 🎯 Custom Layer System

The custom layer system is vsc-sync's most powerful feature, allowing you to explicitly control layer ordering and mix different configuration sources.

### Understanding Layers

Layers are applied in order, with the first `--layer` being the base and subsequent layers stacking on top:

```bash
vsc-sync apply vscode --settings \
  --layer base \        # Foundation settings (applied first)
  --layer python \      # Python-specific settings  
  --layer vscode \      # VSCode-specific settings
  --layer work \        # Work environment settings
  --layer personal      # Personal preference overrides (applied last, takes precedence)
```

### Layer Sources

Each layer can come from three different sources:

1. **Simple Names** (intelligent resolution)
2. **TOML Aliases** (from config.toml)  
3. **Literal Paths** (file or directory)

#### Simple Names (Intelligent Resolution)

vsc-sync automatically searches your vscode-configs directory:

```
~/vscode-configs/
├── base/                   # --layer base
├── apps/
│   ├── vscode/            # --layer vscode
│   ├── cursor/            # --layer cursor
│   └── windsurf/          # --layer windsurf
├── stacks/
│   ├── python/            # --layer python
│   ├── web/               # --layer web
│   └── typescript/        # --layer typescript
└── projects/
    ├── my-app/            # --layer my-app
    └── api-server/        # --layer api-server
```

Search order for name resolution:
1. `~/vscode-configs/{name}/`
2. `~/vscode-configs/apps/{name}/`
3. `~/vscode-configs/stacks/{name}/`
4. `~/vscode-configs/projects/{name}/`

#### TOML Aliases

Define custom aliases in your `~/.config/vsc-sync/config.toml`:

```toml
[layer_aliases.work]
name = "work"
path = "/company/shared/vscode-config"
description = "Company-wide settings"

[layer_aliases.personal]
name = "personal"
path = "~/my-personal-configs/vscode.json"
description = "Personal preference overrides"

[layer_aliases.project-x]
name = "project-x"
path = "~/projects/project-x/.vscode-config"
description = "Project X specific settings"
```

Usage:
```bash
vsc-sync apply vscode --settings \
  --layer base \
  --layer work \        # Resolves to /company/shared/vscode-config
  --layer personal      # Resolves to ~/my-personal-configs/vscode.json
```

#### Literal Paths

Specify exact file or directory paths:

```bash
vsc-sync apply vscode --settings \
  --layer ~/vscode-configs/base \
  --layer /shared/team-settings \
  --layer ./project-specific-config.json
```

### Advanced Layer Examples

#### Development Environment Stacks
```bash
# Python data science setup
vsc-sync apply vscode --all \
  --layer base \
  --layer python \
  --layer data-science \
  --layer jupyter

# Full-stack web development
vsc-sync apply cursor --all \
  --layer base \
  --layer javascript \
  --layer react \
  --layer nodejs \
  --layer personal
```

#### Project-Specific Configurations
```bash
# Client project with specific requirements
vsc-sync apply vscode --config \
  --layer base \
  --layer company-standard \
  --layer client-project \
  --layer ~/projects/client-app/.vscode-overrides

# Open source project
vsc-sync apply windsurf --all \
  --layer base \
  --layer open-source \
  --layer typescript \
  --layer personal
```

#### Multi-Language Development
```bash
# Polyglot developer setup
vsc-sync apply vscode --settings \
  --layer base \
  --layer python \
  --layer javascript \  # Multiple layers of same level
  --layer rust \
  --layer personal
```

---

## 🎮 Layer Presets

Layer presets allow you to define common layer combinations once and reuse them everywhere.

### Defining Presets

In your `~/.config/vsc-sync/config.toml`:

```toml
[layer_presets]
# Development environments
python-dev = ["base", "python", "personal"]
web-dev = ["base", "javascript", "web", "personal"]
fullstack = ["base", "javascript", "python", "web", "personal"]
data-science = ["base", "python", "jupyter", "data-science"]

# Project types
startup = ["base", "startup", "fast-iteration", "personal"]
enterprise = ["base", "company-standard", "enterprise", "personal"]
open-source = ["base", "open-source", "community", "personal"]

# Specialized workflows
debugging = ["base", "debugging", "logging", "personal"]
testing = ["base", "testing", "ci-cd", "personal"]
presentation = ["base", "presentation", "clean-ui", "minimal"]

# Editor-specific
vscode-power = ["base", "vscode", "extensions-heavy", "personal"]
cursor-ai = ["base", "cursor", "ai-enhanced", "personal"]
minimal-setup = ["base", "minimal"]
```

### Using Presets

```bash
# Apply complete development environments
vsc-sync apply vscode --all --preset python-dev
vsc-sync apply cursor --all --preset web-dev
vsc-sync apply windsurf --config --preset enterprise

# Combine with other flags
vsc-sync apply vscode --extensions --preset debugging
vsc-sync apply cursor --settings --keybindings --preset presentation
```

### Preset Resolution

Presets resolve each layer name using the same three-tier strategy:
1. Intelligent name resolution
2. TOML alias resolution  
3. Literal path resolution

```toml
# This preset mixes all resolution types
mixed-preset = [
  "base",                    # Intelligent: ~/vscode-configs/base/
  "company",                 # Alias: /company/shared/config
  "~/custom/personal.json"   # Literal path
]
```

### Advanced Preset Patterns

#### Conditional Presets
```toml
# Different presets for different contexts
[layer_presets]
work-python = ["base", "company", "python", "work-personal"]
home-python = ["base", "python", "home-personal", "experimental"]
demo-python = ["base", "python", "presentation", "minimal"]
```

#### Hierarchical Presets
```toml
# Build complexity gradually
[layer_presets]
minimal = ["base"]
basic-python = ["base", "python"]
python-dev = ["base", "python", "development"]
python-full = ["base", "python", "development", "testing", "personal"]
```

#### Role-Based Presets
```toml
# Different roles, different configs
[layer_presets]
backend-dev = ["base", "python", "api", "database", "personal"]
frontend-dev = ["base", "javascript", "react", "design", "personal"]
devops = ["base", "infrastructure", "ci-cd", "monitoring", "personal"]
data-scientist = ["base", "python", "jupyter", "ml", "visualization"]
```

---

## 🧠 Intelligent Layer Resolution Deep Dive

### Configuration Path Setup

The intelligent resolution system relies on the `vscode_configs_path` in your TOML config:

```toml
# ~/.config/vsc-sync/config.toml
vscode_configs_path = "~/vscode-configs"
```

### Resolution Algorithm

When you specify a layer name, vsc-sync follows this resolution order:

```python
def resolve_layer_spec(layer_name):
    # 1. Try intelligent name resolution
    for directory in ["", "apps/", "stacks/", "projects/"]:
        path = vscode_configs_path / directory / layer_name
        if path.exists():
            return path
    
    # 2. Try alias resolution
    if layer_name in toml_config.layer_aliases:
        return toml_config.layer_aliases[layer_name].path
    
    # 3. Try literal path resolution
    path = Path(layer_name)
    return path  # Return as-is (may or may not exist)
```

### Directory Structure Conventions

The intelligent resolution works best with this recommended structure:

```
~/vscode-configs/
├── base/                           # Core settings for all setups
│   ├── settings.json
│   ├── keybindings.json
│   └── extensions.json
├── apps/                           # Editor-specific configurations
│   ├── vscode/
│   │   ├── settings.json           # VSCode-specific settings
│   │   └── extensions.json         # VSCode-specific extensions
│   ├── cursor/
│   │   ├── settings.json           # Cursor-specific settings
│   │   └── extensions.json         # AI-enhanced extensions
│   └── windsurf/
│       └── settings.json           # Windsurf-specific settings
├── stacks/                         # Technology stack configurations
│   ├── python/
│   │   ├── settings.json           # Python development settings
│   │   ├── extensions.json         # Python-related extensions
│   │   └── snippets/
│   │       └── python.json         # Python code snippets
│   ├── javascript/
│   │   ├── settings.json           # JS/TS development settings
│   │   ├── extensions.json         # JavaScript extensions
│   │   └── keybindings.json        # JS-specific key bindings
│   └── web/
│       ├── settings.json           # Web development settings
│       └── extensions.json         # Web development extensions
├── projects/                       # Project-specific configurations
│   ├── my-react-app/
│   │   ├── settings.json           # Project-specific settings
│   │   └── tasks.json              # Project build tasks
│   └── api-server/
│       ├── settings.json
│       └── launch.json             # Debug configurations
└── environments/                   # Environment-specific configs
    ├── work/
    │   ├── settings.json
    │   └── extensions.json
    └── personal/
        ├── settings.json
        └── keybindings.json
```

---

## 🔧 TOML Configuration Management

### Complete TOML Configuration Reference

```toml
# ~/.config/vsc-sync/config.toml

# Path to vscode-configs repository for intelligent layer resolution
vscode_configs_path = "~/vscode-configs"

# Default settings applied when no flags specified
[defaults]
components = ["settings", "keybindings", "extensions"]
backup = true
extension_mode = "add"  # "add", "remove-extra", "replace-all"

# Layer aliases for custom paths and external configurations
[layer_aliases.work]
name = "work"
path = "/company/shared/vscode-config"
description = "Company-wide development standards"

[layer_aliases.personal]
name = "personal"
path = "~/my-configs/personal.json"
description = "Personal preference overrides"

[layer_aliases.legacy]
name = "legacy"
path = "~/old-configs/legacy-settings"
description = "Legacy project compatibility settings"

# Layer presets for common workflows
[layer_presets]
# Development environments
python-dev = ["base", "python", "personal"]
web-dev = ["base", "javascript", "web", "personal"]
fullstack = ["base", "python", "javascript", "web", "personal"]

# Project types
startup = ["base", "fast", "experimental", "personal"]
enterprise = ["base", "work", "security", "compliance"]
open-source = ["base", "community", "documentation", "personal"]

# Specialized workflows
debugging = ["base", "debug", "logging", "verbose"]
testing = ["base", "testing", "ci", "coverage"]
demo = ["base", "presentation", "clean", "minimal"]

# Editor-specific configurations  
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
extension_timeout = 10
```

### Managing TOML Configuration

#### View Configuration
```bash
# Show complete configuration
vsc-sync config --show

# Show just the file path
vsc-sync config --path
```

#### Edit Configuration
```bash
# Open in your default editor
vsc-sync config --edit

# Initialize with example configuration
vsc-sync config --init
```

#### Validate Configuration
```bash
# Check if your configuration is valid
vsc-sync config --show | head -10
```

---

## 🔀 Advanced Component Management

### Selective Component Application

Apply different components with different layer combinations:

```bash
# Apply settings and keybindings with full stack
vsc-sync apply vscode --settings --keybindings \
  --layer base --layer python --layer personal

# Apply only extensions with minimal layers
vsc-sync apply vscode --extensions \
  --layer base --layer python

# Apply snippets from specific project
vsc-sync apply vscode --snippets \
  --layer base --layer my-project
```

### Extension Management Strategies

#### Incremental Extension Management
```bash
# Default: Only install missing extensions
vsc-sync apply vscode --extensions --layer base --layer python

# Add project-specific extensions
vsc-sync apply vscode --extensions --layer base --layer current-project
```

#### Curated Extension Management
```bash
# Remove extensions not in configuration
vsc-sync apply vscode --extensions --remove-extra \
  --preset python-dev

# Clean slate: remove all, reinstall from config
vsc-sync apply vscode --extensions --replace-all \
  --preset minimal
```

#### Local Extension Fallback
When marketplace fails, vsc-sync searches `~/Documents/vscode-extension/`:

```bash
# Your local extension directory
ls ~/Documents/vscode-extension/
# ms-python.python.vsix
# ms-python.python-2023.1.0.vsix
# github.copilot-1.67.7.vsix
# publisher.extension.vsix
```

Supported filename patterns:
- `{publisher}.{extension}.vsix`
- `{publisher}.{extension}-{version}.vsix`

---

## 🔄 Complex Workflows

### Development Environment Switching

#### Context-Aware Development
```bash
# Morning: Start with clean environment
vsc-sync apply vscode --all --preset minimal

# Switch to Python project
vsc-sync apply vscode --config --preset python-dev

# Add project-specific settings
vsc-sync apply vscode --settings \
  --layer base --layer python --layer current-project

# Evening: Switch to personal projects
vsc-sync apply vscode --all --preset personal-dev
```

#### Multi-Project Management
```bash
# Set up project A
vsc-sync apply vscode --all \
  --layer base --layer web --layer project-a

# Quick switch to project B (same base, different project)
vsc-sync apply vscode --settings --tasks \
  --layer base --layer web --layer project-b

# Debugging project C with enhanced tools
vsc-sync apply vscode --all \
  --layer base --layer debugging --layer project-c
```

### Team Collaboration Workflows

#### Shared Configuration Management
```bash
# Pull team updates
cd ~/vscode-configs
git pull origin main

# Apply team standard with personal overrides
vsc-sync apply vscode --all \
  --layer base --layer team-standard --layer personal

# Push personal improvements back to shared layers
vsc-sync pull vscode --to stack team-improvements \
  --settings --keybindings
```

#### Onboarding New Team Members
```bash
# Clone team repository
vsc-sync init --repo git@company.com:team/vscode-configs.git

# Apply team preset
vsc-sync apply vscode --all --preset team-standard

# Add personal customizations
vsc-sync config --edit
# Add personal preset: ["base", "team-standard", "personal"]
```

### Configuration Testing and Validation

#### Safe Configuration Testing
```bash
# Preview changes without applying
vsc-sync apply vscode --all --preset experimental --dry-run

# Test in secondary editor first
vsc-sync apply cursor --config --preset experimental

# Apply to main editor if satisfied
vsc-sync apply vscode --all --preset experimental
```

#### A/B Testing Configurations
```bash
# Setup A: Current production config
vsc-sync apply vscode --all --preset production

# Setup B: Test new configuration
vsc-sync apply cursor --all --preset experimental

# Compare and decide
vsc-sync status vscode
vsc-sync status cursor
```

---

## 📊 Monitoring and Troubleshooting

### Configuration Status Monitoring
```bash
# Check overall status
vsc-sync status

# Check specific editor with layers
vsc-sync status vscode --stack python --stack web

# Check configuration differences
vsc-sync apply vscode --all --preset python-dev --dry-run
```

### Layer Resolution Debugging
```bash
# Check what layers would be resolved
vsc-sync config --show

# Verify vscode_configs_path
ls -la $(vsc-sync config --show | grep vscode_configs_path | cut -d'"' -f2)

# Test specific layer resolution
vsc-sync apply vscode --settings --layer python --dry-run
```

### Extension Installation Debugging
```bash
# Check marketplace connectivity
vsc-sync apply vscode --extensions --dry-run

# Check local VSIX files
ls -la ~/Documents/vscode-extension/

# Force marketplace-only (skip local fallback)
# Currently not available - feature request
```

---

## 🎯 Best Practices

### Layer Organization
1. **Keep base minimal**: Only essential settings in base layer
2. **Use specific layers**: Create focused layers for specific purposes
3. **Personal overrides last**: Always apply personal layer last
4. **Document layers**: Use clear descriptions in TOML aliases

### Preset Design
1. **Start simple**: Begin with minimal presets, build complexity
2. **Use descriptive names**: `python-dev` not `p1`
3. **Group by purpose**: Development, testing, presentation, etc.
4. **Test thoroughly**: Validate presets work in different contexts

### Configuration Management
1. **Version control**: Keep vscode-configs in Git
2. **Backup before changes**: Let vsc-sync handle backups
3. **Test in isolation**: Use different editors for testing
4. **Document workflows**: Comment your TOML configuration

### Team Collaboration
1. **Shared base**: Common base layer for team consistency
2. **Personal freedom**: Allow personal override layers
3. **Clear conventions**: Establish naming conventions for layers
4. **Regular updates**: Keep shared layers updated and tested

This advanced usage guide covers the most sophisticated features of vsc-sync. For basic usage, see the [Usage Guide](usage.md). For initial setup, see the [Quick Start](tutorials/quick-start.md).