# Eval-Ergebnis: `regex_baseline` (n = 80 synthetische Dokumente)

## Pro Feld

| Feld | Precision | Recall | F1 | falsch | verpasst | halluziniert | Verzicht korrekt |
|---|---|---|---|---|---|---|---|
| po_number | 98.6 % | 98.6 % | 98.6 % | 1 | 0 | 0 | 100.0 % (n=7) |
| confirmed_delivery_date | 60.5 % | 68.7 % | 64.3 % | 21 | 0 | 9 | 30.8 % (n=13) |
| confirmed_quantity | 85.0 % | 85.0 % | 85.0 % | 12 | 0 | 0 | – (n=0) |
| unit_price | 100.0 % | 97.5 % | 98.7 % | 0 | 2 | 0 | – (n=0) |
| currency | 100.0 % | 97.5 % | 98.7 % | 0 | 2 | 0 | – (n=0) |
| supplier_name | 100.0 % | 96.2 % | 98.1 % | 0 | 3 | 0 | – (n=0) |

Makro-F1: **90.6 %**

## Review-Logik (verhindert die teuren Fehler)

- Dokumente mit falschem oder halluziniertem Schlüsselfeld (PO, Termin): **30** von 80
- davon **ohne Prüfmarkierung übernommen**: **30** (37.5 % aller Dokumente)
- Fehlerfang-Rate (Fehler, die `needs_review` auslösen): 0.0 %
- Unnötige Prüfmarkierung bei korrekten Dokumenten: 0.0 %

## Konfidenz

- ECE: **0.007** (n = 462 Vorhersagen)
- Trefferquote bei Konfidenz ≥ 0,7: 90.7 % (n = 462)
- Trefferquote bei Konfidenz < 0,7: – (n = 0)

## Evidenz

- Wörtlich im Dokument gefundene Belegstellen: 100.0 % (462 von 462)

## Nach Szenario (Schlüsselfelder)

| Szenario | n | PO richtig | Termin richtig | Termin falsch | Termin halluziniert | unmarkierte Fehler |
|---|---|---|---|---|---|---|
| ambiguous_date | 7 | 7/7 | 0/7 | 0 | 7 | 7 |
| both_dates | 18 | 18/18 | 8/18 | 10 | 0 | 10 |
| clean | 21 | 21/21 | 21/21 | 0 | 0 | 0 |
| distractor | 6 | 5/6 | 0/6 | 6 | 0 | 6 |
| email | 11 | 11/11 | 6/11 | 5 | 0 | 5 |
| missing_po | 7 | 7/7 | 7/7 | 0 | 0 | 0 |
| ocr_noise | 4 | 4/4 | 4/4 | 0 | 0 | 0 |
| only_requested | 6 | 6/6 | 4/6 | 0 | 2 | 2 |
