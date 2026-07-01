# WhatsApp Interactive Motion

MVP pendamping WhatsApp Desktop untuk membaca gesture lawan bicara dan memunculkan efek pada video kamera sendiri.

## Fase Saat Ini

- Fase 1: skeleton app + webcam preview.
- Fase 2: manual screen crop preview untuk area video lawan bicara di WhatsApp.
- Fase 3: gesture detection dari crop WhatsApp.
- Fase 4: gesture stabilizer + event cooldown.
- Fase 5: effect renderer di video webcam sendiri.
- Fase 6: virtual camera output untuk WhatsApp.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run Fase 1

```powershell
python -m app.main
```

Tekan `q` atau `Esc` pada window preview untuk berhenti.

Jika kamera utama bukan index `0`:

```powershell
python -m app.main --camera-index 1
```

## Run Fase 2

Preview crop layar manual:

```powershell
python -m app.main --mode crop
```

Atur crop langsung dari command:

```powershell
python -m app.main --mode crop --crop-x 100 --crop-y 100 --crop-width 640 --crop-height 360
```

Preview webcam dan crop bersamaan:

```powershell
python -m app.main --mode dual
```

Nilai default crop ada di `config.json`:

```json
{
  "screen_crop": {
    "x": 100,
    "y": 100,
    "width": 640,
    "height": 360,
    "backend": "auto"
  }
}
```

Backend `auto` akan mencoba `dxcam` lebih dulu, lalu fallback ke `mss`.

## Setup Model Gesture

MediaPipe Gesture Recognizer butuh model `.task` lokal:

```powershell
.\scripts\download_gesture_model.ps1
```

File model akan disimpan ke:

```text
models/gesture_recognizer.task
```

File `.task` tidak masuk git karena ukurannya relatif besar.

## Run Fase 3

Gesture detection aktif otomatis di mode `crop` dan `dual` kalau model sudah ada:

```powershell
python -m app.main --mode crop
```

Gesture yang ditampilkan:

- `Open Palm`
- `Fist`
- `Thumbs Up`
- `Victory`
- `OK Sign`

Kalau ingin tes crop tanpa gesture detection:

```powershell
python -m app.main --mode crop --disable-gesture-detection
```

## Run Fase 4

Fase 4 aktif otomatis di mode `crop` dan `dual`. Preview akan menampilkan:

- raw gesture per frame
- stable candidate dan jumlah frame berturut-turut
- event terakhir yang sudah lolos stabilizer

Default stabilizer ada di `config.json`:

```json
{
  "gesture": {
    "stable_frames": 4,
    "cooldown_ms": 1200
  }
}
```

Override dari command:

```powershell
python -m app.main --mode crop --stable-frames 3 --gesture-cooldown-ms 1000
```

## Run Fase 5

Efek aktif otomatis di mode `dual`. Gesture stabil dari crop WhatsApp akan memicu efek pada preview webcam:

- `Open Palm` -> border glow
- `Fist` -> shake + impact flash
- `Thumbs Up` -> LIKE badge
- `Victory` -> confetti
- `OK Sign` -> ring pulse

```powershell
python -m app.main --mode dual
```

Tes efek tanpa WhatsApp/gesture:

```powershell
python -m app.main --mode webcam --demo-effect Victory
```

Matikan efek:

```powershell
python -m app.main --mode dual --disable-effects
```

Ubah durasi efek:

```powershell
python -m app.main --mode dual --effect-duration-ms 1800
```

## Run Fase 6

Fase 6 memakai OBS + DroidCam OBS Virtual Output agar video Python muncul sebagai kamera di WhatsApp.

Cara paling mudah:

```powershell
.\start_launcher.vbs
```

Pakai `start_launcher.vbs` agar tidak muncul terminal tambahan.

Di launcher:

1. Pilih kamera.
2. Pilih resolusi.
3. Aktifkan atau matikan efek gesture.
4. Set OBS path atau klik `Browse` kalau belum otomatis terisi.
5. Aktifkan `Auto-open OBS saat Start App` jika perlu.
6. Klik `Pilih Area Tangkapan` kalau area WhatsApp berubah.
7. Klik `Start App`.

Launcher memakai mode ringan default: deteksi gesture tiap 2 frame dan input MediaPipe diperkecil ke maksimal 640px.

Jalankan output bersih dari app Python dan pilih area video lawan bicara:

```powershell
.\.venv\Scripts\python.exe -m app.main --mode dual --clean-output --select-crop --camera-index 2 --width 960 --height 540 --fps 30 --crop-backend mss
```

Capture window bernama:

```text
WhatsApp Interactive Motion - Clean Output
```

Kalau ingin menyimpan area crop yang dipilih:

```powershell
.\.venv\Scripts\python.exe -m app.main --mode dual --clean-output --select-crop --save-crop --camera-index 2 --width 960 --height 540 --fps 30 --crop-backend mss
```

Prasyarat Windows:

- Install OBS Studio.
- Install DroidCam OBS Virtual Output:
  https://github.com/dev47apps/droidcam-obs-virtual-output/releases

Alur di OBS:

1. Tambahkan source `Window Capture`.
2. Pilih window `WhatsApp Interactive Motion - Clean Output`.
3. Buka menu `Tools`.
4. Aktifkan DroidCam virtual output.
5. Di WhatsApp, pilih kamera DroidCam output.
