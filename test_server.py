"""Tests der API und des Excel-Imports.

Die Fachlogik selbst ist im Kern getestet (agp_control_kern/tests/test_ptn_zpk.py);
hier geht es um die Anbindung: Route, Datenformat, Dateieinlesen.
"""

import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from agp_control_kern import ptn_sprungantwort, ptn_sprungantwort_norm

import excel_io
from server import app

client = TestClient(app)


def _zeit_fuer_anteil(anteil, T, n, t0):
    lo, hi = t0, t0 + 100.0 * T * n
    for _ in range(200):
        m = (lo + hi) / 2
        if ptn_sprungantwort_norm(m, T, n, t0) < anteil:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


def _mappe(zeilen) -> bytes:
    wb = Workbook()
    ws = wb.active
    for z in zeilen:
        ws.append(z)
    puffer = io.BytesIO()
    wb.save(puffer)
    return puffer.getvalue()


# ── API ─────────────────────────────────────────────────────────────────────

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_startseite_wird_ausgeliefert():
    r = client.get("/")
    assert r.status_code == 200
    assert "PTn-Parameter" in r.text


def test_auswertung_findet_ordnung():
    T, t0, n = 2.0, 0.0, 4
    r = client.post("/api/auswertung", json={
        "t0": t0,
        "t10": _zeit_fuer_anteil(0.10, T, n, t0),
        "t50": _zeit_fuer_anteil(0.50, T, n, t0),
        "t90": _zeit_fuer_anteil(0.90, T, n, t0),
        "k_s": 1.0, "d_u": 1.0, "y_a": 0.0,
    })
    assert r.status_code == 200
    e = r.json()
    assert e["gueltig"] is True
    assert e["n_opt"] == n
    assert e["T_n_opt"] == pytest.approx(T, rel=0.01)
    assert e["n_opt_m1"] == n - 1 and e["n_opt_p1"] == n + 1
    assert len(e["modell_opt"]) == len(e["zeit_effektiv"]) > 0


def test_auswertung_ungueltige_zeiten():
    r = client.post("/api/auswertung",
                    json={"t0": 0, "t10": 9, "t50": 3, "t90": 8})
    assert r.status_code == 200
    e = r.json()
    assert e["gueltig"] is False
    assert e["n_opt"] is None
    assert e["modell_opt"] == []


def test_auswertung_ohne_signalwerte_liefert_kennwerte_ohne_kurven():
    r = client.post("/api/auswertung",
                    json={"t0": 0, "t10": 1, "t50": 3, "t90": 8})
    e = r.json()
    assert e["gueltig"] is True
    assert e["n_opt"] is not None
    assert e["modell_opt"] == []


def test_auswertung_mit_messdaten_liefert_abweichungen():
    T, t0, n = 1.5, 0.0, 3
    zeit = np.linspace(0, 30, 300)
    mess = ptn_sprungantwort(zeit, T, n, t0, 0.0, 1.0, 1.0)
    r = client.post("/api/auswertung", json={
        "t0": t0,
        "t10": _zeit_fuer_anteil(0.10, T, n, t0),
        "t50": _zeit_fuer_anteil(0.50, T, n, t0),
        "t90": _zeit_fuer_anteil(0.90, T, n, t0),
        "k_s": 1.0, "d_u": 1.0, "y_a": 0.0,
        "zeit_daten": zeit.tolist(), "mess_daten": mess.tolist(),
    })
    e = r.json()
    assert e["n_opt"] == n
    assert len(e["abw_opt"]["diffs"]) == len(zeit)
    assert e["abw_opt"]["kum_summe_gesamt"] < 1e-3


# ── Excel-Import ────────────────────────────────────────────────────────────

def test_excel_aufbau_c_mit_drei_kopfzeilen():
    inhalt = _mappe([
        ["Versuch 7", None, None],
        ["Zeit", "Temperatur", "Ventil"],
        ["s", "degC", "%"],
        [0.0, 20.0, 0.0],
        [1.0, 22.5, 10.0],
        [2.0, 25.0, 10.0],
    ])
    e = excel_io.messdaten_lesen(inhalt, "versuch7.xlsx")
    assert e["systemname"] == "Versuch 7"
    assert e["var_namen"] == {"zeit": "Zeit", "y": "Temperatur", "u": "Ventil"}
    assert e["einheiten"]["y"] == "degC"
    assert e["zeit"] == [0.0, 1.0, 2.0]
    assert e["y_daten"] == [20.0, 22.5, 25.0]
    assert e["u_daten"] == [0.0, 10.0, 10.0]


def test_excel_aufbau_ab_ohne_kopfzeilen():
    inhalt = _mappe([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0]])
    e = excel_io.messdaten_lesen(inhalt, "roh.xlsx")
    assert e["systemname"] == "roh"          # Dateiname ohne Endung
    assert e["zeit"] == [0.0, 1.0, 2.0]
    assert e["y_daten"] == [1.0, 2.0, 3.0]
    assert e["u_daten"] == []                # dritte Spalte fehlt


def test_excel_ueberspringt_unlesbare_zeilen():
    inhalt = _mappe([[0.0, 1.0], ["Summe", "x"], [1.0, 2.0]])
    e = excel_io.messdaten_lesen(inhalt, "l.xlsx")
    assert e["zeit"] == [0.0, 1.0]


def test_excel_ohne_messwerte_meldet_fehler():
    with pytest.raises(excel_io.ExcelError):
        excel_io.messdaten_lesen(_mappe([["nur", "Text"], ["noch", "Text"]]), "x.xlsx")


def test_excel_route():
    inhalt = _mappe([[0.0, 1.0], [1.0, 2.0]])
    r = client.post("/api/messdaten",
                    files={"datei": ("m.xlsx", inhalt,
                                     "application/vnd.openxmlformats-officedocument."
                                     "spreadsheetml.sheet")})
    assert r.status_code == 200
    assert r.json()["zeit"] == [0.0, 1.0]


def test_excel_route_meldet_fehler_verstaendlich():
    r = client.post("/api/messdaten",
                    files={"datei": ("kaputt.xlsx", b"kein xlsx", "application/octet-stream")})
    assert r.status_code == 400
    assert "detail" in r.json()


def test_konstanten_endpunkt():
    """Die Prueseite braucht die Tabellen der Methode."""
    r = client.get("/api/konstanten")
    assert r.status_code == 200
    k = r.json()
    assert len(k["my_theo_1090"]) == 10
    assert len(k["alpha"]) == 10 and all(len(z) == 3 for z in k["alpha"])
    # alpha_inv ist die elementweise Inverse
    for za, zi in zip(k["alpha"], k["alpha_inv"]):
        for a, i in zip(za, zi):
            assert i == pytest.approx(1.0 / a)
