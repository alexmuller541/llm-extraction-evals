# llm-extraction-evals

Eval-Harness für eine LLM-Pipeline, die Felder aus **Auftragsbestätigungen** extrahiert (Lieferant, Bestellnummer, Position, Menge, Preis, Währung, Liefertermin, Incoterm).

**Frage, die das Repo beantwortet:** Wie gut ist die Extraktion wirklich – pro Feld, mit welcher Konfidenz, und bricht ein Prompt-Change etwas?

> **Status: Skelett.** Alle Zahlen unten sind Platzhalter, bis `make eval` echte Werte liefert.

## Ergebnis (wird nach dem ersten Lauf ausgefüllt)

| Feld | Precision | Recall | F1 |
|---|---|---|---|
| order_no | TBD | TBD | TBD |
| supplier | TBD | TBD | TBD |
| delivery_date | TBD | TBD | TBD |
| quantity | TBD | TBD | TBD |
| unit_price | TBD | TBD | TBD |
| currency | TBD | TBD | TBD |
| incoterm | TBD | TBD | TBD |

Gold-Set: n = TBD synthetische Dokumente (siehe `data/gold/`). Kalibrierung (ECE): TBD. LLM-as-Judge vs. manuelle Labels: TBD (n = 30).

## Aufbau
```
data/gold/          Gold-Set: <id>.txt + <id>.json (Ground Truth) – synthetisch, keine echten Daten
eval/schema.py      Feldschema (Pydantic)
eval/generate_gold.py  erzeugt Dokumente + Labels reproduzierbar (Seed)
eval/metrics.py     Normalisierung, Precision/Recall/F1 pro Feld, ECE
eval/run_eval.py    Pipeline über Gold-Set laufen lassen, results/*.json schreiben
tests/              Tests für Metriken und Regressions-Gate
.github/workflows/eval.yml   CI: Tests + Regressions-Gate
```

## Schnellstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python eval/generate_gold.py --n 60 --seed 42
pytest
python eval/run_eval.py --model <modell>   # braucht ANTHROPIC_API_KEY oder OPENAI_API_KEY
```

## Methodik
1. Gold-Set synthetisch mit variierenden Layouts, DE/EN, Datumsformaten und gezieltem Rauschen; ca. 15 handgebaute schwierige Fälle.
2. Feldweiser Vergleich nach Normalisierung (Datum, Zahl, Währung).
3. Kalibrierung: Konfidenz-Bins gegen tatsächliche Trefferquote (ECE).
4. LLM-as-Judge nur für Freitextfelder; Validierung gegen 30 manuelle Labels.
5. CI-Gate: F1 darf pro Feld nicht mehr als `TOLERANCE` unter `baseline.json` fallen.

## Grenzen
Synthetische Daten bilden reale Dokumente nur begrenzt ab. Keine Daten von Arbeitgebern oder Kunden im Repo.
