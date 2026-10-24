import re

import pytest

from arc2dia import dia as D
from arc2dia.errors import Arc2DiaError
from arc2dia.model import Sidebar, tab_url
from arc2dia.transform import transform
from arc2dia.verify import render_verify, verify
from conftest import make_plan, space_by_title


def simulate_dia_import(sb, rename=None, drop=(), favorites=True):
    """What Dia's importer is observed to do: one profile per space with the pinned tabs,
    http(s) only, no open tabs; Favorites show up as isPinned tabs."""
    rename = rename or {}
    fav_tabs = []
    if favorites:
        for _, e in sb.favorite_entries():
            if e.kind == "tab":
                fav_tabs.append(D.DiaTab(tab_url(e.obj), e.obj.get("title") or "", True))
    profiles = [D.DiaProfile(1, "Default", [D.DiaTab("dia://newtab", "New Tab", False)])]
    for n, space in enumerate(sb.spaces, 2):
        tabs = list(fav_tabs)
        for e in sb.walk(space.pinned_id):
            url = tab_url(e.obj) if e.kind == "tab" else None
            if url and url.startswith("http") and url not in drop:
                tabs.append(D.DiaTab(url, e.obj.get("title") or "", False))
        profiles.append(D.DiaProfile(n, rename.get(space.title, space.title), tabs))
    return profiles


def test_prepared_import_verifies_clean(rich_sb):
    cleaned = transform(rich_sb, make_plan(rich_sb, folder_strategy="path-names")).sidebar
    report = verify(cleaned, simulate_dia_import(cleaned), original_sb=rich_sb, mode="prepared")
    assert report.ok
    work = report.spaces[0]
    assert work.profile_name == "Work" and work.match_method == "name"
    assert work.matched == work.expected
    assert work.expected_losses == {"non-web URLs (Dia drops them)": 5}
    assert report.unmatched_profiles == ["Default"]
    assert report.favorites_missing == []
    assert "OK" in render_verify(report)


def test_original_mode_explains_lost_open_tabs(rich_sb):
    report = verify(rich_sb, simulate_dia_import(rich_sb), mode="original")
    assert report.ok
    work = report.spaces[0]
    assert work.expected_losses["open tabs (Dia's importer skips them)"] == 5  # web ones; data:/about: aside
    assert work.expected_losses["non-web URLs (Dia drops them)"] == 4


def test_missing_url_is_flagged(rich_sb):
    profiles = simulate_dia_import(rich_sb, drop=("https://beta.example.com/",))
    report = verify(rich_sb, profiles)
    assert not report.ok
    work = report.spaces[0]
    assert work.unexplained_missing == 1
    assert "MISSING in Dia: 1" in render_verify(report)


def test_trailing_slash_difference_is_explained(rich_sb):
    profiles = simulate_dia_import(rich_sb)
    work = [p for p in profiles if p.name == "Work"][0]
    for t in work.tabs:
        if t.url == "https://alpha.example.com/board":
            t.url = "https://alpha.example.com/board/"
    report = verify(rich_sb, profiles)
    assert report.ok
    diff = [d for d in report.spaces[0].missing if "slightly different" in d.explanation]
    assert len(diff) == 1


def test_extra_tabs_are_classified(rich_sb):
    profiles = simulate_dia_import(rich_sb)
    work = [p for p in profiles if p.name == "Work"][0]
    work.tabs.append(D.DiaTab("https://mail.example.com/inbox", "Inbox", False))
    work.tabs.append(D.DiaTab("https://bank.example.com/", "Bank", False))
    work.tabs.append(D.DiaTab("https://elsewhere.example.com/", "?", False))
    work.tabs.append(D.DiaTab("chrome://settings", "Settings", False))
    report = verify(rich_sb, profiles)
    reasons = {d.url: d.explanation for d in report.spaces[0].extra}
    assert reasons["https://mail.example.com/inbox"] == "an Arc open tab of this space"
    assert reasons["https://bank.example.com/"] == "an Arc favorite"
    assert reasons["https://elsewhere.example.com/"].startswith("not in the Arc sidebar")
    assert reasons["chrome://settings"].startswith("browser page")
    assert report.ok  # extras never fail the check


