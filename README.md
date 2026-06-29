# WhatsApp Interactive Motion

MVP pendamping WhatsApp Desktop untuk membaca gesture lawan bicara dan memunculkan efek pada video kamera sendiri.

## Fase Saat Ini

Fase 1: skeleton app + webcam preview.

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
