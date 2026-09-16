# PTn-ZPK – Projektnotizen

> **📍 Aktueller Stand: siehe [`STATUS.md`](STATUS.md) – zu Sitzungsbeginn zuerst lesen.**
> **🔄 Am Ende jeder Arbeitssitzung `STATUS.md` aktualisieren** – auch ohne Aufforderung
> (Stichpunkte: was getan, Commit-Hashes, offene Punkte). Grundlage der Tagesdoku.
> Diese Datei = stabile Projektnotizen + Architektur; `STATUS.md` = lebender Stand.

## Projektbeschreibung
Web-App zur Bestimmung der Parameter eines **PTn-Streckenmodells** aus einer
gemessenen Sprungantwort nach der **Zeit-Prozent-Kennwert-Methode (ZPK)**.
Aus den drei Zeiten t10/t50/t90 werden Ordnung *n* und Zeitkonstante *T*
bestimmt; die Nachbarordnungen n−1 und n+1 werden mitgerechnet, damit der
Anwender vergleichen kann, welches Modell die Messung am besten trifft.

- **Backend:** Python, FastAPI (`server.py`), Excel-Import in `excel_io.py`.
  Die **Fachlogik liegt im gemeinsamen Paket `agp_control_kern.ptn_zpk`** –
  nicht in dieser App. So benutzen alle Programme der Familie dieselbe Rechnung.
