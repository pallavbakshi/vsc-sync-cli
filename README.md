# vsc-sync

A CLI tool to synchronize VSCode-like configurations across multiple editors.

## Overview

`vsc-sync` helps you maintain consistent configurations across various VSCode-like editors including:

- Visual Studio Code
- VSCodium  
- Cursor
- Windsurf
- Void
- PearAI

The tool uses a layered configuration approach with a centralized Git repository containing your configuration snippets organized by:

- **Base**: Fundamental settings that apply to all editors
- **Apps**: Editor-specific configurations
- **Stacks**: Technology-specific settings (Python, JavaScript, etc.)
- **Projects**: Project templates and workspace configurations

## Installation

### From Source (Development)

1. Clone this repository:
```bash
git clone https://github.com/yourusername/vsc-sync-cli.git
cd vsc-sync-cli
```

2. Install with uv (recommended):
```bash
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -e .
```

Or with pip:
```bash
pip install -e .
```

## Quick Start

1. **Initialize vsc-sync** (sets up configuration and discovers editors):
```bash
vsc-sync init
```

2. **Discover installed VSCode-like applications**:
```bash
vsc-sync discover
```

3. **Apply configurations** to an editor:
```bash
vsc-sync apply vscode --stack python
```

4. **Check configuration status**:
```bash
vsc-sync status
```

## Configuration Repository Structure

Your `vscode-configs` repository should follow this structure:

```
vscode-configs/
├── base/
│   ├── settings.json
│   ├── keybindings.json
│   ├── extensions.json
│   └── snippets/
├── apps/
│   ├── vscode/
│   ├── cursor/
│   └── windsurf/
├── stacks/
│   ├── python/
│   ├── javascript/
│   └── web-dev/
└── projects/
    ├── python-api/
    └── react-app/
```

## Commands

### Initialization & App Management

- `vsc-sync init` - Initialize vsc-sync for first-time use
- `vsc-sync add-app <alias> <config-path>` - Register a new editor
- `vsc-sync list-apps` - List all registered editors
- `vsc-sync discover` - Auto-discover VSCode-like applications

### Configuration Management

- `vsc-sync apply <app> [--stack <stack>...]` - Apply configurations to an editor
- `vsc-sync status [<app>]` - Check configuration status
- `vsc-sync pull <app> --to <layer>` - Save current config back to repository

### Project Setup

- `vsc-sync setup-project [path] [--stack <stack>...]` - Setup workspace configuration

### Utilities

- `vsc-sync edit <layer-type> <layer-name>` - Edit configuration files

## Examples

```bash
# Apply Python development configuration to VSCode
vsc-sync apply vscode --stack python

# Apply multiple stacks
vsc-sync apply cursor --stack python --stack web-dev

# Setup a new Python project
vsc-sync setup-project ./my-project --stack python

# Pull current VSCode settings to Python stack
vsc-sync pull vscode --to stack python --include-extensions

# Check what would change (dry run)
vsc-sync apply vscode --stack python --dry-run
```

## Development

### Prerequisites

- Python 3.8+
- uv (recommended) or pip

### Setup Development Environment

```bash
git clone https://github.com/yourusername/vsc-sync-cli.git
cd vsc-sync-cli

# Create virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code  
ruff check src/ tests/

# Type checking
mypy src/
```

## Project Status

🚧 **This project is currently in development.** 

Current status:
- ✅ Project scaffold and core architecture
- ✅ Configuration management and layer merging
- ✅ Application discovery and management
- ✅ Basic CLI structure
- 🚧 Command implementations (in progress)
- ⏳ Git integration
- ⏳ Extension management
- ⏳ Project workspace setup

See the [issues](https://github.com/yourusername/vsc-sync-cli/issues) for planned features and current development status.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.