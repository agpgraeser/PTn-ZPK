# STATUS – PTn-ZPK

Lebendes Logbuch. Neueste Einträge oben.

---

## 2026-08-17 – Projekt angelegt (Portierung aus React)

**Was getan**

- Neues Projekt `PTn-ZPK` im Stack von `RegelkreisSimulationen` aufgebaut
  (FastAPI + vanilla JS + AGP·Control-Design-System). Die alte React-App
  bleibt unverändert lauffähig.
- **Fachlogik in den gemeinsamen Kern gelegt:** `agp_control_kern/ptn_zpk.py`
  (portiert aus `ptnMath.ts`, Tabellen und Rechenweg 1:1 übernommen).
  Commit im Kern-Repo: `e1ac7ea`.
- Excel-Import portiert (`excelParser.ts` → `excel_io.py`, openpyxl).
- Oberfläche neu gebaut: Signalwerte, ZPK-Zeiten, Kennwerte-Tabelle für
  n−1/n/n+1, vier Darstellungen im unteren Diagramm, Messdaten laden.
- `agpProjekt.ts` (256 Zeilen TypeScript-Nachbildung des Projektdatei-Formats)
  **entfällt** – ersetzt durch `agp_control_kern.projektdatei`.

**Vorgeschichte / Fallstrick**

Die Quelle der Live-App lag **nicht** im lokalen Ordner `PTkPTn-WebApp` (der
enthält trotz seines Namens die PT1TT-3-Punkt-App und hängt am Repo
`PT1TT_Berechnung`), sondern nur auf GitHub: `agpgraeser/PTkPTn-WebApp`,
Branch `react-fe`. Geklont nach `..\PTkPTn-PTn-Quelle`, Beschriftungen gegen
die Live-Seite ptkptn.agpcontrol.com geprüft.

**Tests**

| Suite | Ergebnis |
|---|---|
| `agp_control_kern/tests/` (57) | ✅ grün – davon 42 neu für ptn_zpk |
| `PTn-ZPK/test_server.py` (12) | ✅ grün – API + Excel-Import |
| `RegelkreisSimulationen/test_sim_core.py` (74) | ✅ grün – keine Regression |

Kernprüfung: Aus einer exakten PTn-Sprungantwort werden t10/t50/t90 numerisch
bestimmt; das Verfahren gewinnt für **alle Ordnungen 1…10** die Ordnung n und
die Zeitkonstante T (auf 1 % genau) zurück.

**Offene Punkte**

- [x] `agp_control_kern` gepusht (Commit `e1ac7ea` auf `main`).
      Gegengeprüft in einem frischen venv: Installation von GitHub liefert
      `zpk_auswertung`, Probe PT4 ergibt n = 4, T = 1,9995.
      `pip install -r requirements.txt` funktioniert damit, Render kann bauen.
- [x] GitHub-Repo angelegt und gepusht:
      https://github.com/agpgraeser/PTn-ZPK – öffentlich, Branch `main`
      (wie `agp_control_kern`). Vor der Veröffentlichung auf Zugangsdaten
      geprüft, keine gefunden.
- [ ] Render-Deployment einrichten (`render.yaml` liegt bereit)
- [ ] AGP-Projektdatei in der Oberfläche anbinden (Server-Routen existieren)
- [ ] Vergleich alte ./. neue App mit denselben Messdaten durch den Nutzer
- [ ] Danach: PTkPTn-Vergleiche nach demselben Muster portieren

**Nicht Teil dieses Projekts, aber notiert**

Zwei divergente PT1TT-Linien (Ordner `PTkPTn-WebApp` mit V3b-AGP-Arbeit am
Repo `PT1TT_Berechnung` vs. Ordner `PT1TT_Berechnung` mit Netlify-Konfig am
Repo `pt1tt-3punkt`). Vom Nutzer bewusst vertagt.
