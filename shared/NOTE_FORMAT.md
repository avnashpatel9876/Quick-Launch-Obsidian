# Note format (both apps)

File: `<vault>/<capture folder>/YYYYMMDD-HHMMSS-<win|and>-<6 hex>-<slug>.md`
Attachments (Windows): `<capture folder>/Attachments/img-….png`, embedded as `![[<capture folder>/Attachments/…]]`

```
---
created: 2026-11-07T10:15:30+05:30
source: windows            # windows | android-widget | android-share
category: Ideas
tags: [cybersecurity, ideas]
---

# Title

Body text
```

Title: explicit title, else the first body line if it is ≤ 80 characters (leading `#`, `>`, `- [ ]` removed; the line is
then not repeated in the body), else `Capture YYYY-MM-DD HH:MM`.
Category: first matching entry of `rules.json` → categories (keywords match at a word start), else `Unsorted`.
Tags: lowercase category plus every matching entry of `rules.json` → tags, sorted.
Slug: lowercase, non-word runs → `-`, max 40 chars, `capture` if empty.
