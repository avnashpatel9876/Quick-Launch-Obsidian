"""Generates a JVM test harness from shared/rules.json + shared/test_vectors.json.
Usage: see android/tools/check_kotlin.sh"""
import json, sys
from pathlib import Path
shared = Path(sys.argv[1]); out = Path(sys.argv[2])
rules = json.loads((shared / "rules.json").read_text(encoding="utf-8"))
vec = json.loads((shared / "test_vectors.json").read_text(encoding="utf-8"))
def k(s): return json.dumps(s).replace("$", "\\$")
def pairs(items, key): return ",\n    ".join(f"{k(i[key])} to listOf({', '.join(k(w) for w in i['keywords'])})" for i in items)
cases = ",\n  ".join(f"arrayOf({k(c['title'])}, {k(c['body'])}, {k(c['source'])}, {k(c['file_name'])}, {k(c['markdown'])})" for c in vec["cases"])
out.write_text(f'''package com.example.quickcapture
import java.time.OffsetDateTime
fun main() {{
  val rules = Rules.of({k(rules["default_category"])},
    listOf({pairs(rules["categories"], "name")}),
    listOf({pairs(rules["tags"], "tag")}))
  val now = OffsetDateTime.parse({k(vec["now"])})
  val cases = listOf(
  {cases})
  var bad = 0
  for (c in cases) {{
    val n = NoteLogic.buildNote(c[0], c[1], c[2], now, {k(vec["uniq"])}, rules)
    if (n.fileName != c[3] || n.markdown != c[4]) {{ bad++; println("MISMATCH for " + c[0].take(30) + "/" + c[1].take(30)); println(" got:  " + n.fileName + "\\n" + n.markdown); println(" want: " + c[3] + "\\n" + c[4]) }}
  }}
  println("kotlin vectors: " + (cases.size - bad) + "/" + cases.size + " match")
  if (bad > 0) kotlin.system.exitProcess(1)
}}
''', encoding="utf-8")