- **Frontend:** `index.html` (eine Seite, vanilla JS), Plotly.js.
  Styling über das **AGP·Control-Design-System**: `static/agp-design-system.css`
  (Kopie; Master in `F:\Dropbox\1_a_a_WebApp\_AGP-DesignSystem\`) +
  `static/app.css` (App-Spezifisches).
- **Start:** `start.bat` → http://localhost:8010 (ein Server liefert Seite UND API, kein CORS)
- **Tests:** `venv\Scripts\python.exe -m pytest test_server.py`
  (Fachlogik-Tests liegen im Kern: `agp_control_kern/tests/test_ptn_zpk.py`)

## Herkunft (Stack-Vereinheitlichung 2026-08-17)
Neuaufbau der React/Vite/MUI-App **PTkPTn** im Stack von `RegelkreisSimulationen`.
Die alte App bleibt unverändert lauffähig; Ziel ist, dass später alle Programme
über ein übergeordnetes Programm aufgerufen und gekoppelt werden können.

**Quelle der Portierung:** GitHub `agpgraeser/PTkPTn-WebApp`, Branch **`react-fe`**,
lokal geklont nach `F:\Dropbox\1_a_a_WebApp\PTkPTn-PTn-Quelle`.
⚠️ **Nicht** der lokale Ordner `PTkPTn-WebApp` – der enthält trotz seines Namens
die PT1TT-3-Punkt-App und hängt am Repo `PT1TT_Berechnung`.

Portiert wurde:
- `src/utils/ptnMath.ts` → `agp_control_kern/ptn_zpk.py` (Tabellen und Rechenweg 1:1)
- `src/utils/excelParser.ts` → `excel_io.py` (openpyxl statt xlsx)
- `ParameterPanel.tsx` + `ResponseChart.tsx` → `index.html`
- `agpProjekt.ts` **entfällt** – die AGP-Projektdatei kommt jetzt aus
  `agp_control_kern.projektdatei`, es gibt keine TypeScript-Nachbildung mehr.

## Fachliche Kurzfassung
- Eingaben: YA/YE (Ausgangsgröße), UA/UE (Stellgröße), t₀ und t10/t50/t90
- DY = YE − YA, DU = UE − UA, **kS = DY / DU**
- Y10/Y50/Y90 = YA + 0,1/0,5/0,9 · DY (die Amplituden, zu denen die Zeiten abgelesen werden)
- Ordnung: n so, dass |t10/t90 − µ_theo(n)| minimal wird (Tabelle `MY_THEO_1090`)
- Zeitkonstante: T = ⅓ · (α10·t10 + α50·t50 + α90·t90) mit den α aus `ALPHA`
- Var = Streuung der drei Einzelschätzungen α·t/3 – klein heißt, die drei
  Zeitwerte passen konsistent zu dieser Ordnung

## Wichtige Design-Entscheidungen
- **Ungültige Eingaben liefern `gueltig: False` statt einer Exception.** Die
  Oberfläche rechnet beim Tippen live mit; ein Fehler bei jedem Zwischenstand
  wäre unbrauchbar. Übernommen aus der Alt-App.
- **Ohne Messdaten** wird ein synthetischer Zeitvektor erzeugt (1000 Punkte,
  0 … t₀ + T·n·5), damit die Modellkurven auch ohne Excel sichtbar sind.
- Die Reihe der Sprungantwort wird **iterativ** aufgebaut
  (Term_i = Term_{i−1}·τ/i) statt über τ^i/i! – das bleibt bei hohen
  Ordnungen numerisch stabil.
- Seite ist bewusst **hell gepinnt** (`color-scheme: light` in app.css), weil die
  Plotly-Charts noch nicht dark-mode-fähig gestylt sind (wie RegelkreisSimulationen).

## Plotly
Erfahrungen/Fallstricke: Skill `plotly-erfahrungen`.
Hier umgesetzt: `hovermode:'closest'`, Neuzeichnen per `purge`+`newPlot`,
keine Shapes mit NaN-Koordinaten (jede Hilfslinie hat eine eigene
Gültigkeitsprüfung – eine einzige NaN-Koordinate deaktiviert in Plotly den
gesamten Hover-Layer), keine leeren Traces.

## Automatisierungsgrad (Trainer-Vorgabe, 2026-09-16)
Der Kursleiter legt fest, wie viel die App dem Teilnehmer bei der
Parameterbestimmung abnimmt. Messdaten laden kann der Teilnehmer in **allen**
Fällen; der gewählte Grad steht in der Kopfzeile zwischen „PTn-Parameter Tool"
und „Berechnungen überprüfen".

| Grad | Anzeige | YA/YE/UA/UE, t₀ | Y10/Y50/Y90 | t10/t50/t90 |
|---|---|---|---|---|
| **a** | Manuell | von Hand | **von Hand** | von Hand |
| **b** | Teilautomatisch | von Hand | berechnet, gesperrt | von Hand |
| **c** | Vollautomatisch | abgelesen | abgelesen | abgelesen |

Grad **b** ist der Stand vor dieser Erweiterung und bleibt die Vorgabe.
In **c** sind alle Werte änderbar – die Erfassung ist ein Vorschlag.

**Einstellung:** Grundwert über die Umgebungsvariable `AGP_AUTOMATIK=a|b|c`
(Render: je Dienst unter *Environment*; lokal in `start.bat`), zur Laufzeit
überschreibbar per URL-Parameter `?modus=a|b|c`. Unbekannte Werte fallen auf
`b` zurück. Der URL-Parameter ist Absicht (Steigerung a → b → c im Kurs), er
ist **keine Sperre** – ein Teilnehmer kann ihn selbst setzen.

**Wo:** `modus_lesen()` und `/api/modus` in `server.py`, `modusAnwenden()` in
`index.html`, Badge `.modus-anzeige` in `static/app.css`.

### Auto-Erfassung (`autoerfassung.py`)
Liegt bewusst **in dieser App**, nicht im Kern – sie hängt am Messdatenformat
(`excel_io.py` liegt aus demselben Grund lokal). Verfahren:
- YA/YE als **Median** eines 5-%-Randbereichs (robust gegen Rauschen)
- t₀, UA, UE aus dem Sprung der **Stellgröße**
- t10/t50/t90 durch **lineare Interpolation** zwischen den Nachbarpunkten
- fallende Sprünge (ΔY < 0) sind mitbehandelt

**⚠️ Ohne Stellgrößenspalte bleibt t₀ offen.** Eine träge Strecke läuft nach
dem Sprung fast waagerecht los; jede Schätzung aus y allein liegt zu spät, und
t₀ geht direkt in die Rechnung ein. Gemessen (T = 2, exakte Sprungantworten):

| n soll | n mit u | n ohne u | T ohne u |
|---|---|---|---|
| 2 | 2 | 1 | 2,31 |
| 5 | 5 | **1** | 6,82 |
| 8 | 8 | **2** | 4,42 |

Deshalb werden UA, UE **und t₀** dann nicht eingetragen, sondern als Hinweis
gemeldet (der Schätzwert steht im Text als Anhaltspunkt). **Nicht bestimmbare
Felder werden geleert**, nicht mit dem Altwert stehen gelassen – sonst rechnet
die App stillschweigend mit dem Vorgabewert t₀ = 0 weiter und liefert eine
falsche Ordnung (im Browser genau so beobachtet).

### Fallstrick Design-System
`.agp-btn { display: inline-flex }` **überstimmt das Attribut `hidden`** – ein
per JS ausgeblendeter Knopf bleibt sichtbar. Behoben mit
`[hidden] { display: none !important; }` in `static/app.css`; gehört
mittelfristig in den Master unter `_AGP-DesignSystem\`.

## Offene Punkte
- AGP-Projektdatei: Lesen/Schreiben ist im Server angelegt
  (`/api/projekt_parse`, `/api/projekt_xlsx`), in der Oberfläche aber noch
  nicht angebunden.
- ~~Deployment (Render)~~ – erledigt, live unter https://ptn-zpk.onrender.com
- `[hidden]`-Korrektur in den Design-System-Master übernehmen (betrifft alle Apps).
- Auto-Erfassung nach `agp_control_kern` heben, wenn sie sich bewährt hat.
