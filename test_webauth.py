"""Tests des Zugriffsschutzes (HTTP Basic Auth).

Geprueft wird die eingehaengte Middleware der echten App - also auch, dass
die Verdrahtung in server.py stimmt.
"""

import base64

from fastapi.testclient import TestClient

from server import app

client = TestClient(app)

PASSWORT = "kurs-2026"


def kopf(benutzer="agp", passwort=PASSWORT):
    roh = base64.b64encode(f"{benutzer}:{passwort}".encode()).decode()
    return {"Authorization": f"Basic {roh}"}


def test_ohne_passwort_umgebung_offen(monkeypatch):
    monkeypatch.delenv("AGP_PASSWORT", raising=False)
    assert client.get("/").status_code == 200


def test_mit_passwort_gesperrt(monkeypatch):
    monkeypatch.setenv("AGP_PASSWORT", PASSWORT)
    antwort = client.get("/")
    assert antwort.status_code == 401
    assert "Basic" in antwort.headers.get("www-authenticate", "")


def test_richtiges_passwort_kommt_durch(monkeypatch):
    monkeypatch.setenv("AGP_PASSWORT", PASSWORT)
    assert client.get("/", headers=kopf()).status_code == 200


def test_falsches_passwort_bleibt_draussen(monkeypatch):
    monkeypatch.setenv("AGP_PASSWORT", PASSWORT)
    assert client.get("/", headers=kopf(passwort="falsch")).status_code == 401
    assert client.get("/", headers=kopf(benutzer="wer")).status_code == 401


def test_healthcheck_bleibt_offen(monkeypatch):
    """Render prueft /api/health ohne Zugangsdaten."""
    monkeypatch.setenv("AGP_PASSWORT", PASSWORT)
    assert client.get("/api/health").status_code == 200


def test_statische_dateien_sind_geschuetzt(monkeypatch):
    """Der Schutz muss auch fuer gemountete Dateien greifen, nicht nur fuer Routen."""
    monkeypatch.setenv("AGP_PASSWORT", PASSWORT)
    assert client.get("/static/app.css").status_code == 401
