# Quick start

Follow this guide if you want to get up and running in less than five minutes.

```bash
# 1. Install the CLI from source
git clone https://github.com/your-org/vsc-sync-cli.git
cd vsc-sync-cli

# (optional but recommended)
python -m venv .venv && source .venv/bin/activate

# Editable install so changes are picked up immediately
pip install -e .[cli]

# 2. Create an empty private repository on GitHub (or GitLab, Gitea…)

# 3. Initialise sync on the *first* machine
vsc-sync init git@github.com:your-user/dotfiles-vscode.git

# 4. Tweak VS Code to your liking

# 5. Persist changes to the repo
vsc-sync edit -m "Initial VS Code setup"

# 6. On any *other* machine (with vsc-sync installed)
vsc-sync apply
```

Repeat steps 4–5 whenever you modify your local VS Code configuration.  On other machines simply run `vsc-sync apply` to pull the updates.
