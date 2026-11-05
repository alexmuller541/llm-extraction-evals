# llm-extraction-evals

Eval-Harness für LLM-Extraktion aus **Lieferanten-Auftragsbestätigungen** (DE/EN, Formular oder E-Mail-Text).

Die zentrale Frage ist nicht nur „Wie viele Felder stimmen?“, sondern: **Wie oft landet ein falscher Liefertermin ohne Prüfmarkierung im System?** Ein falscher bestätigter Termin verfälscht Bestandsprognosen und Euro-Zahlen, ein fehlender Termin kostet nur einen Blick.

> **Status:** Harness, Gold-Set, Metriken, Tests und regelbasierte Baseline laufen. Die Messung des ORIGIN-Prompts mit einem LLM (Tabelle unten) steht noch aus und wird erst eingetragen, wenn sie gelaufen ist.

## Was gemessen wird

| Metrik | Bedeutung |
|---|---|
| Precision / Recall / F1 pro Feld | Feldweiser Vergleich nach Normalisierung (Datum, Zahl, Währung, PO-Nummer) |
| **Verzicht (Abstention)** | Bei fehlenden oder uneindeutigen Angaben muss `null` kommen. Jeder erfundene Wert zählt als Halluzination |
| **Unmarkierte Fehler** | Schlüsselfeld (PO, Termin) falsch, aber `needs_review = false`. Der gefährliche Fall |
| Fehlerfang-Rate | Anteil der Fehler, die die Pipeline selbst zur Prüfung markiert |
| Kalibrierung (ECE) | Passt die angegebene Konfidenz zur tatsächlichen Trefferquote? |
| Evidenz | Steht das gelieferte Beleg-Snippet wörtlich im Dokument? |
| Szenario-Aufschlüsselung | Wo genau scheitert ein System (z. B. nur bei Wunsch- vs. Bestätigungstermin) |

## Das Gold-Set

80 synthetische Dokumente, reproduzierbar per Seed (`python eval/generate_gold.py --n 80 --seed 42`). Labels entstehen zusammen mit dem Dokument. Keine echten Kunden- oder Arbeitgeberdaten.

| Szenario | Was es testet | Soll |
|---|---|---|
| `clean` | ein klar beschrifteter Termin | Termin |
| `both_dates` | Wunschtermin des Käufers **und** bestätigter Termin | den bestätigten |
| `only_requested` | nur der Wunschtermin steht im Dokument | `null` |
| `ambiguous_date` | `04/05/2026`: Tag und Monat nicht unterscheidbar | `null` |
| `missing_po` | keine Bestellnummer, nur eine AB-Nummer | `null` für die PO |
| `email` | Fließtext statt Formular | Termin, PO, Preis |
| `distractor` | Termin/PO einer früheren Lieferung im selben Dokument | die richtigen |
| `ocr_noise` | OCR-Verwechslungen in den Beschriftungen | Werte trotzdem richtig |

## Ergebnisse

Gemessen auf n = 80, Stand des Repos. „–“ heißt: noch nicht gemessen.

| | Regelbasierte Baseline | ORIGIN-Prompt auf NIM (`nemotron-3-ultra-550b`) |
|---|---|---|
| PO-Nummer F1 | 98,6 % | – |
| **Termin F1** | **64,3 %** | – |
| Termin halluziniert (Soll `null`) | 9 | – |
| Dokumente mit falschem Schlüsselfeld | 30 von 80 | – |
| davon **ohne Prüfmarkierung** | **30** (37,5 %) | – |
| Fehlerfang-Rate | 0 % | – |

Die Baseline nimmt das erste Datum in einer Zeile mit „liefer/deliver/ship“. Sie scheitert genau dort, wo man es erwartet: Wunschtermin statt bestätigtem (10 von 18 `both_dates`), mehrdeutige Daten (7 von 7 halluziniert), Termin einer früheren Lieferung (6 von 6 falsch). Keiner ihrer 30 Fehler wird zur Prüfung markiert. Ihr Mengenfeld liest deutsche Tausenderpunkte falsch (`1.200` als 1,2). Das ist eine echte Schwäche einfacher Regeln und kein Messfehler.

Vollständiger Bericht: [`results/regex_baseline.md`](results/regex_baseline.md).

## Aufbau

