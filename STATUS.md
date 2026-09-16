# STATUS – PTn-ZPK

Lebendes Logbuch. Neueste Einträge oben.

---

## 2026-09-16 – Automatisierungsgrad a/b/c (Trainer-Vorgabe)

**Was getan**

- Der Kursleiter kann jetzt vorgeben, wie viel die App bei der
  Parameterbestimmung abnimmt: **a** manuell, **b** teilautomatisch (bisheriger
  Stand, bleibt Vorgabe), **c** vollautomatisch. Messdaten laden geht in allen
  Fällen. Der Grad steht als Badge in der Kopfzeile zwischen „PTn-Parameter
  Tool" und „Berechnungen überprüfen".
- Einstellung zweistufig: `AGP_AUTOMATIK=a|b|c` als Grundwert (Render
  *Environment* / `start.bat`), `?modus=a|b|c` überschreibt zur Laufzeit –
  damit im Kurs die Steigerung a → b → c möglich ist, ohne den Dienst neu zu
  starten. Unbekannte Werte fallen auf `b`.
- Neu: `autoerfassung.py` (Ablesen aus der Messung), `/api/modus`,
  `/api/autoerfassung`, `modusAnwenden()` + `autoErfassen()` in `index.html`,
  Knopf „Werte neu erfassen", Badge in `static/app.css`.
- In **a** sind Y10/Y50/Y90 freie Felder, und die grünen Ablesehilfslinien
  folgen dem **eingegebenen** Wert – ein Rechenfehler wird im Diagramm sichtbar
  (so vom Nutzer gewünscht; das Programm meldet dazu nichts).

**Zwei Befunde, die den Entwurf geändert haben**

1. **Ohne Stellgrößenspalte ist t₀ nicht bestimmbar** – und t₀ geht direkt in
   die ZPK-Rechnung ein. Eine träge Strecke läuft nach dem Sprung fast
   waagerecht los, jede Schätzung aus y allein liegt zu spät. Gemessen an
   exakten Sprungantworten (T = 2): aus PT5 wird PT1 (T = 6,8), aus PT8 wird
   PT2 (T = 4,4). Deshalb bleibt t₀ dann **offen** wie UA/UE, mit Hinweis und
   Schätzwert als Anhaltspunkt. Ursprünglich war „alles außer UA/UE
   automatisch" verabredet – der Messwert hat das widerlegt.
2. **Nicht bestimmbare Felder müssen geleert werden.** Beim ersten Entwurf
   blieben sie stehen; die App rechnete dann mit dem Vorgabewert t₀ = 0 weiter
   und zeigte stillschweigend n = 6 statt 4. Im Browser genau so beobachtet.

**Nebenbefund (betrifft alle Apps der Familie)**

`.agp-btn { display: inline-flex }` im Design-System **überstimmt das Attribut
`hidden`** – ein per JS ausgeblendeter Knopf bleibt sichtbar. Hier mit
`[hidden] { display: none !important; }` in `static/app.css` behoben; gehört in
den Master unter `_AGP-DesignSystem\`.

**Tests**

| Suite | Ergebnis |
|---|---|
| `test_server.py` + `test_webauth.py` (28) | ✅ grün – davon 8 neu für Modus und Auto-Erfassung |

Geprüft wird unter anderem, dass die erfassten Werte die Ordnung und
Zeitkonstante **zurückgeben** (PT4, T = 3 → n = 4, T = 3,01), dass ein
verrauschtes Signal YA/YE nicht verschiebt und dass fallende Sprünge
funktionieren.

**Im Browser nachgeprüft** (alle drei Grade, PT4 mit T = 3, t₀ = 2):
a → Felder frei und leer, Hilfslinie folgt einem falsch eingegebenen Y50;
b → unverändert gesperrt und gerechnet;
c → alle Felder gefüllt, n = 4, T = 3,01, kS = 2,5, Werte änderbar.

**Offene Punkte**

- [ ] `[hidden]`-Korrektur in den Design-System-Master übernehmen
- [ ] Auto-Erfassung nach `agp_control_kern` heben, wenn sie sich bewährt hat
- [ ] Entscheiden, welcher Grad im Kurs die Render-Vorgabe wird
      (`AGP_AUTOMATIK` beim Dienst `ptn-zpk` setzen)

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
- [x] **Live unter https://ptn-zpk.onrender.com** (2026-08-17).
      Fachlich geprüft: exaktes PT4 ergibt n=4, T=1,9995, Var 6,5·10⁻⁸.
      Karte in der HdT-Oberfläche freigeschaltet.
- [ ] ⚠️ **Dienst flattert:** ca. 13 von 15 Abrufen kommen durch, der Rest
      endet mit `x-render-routing: no-server`. Das kommt von Renders
      Routing, nicht von der App (eine echte App-404 sähe anders aus, und
      OpenAPI zeigt alle Routen). `ptn-vergleich` läuft mit derselben
      Bauart 15/15 – also dienstspezifisch. Render-Logs/Events prüfen:
      hängengebliebener Deploy oder Neustart (Free-Plan: 512 MB, numpy).
- [ ] AGP-Projektdatei in der Oberfläche anbinden (Server-Routen existieren)
- [ ] Vergleich alte ./. neue App mit denselben Messdaten durch den Nutzer
- [ ] Danach: PTkPTn-Vergleiche nach demselben Muster portieren

**Nicht Teil dieses Projekts, aber notiert**

Zwei divergente PT1TT-Linien (Ordner `PTkPTn-WebApp` mit V3b-AGP-Arbeit am
Repo `PT1TT_Berechnung` vs. Ordner `PT1TT_Berechnung` mit Netlify-Konfig am
Repo `pt1tt-3punkt`). Vom Nutzer bewusst vertagt.
