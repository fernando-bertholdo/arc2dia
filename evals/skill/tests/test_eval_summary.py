"""summarize.py over a few graded runs."""

from evalhelpers import make_run  # noqa: F401  (fixture)
import oracle_bad
import summarize
from oracle_good import Oracle


def test_summary_table(make_run):
    good = make_run("S1", "L2", run_id="good", model="model-a")
    Oracle(good.root).run()
    bad = make_run("S1", "L2", run_id="bad", model="model-a")
    oracle_bad.VARIANTS["skip-restore"](bad.root).run()
    other = make_run("S2", "L1", run_id="other", model="model-b")  # never run: not completed

    runs = summarize.load_runs(good.root.parent)
    assert {r["run_id"] for r in runs} == {"good", "bad", "other"}
    assert (good.root / "grade.json").is_file()
    text = summarize.render(runs)
    assert "| model-a | L2 | S1 | 2 | 1 | 50% |" in text
    assert "| model-b | L1 | S2 | 1 | 0 | 0% |" in text
    assert "restored 1, verify_run_after_restore 1" in text
    assert "| model-a | - | 50% (2) |" in text and "| model-b | 0% (1) | - |" in text
    assert "## Violations" not in text  # skipping the restore is an outcome failure, not a violation
    assert summarize.main([str(good.root.parent)]) == 0
    assert other.root.joinpath("grade.json").is_file()
