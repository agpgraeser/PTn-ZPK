"""
server.py – FastAPI-Server der PTn-Parameterbestimmung (ZPK-Methode).

Liefert die HTML-Seite und die API aus – ein Server, ein Port, kein CORS.
Die Fachlogik liegt im gemeinsamen Paket `agp_control_kern.ptn_zpk`, damit
die Programmfamilie dieselbe Rechnung benutzt.

Start: python -m uvicorn server:app --port 8010   (oder start.bat)
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agp_control_kern import projektdatei, ptn_zpk

import excel_io

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

BASE = Path(__file__).resolve().parent

app = FastAPI(title="AGP-Control - PTn-Parameter (ZPK)", version="1.0")


@app.middleware("http")
async def kein_browser_cache(request, call_next):
    """Browser duerfen HTML/JS/CSS nicht zwischenspeichern – sonst liefert
    Chrome nach einem App-Update tagelang eine alte Kopie aus, ohne den
    Server zu fragen (siehe RegelkreisSimulationen)."""
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ─── Request-Modelle ─────────────────────────────────────────────────────────

class AuswertungRequest(BaseModel):
    """Zeitwerte der ZPK-Methode plus – optional – Signal- und Messdaten."""
    t0: float
    t10: float
    t50: float
    t90: float
    k_s: float | None = None
    d_u: float | None = None
    y_a: float | None = None
    zeit_daten: list[float] | None = None
    mess_daten: list[float] | None = None


class ProjektSpeichernRequest(BaseModel):
    """Speichert das ermittelte Modell in eine AGP-Projektdatei.
    `projekt` = zuvor geladenes Projekt-dict; None = neue Datei anlegen."""
    projekt: dict | None = None
    fallname: str = "Fall"
    beschreibung: str = ""
    modelle: list | None = None
    programm: str = "PTn-ZPK"
    aktion: str = "gespeichert"


# ─── API ─────────────────────────────────────────────────────────────────────

@app.post("/api/auswertung")
def auswertung(req: AuswertungRequest):
    """Bestimmt Ordnung, Zeitkonstante und Varianz – auch fuer die
    Nachbarordnungen – und liefert die Modellkurven dazu."""
    try:
        return ptn_zpk.zpk_auswertung(
            req.t0, req.t10, req.t50, req.t90,
            k_s=req.k_s, d_u=req.d_u, y_a=req.y_a,
            zeit_daten=req.zeit_daten, mess_daten=req.mess_daten,
        )
    except Exception as ex:                       # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Interner Fehler: {ex}")


@app.post("/api/messdaten")
async def messdaten(datei: UploadFile):
    """Liest eine Excel-Messdatei (Zeit | y | u)."""
    try:
        return excel_io.messdaten_lesen(await datei.read(), datei.filename or "")
    except excel_io.ExcelError as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@app.post("/api/projekt_parse")
async def projekt_parse(datei: UploadFile):
    """Liest eine AGP-Projektdatei (Formatversion 1)."""
    try:
        return projektdatei.lesen(await datei.read())
    except projektdatei.ProjektdateiError as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@app.post("/api/projekt_xlsx")
def projekt_xlsx(req: ProjektSpeichernRequest):
    """Erzeugt die Projektdatei; Dateiname/Speicherort waehlt das Frontend."""
    try:
        projekt = req.projekt
        if projekt is None:
            projekt = projektdatei.neu(fallname=req.fallname,
                                       beschreibung=req.beschreibung,
                                       programm="PTn-ZPK")
        if req.modelle is not None:
            projekt["modelle"] = req.modelle
        if req.fallname:
            projekt.setdefault("meta", {})["fallname"] = req.fallname
        inhalt = projektdatei.schreiben(projekt, programm=req.programm,
                                        aktion=req.aktion)
        return Response(content=inhalt, media_type=XLSX_MIME)
    except projektdatei.ProjektdateiError as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@app.get("/api/health")
def health():
    return {"status": "ok", "message": "PTn-ZPK-Server laeuft"}


# ─── HTML-Seite und statische Dateien ────────────────────────────────────────

@app.get("/")
def seite1():
    return FileResponse(BASE / "index.html")


app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
