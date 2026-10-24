"""Synthetic StorableSidebar.json files that mimic the observed format. No real user data.

Run ``python3 tests/fixturegen.py`` to regenerate examples/synthetic-StorableSidebar.json.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

NAMESPACE = uuid.UUID("6f1c3a52-7d0e-4b8e-9a35-2b8f4f0c9e11")
DEVICE = "SYNTHETIC-DEVICE-0001"
DEFAULT_PROFILE = {"default": True}
CUSTOM_PROFILE = {"custom": {"_0": {"directoryBasename": "Profile 1", "machineID": "SYNTHETIC-MACHINE"}}}


class Builder:
    def __init__(self, seed: str = "fixture", sync: bool = True):
        self.seed = seed
        self.sync = sync
        self.items: List[Tuple[str, dict]] = []
        self.index = {}
        self.spaces: List[Tuple[str, dict]] = []
        self.top_apps: list = []
        self.counter = 0
        self.clock = 700000000.0  # Apple epoch seconds (2023-03-07)

    def _id(self) -> str:
        self.counter += 1
        return str(uuid.uuid5(NAMESPACE, f"{self.seed}-{self.counter}")).upper()

    def _tick(self) -> float:
        self.clock += 61.5
        return self.clock

    def _add(self, parent: Optional[str], title, data: dict, item_id: Optional[str] = None) -> str:
        item_id = item_id or self._id()
        obj = {
            "id": item_id,
            "title": title,
            "isUnread": False,
            "createdAt": self._tick(),
            "originatingDevice": DEVICE,
            "parentID": parent,
            "childrenIds": [],
            "data": data,
        }
        self.items.append((item_id, obj))
        self.index[item_id] = obj
        if parent is not None and parent in self.index:
            self.index[parent]["childrenIds"].append(item_id)
        return item_id

    # -- building blocks

    def space(self, title: Optional[str], profile=None) -> Tuple[str, str, str]:
        space_id = self._id()
        pinned = self._add(None, None, {"itemContainer": {"containerType": {"spaceItems": {"_0": space_id}}}})
        unpinned = self._add(None, None, {"itemContainer": {"containerType": {"spaceItems": {"_0": space_id}}}})
        obj = {
            "id": space_id,
            "title": title,
            "profile": profile if profile is not None else DEFAULT_PROFILE,
            "customInfo": {"iconType": {"icon": "star"}, "windowTheme": {"semanticColorPalettes": {}}},
            "newContainerIDs": [{"pinned": {}}, pinned, {"unpinned": {"_0": {"shared": {}}}}, unpinned],
            "containerIDs": ["pinned", pinned, "unpinned", unpinned],
        }
        self.spaces.append((space_id, obj))
        return space_id, pinned, unpinned

    def favorites(self, profile=None) -> str:
        profile = profile if profile is not None else DEFAULT_PROFILE
        cid = self._add(None, None, {"itemContainer": {"containerType": {"topApps": {"_0": profile}}}})
        self.top_apps.extend([profile, cid])
        return cid

    def folder(self, parent: str, title: Optional[str]) -> str:
        return self._add(parent, title, {"list": {}})

    def tab(self, parent: str, url: str, title: Optional[str] = "", saved_title: Optional[str] = None) -> str:
        if title == "":
            title = url.split("//")[-1].split("/")[0] or url
        t = self._tick()
        data = {
            "tab": {
                "savedURL": url,
                "savedTitle": saved_title if saved_title is not None else (title or ""),
                "timeLastActiveAt": t,
                "savedMuteStatus": "allowAudio",
            }
        }
        return self._add(parent, title, data)

    def split(self, parent: str, urls: List[str]) -> str:
        sid = self._add(parent, None, {"splitView": {"layoutOrientation": "horizontal", "timeLastActiveAt": self._tick()}})
        for url in urls:
            self.tab(sid, url)
        return sid

    def tab_group(self, parent: str, title: str) -> str:
        """An Arc tab group as seen among open tabs: name in data.tabGroup.title, null title and device."""
        gid = self._add(parent, None, {"tabGroup": {"title": title}})
        self.index[gid]["originatingDevice"] = None
        return gid

    def urlless_tab(self, parent: str, saved_title: str, title: Optional[str] = None,
                    before: Optional[str] = None) -> str:
        """A tab item with no savedURL at all (seen in real files)."""
        data = {"tab": {"savedMuteStatus": "allowAudio", "timeLastActiveAt": self._tick(), "savedTitle": saved_title}}
        if before is not None:
            data["tab"]["activeTabBeforeCreationID"] = before
        return self._add(parent, title, data)

    def easel(self, parent: str, title: str) -> str:
        return self._add(parent, title, {"easel": {"easelID": self._id(), "title": title}})

    def document(self, parent: str, title: str) -> str:
        return self._add(parent, title, {"arcDocument": {"arcDocumentID": self._id()}})

    def orphan_tab(self, url: str) -> str:
        return self._add("MISSING-PARENT-ID", url, {"tab": {"savedURL": url, "savedTitle": url}})

    def build(self) -> dict:
        items: list = []
        for item_id, obj in self.items:
            items.extend([item_id, obj])
        spaces: list = []
        for space_id, obj in self.spaces:
            spaces.extend([space_id, obj])
        raw = {
            "sidebar": {
                "containers": [
                    {"global": {}},
                    {"spaces": spaces, "items": items, "topAppsContainerIDs": list(self.top_apps)},
                ]
            },
            "version": 1,
        }
        if self.sync:
            raw["sidebarSyncState"] = {"container": {"value": {"orderedSpaceIDs": [s for s, _ in self.spaces]}}}
            raw["firebaseSyncState"] = {"syncData": {"lastSyncedAt": 0}, "userID": "SYNTHETIC-USER"}
        return raw


def edge_tree_with_layer(b: Builder, parent: str) -> str:
    """'Imported From Edge' with the extra 'Favorites bar' / 'Other favorites' layer (5 levels deep)."""
    root = b.folder(parent, "Imported From Edge")
    bar = b.folder(root, "Favorites bar")
    dev = b.folder(bar, "Dev")
    py = b.folder(dev, "Python")
    libs = b.folder(py, "Libraries")
    b.tab(libs, "https://pypi.example.org/project/requests", "requests")
    b.tab(libs, "https://pypi.example.org/project/attrs", "attrs")
    b.tab(py, "https://docs.python.example.org/3/", "Python docs")
    b.tab(dev, "https://git.example.com/", "Git host")
    b.tab(bar, "https://news.example.com/", "News")
    other = b.folder(root, "Other favorites")
    b.tab(other, "https://recipes.example.net/bread", "Bread")
    b.tab(other, "javascript:alert('bookmarklet')", "A bookmarklet")
    return root


def edge_tree_flat(b: Builder, parent: str) -> str:
    """The same bookmarks imported again, without the extra layer."""
    root = b.folder(parent, "Imported From Edge")
    dev = b.folder(root, "Dev")
    py = b.folder(dev, "Python")
    libs = b.folder(py, "Libraries")
    b.tab(libs, "https://pypi.example.org/project/requests", "requests")
    b.tab(libs, "https://pypi.example.org/project/attrs", "attrs")
    b.tab(py, "https://docs.python.example.org/3/", "Python docs")
    b.tab(dev, "https://git.example.com/", "Git host")
    b.tab(root, "https://news.example.com/", "News")
    b.tab(root, "https://recipes.example.net/bread", "Bread")
    b.tab(root, "javascript:alert('bookmarklet')", "A bookmarklet")
    return root


def research_space(b: Builder) -> None:
    """Tab groups, tabs without a URL and same-named trees that do not contain each other."""
    _, pinned, unpinned = b.space("Research")
    b.tab(pinned, "https://research.example.org/home", "Research home")
    reading = b.tab_group(pinned, "Reading list")
    b.tab(reading, "https://papers.example.org/1", "Paper 1")
    b.tab(reading, "https://papers.example.org/2", "Paper 2")
    edge_c = b.folder(pinned, "Imported From Edge")
    tools_c = b.folder(edge_c, "Tools")
    b.tab(tools_c, "https://tools.example.com/a", "Tool A")
    b.tab(tools_c, "https://tools.example.com/c", "Tool C")
    b.urlless_tab(tools_c, "Untitled draft")
    b.tab(edge_c, "https://shared.example.com/x", "Shared X")
    edge_d = b.folder(pinned, "Imported From Edge")
    tools_d = b.folder(edge_d, "Tools")
    b.tab(tools_d, "https://tools.example.com/a", "Tool A")
    b.tab(tools_d, "https://tools.example.com/b", "Tool B")
    b.tab(edge_d, "https://other.example.com/y", "Other Y")
    snippets = b.folder(pinned, "Snippets")
    b.tab(snippets, "https://snip.example.com/1", "Snippet 1")
    b.urlless_tab(snippets, "Blank snippet", title="Blank snippet")
    archive = b.folder(pinned, "Archive")
    old = b.folder(archive, "Snippets")  # identical copy that also holds a tab without URL
    b.tab(old, "https://snip.example.com/1", "Snippet 1")
    b.urlless_tab(old, "Blank snippet", title="Blank snippet")

    b.tab(unpinned, "https://inbox.example.org/", "Inbox")
    trip = b.tab_group(unpinned, "Trip planning")
    b.tab(trip, "https://flights.example.com/", "Flights")
    hotels = b.tab(trip, "https://hotels.example.com/", "Hotels")
    b.urlless_tab(trip, "New Tab", before=hotels)
    shop = b.tab_group(unpinned, "Shopping")
    b.tab(shop, "https://shop.example.com/cart", "Cart")
    b.tab(shop, "https://compare.example.com/", "Compare")
    b.tab(unpinned, "file:///Users/example/notes.txt", "notes.txt")


def rich_sidebar(orphan: bool = False, sync: bool = True) -> dict:
    """Four spaces covering every case the tool handles. See tests/test_scan.py for the counts."""
    b = Builder(sync=sync)

    # Space "Work"
    _, pinned, unpinned = b.space("Work")
    b.tab(pinned, "https://wiki.example.com/", "Team Wiki")
    b.split(pinned, ["https://docs.example.com/a", "https://docs.example.com/b"])
    projects = b.folder(pinned, "Projects")
    b.tab(projects, "https://alpha.example.com/board", "Alpha board")
    alpha = b.folder(projects, "Alpha")
    b.tab(alpha, "https://alpha.example.com/spec", "Alpha spec")
    b.tab(alpha, "https://alpha.example.com/notes", None, saved_title="Alpha notes")
    beta = b.folder(projects, "Beta")
    b.tab(beta, "https://beta.example.com/", "Beta")
    b.tab(beta, "https://wiki.example.com/", "Team Wiki (again)")
    edge_tree_with_layer(b, pinned)
    edge_tree_flat(b, pinned)
    b.folder(pinned, "Empty folder")
    untitled = b.folder(pinned, None)
    b.tab(untitled, "file:///Users/example/Documents/report.pdf", "report.pdf")
    b.tab(untitled, "chrome-extension://abcdefghijklmnop/options.html", "Extension options")
    shells = b.folder(pinned, "Shells")
    b.folder(shells, "Inner")
    b.easel(pinned, "Moodboard")

    b.tab(unpinned, "https://mail.example.com/inbox", "Inbox")
    b.split(unpinned, ["https://calendar.example.com/", "https://meet.example.com/room"])
    b.tab(unpinned, "https://wiki.example.com/", "Team Wiki")
    b.tab(unpinned, "https://search.example.com/?q=arc+to+dia", None, saved_title="")
    b.tab(unpinned, "data:text/plain,hello", "data URL")
    b.tab(unpinned, "about:blank", "Blank")
    b.document(unpinned, "Scratch notes")

    # Space "Personal" (another Arc profile)
    _, pinned, unpinned = b.space("Personal", CUSTOM_PROFILE)
    recipes = b.folder(pinned, "Recipes")
    b.tab(recipes, "https://recipes.example.net/soup", "Soup <& \"quotes\">")
    b.tab(recipes, "https://recipes.example.net/cake", "Cake")
    reading = b.folder(pinned, "Reading")
    copy = b.folder(reading, "Recipes")
    b.tab(copy, "https://recipes.example.net/soup", "Soup <& \"quotes\">")
    b.tab(copy, "https://recipes.example.net/cake", "Cake")
    b.tab(reading, "https://books.example.org/list", "Book list")
    b.tab(pinned, "https://bank.example.com/", "Bank")
    b.tab(unpinned, "https://video.example.com/watch?v=123", "A video")
    b.tab(unpinned, "https://shop.example.com/cart", "Cart")

    # A space without a title
    _, pinned, unpinned = b.space(None)
    b.tab(unpinned, "https://scratch.example.com/", "Scratch")

    research_space(b)

    fav = b.favorites(DEFAULT_PROFILE)
    b.tab(fav, "https://chat.example.com/", "Chat")
    b.tab(fav, "https://music.example.com/", "Music")
    fav2 = b.favorites(CUSTOM_PROFILE)
    b.tab(fav2, "https://bank.example.com/", "Bank")

    if orphan:
        b.orphan_tab("https://orphan.example.com/")
    return b.build()


def deep_sidebar(levels: int = 5, tabs_per_level: int = 2) -> dict:
    """One space with a single chain of nested folders, each holding a few tabs."""
    b = Builder(seed="deep")
    _, pinned, _ = b.space("Deep")
    parent = pinned
    for level in range(1, levels + 1):
        parent = b.folder(parent, f"Level {level}")
        for n in range(tabs_per_level):
            b.tab(parent, f"https://deep.example.com/l{level}/t{n}", f"L{level} T{n}")
    return b.build()


EXAMPLE_PATH = Path(__file__).resolve().parent.parent / "examples" / "synthetic-StorableSidebar.json"


def dump(raw: dict) -> str:
    return json.dumps(raw, indent=2, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    EXAMPLE_PATH.parent.mkdir(exist_ok=True)
    EXAMPLE_PATH.write_text(dump(rich_sidebar()), encoding="utf-8")
    print(f"wrote {EXAMPLE_PATH}", file=sys.stderr)
