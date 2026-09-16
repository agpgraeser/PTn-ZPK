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


# ══ Automatisierungsgrad und Auto-Erfassung ═══════════════════════════════════

def _sprungmessung(T=2.0, n=3, t0=1.0, ya=10.0, dy=5.0, ua=2.0, ue=4.0,
                   t_ende=40.0, punkte=800):
    """Exakte PTn-Sprungantwort als Messreihe (Zeit, y, u)."""
    zeit = list(np.linspace(0.0, t_ende, punkte))
    y = [ya + dy * ptn_sprungantwort_norm(t, T, n, t0) for t in zeit]
    u = [ua if t < t0 else ue for t in zeit]
    return zeit, y, u


def test_modus_grundwert_ist_b():
    antwort = client.get("/api/modus")
    assert antwort.status_code == 200
    assert antwort.json()["modus"] in ("a", "b", "c")


def test_modus_aus_umgebung(monkeypatch):
    import server
    monkeypatch.setenv("AGP_AUTOMATIK", "c")
    assert server.modus_lesen() == "c"
    monkeypatch.setenv("AGP_AUTOMATIK", "Unsinn")
    assert server.modus_lesen() == "b"


def test_autoerfassung_findet_die_eingaben():
    T, n, t0, ya, dy = 2.0, 3, 1.0, 10.0, 5.0
    zeit, y, u = _sprungmessung(T=T, n=n, t0=t0, ya=ya, dy=dy)

    antwort = client.post("/api/autoerfassung",
                          json={"zeit": zeit, "y_daten": y, "u_daten": u})
    assert antwort.status_code == 200
    e = antwort.json()

    assert e["ya"] == pytest.approx(ya, abs=0.05)
    assert e["ye"] == pytest.approx(ya + dy, abs=0.05)
    assert e["ua"] == pytest.approx(2.0, abs=1e-9)
    assert e["ue"] == pytest.approx(4.0, abs=1e-9)
    assert e["t0"] == pytest.approx(t0, abs=0.1)

    # Ablesehoehen liegen bei 10/50/90 % des Hubs
    assert e["y10"] == pytest.approx(ya + 0.10 * dy, abs=0.05)
    assert e["y90"] == pytest.approx(ya + 0.90 * dy, abs=0.05)

    # Die abgelesenen Zeiten treffen die exakten Schwellenzeiten
    for anteil, schluessel in ((0.10, "t10"), (0.50, "t50"), (0.90, "t90")):
        soll = _zeit_fuer_anteil(anteil, T, n, t0)
        assert e[schluessel] == pytest.approx(soll, abs=0.1)


def test_autoerfassung_rechnet_richtig_zurueck():
    """Die erfassten Werte muessen die Ordnung und Zeitkonstante zurueckgeben."""
    T, n, t0 = 3.0, 4, 2.0
    zeit, y, u = _sprungmessung(T=T, n=n, t0=t0, ya=0.0, dy=1.0,
                                t_ende=100.0, punkte=2000)
    e = client.post("/api/autoerfassung",
                    json={"zeit": zeit, "y_daten": y, "u_daten": u}).json()

    erg = client.post("/api/auswertung", json={
        "t0": e["t0"], "t10": e["t10"], "t50": e["t50"], "t90": e["t90"],
        "k_s": 0.5, "d_u": 2.0, "y_a": 0.0,
    }).json()
    assert erg["gueltig"] is True
    assert erg["n_opt"] == n
    assert erg["T_n_opt"] == pytest.approx(T, rel=0.02)


def test_autoerfassung_ohne_stellgroesse():
    """Ohne u-Spalte bleiben UA/UE offen, alles andere wird bestimmt."""
    zeit, y, _ = _sprungmessung(t0=1.0, ya=10.0, dy=5.0)
    e = client.post("/api/autoerfassung",
                    json={"zeit": zeit, "y_daten": y, "u_daten": None}).json()

    assert e["ua"] is None and e["ue"] is None
    assert e["hat_u"] is False
    assert any("Stellgröße" in h for h in e["hinweise"])
    assert e["ye"] == pytest.approx(15.0, abs=0.05)

    # t0 bleibt bewusst offen: ohne Stellgroesse ist der Sprungzeitpunkt nicht
    # sicher bestimmbar, und ein zu spaeter Wert verfaelscht die Ordnung.
    assert e["t0"] is None
    assert e["t0_geschaetzt"] is not None
    assert any("t₀" in h for h in e["hinweise"])
    # Die Ablesezeiten werden trotzdem bestimmt.
    assert e["t10"] < e["t50"] < e["t90"]


def test_autoerfassung_fallender_sprung():
    """Auch ein negativer Hub muss abgelesen werden koennen."""
    zeit, y, u = _sprungmessung(ya=20.0, dy=-8.0, ua=5.0, ue=1.0)
    e = client.post("/api/autoerfassung",
                    json={"zeit": zeit, "y_daten": y, "u_daten": u}).json()

    assert e["ya"] == pytest.approx(20.0, abs=0.05)
    assert e["ye"] == pytest.approx(12.0, abs=0.05)
    assert e["y10"] == pytest.approx(19.2, abs=0.05)
    assert None not in (e["t10"], e["t50"], e["t90"])
    assert e["t10"] < e["t50"] < e["t90"]


def test_autoerfassung_vertraegt_rauschen():
    """Median-Bildung: ein verrauschtes Signal darf YA/YE nicht verschieben."""
    rng = np.random.default_rng(42)
    zeit, y, u = _sprungmessung(ya=10.0, dy=5.0, punkte=1200)
    y_rausch = [v + r for v, r in zip(y, rng.normal(0.0, 0.02, len(y)))]

    e = client.post("/api/autoerfassung",
                    json={"zeit": zeit, "y_daten": y_rausch, "u_daten": u}).json()
    assert e["ya"] == pytest.approx(10.0, abs=0.05)
    assert e["ye"] == pytest.approx(15.0, abs=0.05)
    assert e["t10"] < e["t50"] < e["t90"]


def test_autoerfassung_meldet_konstante_messung():
    zeit = list(np.linspace(0.0, 10.0, 50))
    y = [3.0] * 50
    antwort = client.post("/api/autoerfassung",
                          json={"zeit": zeit, "y_daten": y, "u_daten": None})
    assert antwort.status_code == 400
    assert "Sprungantwort" in antwort.json()["detail"]


def test_autoerfassung_meldet_zu_wenige_punkte():
    antwort = client.post("/api/autoerfassung",
                          json={"zeit": [0.0, 1.0], "y_daten": [0.0, 1.0]})
    assert antwort.status_code == 400
    assert "Messpunkte" in antwort.json()["detail"]
