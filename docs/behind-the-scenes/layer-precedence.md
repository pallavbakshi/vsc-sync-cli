# Layer precedence & conflict resolution

When **VSC Sync CLI** builds the final VS Code configuration for a machine it
combines several *layers* of files. If the same setting appears in more than
one layer, the **layer applied last wins**.  This page explains the exact order
and the logic behind it.

## Precedence order

```
base   ← lowest priority
app
stack(s)  ← highest priority (last one wins if multiple)
```

1. **base/** – settings/snippets/extensions that should apply *everywhere*.
2. **apps/<alias>/** – overrides specific to the running editor (VS Code,
   VSCodium, Cursor, …).
3. **stacks/<name>/** – language- or framework-specific tweaks, e.g. `python`,
   `web-dev`. If you pass multiple `--stack` options, they are applied in the
   order given on the command line and the *right-most* one has the final say.

Projects
:   `projects/<repo-name>/` layers sit outside this automatic merge because they
    are copied verbatim into the **workspace folder** rather than into the
    global user-profile.

## What happens on conflict?

The merge algorithm lives in
`vsc_sync/core/config_manager.py → LayerConfigManager.deep_merge_dicts`.

• For every duplicate key, the value coming from the **later layer** replaces
  the previous one. 
• Nested dictionaries are merged recursively, so only the conflicting subtree
  is replaced, not the entire parent.
• Lists (like the `recommendations` array in `extensions.json`) are
  *concatenated* and deduplicated to avoid duplicates.

### Example

Assume the setting `"editor.tabSize"` is defined in all three layers:

| Layer | Value |
|-------|-------|
| base  | `2`   |
| app   | `4`   |
| stack | `8`   |

Final output after `vsc-sync apply` → `"editor.tabSize": 8`.

## Keybindings & snippets

* `keybindings.json` is **not merged**. The file from the *most specific* layer
  that provides it is copied (search order: last stack → first stack → app →
  base).
* Snippets directories from *all* layers are unioned and copied into the
  target VS Code profile.

### Why keybindings are not merged

VS Code represents keybindings as an **ordered list of objects**. If two layers
define shortcuts for the same keystroke VS Code keeps **both** entries and only
the *last one defined in the file wins*, so naïvely concatenating JSON arrays
can lead to unpredictable behaviour.

To keep things explicit vsc-sync takes the first `keybindings.json` it finds
when scanning layers from most-specific to least and copies it verbatim into
the user profile.  That means you get one authoritative place to edit
shortcuts per machine configuration.

If you *need* different keybindings for, say, Linux vs macOS: put the file in
the corresponding **app layer** (`apps/vscode-linux/`, `apps/vscode-macos/`, …)
or create dedicated stacks (e.g. `stacks/linux`) and pass the appropriate
`--stack` flag when applying.

## Take-away

> When two layers disagree, ask “which one is applied last?” — that layer wins.

Keeping this mental model in mind makes it easy to reason about the final
configuration, even with many stacks and editor variants in play.
