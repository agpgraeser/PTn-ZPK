"""
excel_io.py – Einlesen der Messdaten-Arbeitsmappen.

Portiert aus `src/utils/excelParser.ts` der React-App (2026-08-17), damit
dieselben Dateien wie bisher gelesen werden koennen.

Erkannt werden zwei Aufbauten:

Aufbau C – drei Kopfzeilen:
    Zeile 1: Systemname
    Zeile 2: Variablennamen  (Zeit | y | u)
    Zeile 3: Einheiten
    ab Zeile 4: Messwerte

Aufbau A/B – keine oder eine Kopfzeile, Spalten Zeit | y | u.
"""

from __future__ import annotations

import io

from openpyxl import load_workbook


class ExcelError(ValueError):
    """Fehler mit verstaendlicher Meldung fuer das Frontend."""


def _zahl(wert) -> float | None:
    """Wandelt eine Zelle in eine Zahl; gibt None zurueck wenn das nicht geht."""
    if wert is None or isinstance(wert, bool):
        return None
    if isinstance(wert, (int, float)):
        return float(wert)
    text = str(wert).strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def messdaten_lesen(inhalt: bytes, dateiname: str = "") -> dict:
    """Liest die erste Tabelle der Arbeitsmappe.

    Rueckgabe: zeit / y_daten / u_daten (Listen), systemname, var_namen,
    einheiten und die ersten drei Zeilen als Vorschau.
    """
    try:
        wb = load_workbook(io.BytesIO(inhalt), data_only=True, read_only=True)
    except Exception as ex:
        raise ExcelError(f"Datei konnte nicht gelesen werden: {ex}")

    try:
        ws = wb[wb.sheetnames[0]]
        zeilen = [list(z) for z in ws.iter_rows(values_only=True)]
    finally:
        wb.close()

    if not zeilen:
        raise ExcelError("Die Tabelle ist leer.")

    basisname = dateiname.rsplit(".", 1)[0] if "." in dateiname else dateiname

    erste = zeilen[0] if len(zeilen) > 0 else []
    zweite = zeilen[1] if len(zeilen) > 1 else []
    dritte = zeilen[2] if len(zeilen) > 2 else []

    def ist_text(zeile, spalte=0):
        return (len(zeile) > spalte
                and isinstance(zeile[spalte], str)
                and zeile[spalte].strip() != "")

    # Aufbau C: Kopfzeile 1 und 2 sind Text, es gibt eine dritte Zeile
    aufbau_c = ist_text(erste) and ist_text(zweite) and len(dritte) > 0

    def txt(zeile, i, vorgabe):
        if len(zeile) > i and zeile[i] not in (None, ""):
            return str(zeile[i])
        return vorgabe

    if aufbau_c:
        systemname = str(erste[0])
        var_namen = {"zeit": txt(zweite, 0, "Zeit"),
                     "y": txt(zweite, 1, "y"),
                     "u": txt(zweite, 2, "u")}
        einheiten = {"zeit": txt(dritte, 0, ""),
                     "y": txt(dritte, 1, ""),
                     "u": txt(dritte, 2, "")}
        daten_ab = 3
        hat_u = len(zweite) >= 3 and zweite[2] not in (None, "")
    else:
        systemname = basisname
        var_namen = {"zeit": "Zeit", "y": "y", "u": "u"}
        einheiten = {"zeit": "", "y": "", "u": ""}
        daten_ab = 0
        hat_u = len(erste) >= 3

    zeit: list[float] = []
    y_daten: list[float] = []
    u_daten: list[float] = []

    for zeile in zeilen[daten_ab:]:
        if not zeile or len(zeile) < 2:
            continue
        t = _zahl(zeile[0])
        y = _zahl(zeile[1])
        if t is None or y is None:
            continue                      # Kopf-/Leerzeilen ueberspringen
        zeit.append(t)
        y_daten.append(y)
        if hat_u and len(zeile) >= 3:
            u = _zahl(zeile[2])
            u_daten.append(u if u is not None else 0.0)

    if not zeit:
        raise ExcelError("Keine auswertbaren Messwerte gefunden "
                         "(erwartet: Spalte 1 Zeit, Spalte 2 Messgroesse).")

    vorschau = [[("" if z is None else str(z)) for z in (zeile or [])[:3]]
                for zeile in zeilen[:3]]

    return {
        "zeit": zeit,
        "y_daten": y_daten,
        "u_daten": u_daten,
        "systemname": systemname,
        "var_namen": var_namen,
        "einheiten": einheiten,
        "vorschau": vorschau,
        "dateiname": dateiname,
    }
