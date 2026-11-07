# Obsidian Universal Quick Capture — v0.2 (prototype)

One capture format, two front-ends. A Windows global shortcut and an Android home-screen widget each save an
**individual Markdown note** into the **same `Quick Capture` folder** of your vault. Obsidian is never launched.

```
shared/     rules.json (categories + tags, used by both apps), test_vectors.json, NOTE_FORMAT.md
windows/    quick_capture.py (GUI), qc_core.py (logic), tests/
android/    Android Studio project (Kotlin, no third-party dependencies), tools/check_kotlin.sh
```

## Try it on a disposable vault first
Neither app has been run against a real vault yet (see "What has actually been tested"). Make a throw-away vault
with one note in it, use that for a day, and only then point the apps at your real one.

## Windows
1. Install Python 3.10+ (python.org build, with `py` and tkinter).
2. Double-click `windows/run_quick_capture.bat` (starts without a console window).
3. **Settings** → Browse → choose the vault root. Capture folder defaults to `Quick Capture`.
4. `Ctrl+Shift+Space` from any app. `Ctrl+Enter` saves, `Esc` hides (your text is kept as a draft).
5. Optional: `py -m pip install Pillow` for screenshots and clipboard images;
   `py -m pip install SpeechRecognition sounddevice` for the Voice button (uses Google's online service — don't dictate secrets). No C++ compiler needed. Windows 11's built-in voice typing (**Win+H**) also works inside the capture window.
6. Autostart: put a shortcut to the `.bat` in `shell:startup`.

Buttons: **Clipboard** (text, or an image saved to `Quick Capture/Attachments`), **Screenshot** (hides the window,
grabs all monitors), **Voice**, **Recent** (last 30 captures; double-click opens the note in Obsidian).
Errors are logged to `%APPDATA%\ObsidianQuickCapture\quick_capture.log`.

## Android
1. Open `android/` in Android Studio (Ladybug or newer), let Gradle sync, run on your phone.
2. Open the **Quick Capture** app → **Choose vault folder** → pick the vault root (the folder containing `.obsidian`).
   The app creates the sub-folder, and Android remembers the permission across reboots.
3. Add the **Quick Capture** widget from the widget picker. Tap it → floating panel → Save.
4. Any app → Share → **Quick Capture** sends text (and the subject as title) to the same place.

If the vault can't be reached, the note is kept inside the app ("Queued") and retried automatically the next time you
save or open the app, so a capture isn't lost.

### Where your vault lives matters
Android 11+ will not let any app pick `Android/data/...` through the folder picker. If your Obsidian vault was created
in Obsidian's own app folder, pick a different location (for example `Documents/`) by moving the vault or creating a new
one there. Syncing the two devices (Obsidian Sync, Syncthing, etc.) is separate from this project; filenames carry a
timestamp, a source tag and a random suffix, so two devices never write the same file.

## Customising categories and tags
Edit `shared/rules.json` (Android bundles it at build time). On Windows you can instead drop a copy at
`%APPDATA%\ObsidianQuickCapture\rules.json`. Keywords match at the **start of a word**: `learn` matches "learning"
but `work` does not match "network". Categories are checked top to bottom; first match wins.
If you change the rules or `qc_core.py`, run `python windows/tests/make_vectors.py`, then both test suites (below).

## Tests
```
python -m unittest discover -s windows/tests -v            # logic + voice recorder, 21 tests
android/tools/check_kotlin.sh <kotlinc> <android.jar>      # optional: compile + Kotlin-vs-Python vectors
```

## What has actually been tested
| Piece | Evidence |
|---|---|
| Note logic (Python) | 17 unit tests |
| Note logic (Kotlin) | Output identical to Python on 12 golden cases (JVM run) |
| Windows UI | Run headless under Linux with the Win32 calls mocked: save, draft, history, clipboard, image embed, voice event |
| Windows hotkey / DPI / Obsidian link | **Not tested on real Windows** |
| Android code | Compiles against Android API 34 stubs |
| Android SAF writes, widget, share sheet, voice, XML resources | **Not run on a device or emulator** |

## Not implemented
Reminders / due dates, Android screenshot capture, Android draft history beyond the single autosaved draft,
sharing images or files into Android. See `FEATURE_STATUS.md`.

## Android without Android Studio (GitHub builds the APK for you)
1. Create a free GitHub account, make a **private** repository, and upload the contents of this folder
   (including the hidden `.github` folder) to it.
2. Open the repository's **Actions** tab → **Build Android APK** → **Run workflow**. Wait a few minutes.
3. Open the finished run, download the **quick-capture-apk** artifact, and unzip it to get `app-debug.apk`.
4. Copy the APK to your phone, open it, and allow "install unknown apps" for your file manager or browser when asked.
This workflow has not been run yet; if the build fails, open the run's log and send me the error.
