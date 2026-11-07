# Changelog

## 0.2.1
- Windows voice no longer needs PyAudio (which fails to install on new Python versions without a C++ compiler). The Voice button now records with `sounddevice`; PyAudio is still used if already installed.

## 0.2
Fixed
- Android notes were written with a literal `\n` instead of line breaks, which broke the front matter.
- "network" (and similar words) was filed under Work because keywords matched anywhere inside a word.
- Windows and Android used different category priority and keyword lists.
- Android settings screen could not be opened (no launcher entry).
- Windows screenshots included the capture window itself; title edits were not autosaved;
  the hotkey thread touched Tk from a background thread.
Added
- Android: Storage Access Framework folder picker with persisted permission, queue-and-retry for failed writes,
  autosaved draft, recent list, share subject as title; removed unneeded RECORD_AUDIO permission.
- Windows: configurable shortcut, single instance, no console window, clipboard images, all-monitor screenshots,
  recent-captures window, log file.
- Shared `rules.json` + `NOTE_FORMAT.md` + golden test vectors keeping both apps identical.
Changed
- Notes are written flat into the capture folder (category is in the front matter) instead of per-category sub-folders.
- First short line of a capture becomes the title and is not repeated in the body.