```
data/gold/             80 Dokumente (.txt) + Ground Truth (.json) + manifest.json
eval/generate_gold.py  Szenario-Generator (Seed)
eval/metrics.py        alle Metriken, Regressions-Gate
eval/run_eval.py       Adapter über das Gold-Set laufen lassen, Bericht schreiben
eval/report.py         Markdown-Bericht
eval/adapters/         austauschbare Systeme unter Test
  regex_baseline.py    regelbasiert, ohne LLM, läuft überall
  origin_ab_parser.py      ORIGIN-Parser, produktiver Pfad (Anthropic Haiku)
  origin_ab_parser_nim.py  derselbe Prompt auf NVIDIA NIM (Standard: nemotron-3-ultra-550b)
eval/baselines/        Referenzwerte für das CI-Gate
tests/                 18 Tests für Metriken, Generator, Baseline, Adapter-Anbindung
```

## Schnellstart (offline, ohne API-Key)

```bash
python eval/generate_gold.py --n 80 --seed 42
python -m pytest -q
python eval/run_eval.py --adapter regex_baseline
```

## Die LLM-Pipeline messen

Beide Adapter laden `ab_parser_service.py` **unverändert aus dem lokalen ORIGIN-Repo** (nicht öffentlich, nichts davon wird hier kopiert). Sie ersetzen nur die zwei internen Importe (`config`, `timeouts`) durch minimale Stubs.

**Wichtig:** ORIGIN ruft den Parser produktiv über Anthropic Haiku auf. Die zwei Adapter messen deshalb zwei verschiedene Dinge, und die Ergebnisse dürfen nicht vermischt werden.

| Adapter | Was gemessen wird | Braucht |
|---|---|---|
| `origin_ab_parser` | der produktive Pfad (Prompt + Validierung + Haiku) | `anthropic`-Paket, `ANTHROPIC_API_KEY` |
| `origin_ab_parser_nim` | derselbe **Prompt und dieselbe Validierung**, aber **ein NIM-Modell** (Standard: `nvidia/nemotron-3-ultra-550b-a55b`) | nur `NIM_API_KEY` (Standardbibliothek) |

```bash
export ORIGIN_PATH=/pfad/zu/ORIGIN
export NIM_API_KEY=nvapi-...                  # oder ANTHROPIC_API_KEY für den Haiku-Pfad
python eval/run_eval.py --adapter origin_ab_parser_nim --limit 5 --concurrency 1   # kleiner Test zuerst
python eval/run_eval.py --adapter origin_ab_parser_nim --concurrency 1             # voller Lauf
python eval/run_eval.py --adapter origin_ab_parser_nim --concurrency 1 --save-baseline
```

Der NIM-Adapter hält das Free-Tier-Limit von 5 Aufrufen pro Minute ein (mindestens 12,5 s Abstand, Wartezeit bei HTTP 429). Ein voller Lauf über 80 Dokumente dauert deshalb etwa 17 bis 20 Minuten. Jede Antwort wird in `results/cache/` gespeichert, ein abgebrochener Lauf setzt dort fort. Ein anderes NIM-Modell lässt sich über `NIM_MODEL` einstellen. Welche Modelle ein Free-Tier-Key bedienen darf, ist kontoabhängig: HTTP 404 heißt nicht freigegeben, 410 abgeschaltet (Llama 3.3 70B liefert inzwischen 410), und manche Modelle brauchen für den langen Prompt zu lange oder brechen das JSON ab. Der Bericht nennt immer das verwendete Modell.

## CI-Gate

`run_eval.py` bricht mit Fehlercode ab, wenn ein Feld-F1 um mehr als 2 Prozentpunkte unter die gespeicherte Baseline fällt oder die Rate **unmarkierter Fehler** steigt. Aktuell läuft das Gate in GitHub Actions offline gegen die Regel-Baseline. Das Live-Gate gegen die LLM-Pipeline kommt, sobald deren Baseline gespeichert ist.

## Grenzen

- Synthetische Dokumente bilden echte Scans und Layouts nur begrenzt ab. Die Szenarien decken typische Fehlerquellen ab, aber keine echten OCR-Fehler in Werten.
- Das Gold-Set ist mit 80 Dokumenten klein. Pro Szenario sind es oft nur 6–20. Die Zahlen sind Richtwerte, keine belastbaren Konfidenzintervalle.
- Noch nicht umgesetzt: LLM-as-Judge für Freitextfelder, handgebaute Härtefälle, Modell-/Prompt-Vergleich.
