"""Pure note logic for Obsidian Universal Quick Capture.

No GUI and no Windows APIs in here, so it can be unit-tested anywhere.
android/.../NoteLogic.kt is a deliberate line-for-line port of this file;
shared/test_vectors.json is how the two are kept in agreement.
"""
import json
import re
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------- rules ----

def load_rules(*paths):
    """Load the first readable rules.json from `paths` and pre-compile it."""
    last_err = None
    for p in paths:
        try:
            data = json.loads(Path(p).read_text(encoding="utf-8"))
            return compile_rules(data)
        except (OSError, ValueError) as e:
            last_err = e
    raise FileNotFoundError(f"rules.json not found or invalid ({last_err})")


def _kw_regex(keywords):
    # A keyword must start at a word boundary ("work" matches "workflow" but
    # not "network"). Suffixes are allowed ("learn" matches "learning").
    alt = "|".join(re.escape(k.lower()) for k in keywords)
    return re.compile(r"(?<!\w)(?:" + alt + ")")


def compile_rules(data):
    return {
        "default_category": data.get("default_category", "Unsorted"),
        "categories": [(c["name"], _kw_regex(c["keywords"])) for c in data["categories"]],
        "tags": [(t["tag"], _kw_regex(t["keywords"])) for t in data["tags"]],
    }


def categorize(text, rules):
    t = text.lower()
    for name, rx in rules["categories"]:
        if rx.search(t):
            return name
    return rules["default_category"]


def tags_for(text, category, rules):
    t = text.lower()
    out = {category.lower()}
    for tag, rx in rules["tags"]:
        if rx.search(t):
            out.add(tag)
    return sorted(out)

# ---------------------------------------------------------------- notes ----

_TITLE_PREFIX = re.compile(r"^(?:#{1,6}\s+|>\s*|[-*]\s+(?:\[[ xX]\]\s+)?)")


def split_title(title, body):
    """Return (title, body). With no explicit title, a short first line of the
    body becomes the title and is removed from the body."""
    title = (title or "").strip()
    body = (body or "").strip()
    if title:
        return title, body
    lines = body.splitlines()
    for i, line in enumerate(lines):
        s = line.strip()
        if not s:
            continue
        if s.startswith("![["):
            break
        cleaned = _TITLE_PREFIX.sub("", s, count=1).strip()
        if cleaned and len(cleaned) <= 80:
            return cleaned, "\n".join(lines[i + 1:]).strip()
        break
    return "", body


def slugify(s):
    s = re.sub(r"[^\w-]+", "-", s.lower())
    s = re.sub(r"-{2,}", "-", s).strip("-")[:40].strip("-")
    return s or "capture"


def sanitize_folder(name):
    """Capture folder as a safe vault-relative path ('' allowed)."""
    parts = [p.strip() for p in re.split(r"[\\/]+", name or "")]
    parts = [re.sub(r'[<>:"|?*\x00-\x1f]', "-", p) for p in parts if p not in ("", ".", "..")]
    return "/".join(parts)


def build_note(title, body, source, now, uniq, rules):
    """Build one capture. Returns dict(file_name, markdown, title, category).

    now  : timezone-aware datetime
    uniq : 6 hex chars, supplied by the caller so output is reproducible
    """
    t, rest = split_title(title, body)
    text = (t + "\n" + rest).strip()
    category = categorize(text, rules)
    tags = tags_for(text, category, rules)
    heading = t or f"Capture {now:%Y-%m-%d %H:%M}"
    short = source.split("-")[0][:3]
    file_name = f"{now:%Y%m%d-%H%M%S}-{short}-{uniq}-{slugify(t)}.md"
    md = (
        "---\n"
        f"created: {now.isoformat(timespec='seconds')}\n"
        f"source: {source}\n"
        f"category: {category}\n"
        f"tags: [{', '.join(tags)}]\n"
        "---\n\n"
        f"# {heading}\n"
    )
    if rest:
        md += f"\n{rest}\n"
    return {"file_name": file_name, "markdown": md, "title": heading, "category": category}

# --------------------------------------------------------------- hotkey ----

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN = 0x1, 0x2, 0x4, 0x8
_MODS = {"alt": MOD_ALT, "ctrl": MOD_CONTROL, "control": MOD_CONTROL,
         "shift": MOD_SHIFT, "win": MOD_WIN}


def parse_hotkey(spec):
    """'ctrl+shift+space' -> (modifier_mask, virtual_key). Raises ValueError."""
    mods, key = 0, None
    for part in [p.strip().lower() for p in spec.split("+") if p.strip()]:
        if part in _MODS:
            mods |= _MODS[part]
        elif key is not None:
            raise ValueError("only one non-modifier key allowed")
        elif part == "space":
            key = 0x20
        elif len(part) == 1 and (part.isascii() and part.isalnum()):
            key = ord(part.upper())
        elif re.fullmatch(r"f([1-9]|1[0-2])", part):
            key = 0x70 + int(part[1:]) - 1
        else:
            raise ValueError(f"unsupported key '{part}'")
    if mods == 0 or key is None:
        raise ValueError("need at least one modifier and one key, e.g. ctrl+shift+space")
    return mods, key
