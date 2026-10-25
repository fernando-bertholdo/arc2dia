# Changelog

## 0.1.2 (2026-10-24)

- `swap --allow-other-source` (testing only): install a cleaned file prepared from a different
  sidebar, such as the synthetic example, so the whole flow can be tested on a Mac without giving
  Dia your own data. The current Arc file is still backed up and restored.
- README: quick start, honest status line, real clone URL.

## 0.1.1 (2026-10-24)

Fixes from the first run on a real sidebar.

- Arc tab groups (`data.tabGroup`) among open tabs were treated as unsupported, so the tabs
  inside them were left behind (82 of 87 in one space). Their tabs now move with the other open
  tabs. By default the group wrappers are flattened in order; `open_tabs_tab_groups: "subfolders"`
  (`--tab-groups subfolders`) makes one subfolder per group instead. A tab group in the pinned area
  is handled like a folder by every strategy.
- Tabs without a saved URL broke validation ("duplicate  was removed but no other copy survives")
  and were reported as dropped. They are no longer deduplicated, exported or dropped: they stay in
  the sidebar, with "no URL" as the reason in the report. A folder that holds no URLs is never
  treated as a duplicate tree.
- `bookmarks.html` now merges sibling folders with the same name (for example two "Imported From
  Edge" trees) and keeps one copy of a URL per folder. Turn it off with
  `merge_bookmark_folders: false` (`--no-merge-bookmark-folders`).
- `scan` reports tab groups and tabs without a URL; the synthetic fixture gained a "Research" space
  that covers these cases.

## 0.1.0 (2026-10-24)

First version.

- `scan`: read-only diagnosis per space (pinned tabs, folders and nesting depth, open tabs, split views,
  favorites, non-web URLs, duplicate folder trees, repeated URLs) with a prediction of what Dia's
  importer will create and what it will drop. Text, `--json` or `--tree` output.
- `plan`: writes a JSON plan with per-space choices and a what-if table for each folder strategy
  (`keep`, `path-names`, `merge-to-top`, `to-bookmarks`), per-folder overrides, duplicate removal,
  open-tab handling, empty-folder cleanup, non-web link export and space exclusion.
- `prepare`: applies the plan to a copy, writes the cleaned `StorableSidebar.json` and a nested
  Netscape `bookmarks.html`, then re-reads both and checks shape, id integrity and that every original
  URL is accounted for.
- `swap` / `restore` / `status`: dry run by default; refuse while Arc runs; timestamped backups with
  SHA-256 checks; byte-for-byte restore; nothing is ever deleted.
- `verify`: reads Dia's profiles and tab URLs through a read-only AppleScript and compares them with
  Arc per profile and per URL, explaining expected differences.
