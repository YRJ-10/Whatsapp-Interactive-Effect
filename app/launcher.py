from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from tkinter import BooleanVar
from tkinter import StringVar
from tkinter import Tk
from tkinter import Toplevel
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

from app.capture.crop_selector import select_screen_crop
from app.capture.whatsapp_crop import ScreenCropSettings


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "config.json"
RUNTIME_DIR = ROOT_DIR / ".runtime"
EFFECT_TRIGGER_PATH = RUNTIME_DIR / "effect_trigger.json"
OUTPUT_WINDOW_NAME = "WhatsApp Interactive Motion - Clean Output"
DEFAULT_OBS_PATHS = (
    Path("C:/Program Files/obs-studio/bin/64bit/obs64.exe"),
    Path("C:/Program Files (x86)/obs-studio/bin/64bit/obs64.exe"),
)


class LauncherApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.process: subprocess.Popen[bytes] | None = None
        self.config = self._load_config()

        camera = self.config.get("camera", {})
        crop = self.config.get("screen_crop", {})
        effects = self.config.get("effects", {})
        obs = self.config.get("obs", {})

        self.camera_index = StringVar(value=str(camera.get("index", 0)))
        width = int(camera.get("width", 960))
        height = int(camera.get("height", 540))
        self.resolution = StringVar(value=f"{width}x{height}")
        self.fps = StringVar(value=str(camera.get("fps", 30)))
        effect_enabled = True
        if isinstance(effects, dict):
            effect_enabled = bool(effects.get("enabled", True))
        self.effects_enabled = BooleanVar(value=effect_enabled)
        obs_path = ""
        auto_open_obs = False
        if isinstance(obs, dict):
            obs_path = str(obs.get("path", ""))
            auto_open_obs = bool(obs.get("auto_open", False))
        if not obs_path:
            obs_path = _detect_obs_path()
        self.obs_path = StringVar(value=obs_path)
        self.auto_open_obs = BooleanVar(value=auto_open_obs)
        self.crop_text = StringVar(value=self._format_crop(crop))
        self.status = StringVar(value="Siap.")
        self.checklist = StringVar(value="")

        self._build_ui()
        self._refresh_checklist()
        self._refresh_loop()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        self.root.title("WhatsApp Interactive Motion Launcher")
        self.root.geometry("620x660")
        self.root.minsize(560, 600)

        main = ttk.Frame(self.root, padding=14)
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)

        ttk.Label(main, text="Camera").grid(row=0, column=0, sticky="w", pady=4)
        camera_row = ttk.Frame(main)
        camera_row.grid(row=0, column=1, sticky="ew", pady=4)
        camera_row.columnconfigure(0, weight=1)
        self.camera_combo = ttk.Combobox(
            camera_row,
            textvariable=self.camera_index,
            values=[str(index) for index in range(10)],
        )
        self.camera_combo.grid(row=0, column=0, sticky="ew")
        ttk.Button(camera_row, text="Scan", command=self._scan_cameras).grid(
            row=0, column=1, padx=(8, 0)
        )

        ttk.Label(main, text="Resolusi").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Combobox(
            main,
            textvariable=self.resolution,
            values=["640x480", "960x540", "1280x720", "1920x1080"],
        ).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(main, text="FPS").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Combobox(
            main,
            textvariable=self.fps,
            values=["15", "24", "30", "60"],
        ).grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Label(main, text="Efek").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Checkbutton(
            main,
            text="Aktifkan efek gesture",
            variable=self.effects_enabled,
            command=self._save_settings,
        ).grid(row=3, column=1, sticky="w", pady=4)

        ttk.Separator(main).grid(row=4, column=0, columnspan=2, sticky="ew", pady=12)

        ttk.Label(main, text="OBS").grid(row=5, column=0, sticky="w", pady=4)
        obs_row = ttk.Frame(main)
        obs_row.grid(row=5, column=1, sticky="ew", pady=4)
        obs_row.columnconfigure(0, weight=1)
        ttk.Entry(obs_row, textvariable=self.obs_path).grid(row=0, column=0, sticky="ew")
        ttk.Button(obs_row, text="Browse", command=self._browse_obs).grid(
            row=0, column=1, padx=(8, 0)
        )
        obs_buttons = ttk.Frame(main)
        obs_buttons.grid(row=6, column=1, sticky="ew", pady=4)
        obs_buttons.columnconfigure(0, weight=1)
        obs_buttons.columnconfigure(1, weight=1)
        ttk.Checkbutton(
            obs_buttons,
            text="Auto-open OBS saat Start App",
            variable=self.auto_open_obs,
            command=self._save_settings,
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(obs_buttons, text="Open OBS", command=self._open_obs).grid(
            row=0, column=1, sticky="ew", padx=(8, 0)
        )
        ttk.Button(
            obs_buttons,
            text="Panduan Setup OBS",
            command=self._show_obs_guide,
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        ttk.Separator(main).grid(row=7, column=0, columnspan=2, sticky="ew", pady=12)

        ttk.Label(main, text="Crop").grid(row=8, column=0, sticky="w", pady=4)
        ttk.Label(main, textvariable=self.crop_text).grid(
            row=8, column=1, sticky="w", pady=4
        )

        crop_buttons = ttk.Frame(main)
        crop_buttons.grid(row=9, column=0, columnspan=2, sticky="ew", pady=4)
        crop_buttons.columnconfigure(0, weight=1)
        crop_buttons.columnconfigure(1, weight=1)
        ttk.Button(
            crop_buttons,
            text="Pilih Area Tangkapan",
            command=self._select_crop,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(
            crop_buttons,
            text="Simpan Setting",
            command=self._save_settings,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        run_buttons = ttk.Frame(main)
        run_buttons.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(14, 6))
        run_buttons.columnconfigure(0, weight=1)
        run_buttons.columnconfigure(1, weight=1)
        ttk.Button(run_buttons, text="Start App", command=self._start_app).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(run_buttons, text="Stop App", command=self._stop_app).grid(
            row=0, column=1, sticky="ew", padx=(6, 0)
        )
        ttk.Button(run_buttons, text="Test Effect", command=self._test_effect).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0)
        )

        ttk.Separator(main).grid(row=11, column=0, columnspan=2, sticky="ew", pady=12)

        ttk.Label(main, text="Status").grid(row=12, column=0, sticky="nw", pady=4)
        ttk.Label(main, textvariable=self.checklist).grid(
            row=12, column=1, sticky="w", pady=4
        )

        mapping_text = (
            "Open Palm -> Glow\n"
            "Fist -> Impact\n"
            "Thumbs Up -> LIKE\n"
            "Victory -> Confetti\n"
            "OK Sign -> OK Ring"
        )
        ttk.Label(main, text="Gesture").grid(row=13, column=0, sticky="nw", pady=4)
        ttk.Label(main, text=mapping_text).grid(row=13, column=1, sticky="w", pady=4)

        obs_text = (
            f"OBS Window Capture: {OUTPUT_WINDOW_NAME}\n"
            "WhatsApp Camera: DroidCam Output"
        )
        ttk.Label(main, text=obs_text).grid(
            row=14, column=0, columnspan=2, sticky="w", pady=(10, 2)
        )
        ttk.Label(main, textvariable=self.status).grid(
            row=15, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

    def _load_config(self) -> dict[str, object]:
        if not CONFIG_PATH.exists():
            return {}
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}

    def _save_settings(self) -> None:
        width, height = self._parse_resolution()
        self.config.setdefault("camera", {})
        self.config.setdefault("screen_crop", {})
        self.config.setdefault("effects", {})
        self.config.setdefault("gesture", {})
        self.config.setdefault("obs", {})

        camera = self.config["camera"]
        crop = self.config["screen_crop"]
        effects = self.config["effects"]
        gesture = self.config["gesture"]
        obs = self.config["obs"]
        if isinstance(camera, dict):
            camera["index"] = int(self.camera_index.get())
            camera["width"] = width
            camera["height"] = height
            camera["fps"] = int(self.fps.get())
        if isinstance(crop, dict):
            crop["backend"] = "mss"
        if isinstance(effects, dict):
            effects["enabled"] = bool(self.effects_enabled.get())
        if isinstance(gesture, dict):
            gesture.setdefault("detection_interval_frames", 2)
            gesture.setdefault("max_input_size", 640)
        if isinstance(obs, dict):
            obs["path"] = self.obs_path.get().strip()
            obs["auto_open"] = bool(self.auto_open_obs.get())

        CONFIG_PATH.write_text(
            json.dumps(self.config, indent=2) + "\n",
            encoding="utf-8",
        )
        self.status.set("Setting tersimpan.")
        self._refresh_checklist()

    def _select_crop(self) -> None:
        self._save_settings()
        crop = self.config.get("screen_crop", {})
        if not isinstance(crop, dict):
            crop = {}

        settings = ScreenCropSettings(
            x=int(crop.get("x", 100)),
            y=int(crop.get("y", 100)),
            width=int(crop.get("width", 640)),
            height=int(crop.get("height", 360)),
            backend="mss",
        )

        try:
            selected = select_screen_crop(settings)
        except Exception as exc:
            self.status.set("Pilih crop dibatalkan.")
            messagebox.showerror("Crop", str(exc))
            return

        self.config["screen_crop"] = {
            "x": selected.x,
            "y": selected.y,
            "width": selected.width,
            "height": selected.height,
            "backend": selected.backend,
        }
        self.crop_text.set(self._format_crop(self.config["screen_crop"]))
        self._save_settings()

    def _start_app(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.status.set("App masih berjalan.")
            return

        self._save_settings()
        if self.auto_open_obs.get():
            self._open_obs(show_message=False)
        width, height = self._parse_resolution()
        command = [
            _pythonw_executable(),
            "-m",
            "app.main",
            "--mode",
            "dual",
            "--clean-output",
            "--camera-index",
            self.camera_index.get(),
            "--width",
            str(width),
            "--height",
            str(height),
            "--fps",
            self.fps.get(),
            "--crop-backend",
            "mss",
            "--effect-trigger-file",
            str(EFFECT_TRIGGER_PATH),
        ]
        if not self.effects_enabled.get():
            command.append("--disable-effects")

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.process = subprocess.Popen(
            command,
            cwd=ROOT_DIR,
            creationflags=creationflags,
        )
        self.status.set("App berjalan. Capture Clean Output di OBS.")
        self._refresh_checklist()

    def _browse_obs(self) -> None:
        path = filedialog.askopenfilename(
            title="Pilih obs64.exe",
            filetypes=[("OBS executable", "obs64.exe"), ("Executable", "*.exe")],
        )
        if not path:
            return
        self.obs_path.set(path)
        self._save_settings()

    def _open_obs(self, show_message: bool = True) -> None:
        obs_path = Path(self.obs_path.get().strip())
        if not obs_path.exists():
            self.status.set("OBS path belum benar. Klik Browse.")
            if show_message:
                messagebox.showerror("OBS", "OBS path belum benar. Klik Browse.")
            return

        try:
            subprocess.Popen(
                [str(obs_path)],
                cwd=obs_path.parent,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as exc:
            self.status.set("Gagal membuka OBS.")
            if show_message:
                messagebox.showerror("OBS", str(exc))
            return

        self.status.set("OBS dibuka.")
        self._refresh_checklist()

    def _show_obs_guide(self) -> None:
        guide = Toplevel(self.root)
        guide.title("Panduan Setup OBS")
        guide.geometry("520x390")
        guide.minsize(480, 360)
        guide.transient(self.root)

        frame = ttk.Frame(guide, padding=14)
        frame.grid(row=0, column=0, sticky="nsew")
        guide.columnconfigure(0, weight=1)
        guide.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        steps = (
            "1. Di launcher, klik Start App.\n"
            "2. Di OBS, tambah source Window Capture.\n"
            f"3. Pilih window: {OUTPUT_WINDOW_NAME}\n"
            "4. Pastikan preview OBS menampilkan video kamera efek.\n"
            "5. Di OBS menu Tools, aktifkan DroidCam Virtual Output.\n"
            "6. Di WhatsApp, pilih kamera DroidCam Output.\n"
            "7. Klik Test Effect untuk memastikan jalur sudah benar."
        )
        ttk.Label(frame, text=steps, justify="left").grid(
            row=0,
            column=0,
            sticky="w",
        )

        buttons = ttk.Frame(frame)
        buttons.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)
        ttk.Button(
            buttons,
            text="Copy Window Name",
            command=lambda: self._copy_text(OUTPUT_WINDOW_NAME),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(
            buttons,
            text="Copy OBS Steps",
            command=lambda: self._copy_text(steps),
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ttk.Button(frame, text="Tutup", command=guide.destroy).grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(12, 0),
        )

    def _copy_text(self, value: str) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.status.set("Teks disalin.")

    def _stop_app(self) -> None:
        if self.process is None or self.process.poll() is not None:
            self.status.set("Tidak ada app yang berjalan.")
            self._refresh_checklist()
            return
        self.process.terminate()
        self.status.set("App dihentikan.")
        self._refresh_checklist()

    def _test_effect(self) -> None:
        if self.process is None or self.process.poll() is not None:
            self.status.set("Start App dulu sebelum Test Effect.")
            self._refresh_checklist()
            return
        if not self.effects_enabled.get():
            self.status.set("Efek sedang OFF. Aktifkan efek dulu.")
            self._refresh_checklist()
            return

        RUNTIME_DIR.mkdir(exist_ok=True)
        EFFECT_TRIGGER_PATH.write_text(
            json.dumps({"gesture": "Victory", "timestamp": time.time_ns()}),
            encoding="utf-8",
        )
        self.status.set("Test Effect dikirim: Victory/confetti.")
        self._refresh_checklist()

    def _scan_cameras(self) -> None:
        self.status.set("Scan kamera...")
        threading.Thread(target=self._scan_cameras_worker, daemon=True).start()

    def _scan_cameras_worker(self) -> None:
        import cv2

        found: list[str] = []
        for index in range(10):
            capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if capture.isOpened():
                found.append(str(index))
            capture.release()

        def update() -> None:
            values = found or [str(index) for index in range(10)]
            self.camera_combo.configure(values=values)
            if found:
                self.status.set(f"Kamera ditemukan: {', '.join(found)}")
            else:
                self.status.set("Tidak ada kamera terdeteksi dari scan.")

        self.root.after(0, update)

    def _parse_resolution(self) -> tuple[int, int]:
        value = self.resolution.get().lower().replace(" ", "")
        width_text, height_text = value.split("x", 1)
        return int(width_text), int(height_text)

    def _format_crop(self, crop: object) -> str:
        if not isinstance(crop, dict):
            return "Belum ada."
        return (
            f"x={crop.get('x', 0)}, y={crop.get('y', 0)}, "
            f"w={crop.get('width', 0)}, h={crop.get('height', 0)}"
        )

    def _refresh_checklist(self) -> None:
        app_running = self.process is not None and self.process.poll() is None
        crop = self.config.get("screen_crop", {})
        crop_ready = (
            isinstance(crop, dict)
            and int(crop.get("width", 0)) > 0
            and int(crop.get("height", 0)) > 0
        )
        self.checklist.set(
            "\n".join(
                [
                    f"App: {'RUNNING' if app_running else 'STOPPED'}",
                    f"Efek: {'ON' if self.effects_enabled.get() else 'OFF'}",
                    f"Crop: {'OK' if crop_ready else 'BELUM'}",
                    f"OBS Auto-open: {'ON' if self.auto_open_obs.get() else 'OFF'}",
                    f"OBS: {OUTPUT_WINDOW_NAME}",
                    "WhatsApp: DroidCam Output",
                ]
            )
        )

    def _refresh_loop(self) -> None:
        self._refresh_checklist()
        self.root.after(1000, self._refresh_loop)

    def _on_close(self) -> None:
        self._stop_app()
        self.root.destroy()


def main() -> int:
    root = Tk()
    LauncherApp(root)
    root.mainloop()
    return 0


def _pythonw_executable() -> str:
    executable = Path(sys.executable)
    pythonw = executable.with_name("pythonw.exe")
    if pythonw.exists():
        return str(pythonw)
    return str(executable)


def _detect_obs_path() -> str:
    for path in DEFAULT_OBS_PATHS:
        if path.exists():
            return str(path)
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
