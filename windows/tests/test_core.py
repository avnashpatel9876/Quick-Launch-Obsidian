import json, sys, unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import qc_core as core

SHARED = HERE.parent.parent / "shared"
RULES = core.load_rules(SHARED / "rules.json")
NOW = datetime(2026, 11, 7, 10, 15, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))


def note(title, body, source="windows", uniq="abc123"):
    return core.build_note(title, body, source, NOW, uniq, RULES)


class Categories(unittest.TestCase):
    def test_network_is_not_work(self):  # prototype bug: substring "work" in "network"
        self.assertEqual(core.categorize("scan the network with nmap", RULES), "Unsorted")

    def test_word_prefix_still_matches(self):
        self.assertEqual(core.categorize("Learning burp suite", RULES), "Learning")
        self.assertEqual(core.categorize("workflow cleanup", RULES), "Work")

    def test_priority_order(self):
        self.assertEqual(core.categorize("idea: study for the meeting", RULES), "Ideas")

    def test_tags(self):
        self.assertEqual(core.tags_for("nmap python script", "Unsorted", RULES),
                         ["cybersecurity", "python", "unsorted"])


class Titles(unittest.TestCase):
    def test_explicit_title_wins(self):
        self.assertEqual(core.split_title("T", "body"), ("T", "body"))

    def test_first_line_becomes_title(self):
        self.assertEqual(core.split_title("", "Check UDP scan\nmore"), ("Check UDP scan", "more"))

    def test_markdown_prefix_stripped(self):
        self.assertEqual(core.split_title("", "- [ ] buy milk"), ("buy milk", ""))

    def test_long_first_line_not_used(self):
        t, b = core.split_title("", "x" * 81)
        self.assertEqual((t, b), ("", "x" * 81))

    def test_image_first_line_not_used(self):
        t, b = core.split_title("", "![[a.png]]\ntext")
        self.assertEqual(t, "")


class Notes(unittest.TestCase):
    def test_front_matter_has_real_newlines(self):  # prototype bug: literal "\\n"
        n = note("", "Idea: ship it")
        self.assertNotIn("\\n", n["markdown"])
        self.assertTrue(n["markdown"].startswith("---\ncreated: 2026-11-07T10:15:30+05:30\n"))
        self.assertEqual(n["markdown"].count("---\n"), 2)

    def test_file_name(self):
        n = note("Hello, World!", "x")
        self.assertEqual(n["file_name"], "20261107-101530-win-abc123-hello-world.md")
        n = note("x", "y", source="android-share")
        self.assertIn("-and-", n["file_name"])

    def test_fallback_heading(self):
        n = note("", "![[a.png]]")
        self.assertIn("# Capture 2026-11-07 10:15", n["markdown"])
        self.assertTrue(n["file_name"].endswith("-capture.md"))

    def test_no_duplicate_heading_text(self):
        n = note("", "Check nmap flags")
        self.assertEqual(n["markdown"].count("Check nmap flags"), 1)


class Misc(unittest.TestCase):
    def test_slug(self):
        self.assertEqual(core.slugify("../../etc/passwd"), "etc-passwd")
        self.assertEqual(core.slugify("   "), "capture")
        self.assertLessEqual(len(core.slugify("a" * 100)), 40)

    def test_sanitize_folder(self):
        self.assertEqual(core.sanitize_folder("../Quick Capture/"), "Quick Capture")
        self.assertEqual(core.sanitize_folder("A\\B/C"), "A/B/C")
        self.assertEqual(core.sanitize_folder(""), "")

    def test_hotkey(self):
        self.assertEqual(core.parse_hotkey("Ctrl+Shift+Space"), (0x6, 0x20))
        self.assertEqual(core.parse_hotkey("alt+f9"), (0x1, 0x78))
        self.assertEqual(core.parse_hotkey("ctrl+alt+q"), (0x3, ord("Q")))
        for bad in ["space", "ctrl", "ctrl+a+b", "ctrl+??"]:
            with self.assertRaises(ValueError):
                core.parse_hotkey(bad)


class Vectors(unittest.TestCase):
    """Golden outputs that the Kotlin port must reproduce byte-for-byte."""
    def test_vectors(self):
        vec = json.loads((SHARED / "test_vectors.json").read_text(encoding="utf-8"))
        for v in vec["cases"]:
            n = core.build_note(v["title"], v["body"], v["source"], NOW, "abc123", RULES)
            self.assertEqual(n["file_name"], v["file_name"], v)
            self.assertEqual(n["markdown"], v["markdown"], v)


if __name__ == "__main__":
    unittest.main()
