# Feature status (v0.2)

| Feature | Windows | Android |
|---|---|---|
| Entry point | Global shortcut (configurable) | Widget tap, Share sheet |
| Saves one Markdown note per capture, no Obsidian launch | Implemented | Implemented (SAF) — device-untested |
| Vault access | Folder browse | Storage Access Framework picker, persisted permission — device-untested |
| Same Quick Capture folder, same note format | Implemented | Implemented |
| Offline / failure safety | Error shown, text kept | Queue in app storage, auto-retry |
| Clipboard | Text or image | Share sheet (text) |
| Screenshot | Implemented (Pillow) | Not implemented |
| Voice | Optional, online service | System recognizer, prefers offline |
| Auto category + tags | Shared `rules.json`, word-boundary matching | Same |
| Draft autosave | Implemented | Single draft, restored on reopen |
| Recent history | Recent window | List on main screen |
| Reminders / due dates | Not implemented | Not implemented |
