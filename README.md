# arc2dia

Move your Arc sidebar to Dia without losing your open tabs or the shape of your nested folders.

arc2dia is a small command-line tool for macOS. It does not replace Dia's own Arc importer: it
prepares a cleaned copy of Arc's sidebar file, lets the official importer read that copy, and then
puts your original file back, byte for byte. It is written in plain Python 3.9+ with no
dependencies and no network access.

Status: v0. The cleaning approach was used in a real migration (Dia imported the cleaned file as
expected), and `scan`, `prepare` and `verify` were checked against real Arc and Dia data. The
`swap` and `restore` commands are covered by tests but have not yet run end to end on a real Mac.
Arc's and Dia's formats are undocumented and may change. Read the safety notes before you use it.

## Quick start

```sh
git clone https://github.com/fernando-bertholdo/arc2dia.git && cd arc2dia
python3 -m arc2dia scan                      # see what Dia's importer would do (read-only)
python3 -m arc2dia prepare                   # write a cleaned copy to arc2dia-out/
# quit Arc, then:
python3 -m arc2dia swap --apply              # put the cleaned copy in Arc's place
# in Dia: Dia > Import from Another Browser... > Arc, and wait for it to finish
python3 -m arc2dia restore --apply           # put your original Arc file back
python3 -m arc2dia verify --prepared arc2dia-out
```

Read "The safe workflow" below before running `swap` for real.

## Use it as an Agent Skill

`skill/arc2dia/` is an Agent Skill: a `SKILL.md` plus the whole tool in one file,
`scripts/arc2dia.pyz`. Copy the folder into your agent's skills folder (for Claude Code,
`~/.claude/skills/arc2dia/`) and ask it to migrate your Arc spaces, folders and open tabs to Dia.
The skill walks the agent through the same workflow: it shows you the plan, asks you to quit Arc,
waits while you run Dia's importer, always restores your original file, and never opens tabs.
If your agent's permission check stops `swap --apply`, approve it in your app; the skill tells the
agent never to work around it.

`scripts/build_skill.sh` rebuilds the archive after a code change. `evals/skill/` holds the test
harness, and `evals/skill/RESULTS.md` describes how Haiku, Sonnet and Opus did with three levels of
detail in the instructions. The shipped `SKILL.md` is the most detailed level.

## Why

Arc shuts down on December 22, 2026. Dia, from the same company, has an official importer
(Dia > Import from Another Browser... > Arc, also offered during first-run onboarding). It turns
each Arc Space into a Dia Profile and each Arc folder into a pinned Tab Group, and it keeps
Favorites, pinned tabs, bookmarks, history, passwords, cookies and extensions.

Two things go wrong, though:

**Open tabs are not imported.** Arc's open ("Today", unpinned) tabs did not come over at all in a
real migration: 0 of 210, even though the help article says they do.

**Nested folders are flattened.** Dia cannot nest Tab Groups, so every nested Arc folder becomes its
own top-level pinned group, named only after itself. A space with 116 folders, 112 of them nested
up to 5 levels deep, became over a hundred flat groups in one long list, each with no hint of
where it came from. Most of them were two copies of the same old "Imported From Edge" bookmark
tree.

Re-creating the missing tabs by script is not a good fix either. Tabs created through Dia's
AppleScript load immediately, and opening about 50 at once froze a 16 GB Mac. Tabs that come in
through the importer stay unloaded until you click them. arc2dia therefore never opens tabs in Dia;
it only changes what the importer sees.

## What Dia's importer does, and what arc2dia changes

| In Arc | Dia's importer | With arc2dia |
| --- | --- | --- |
| Space | New Profile (every import creates new ones) | Same; a space can also be left out |
| Pinned tabs | Pinned tabs, unloaded until clicked | Same |
| Top-level folder | Pinned Tab Group | Same |
| Nested folder | Its own flat group, named after itself only | Your choice of four strategies (below) |
| Open (Today) tabs, including Arc tab groups | Not imported | Moved into one pinned folder, "Open tabs from Arc"; tab groups are flattened or become subfolders |
| Duplicate folder trees | Imported twice | Optionally removed when every URL survives elsewhere |
| Favorites | Kept | Not touched |
| `file:`, `data:`, `javascript:`, `chrome-extension:` links | Dropped | Reported; optionally exported to `bookmarks.html` |
| Easels, Arc notes/documents | No equivalent | Reported and left in place |
| Tabs with no saved URL | Unknown | Never removed, deduplicated or exported; left in the sidebar and listed with "no URL" |

