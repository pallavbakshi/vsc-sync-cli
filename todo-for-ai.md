# TODO – tasks.json support rollout

Checklist tracking the implementation and release of *tasks.json* syncing in
VSC Sync CLI.  Completed items are ticked; remaining work sits unchecked.

## ✅ Implemented & tested

- [x] Design & scope agreed (user-level, winner-takes-all)
- [x] Data-model updated (`tasks_source` in `MergeResult`)
- [x] Core merge logic (`find_tasks_file`, precedence tests)
- [x] File operations (`_apply_tasks`, copy logic tests)
- [x] Application orchestration (apply, dry-run, cleanup)
- [x] CLI surface (`--tasks / --no-tasks`, edit support)
- [x] Documentation (usage, layer precedence, template example)
- [x] Automated tests (unit + CLI integration)

## 🔜 Remaining

- [ ] Changelog & version bump
  - [ ] Add “Added: tasks.json syncing” entry to `docs/changelog.md`.
  - [ ] Bump version in `pyproject.toml` & `src/vsc_sync/__init__.py`.

- [ ] CI & code-quality
  - [ ] Run `pre-commit run --all-files`; fix any new linting issues.
  - [ ] Ensure full `pytest` suite passes in CI.

- [ ] Release
  - [ ] Merge PR, tag new version, push to origin.
  - [ ] Verify GitHub Pages deploys updated docs.

- [ ] Post-release smoke test
  - [ ] On a clean machine: clone config repo with `tasks.json`, run
        `vsc-sync apply`, confirm tasks appear in “Tasks: Run Task…”.
