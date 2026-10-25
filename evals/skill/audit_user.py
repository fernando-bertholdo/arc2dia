"""List agent messages the simulated user answered with the fallback reply, plus every action it
took, so misreads can be checked by hand."""
import json, pathlib, sys
for run in sys.argv[1:]:
    p = pathlib.Path(run) / "log" / "user.jsonl"
    if not p.exists():
        continue
    print("==", pathlib.Path(run).name)
    for line in p.open():
        e = json.loads(line)
        acts = [a.get("intent") for a in e.get("actions", [])]
        flag = "FALLBACK" if e["reply"] == "Go ahead." else ",".join(acts)
        print(f"  #{e['seq']:<3} {flag:<28} {e['message'][:150]!r}")
