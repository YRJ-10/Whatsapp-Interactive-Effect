# WhatsApp Interactive Motion

MVP pendamping WhatsApp Desktop untuk membaca gesture lawan bicara dan memunculkan efek pada video kamera sendiri.

## Fase Saat Ini

- Fase 1: skeleton app + webcam preview.
- Fase 2: manual screen crop preview untuk area video lawan bicara di WhatsApp.

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