## How it works

Dia's importer reads Arc's `~/Library/Application Support/Arc/StorableSidebar.json`. With Arc
quit, arc2dia moves that file into a backup folder, puts a cleaned copy in its place, and waits
while you run Dia's importer. Then it copies the original back and checks its SHA-256 hash. Arc
must stay closed the whole time: when Arc Sync is on (the file has `sidebarSyncState` or
`firebaseSyncState`), an open Arc could upload the modified sidebar to your other devices.

Dia's encrypted `tabs.db` cannot be edited, and Dia's AppleScript has no access to tab groups, so
changing the importer's input is the only safe lever.

## Requirements

macOS with Arc and Dia installed, and Python 3.9 or newer. The `python3` that ships with macOS
(3.9, installed with the Command Line Tools) is enough. `scan`, `plan` and `prepare` also run on
other systems if you pass `--sidebar` with a copy of the file.

Run it from a checkout, without installing anything:

```sh
git clone https://github.com/fernando-bertholdo/arc2dia.git && cd arc2dia
python3 -m arc2dia --help
```

Or install the `arc2dia` command with `pipx install .` (or `pip install --user .`).

## The safe workflow

The examples use `arc2dia`; from a checkout, type `python3 -m arc2dia` instead.

**1. Look first.** Nothing is written.

```sh
arc2dia scan            # per-space counts and what Dia's importer would do
arc2dia scan --tree     # the folder outline of each space
```

**2. Make a plan.** This writes `arc2dia-plan.json` and prints, for every space, what Dia would end
up with under each folder strategy, so you can compare before choosing.

```sh
arc2dia plan
arc2dia plan --strategy merge-to-top --override "Imported From Edge=to-bookmarks" --force
```

Edit the file if you want per-space choices (see "Plan file" below).

**3. Prepare.** This applies the plan to a copy and writes everything into `arc2dia-out/`. It then
re-reads the files it wrote and checks them: the file keeps Arc's shape, no id points to a missing
item, and every original URL is accounted for (still in the sidebar, in `bookmarks.html`, removed
as a duplicate with a surviving copy, or dropped with a stated reason).

```sh
arc2dia prepare --plan arc2dia-plan.json
arc2dia scan --tree --sidebar arc2dia-out/StorableSidebar.cleaned.json   # inspect the result
```

**4. Quit Arc** completely (Arc > Quit Arc). Leave it closed until the restore in step 8 is done.

**5. Swap.** Without `--apply` this only prints what it would do.

```sh
arc2dia swap
arc2dia swap --apply
```

It refuses if Arc is running, if the sidebar file changed since `prepare`, if validation failed or
if another swap is still active. The original goes to `~/arc2dia-backups/<timestamp>/`.

**6. Optional: start from a fresh Dia.** Each import creates new profiles and never merges into
existing ones, so importing into a Dia you already used gives you a second set. To start clean,
quit Dia and set its data aside. `swap` prints these commands with a timestamped folder name; the
tool never runs them for you.

```sh
mkdir -p "$HOME/dia-reset-backup"
defaults export company.thebrowser.dia "$HOME/dia-reset-backup/company.thebrowser.dia.plist"
mv "$HOME/Library/Application Support/Dia" "$HOME/dia-reset-backup/Dia"
defaults delete company.thebrowser.dia
```

To undo it later, quit Dia, move the new `Dia` folder aside, move the saved one back, and run
`defaults import company.thebrowser.dia "$HOME/dia-reset-backup/company.thebrowser.dia.plist"`.