def test_name_suffix_and_best_overlap(rich_sb):
    profiles = simulate_dia_import(rich_sb, rename={"Work": "Work 2"})
    profiles.append(D.DiaProfile(9, "Work", [D.DiaTab("https://old.example.com/", "old", False)]))
    report = verify(rich_sb, profiles)
    work = report.spaces[0]
    # Two profiles fit the name; the one holding the space's URLs wins.
    assert work.profile_name == "Work 2" and work.match_method == "name, best URL overlap"
    assert report.ok and "Work" in report.unmatched_profiles
    report = verify(rich_sb, profiles, mapping={"Work": "Work"})
    assert report.spaces[0].profile_name == "Work" and not report.ok
    report = verify(rich_sb, profiles, mapping={"Work": "Work 2"})
    assert report.spaces[0].profile_name == "Work 2" and report.spaces[0].match_method == "map"
    assert report.ok


def test_suffix_match_when_exact_name_is_absent(rich_sb):
    profiles = simulate_dia_import(rich_sb, rename={"Personal": "Personal (2)"})
    report = verify(rich_sb, profiles)
    assert report.spaces[1].profile_name == "Personal (2)"


def test_content_match_when_names_differ(rich_sb):
    profiles = simulate_dia_import(rich_sb, rename={"Work": "Arbeit"})
    report = verify(rich_sb, profiles)
    assert report.spaces[0].profile_name == "Arbeit"
    assert report.spaces[0].match_method == "URL overlap (names differ)"


def test_unmatched_space(rich_sb):
    profiles = [p for p in simulate_dia_import(rich_sb) if p.name != "Personal"]
    report = verify(rich_sb, profiles)
    assert report.spaces[1].profile_name is None and not report.ok
    assert '--map "Personal=<Dia profile>"' in render_verify(report)


# --------------------------------------------------------------------------- osascript interface

def dump_text(profiles):
    rows = []
    for k, p in enumerate(profiles, 1):
        rows.append(D.US.join(["P", str(k), p.name]))
        for t in p.tabs:
            rows.append(D.US.join(["T", str(k), "true" if t.is_pinned else "false", t.url, t.title]))
    return D.RS.join(rows) + "\n"


def test_parse_dump_round_trip(rich_sb):
    profiles = simulate_dia_import(rich_sb)
    parsed = D.parse_dump(dump_text(profiles))
    assert [p.name for p in parsed] == [p.name for p in profiles]
    assert [len(p.tabs) for p in parsed] == [len(p.tabs) for p in profiles]
    assert parsed[1].tabs[0].is_pinned is True


def test_parse_dump_errors():
    with pytest.raises(Arc2DiaError, match="not running"):
        D.parse_dump("ERR" + D.US + "not-running")
    with pytest.raises(Arc2DiaError, match="no open window"):
        D.parse_dump("ERR" + D.US + "no-window")
    assert D.parse_dump("") == []


class FakeRunner(D.Runner):
    def __init__(self, output):
        self.output = output
        self.scripts = []

    def run(self, script):
        self.scripts.append(script)
        return self.output


def test_osascript_source_uses_runner(rich_sb):
    runner = FakeRunner(dump_text(simulate_dia_import(rich_sb)))
    profiles = D.OsascriptDiaSource(runner).read()
    assert len(profiles) == 5
    assert runner.scripts == [D.READ_SCRIPT]


def test_read_script_is_read_only():
    script = D.READ_SCRIPT
    for verb in ("make", "close", "focus", "move", "execute", "delete", "open location", "reload", "activate"):
        assert not re.search(r"\b%s\b" % verb, script), verb
    assert 'tell application "Dia"' in script
    assert "character id 31" in script and "character id 30" in script
    assert "is not running" in script  # does not launch Dia


def test_runner_needs_macos(monkeypatch):
    monkeypatch.setattr(D.sys, "platform", "linux")
    with pytest.raises(Arc2DiaError, match="macOS"):
        D.OsascriptRunner().run("return 1")
