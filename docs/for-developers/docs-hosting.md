# Hosting the documentation site

This page shows how to publish the MkDocs-generated site so everyone can read
it at `https://your-org.github.io/vsc-sync-cli/`.

We’ll use **GitHub Pages** because it’s free, requires zero infra and integrates
directly with the repository’s CI workflow.

---

## 1 · Create a deploy token (one-off)

If your repository is **public**, GitHub Actions can push to the `gh-pages`
branch without any extra permission.

For **private** repos you need a classic Personal Access Token (PAT) with the
`repo` scope stored as a secret (e.g. `GH_PAGES_TOKEN`).

---

## 2 · Add the workflow file

Create `.github/workflows/docs.yml` (already scaffolded below).  The workflow:

1. Checks out the repo
2. Sets up Python 3.11
3. Installs the MkDocs tool-chain
4. Runs `mkdocs gh-deploy --force` which builds the site and pushes **only**
   the static HTML into the `gh-pages` branch.

```yaml
name: Docs

on:
  push:
    branches: [main]

permissions:
  contents: write            # allow push to gh-pages

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install MkDocs stack
        run: |
          python -m pip install --upgrade pip
          pip install mkdocs mkdocs-material \
                     mkdocstrings[python] \
                     mkdocs-gen-files \
                     mkdocs-section-index \
                     mkdocs-git-revision-date-localized-plugin

      - name: Deploy
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}  # or GH_PAGES_TOKEN for private repos
        run: |
          mkdocs gh-deploy --clean --force
```

Commit and push this file to `main`.  GitHub Actions will build and deploy the
docs on every push.

---

## 3 · Enable Pages in repository settings

1. Go to **Settings → Pages**.
2. Source: choose **GitHub Actions**.
3. Branch: select `gh-pages` if prompted.
4. Click **Save**.

GitHub will allocate a public URL such as
`https://<username>.github.io/vsc-sync-cli/`.  You can also add a custom domain.

---

## 4 · Local preview vs production

* `mkdocs serve` — fast live-reload while editing docs.
* `mkdocs gh-deploy --force --message "preview" --dry-run` — build exactly what
  CI will ship but don’t push it (good for troubleshooting warnings).

---

## 5 · Troubleshooting

| Symptom                               | Fix                                             |
|---------------------------------------|-------------------------------------------------|
| 404 after clicking a link             | Enable **`use_directory_urls: true`** (default) |
| Old content despite successful deploy | Clear browser cache; Pages caches aggressively |
| Build fails on CI but not locally     | Pin package versions in `requirements-docs.txt` |

---

Happy documenting! 🚀