**7. Import in Dia.** Open Dia and choose Dia > Import from Another Browser... > Arc (a fresh Dia
offers it during onboarding). Wait until the new profiles appear. Imported pinned tabs only load
when you click them; do not open them all at once.

**8. Restore** the original Arc file. Again, dry run first.

```sh
arc2dia restore
arc2dia restore --apply
```

The original is copied back from the backup and its hash is checked. The backup stays where it is.

**9. Verify.** This reads Dia's profile names and tab URLs (read-only) and compares them with what
Dia was given. Dia must be running with a window open; macOS may ask you to allow your terminal to
control Dia.

```sh
arc2dia verify --prepared arc2dia-out
```

Differences that are expected are explained: non-web links Dia drops, open tabs you chose to leave,
Favorites, tabs you opened after the import, URLs that differ only by a trailing slash. Anything
else is listed as missing. If a profile name does not match its space, pair them with
`--map "Arc space=Dia profile"`.

**10. Open Arc again.** `arc2dia status` tells you at any time whether a swap is still active.

## Folder strategies

Take this Arc folder:

```
Imported From Edge          1 tab
  Dev                       1 tab
    Python                  2 tabs
```

| Strategy | What Dia gets |
| --- | --- |
| `keep` | Dia's default: three flat groups, "Imported From Edge", "Dev" and "Python" |
| `path-names` | Three flat groups named "Imported From Edge", "Imported From Edge › Dev" and "Imported From Edge › Dev › Python". Folders that hold only subfolders disappear, since their names live on in the paths |
| `merge-to-top` | One group, "Imported From Edge", with all four tabs in their original order |
| `to-bookmarks` | Nothing in the sidebar; the whole tree, nested, goes to `bookmarks.html` |

Arc tab groups in the pinned area count as folders for every strategy. A strategy applies to a
space's top-level folders. Each top-level folder can have its own
strategy, and a nested folder can be sent to `to-bookmarks` on its own; its parent folders are
recreated in `bookmarks.html` so it keeps its place. When `plan` is run without `--strategy`, spaces
with nested folders get `path-names` and the others `keep`.

When two exported trees share a name, such as two "Imported From Edge" imports, they become one
folder in `bookmarks.html`, with repeated URLs kept once per folder (`merge_bookmark_folders`).
`bookmarks.html` uses the Netscape bookmark format that browsers import and export. Chromium-based
browsers can import it; check whether your Dia version offers an HTML bookmarks import, or keep the
file as an archive.

## Plan file

`plan` writes JSON. Keys starting with `_` are information for you (counts, the what-if table,
the list of top-level folders with their ids) and are ignored when the plan is read. Each space has:

| Key | Values | Default |
| --- | --- | --- |
| `import` | `true`, or `false` to leave the space out (no Dia profile is created for it) | `true` |
| `folder_strategy` | `keep`, `path-names`, `merge-to-top`, `to-bookmarks` | `path-names` if nested, else `keep` |
| `folder_overrides` | list of `{"path": "A › B", "strategy": ...}` or `{"folder_id": ..., "strategy": ...}` | `[]` |
| `dedupe_trees` | remove a folder tree when another folder with the same name holds all its URLs | `true` |
| `dedupe_urls` | remove repeated URLs in the pinned area, keeping the first copy | `false` |
| `open_tabs` | `pinned-folder`, `bookmarks` or `leave` | `pinned-folder` |
| `open_tabs_folder_name` | any name | `Open tabs from Arc` |
| `open_tabs_split_views` | `flatten` (split views become separate tabs) or `keep` | `flatten` |
| `open_tabs_tab_groups` | `flatten` (tabs from Arc tab groups go straight into the folder, in order) or `subfolders` (one subfolder per group; Dia then shows each as its own flat group) | `flatten` |
| `drop_empty_folders` | remove folders left with nothing in them | `true` |
| `non_web` | `keep` (Dia drops them) or `to-bookmarks` | `keep` |
| `merge_bookmark_folders` | in `bookmarks.html`, merge sibling folders with the same name and keep one copy of a URL per folder | `true` |

