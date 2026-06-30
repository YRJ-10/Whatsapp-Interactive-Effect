from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import StringVar
from tkinter import Tk
from tkinter import messagebox
from tkinter import ttk

from app.capture.crop_selector import select_screen_crop
from app.capture.whatsapp_crop import ScreenCropSettings


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "config.json"
OUTPUT_WINDOW_NAME = "WhatsApp Interactive Motion - Clean Output"


class LauncherApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.process: subprocess.Popen[bytes] | None = None
        self.config = self._load_config()

        camera = self.config.get("camera", {})
        crop = self.config.get("screen_crop", {})

        self.camera_index = StringVar(value=str(camera.get("index", 0)))
        width = int(camera.get("width", 960))
        height = int(camera.get("height", 540))
        self.resolution = StringVar(value=f"{width}x{height}")
        self.fps = StringVar(value=str(camera.get("fps", 30)))
        self.crop_text = StringVar(value=self._format_crop(crop))
        self.status = StringVar(value="Siap.")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        self.root.title("WhatsApp Interactive Motion Launcher")
        self.root.geometry("520x360")
        self.root.minsize(480, 330)

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

        ttk.Separator(main).grid(row=3, column=0, columnspan=2, sticky="ew", pady=12)

        ttk.Label(main, text="Crop").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Label(main, textvariable=self.crop_text).grid(
            row=4, column=1, sticky="w", pady=4
        )

        crop_buttons = ttk.Frame(main)
        crop_buttons.grid(row=5, column=0, columnspan=2, sticky="ew", pady=4)
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
        run_buttons.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(14, 6))
        run_buttons.columnconfigure(0, weight=1)
        run_buttons.columnconfigure(1, weight=1)
        ttk.Button(run_buttons, text="Start App", command=self._start_app).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(run_buttons, text="Stop App", command=self._stop_app).grid(
            row=0, column=1, sticky="ew", padx=(6, 0)
        )

        obs_text = (
            f"OBS Window Capture: {OUTPUT_WINDOW_NAME}\n"
            "WhatsApp Camera: DroidCam Output"
        )
        ttk.Label(main, text=obs_text).grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(10, 2)
        )
        ttk.Label(main, textvariable=self.status).grid(
            row=8, column=0, columnspan=2, sticky="w", pady=(8, 0)
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

        camera = self.config["camera"]
        crop = self.config["screen_crop"]
        if isinstance(camera, dict):
            camera["index"] = int(self.camera_index.get())
            camera["width"] = width
            camera["height"] = height
            camera["fps"] = int(self.fps.get())
        if isinstance(crop, dict):
            crop["backend"] = "mss"

        CONFIG_PATH.write_text(
            json.dumps(self.config, indent=2) + "\n",
            encoding="utf-8",
        )
        self.status.set("Setting tersimpan.")

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
        width, height = self._parse_resolution()
        command = [
            sys.executable,
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
        ]

        creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        self.process = subprocess.Popen(
            command,
            cwd=ROOT_DIR,
            creationflags=creationflags,
        )
        self.status.set("App berjalan. Capture Clean Output di OBS.")

    def _stop_app(self) -> None:
        if self.process is None or self.process.poll() is not None:
            self.status.set("Tidak ada app yang berjalan.")
            return
        self.process.terminate()
        self.status.set("App dihentikan.")

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

    def _on_close(self) -> None:
        self._stop_app()
        self.root.destroy()


def main() -> int:
    root = Tk()
    LauncherApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
