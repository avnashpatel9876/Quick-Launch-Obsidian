"""Regenerate shared/test_vectors.json from qc_core (run after changing rules/logic,
then re-run the Kotlin check)."""
import json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import qc_core as core
SHARED = HERE.parent.parent / "shared"
RULES = core.load_rules(SHARED / "rules.json")
NOW = datetime(2026, 11, 7, 10, 15, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))
INPUTS = [
    ("", "Idea: ship the widget", "windows"),
    ("", "scan the network with nmap", "android-widget"),
    ("Study plan", "Learning burp suite and OWASP top 10", "android-share"),
    ("", "- [ ] remind me to renew the domain\nbefore friday", "windows"),
    ("Workflow notes", "meeting with client about the project", "android-widget"),
    ("", "![[Quick Capture/Attachments/screen-1.png]]", "windows"),
    ("Héllo wörld / ../x", "python script to parse nmap xml", "android-share"),
    ("", "x" * 90, "windows"),
    ("", "## Heading line\n\nbody para one\nbody para two", "windows"),
    ("  ", "   ", "android-widget"),
    ("Cost $5 & 100% done", "maybe a ${template} thing", "android-widget"),
    ("", "Привет мир: need to learn linux", "windows"),
]
cases = []
for t, b, s in INPUTS:
    n = core.build_note(t, b, s, NOW, "abc123", RULES)
    cases.append({"title": t, "body": b, "source": s,
                  "file_name": n["file_name"], "markdown": n["markdown"]})
(SHARED / "test_vectors.json").write_text(
    json.dumps({"now": "2026-11-07T10:15:30+05:30", "uniq": "abc123", "cases": cases},
               indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(len(cases), "vectors written")