Override paths can be written with " › " or " > " between folder names. A path matches every folder
with that full path, so `"Imported From Edge"` catches both copies of a duplicated import.
Duplicate trees are only removed automatically when the folders share a name; folders with
different names but overlapping content are reported by `scan` and left alone.

## What `prepare` writes

All files go into the output folder (`arc2dia-out/` by default), never into Arc's folder:
`StorableSidebar.cleaned.json` (the file Dia will read), `bookmarks.html` (only when something was
exported), `plan.json` (the plan as applied), `report.txt`, `report.json` (with a ledger entry for
every original tab: where it was, what happened to it and why) and `manifest.json` (hashes that
`swap` checks).

These files contain your browsing data. Do not commit or share them.

## Safety guarantees

arc2dia never deletes a file. Files are moved into backup folders or copied, and a test checks that
the code has no delete calls. The only files it overwrites are its own: earlier outputs (only with
`--force`) and its bookkeeping files in the backup folder.

`scan`, `plan`, `prepare` and `verify` do not touch Arc's or Dia's data. `swap` and `restore` are dry
runs unless you pass `--apply`. They check that Arc is not running (`pgrep -x Arc`) before starting
and again right before moving the file. `swap` also refuses when the sidebar file changed since
`prepare`, when validation failed, when the cleaned file was modified, or when a swap is already
active. The original is moved, not rewritten, into a timestamped folder and its hash is checked.
`restore` copies it back and checks the hash again; if the file in Arc's folder changed while
swapped, that version is kept in the backup folder too, not overwritten.

`verify` runs an AppleScript that only reads profile names, tab titles and URLs. It never creates,
loads, closes or focuses tabs, and it does not launch Dia. Print it with `arc2dia verify --print-script`.

There is no network access: the package uses only the Python standard library and imports no
networking module (also checked by a test).

## Limits

`swap`, `restore` and `verify` need macOS. Arc and Dia also run on Windows, where Arc keeps the
sidebar file elsewhere; that path is untested.

Arc's `StorableSidebar.json` and Dia's importer are undocumented. This tool is based on what was
observed in October 2026 and may break with any update of either browser. The prediction of how
many groups Dia creates is an estimate, which is why `scan` shows a range when some folders hold
only subfolders.

Leaving a space out (`"import": false`) removes it from the cleaned file's space list. That is the
least tested option.

Easels and Arc documents have no Dia equivalent and are not migrated. Tabs with no saved URL are
kept as they are; whether Dia imports them is unknown. Non-web links are dropped by
Dia unless you export them to `bookmarks.html`.

If Arc is opened while the cleaned file is in place and Sync is on, the cleaned sidebar may reach
your other devices. `restore` puts the local file back, but it cannot undo a sync. Keep Arc closed.

arc2dia is an independent project. It is not affiliated with, endorsed by or supported by The
Browser Company or Atlassian. Arc and Dia are their trademarks.

## Development

```sh
python3 -m pip install pytest   # the only thing the tests need
python3 -m pytest
```

Tests use synthetic sidebars built by `tests/fixturegen.py` (all URLs use reserved `example.*`
domains); `examples/synthetic-StorableSidebar.json` is one of them, ready for
`arc2dia scan --sidebar examples/synthetic-StorableSidebar.json`. Everything that touches macOS
(`pgrep`, `osascript`) sits behind small interfaces, so the suite runs anywhere.

To test the whole flow on a Mac without giving Dia your own data, prepare the synthetic example and
install it with `arc2dia swap --apply --allow-other-source`. Normally `swap` refuses a cleaned file
that was not prepared from the current Arc file; this flag lets it through for testing, and your
real Arc file is still backed up and restored as usual. Do this with Dia's data set aside (step 6),
so the test profiles land in a throwaway Dia.

The code lives in `arc2dia/`: `model.py` (file format), `analysis.py` (scan and prediction),
`plan.py`, `transform.py` (the strategies), `bookmarks.py`, `validate.py`, `prepare.py`,
`swap.py`, `dia.py` (AppleScript), `verify.py` and `cli.py`.

## License

MIT. See `LICENSE`.
