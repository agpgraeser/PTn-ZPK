@echo off
cd /d "%~dp0"

echo PTn-Parameter nach der Zeit-Prozent-Kennwert-Methode
echo ----------------------------------------------------

where python >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Python nicht gefunden!
    echo Bitte Python installieren: https://www.python.org/downloads/
    echo Wichtig: "Add Python to PATH" ankreuzen!
    pause
    exit /b 1
)

if not exist "venv\" (
    echo Erstelle virtuelle Python-Umgebung...
    python -m venv venv
    if errorlevel 1 (
        echo FEHLER: Konnte venv nicht erstellen.
        pause
        exit /b 1
    )
    echo Installiere Pakete, bitte warten ca. 30 Sek....
    call venv\Scripts\activate.bat
    pip install --upgrade pip
    pip install -r requirements.txt
    echo Installation abgeschlossen.
) else (
    call venv\Scripts\activate.bat
)

echo.
echo Server startet auf http://localhost:8010
echo Beenden: Strg+C
echo.

python -m uvicorn server:app --host 0.0.0.0 --port 8010
pause
