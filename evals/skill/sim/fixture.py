"""The synthetic Arc sidebar and Dia state every eval run starts from. No real user data: all
URLs use reserved example.* domains, built with the repo's tests/fixturegen.py."""

from __future__ import annotations

import sys
from typing import Any, Dict

from .common import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "tests"))
import fixturegen as F  # noqa: E402

FIXTURE_VERSION = "eval-v1"


def eval_sidebar() -> Dict[str, Any]:
    """Three spaces:

    * "Work": nested folders up to 5 levels, two duplicated "Imported From Edge" trees, a split
      view, an empty folder, non-web links, an easel; open tabs with a split view, an Arc tab
      group holding a tab without a URL, data:/about: URLs and an Arc document.
    * "Personal" (a second Arc profile): a duplicate "Recipes" tree; open tabs with a tab group
      and a file: URL.
    * "Research": the fixturegen research space (tab groups in the pinned and open areas, tabs
      without a URL, same-named trees that do not contain each other).

    Favorites in both Arc profiles and Arc Sync keys are present.
    """
    b = F.Builder(seed=FIXTURE_VERSION, sync=True)

    _, pinned, unpinned = b.space("Work")
    b.tab(pinned, "https://wiki.example.com/", "Team Wiki")
    b.split(pinned, ["https://docs.example.com/a", "https://docs.example.com/b"])
    projects = b.folder(pinned, "Projects")
    b.tab(projects, "https://alpha.example.com/board", "Alpha board")
    alpha = b.folder(projects, "Alpha")
    b.tab(alpha, "https://alpha.example.com/spec", "Alpha spec")
    b.tab(alpha, "https://alpha.example.com/notes", None, saved_title="Alpha notes")
    q3 = b.folder(alpha, "Q3")
    b.tab(q3, "https://alpha.example.com/q3/roadmap", "Q3 roadmap")
    beta = b.folder(projects, "Beta")
    b.tab(beta, "https://beta.example.com/", "Beta")
    F.edge_tree_with_layer(b, pinned)
    F.edge_tree_flat(b, pinned)
    b.folder(pinned, "Empty folder")
    local = b.folder(pinned, "Local files")
    b.tab(local, "file:///Users/example/Documents/report.pdf", "report.pdf")
    b.tab(local, "chrome-extension://abcdefghijklmnop/options.html", "Extension options")
    b.easel(pinned, "Moodboard")

    b.tab(unpinned, "https://mail.example.com/inbox", "Inbox")
    b.split(unpinned, ["https://calendar.example.com/", "https://meet.example.com/room"])
    sprint = b.tab_group(unpinned, "Sprint 42")
    b.tab(sprint, "https://tracker.example.com/sprint/42", "Sprint board")
    b.tab(sprint, "https://ci.example.com/builds", "CI builds")
    b.urlless_tab(sprint, "New Tab")
    b.tab(unpinned, "https://search.example.com/?q=arc+to+dia", None, saved_title="")
    b.tab(unpinned, "data:text/plain,hello", "data URL")
    b.tab(unpinned, "about:blank", "Blank")
    b.document(unpinned, "Scratch notes")

    _, pinned, unpinned = b.space("Personal", F.CUSTOM_PROFILE)
    recipes = b.folder(pinned, "Recipes")
    b.tab(recipes, "https://recipes.example.net/soup", "Soup")
    b.tab(recipes, "https://recipes.example.net/cake", "Cake")
    reading = b.folder(pinned, "Reading")
    copy = b.folder(reading, "Recipes")
    b.tab(copy, "https://recipes.example.net/soup", "Soup")
    b.tab(copy, "https://recipes.example.net/cake", "Cake")
    b.tab(reading, "https://books.example.org/list", "Book list")
    b.tab(pinned, "https://bank.example.com/", "Bank")
    b.tab(unpinned, "https://video.example.com/watch?v=123", "A video")
    weekend = b.tab_group(unpinned, "Weekend")
    b.tab(weekend, "https://cinema.example.com/listings", "Cinema")
    b.tab(weekend, "https://weather.example.org/city", "Weather")
    b.tab(unpinned, "file:///Users/example/Downloads/ticket.pdf", "ticket.pdf")

    F.research_space(b)

    fav = b.favorites(F.DEFAULT_PROFILE)
    b.tab(fav, "https://chat.example.com/", "Chat")
    b.tab(fav, "https://music.example.com/", "Music")
    fav2 = b.favorites(F.CUSTOM_PROFILE)
    b.tab(fav2, "https://bank.example.com/", "Bank")
    return b.build()


def initial_dia() -> Dict[str, Any]:
    """Dia as the user has it before the migration: installed, used a little, one profile whose
    name clashes with an Arc space (so an import creates "Personal 2")."""
    return {
        "windows": 1,
        "profiles": [
            {
                "name": "Personal",
                "origin": "existing",
                "tabs": [
                    {"url": "https://start.example.com/", "title": "Start page", "pinned": False},
                    {"url": "https://news.example.com/today", "title": "Today's news", "pinned": False},
                ],
                "groups": [],
            }
        ],
        "archived_profiles": [],
        "imports": [],
    }


def dump(raw: Dict[str, Any]) -> str:
    return F.dump(raw)
