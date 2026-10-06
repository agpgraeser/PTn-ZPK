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

Blatt „Zeitverlaeufe" (seit 2026-10-06) – Ergebnis- und Projektdateien der
AGP-Programmfamilie (z. B. RegelkreisSimulationen, Seite 3). Hat die Mappe
dieses Blatt, wird es statt des ersten Blatts gelesen; die Spalten werden
über ihre Kopfzeile gefunden (t | y | u, Reihenfolge beliebig).
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
        blatt_zv = "Zeitverlaeufe" in wb.sheetnames
        if not blatt_zv and "Meta" in wb.sheetnames:
            raise ExcelError("Projektdatei ohne Blatt „Zeitverlaeufe“ – in "
                             "RegelkreisSimulationen erst einen Streckentest fahren und auf "
                             "Seite 3 „Zeitverläufe → Projektdatei“ speichern.")
        ws = wb["Zeitverlaeufe" if blatt_zv else wb.sheetnames[0]]
        zeilen = [list(z) for z in ws.iter_rows(values_only=True)]
    finally:
        wb.close()

    if not zeilen:
        raise ExcelError("Die Tabelle ist leer.")

    basisname = dateiname.rsplit(".", 1)[0] if "." in dateiname else dateiname

    if blatt_zv:
        return _zeitverlaeufe_lesen(zeilen, basisname, dateiname)

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


def _spaltenname(kopf) -> tuple[str, str]:
    """'t [s]' -> ('t', 's'); 'u_absolut' -> ('u_absolut', '')."""
    text = "" if kopf is None else str(kopf).strip()
    einheit = ""
    if "[" in text and text.endswith("]"):
        text, einheit = text[:text.index("[")].strip(), text[text.index("[") + 1:-1].strip()
    return text.lower(), einheit


def _zeitverlaeufe_lesen(zeilen: list, basisname: str, dateiname: str) -> dict:
    """Blatt „Zeitverlaeufe": Kopfzeile mit Spaltennamen, darunter Werte.

    Gesucht werden t (auch „t [s]", „Zeit"), y und u. Bei Regelkreis-Läufen
    gibt es u_Regler und u_absolut – dann zählt u_absolut, die tatsächlich auf
    die Strecke wirkende Stellgröße.
    """
    kopf = [_spaltenname(k) for k in zeilen[0]]
    namen = [n for n, _ in kopf]

    def finde(*kandidaten):
        for k in kandidaten:
            if k in namen:
                return namen.index(k)
        return None

    i_t = finde("t", "zeit", "time")
    i_y = finde("y")
    i_u = finde("u_absolut", "u")
    if i_t is None or i_y is None:
        raise ExcelError("Blatt „Zeitverlaeufe“: Spalten t und y nicht gefunden "
                         f"(vorhanden: {', '.join(n for n in namen if n)}).")

    zeit: list[float] = []
    y_daten: list[float] = []
    u_daten: list[float] = []
    for zeile in zeilen[1:]:
        if not zeile:
            continue
        t = _zahl(zeile[i_t]) if i_t < len(zeile) else None
        y = _zahl(zeile[i_y]) if i_y < len(zeile) else None
        if t is None or y is None:
            continue
        zeit.append(t)
        y_daten.append(y)
        if i_u is not None:
            u = _zahl(zeile[i_u]) if i_u < len(zeile) else None
            u_daten.append(u if u is not None else 0.0)

    if not zeit:
        raise ExcelError("Blatt „Zeitverlaeufe“ enthält keine Messwerte.")

    hinweis = ""
    if "w" in namen:
        hinweis = ("Regelkreis-Lauf (geschlossener Kreis) – keine reine "
                   "Sprungantwort der Strecke; für PTn-ZPK den Streckentest verwenden.")

    def kopftext(i, vorgabe):
        return str(zeilen[0][i]) if i is not None else vorgabe

    return {
        "zeit": zeit,
        "y_daten": y_daten,
        "u_daten": u_daten,
        "systemname": basisname,
        "var_namen": {"zeit": kopftext(i_t, "t"), "y": kopftext(i_y, "y"),
                      "u": kopftext(i_u, "u")},
        "einheiten": {"zeit": kopf[i_t][1], "y": kopf[i_y][1],
                      "u": kopf[i_u][1] if i_u is not None else ""},
        "vorschau": [[("" if z is None else str(z)) for z in (zeile or [])[:3]]
                     for zeile in zeilen[:3]],
        "dateiname": dateiname,
        "quelle": "Zeitverlaeufe",
        "hinweis": hinweis,
    }
