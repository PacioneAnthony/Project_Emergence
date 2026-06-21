param(
    [string]$Port
)

$ErrorActionPreference = 'Stop'

$arduinoCli = 'C:\Program Files\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe'
$sketch = Join-Path (Split-Path $PSScriptRoot -Parent) 'peripheral\brain_stem'

if (-not (Test-Path -LiteralPath $arduinoCli)) {
    throw "arduino-cli introuvable: $arduinoCli"
}

$serialPorts = @(Get-CimInstance Win32_SerialPort | Select-Object DeviceID, Name, Description, PNPDeviceID)

if (-not $Port) {
    $candidates = @(
        $serialPorts | Where-Object {
            $_.Name -match 'Arduino|Mega' -or
            $_.Description -match 'Arduino|Mega' -or
            $_.PNPDeviceID -match 'VID_2341|VID_2A03|VID_1A86'
        }
    )

    if ($candidates.Count -eq 0) {
        throw @"
Aucun Arduino Mega n'est visible par Windows.

1. Débranche puis rebranche le câble USB côté Arduino et côté PC.
2. Essaie un autre port USB et, si nécessaire, un autre câble USB de données.
3. Attends quelques secondes puis relance ce script.
4. Vérifie que le Gestionnaire de périphériques affiche « Arduino Mega 2560 (COMx) ».

COM1 est le port série système et ne doit pas être utilisé pour ce banc.
"@
    }
    if ($candidates.Count -gt 1) {
        $summary = ($candidates | ForEach-Object { "$($_.DeviceID): $($_.Name)" }) -join [Environment]::NewLine
        throw "Plusieurs périphériques série candidats sont visibles. Relance avec -Port COMx:`n$summary"
    }
    $Port = $candidates[0].DeviceID
}

if ($Port -eq 'COM1') {
    throw 'COM1 est le port série système, pas l Arduino Mega. Rebranche la carte et laisse le script détecter son port.'
}

$selected = $serialPorts | Where-Object { $_.DeviceID -eq $Port }
if (-not $selected) {
    throw "Le port $Port n'est pas visible par Windows. Rebranche l'Arduino puis relance sans préciser -Port."
}

Write-Host "Arduino sélectionné: $($selected.Name) sur $Port"
Write-Host 'Attention: le flash redémarre la carte et peut recentrer le servo à 90 degrés.'

& $arduinoCli compile --upload --port $Port --fqbn arduino:avr:mega $sketch
if ($LASTEXITCODE -ne 0) {
    throw "Échec du flash Arduino, code $LASTEXITCODE."
}

Write-Host "Firmware J0 flashé avec succès sur $Port."
