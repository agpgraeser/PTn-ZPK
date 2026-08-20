"""HTTP Basic Auth fuer die AGP-Control-Apps.

Der Schutz ist **nur aktiv, wenn die Umgebungsvariable `AGP_PASSWORT` gesetzt
ist**. Ohne sie laeuft die App wie bisher offen - so bleibt die lokale
Entwicklung unveraendert, und ein vergessener Eintrag sperrt niemanden aus.

Auf Render je Dienst unter *Environment* setzen:

    AGP_PASSWORT = <Kurspasswort>
    AGP_BENUTZER = <optional, Standard "agp">

Anders als das JS-Gate der Startseite wirkt dies **serverseitig**: ohne
Passwort liefert der Server nichts aus - auch nicht ueber einen Direktlink.
Die Zugangsdaten werden bei jeder Anfrage aus der Umgebung gelesen, damit ein
geaendertes Passwort nach dem Neustart des Dienstes sofort gilt.
"""

from __future__ import annotations

import base64
import os
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Pfade, die immer offen bleiben (Healthcheck von Render).
OFFENE_PFADE = ("/api/health",)


def zugangsdaten() -> tuple[str, str]:
    """Benutzer und Passwort aus der Umgebung (leeres Passwort = kein Schutz)."""
    return os.environ.get("AGP_BENUTZER", "agp"), os.environ.get("AGP_PASSWORT", "")


def _kopfzeile_stimmt(kopfzeile: str, benutzer: str, passwort: str) -> bool:
    if not kopfzeile.startswith("Basic "):
        return False
    try:
        roh = base64.b64decode(kopfzeile[6:]).decode("utf-8")
    except Exception:
        return False
    gesendet_benutzer, trenner, gesendet_passwort = roh.partition(":")
    if not trenner:
        return False
    # compare_digest auf beiden Feldern: die Laufzeit verraet nichts ueber
    # die Anzahl richtiger Zeichen.
    return (secrets.compare_digest(gesendet_benutzer, benutzer)
            and secrets.compare_digest(gesendet_passwort, passwort))


class BasicAuth(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        benutzer, passwort = zugangsdaten()
        if not passwort or request.url.path in OFFENE_PFADE:
            return await call_next(request)
        if _kopfzeile_stimmt(request.headers.get("authorization", ""), benutzer, passwort):
            return await call_next(request)
        return Response(
            "Zugang nur mit Kurspasswort.",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="AGP-Control", charset="UTF-8"'},
        )


def schutz_aktivieren(app) -> bool:
    """Haengt den Schutz in die App ein. Rueckgabe: ob er gerade aktiv ist."""
    app.add_middleware(BasicAuth)
    return bool(zugangsdaten()[1])
