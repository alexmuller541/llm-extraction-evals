# Eval-Ergebnis: `origin_ab_parser_nim` (n = 80 synthetische Dokumente)

Modell: **nvidia/nemotron-3-ultra-550b-a55b (NVIDIA NIM)**

## Pro Feld

| Feld | Precision | Recall | F1 | falsch | verpasst | halluziniert | Verzicht korrekt |
|---|---|---|---|---|---|---|---|
| po_number | 96.1 % | 100.0 % | 98.0 % | 0 | 0 | 3 | 57.1 % (n=7) |
| confirmed_delivery_date | 100.0 % | 98.5 % | 99.2 % | 0 | 1 | 0 | 100.0 % (n=13) |
| confirmed_quantity | 100.0 % | 98.8 % | 99.4 % | 0 | 1 | 0 | – (n=0) |
| unit_price | 100.0 % | 98.8 % | 99.4 % | 0 | 1 | 0 | – (n=0) |
| currency | 100.0 % | 98.8 % | 99.4 % | 0 | 1 | 0 | – (n=0) |
| supplier_name | 100.0 % | 98.8 % | 99.4 % | 0 | 1 | 0 | – (n=0) |

Makro-F1: **99.1 %**

## Review-Logik (verhindert die teuren Fehler)

- Dokumente mit falschem oder halluziniertem Schlüsselfeld (PO, Termin): **3** von 80
- davon **ohne Prüfmarkierung übernommen**: **3** (3.8 % aller Dokumente)
- Fehlerfang-Rate (Fehler, die `needs_review` auslösen): 0.0 %
- Unnötige Prüfmarkierung bei korrekten Dokumenten: 0.0 %

## Konfidenz

- ECE: **0.031** (n = 458 Vorhersagen)
- Trefferquote bei Konfidenz ≥ 0,7: 99.3 % (n = 458)
- Trefferquote bei Konfidenz < 0,7: – (n = 0)

## Evidenz

- Wörtlich im Dokument gefundene Belegstellen: 100.0 % (471 von 471)

## Nach Szenario (Schlüsselfelder)

| Szenario | n | PO richtig | Termin richtig | Termin falsch | Termin halluziniert | unmarkierte Fehler |
|---|---|---|---|---|---|---|
| ambiguous_date | 7 | 7/7 | 7/7 | 0 | 0 | 0 |
| both_dates | 18 | 18/18 | 18/18 | 0 | 0 | 0 |
| clean | 21 | 21/21 | 21/21 | 0 | 0 | 0 |
| distractor | 6 | 6/6 | 6/6 | 0 | 0 | 0 |
| email | 11 | 11/11 | 11/11 | 0 | 0 | 0 |
| missing_po | 7 | 4/7 | 6/7 | 0 | 0 | 3 |
| ocr_noise | 4 | 4/4 | 4/4 | 0 | 0 | 0 |
| only_requested | 6 | 6/6 | 6/6 | 0 | 0 | 0 |
