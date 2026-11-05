"""Markdown-Bericht aus der Summary."""
from __future__ import annotations

from pathlib import Path


def pct(x):
    return "–" if x is None else f"{100 * x:.1f} %"


def write_report(s: dict, path: Path) -> None:
    L = [f"# Eval-Ergebnis: `{s['adapter']}` (n = {s['n_docs']} synthetische Dokumente)\n"]
    if s.get("model"):
        L.append(f"Modell: **{s['model']}**\n")
    L.append("## Pro Feld\n")
    L.append("| Feld | Precision | Recall | F1 | falsch | verpasst | halluziniert | Verzicht korrekt |")
    L.append("|---|---|---|---|---|---|---|---|")
    for f, v in s["fields"].items():
        L.append(f"| {f} | {pct(v['precision'])} | {pct(v['recall'])} | {pct(v['f1'])} | {v['wrong']} | "
                 f"{v['missed']} | {v['hallucinated']} | {pct(v['abstention_accuracy'])} (n={v['n_gold_null']}) |")
    L.append(f"\nMakro-F1: **{pct(s['macro_f1'])}**\n")

    r = s["review"]
    L.append("## Review-Logik (verhindert die teuren Fehler)\n")
    L.append(f"- Dokumente mit falschem oder halluziniertem Schlüsselfeld (PO, Termin): **{r['docs_with_key_error']}** von {r['n']}")
    L.append(f"- davon **ohne Prüfmarkierung übernommen**: **{r['unflagged_errors']}** ({pct(r['unflagged_error_rate'])} aller Dokumente)")
    L.append(f"- Fehlerfang-Rate (Fehler, die `needs_review` auslösen): {pct(r['error_catch_rate'])}")
    L.append(f"- Unnötige Prüfmarkierung bei korrekten Dokumenten: {pct(r['over_flag_rate'])}\n")

    c = s["calibration"]
    L.append("## Konfidenz\n")
    L.append(f"- ECE: **{c['ece']:.3f}** (n = {c['n']} Vorhersagen)")
    L.append(f"- Trefferquote bei Konfidenz ≥ 0,7: {pct(c['accuracy_confident'])} (n = {c['n_confident']})")
    L.append(f"- Trefferquote bei Konfidenz < 0,7: {pct(c['accuracy_unconfident'])} (n = {c['n_unconfident']})\n")

    e = s["evidence"]
    L.append(f"## Evidenz\n\n- Wörtlich im Dokument gefundene Belegstellen: {pct(e['rate'])} ({e['grounded']} von {e['n']})\n")

    L.append("## Nach Szenario (Schlüsselfelder)\n")
    L.append("| Szenario | n | PO richtig | Termin richtig | Termin falsch | Termin halluziniert | unmarkierte Fehler |")
    L.append("|---|---|---|---|---|---|---|")
    for sc, v in s["by_scenario"].items():
        L.append(f"| {sc} | {v['n']} | {v['po_ok']}/{v['n']} | {v['date_ok']}/{v['n']} | {v['date_wrong']} | "
                 f"{v['date_hallucinated']} | {v['unflagged_errors']} |")
    if s.get("errors"):
        L.append(f"\n⚠️ {len(s['errors'])} Dokumente lieferten einen Fehler (Timeout/Parsing).")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
