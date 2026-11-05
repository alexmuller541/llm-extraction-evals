# Eval-Ergebnis: `origin_ab_parser_nim` (n = 5 synthetische Dokumente)

Modell: **nvidia/nemotron-3-ultra-550b-a55b (NVIDIA NIM)**

## Pro Feld

| Feld | Precision | Recall | F1 | falsch | verpasst | halluziniert | Verzicht korrekt |
|---|---|---|---|---|---|---|---|
| po_number | 100.0 % | 100.0 % | 100.0 % | 0 | 0 | 0 | – (n=0) |
| confirmed_delivery_date | 100.0 % | 100.0 % | 100.0 % | 0 | 0 | 0 | 100.0 % (n=1) |
| confirmed_quantity | 100.0 % | 100.0 % | 100.0 % | 0 | 0 | 0 | – (n=0) |
| unit_price | 100.0 % | 100.0 % | 100.0 % | 0 | 0 | 0 | – (n=0) |
| currency | 100.0 % | 100.0 % | 100.0 % | 0 | 0 | 0 | – (n=0) |
| supplier_name | 100.0 % | 100.0 % | 100.0 % | 0 | 0 | 0 | – (n=0) |

Makro-F1: **100.0 %**

## Review-Logik (verhindert die teuren Fehler)

- Dokumente mit falschem oder halluziniertem Schlüsselfeld (PO, Termin): **0** von 5
- davon **ohne Prüfmarkierung übernommen**: **0** (0.0 % aller Dokumente)
- Fehlerfang-Rate (Fehler, die `needs_review` auslösen): –
- Unnötige Prüfmarkierung bei korrekten Dokumenten: 0.0 %

## Konfidenz

- ECE: **0.046** (n = 29 Vorhersagen)
- Trefferquote bei Konfidenz ≥ 0,7: 100.0 % (n = 29)
- Trefferquote bei Konfidenz < 0,7: – (n = 0)

## Evidenz

- Wörtlich im Dokument gefundene Belegstellen: 100.0 % (30 von 30)

## Nach Szenario (Schlüsselfelder)

| Szenario | n | PO richtig | Termin richtig | Termin falsch | Termin halluziniert | unmarkierte Fehler |
|---|---|---|---|---|---|---|
| both_dates | 2 | 2/2 | 2/2 | 0 | 0 | 0 |
| clean | 1 | 1/1 | 1/1 | 0 | 0 | 0 |
| distractor | 1 | 1/1 | 1/1 | 0 | 0 | 0 |
| only_requested | 1 | 1/1 | 1/1 | 0 | 0 | 0 |
