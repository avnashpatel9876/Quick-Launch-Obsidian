"""Obsidian Universal Quick Capture - Windows companion (v0.2).

Global shortcut -> small floating window -> one Markdown note per capture,
written straight into <vault>/<capture folder>/. Obsidian is never launched.
"""
import ctypes
import ctypes.wintypes
import json
import logging
import os
import queue
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import qc_core as core
import qc_voice

HERE = Path(__file__).resolve().parent
APP = Path(os.environ.get("APPDATA", str(Path.home()))) / "ObsidianQuickCapture"
APP.mkdir(parents=True, exist_ok=True)
CFG, DRAFT, HISTORY = APP / "config.json", APP / "draft.json", APP / "history.jsonl"
DEFAULT_CFG = {"vault": "", "folder": "Quick Capture",
               "hotkey": "ctrl+shift+space", "prefill_clipboard": False}

logging.basicConfig(filename=str(APP / "quick_capture.log"), level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
sys.excepthook = lambda *a: logging.error("Unhandled", exc_info=a)

WM_HOTKEY, MOD_NOREPEAT = 0x0312, 0x4000


def load_cfg():
    try:
        return {**DEFAULT_CFG, **json.loads(CFG.read_text(encoding="utf-8"))}
    except Exception:
        return DEFAULT_CFG.copy()


def load_rules():
    return core.load_rules(APP / "rules.json",               # your own override
                           HERE.parent / "shared" / "rules.json",  # shipped default
                           HERE / "rules.json")


class App:
    def __init__(self, root):
        self.root, self.cfg = root, load_cfg()
        self.events = queue.Queue()          # worker threads -> Tk main thread
        self.draft_job = None
        try:
            self.rules = load_rules()
        except FileNotFoundError as e:
            messagebox.showerror("Quick Capture", str(e)); raise SystemExit(1)

        root.title("Obsidian Quick Capture")
        root.attributes("-topmost", True)
        root.protocol("WM_DELETE_WINDOW", self.hide)
        root.bind("<Escape>", lambda e: self.hide())
        root.bind("<Control-Return>", lambda e: self.save())

        f = ttk.Frame(root, padding=12); f.pack(fill="both", expand=True)
        top = ttk.Frame(f); top.pack(fill="x")
        ttk.Label(top, text="Quick Capture", font=("Segoe UI", 14, "bold")).pack(side="left")
        ttk.Button(top, text="Settings", command=self.settings).pack(side="right")
        ttk.Button(top, text="Recent", command=self.recent).pack(side="right", padx=5)

        self.title = tk.StringVar()
        self.title_entry = ttk.Entry(f, textvariable=self.title)
        self.title_entry.pack(fill="x", pady=(12, 6))
        self.body = tk.Text(f, wrap="word", height=11, undo=True)
        self.body.pack(fill="both", expand=True)
        for w in (self.title_entry, self.body):
            w.bind("<KeyRelease>", self.schedule_draft)

        row = ttk.Frame(f); row.pack(fill="x", pady=8)
        ttk.Button(row, text="Clipboard", command=self.clip).pack(side="left")
        ttk.Button(row, text="Screenshot", command=self.screenshot).pack(side="left", padx=5)
        ttk.Button(row, text="Voice", command=self.voice).pack(side="left")
        ttk.Button(row, text="Save  Ctrl+Enter", command=self.save).pack(side="right")
        self.status = tk.StringVar(value=f"{self.cfg['hotkey']} opens · Esc closes")
        ttk.Label(f, textvariable=self.status).pack(anchor="w")

        self.load_draft()
        self.center(520, 400)
        root.withdraw()
        self.start_hotkey()
        self.poll()

    # -- plumbing ---------------------------------------------------------
    def center(self, w, h):
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 3
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def poll(self):
        try:
            while True:
                ev = self.events.get_nowait()
                if ev[0] == "show": self.show()
                elif ev[0] == "status": self.status.set(ev[1])
                elif ev[0] == "voice": self.body.insert("insert", ev[1] + " "); self.schedule_draft()
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def start_hotkey(self):
        try:
            mods, vk = core.parse_hotkey(self.cfg["hotkey"])
        except ValueError as e:
            self.status.set(f"Bad hotkey in settings: {e}"); self.show(); return

        def run():
            user32 = ctypes.windll.user32
            if not user32.RegisterHotKey(None, 1, mods | MOD_NOREPEAT, vk):
                self.events.put(("status", f"{self.cfg['hotkey']} is already in use. Change it in Settings."))
                self.events.put(("show",)); return
            msg = ctypes.wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY:
                    self.events.put(("show",))
        threading.Thread(target=run, daemon=True).start()

    def show(self):
        if self.cfg.get("prefill_clipboard") and not self.body.get("1.0", "end-1c").strip():
            try: self.body.insert("1.0", self.root.clipboard_get())
            except tk.TclError: pass
        self.root.deiconify(); self.root.lift(); self.root.focus_force(); self.body.focus_set()

    def hide(self):
        self.flush_draft(); self.root.withdraw()

    # -- drafts -----------------------------------------------------------
    def load_draft(self):
        try:
            d = json.loads(DRAFT.read_text(encoding="utf-8"))
            self.title.set(d.get("title", "")); self.body.insert("1.0", d.get("body", ""))
        except Exception:
            pass

    def schedule_draft(self, _e=None):
        if self.draft_job: self.root.after_cancel(self.draft_job)
        self.draft_job = self.root.after(400, self.flush_draft)

    def flush_draft(self):
        self.draft_job = None
        t, b = self.title.get(), self.body.get("1.0", "end-1c")
        if not t.strip() and not b.strip():
            DRAFT.unlink(missing_ok=True); return
        DRAFT.write_text(json.dumps({"title": t, "body": b}), encoding="utf-8")

    # -- vault ------------------------------------------------------------
    def vault(self):
        p = Path(self.cfg.get("vault", ""))
        if not self.cfg.get("vault") or not p.is_dir():
            messagebox.showinfo("Quick Capture", "Choose your Obsidian vault folder first.")
            self.settings(); return None
        return p

    def capture_dir(self, v):
        d = v / core.sanitize_folder(self.cfg["folder"])
        d.mkdir(parents=True, exist_ok=True); return d

    # -- actions ----------------------------------------------------------
    def save(self):
        v = self.vault()
        if v is None: return
        title, body = self.title.get(), self.body.get("1.0", "end-1c")
        if not title.strip() and not body.strip(): return
        n = core.build_note(title, body, "windows", datetime.now().astimezone(),
                            uuid.uuid4().hex[:6], self.rules)
        try:
            path = self.capture_dir(v) / n["file_name"]
            path.write_text(n["markdown"], encoding="utf-8")
        except OSError as e:
            logging.error("save failed", exc_info=True)
            messagebox.showerror("Could not save", f"{e}\n\nYour text is still in the window."); return
        self.log_history(n, path)
        self.title.set(""); self.body.delete("1.0", "end")
        DRAFT.unlink(missing_ok=True)
        self.status.set("Saved " + n["file_name"])
        self.root.after(700, self.hide)

    def log_history(self, n, path):
        with HISTORY.open("a", encoding="utf-8") as h:
            h.write(json.dumps({"ts": datetime.now().astimezone().isoformat(timespec="seconds"),
                                "title": n["title"], "category": n["category"],
                                "path": str(path)}, ensure_ascii=False) + "\n")
        try:  # keep the log bounded
            lines = HISTORY.read_text(encoding="utf-8").splitlines()
            if len(lines) > 300:
                HISTORY.write_text("\n".join(lines[-200:]) + "\n", encoding="utf-8")
        except OSError: pass

    def save_image(self, img):
        v = self.vault()
        if v is None: return
        att = self.capture_dir(v) / "Attachments"; att.mkdir(exist_ok=True)
        name = "img-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4] + ".png"
        img.save(att / name)
        rel = "/".join(p for p in (core.sanitize_folder(self.cfg["folder"]), "Attachments", name) if p)
        self.body.insert("insert", f"\n![[{rel}]]\n"); self.schedule_draft()

    def clip(self):
        try:
            self.body.insert("insert", self.root.clipboard_get()); self.schedule_draft(); return
        except tk.TclError:
            pass
        try:  # no text on the clipboard: maybe an image or copied files
            from PIL import ImageGrab
            data = ImageGrab.grabclipboard()
            if data is None: self.status.set("Clipboard is empty.")
            elif isinstance(data, list):
                self.body.insert("insert", "\n".join(data)); self.schedule_draft()
            else: self.save_image(data)
        except ImportError:
            self.status.set("Clipboard has no text. (Pillow needed for images.)")
        except Exception as e:
            self.status.set(f"Clipboard error: {e}")

    def screenshot(self):
        try:
            import PIL  # noqa: F401
        except ImportError:
            messagebox.showinfo("Install Pillow", "Run: py -m pip install Pillow"); return
        if self.vault() is None: return
        self.root.withdraw()                          # keep our own window out of the shot
        self.root.after(350, self._grab)

    def _grab(self):
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab(all_screens=True)
            self.show(); self.save_image(img)
        except Exception as e:
            self.show(); messagebox.showerror("Screenshot error", str(e))

    def voice(self):
        try:
            import speech_recognition as sr
        except ImportError:
            messagebox.showinfo("Optional voice setup",
                                "Install: py -m pip install SpeechRecognition sounddevice\n"
                                "Uses Google's online recognition - don't dictate sensitive content.\n"
                                "(Or press Win+H in the window for Windows voice typing.)"); return
        def run():
            try:
                r = sr.Recognizer()
                try:
                    import pyaudio  # noqa: F401  (used if you happen to have it)
                    with sr.Microphone() as src:
                        audio = r.listen(src, timeout=5, phrase_time_limit=30)
                except ImportError:
                    stream, read = qc_voice.open_mic()
                    try:
                        pcm = qc_voice.record(read)
                    finally:
                        stream.stop(); stream.close()
                    audio = sr.AudioData(pcm, qc_voice.RATE, 2)
                self.events.put(("voice", r.recognize_google(audio)))
                self.events.put(("status", "Voice added."))
            except ImportError:
                self.events.put(("status", "Voice needs: py -m pip install sounddevice"))
            except TimeoutError:
                self.events.put(("status", "No speech heard."))
            except sr.UnknownValueError:
                self.events.put(("status", "Could not understand the audio."))
            except Exception as e:
                logging.error("voice failed", exc_info=True)
                self.events.put(("status", f"Voice error: {e}"))
        threading.Thread(target=run, daemon=True).start()
        self.status.set("Listening… (online recognition)")

    # -- windows ----------------------------------------------------------
    def recent(self):
        w = tk.Toplevel(self.root); w.title("Recent captures"); w.geometry("560x320")
        w.attributes("-topmost", True)
        lb = tk.Listbox(w, activestyle="none"); lb.pack(fill="both", expand=True, padx=8, pady=8)
        items = []
        try:
            for ln in HISTORY.read_text(encoding="utf-8").splitlines()[-30:][::-1]:
                items.append(json.loads(ln))
        except (OSError, ValueError): pass
        for it in items:
            lb.insert("end", f"{it['ts'][5:16].replace('T', ' ')}   [{it.get('category', '')}]   {it['title']}")
        ttk.Label(w, text="Double-click to open the note in Obsidian").pack(pady=(0, 8))
        def open_sel(_e=None):
            sel = lb.curselection()
            if not sel: return
            p = items[sel[0]]["path"]
            try: os.startfile("obsidian://open?path=" + quote(p, safe=""))
            except OSError:
                try: os.startfile(p)
                except OSError as e: messagebox.showerror("Open", str(e))
        lb.bind("<Double-Button-1>", open_sel)

    def settings(self):
        w = tk.Toplevel(self.root); w.title("Settings"); w.geometry("540x290")
        w.attributes("-topmost", True)
        path = tk.StringVar(value=self.cfg["vault"]); folder = tk.StringVar(value=self.cfg["folder"])
        hotkey = tk.StringVar(value=self.cfg["hotkey"]); prefill = tk.BooleanVar(value=self.cfg["prefill_clipboard"])
        ttk.Label(w, text="Obsidian vault folder (the vault root)").pack(anchor="w", padx=12, pady=(12, 2))
        row = ttk.Frame(w); row.pack(fill="x", padx=12)
        ttk.Entry(row, textvariable=path).pack(side="left", fill="x", expand=True)
        def browse():
            p = filedialog.askdirectory(title="Select Obsidian vault", parent=w)
            if p: path.set(p)
        ttk.Button(row, text="Browse", command=browse).pack(side="left", padx=5)
        ttk.Label(w, text="Capture folder inside the vault (blank = vault root)").pack(anchor="w", padx=12, pady=(10, 2))
        ttk.Entry(w, textvariable=folder).pack(fill="x", padx=12)
        ttk.Label(w, text="Global shortcut (restart the app to apply)").pack(anchor="w", padx=12, pady=(10, 2))
        ttk.Entry(w, textvariable=hotkey).pack(fill="x", padx=12)
        ttk.Checkbutton(w, text="Paste clipboard text when the window opens empty", variable=prefill).pack(anchor="w", padx=12, pady=8)
        def save_cfg():
            try: core.parse_hotkey(hotkey.get())
            except ValueError as e: messagebox.showerror("Shortcut", str(e), parent=w); return
            if path.get() and not Path(path.get()).is_dir():
                messagebox.showerror("Vault", "That folder does not exist.", parent=w); return
            self.cfg = {"vault": path.get(), "folder": folder.get().strip(),
                        "hotkey": hotkey.get().strip(), "prefill_clipboard": prefill.get()}
            CFG.write_text(json.dumps(self.cfg, indent=2), encoding="utf-8"); w.destroy()
        ttk.Button(w, text="Save", command=save_cfg).pack(anchor="e", padx=12, pady=6)


def main():
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "ObsidianQuickCaptureSingleInstance")
    if ctypes.windll.kernel32.GetLastError() == 183:   # ERROR_ALREADY_EXISTS
        return
    try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception: pass
    root = tk.Tk(); App(root); root.mainloop()
    del mutex


if __name__ == "__main__":
    main()
