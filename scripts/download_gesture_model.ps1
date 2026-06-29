$ErrorActionPreference = "Stop"

$modelsDir = Join-Path $PSScriptRoot "..\models"
$modelPath = Join-Path $modelsDir "gesture_recognizer.task"
$modelUrl = "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task"

New-Item -ItemType Directory -Force -Path $modelsDir | Out-Null
Invoke-WebRequest -Uri $modelUrl -OutFile $modelPath

Write-Host "Downloaded gesture model to $modelPath"
