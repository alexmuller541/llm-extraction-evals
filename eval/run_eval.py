"""Pipeline über das Gold-Set laufen lassen, Metriken berechnen, Ergebnisse speichern.

    python eval/generate_gold.py --n 80 --seed 42
    python eval/run_eval.py --adapter regex_baseline
    python eval/run_eval.py --adapter origin_ab_parser          # braucht ORIGIN_PATH + ANTHROPIC_API_KEY
    python eval/run_eval.py --adapter origin_ab_parser --save-baseline   # Baseline für das CI-Gate setzen
"""
from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from metrics import regression_failures, summarize  # noqa: E402
from report import write_report  # noqa: E402


async def run(adapter_name: str, gold_dir: Path, today: date, concurrency: int, limit: int):
    adapter = importlib.import_module(f"adapters.{adapter_name}")
    docs = sorted(gold_dir.glob("doc_*.txt"))[:limit] if limit else sorted(gold_dir.glob("doc_*.txt"))
    sem = asyncio.Semaphore(concurrency)

    async def one(path: Path):
        text = path.read_text(encoding="utf-8")
        gold = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        async with sem:
            try:
                pred = await adapter.extract(text, today)
            except Exception as exc:  # ein Dokument darf den Lauf nicht abbrechen
                pred = {"fields": {}, "needs_review": True, "error": f"{type(exc).__name__}: {exc}"}
        return {"id": path.stem, "text": text, "gold": gold, "pred": pred}

    return await asyncio.gather(*(one(p) for p in docs))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--gold", default="data/gold")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0, help="nur die ersten N Dokumente (Kosten begrenzen)")
    ap.add_argument("--baseline", default=None, help="Default: eval/baselines/<adapter>.json")
    ap.add_argument("--save-baseline", action="store_true")
    ap.add_argument("--tolerance", type=float, default=0.02)
    a = ap.parse_args()

    gold_dir = Path(a.gold)
    manifest = json.loads((gold_dir / "manifest.json").read_text())
    today = date.fromisoformat(manifest["today"])
    items = asyncio.run(run(a.adapter, gold_dir, today, a.concurrency, a.limit))
    errors = [i["id"] for i in items if i["pred"].get("error")]
    summary = summarize(items)
    adapter_mod = importlib.import_module(f"adapters.{a.adapter}")
    summary["adapter"], summary["errors"] = a.adapter, errors
    summary["model"] = adapter_mod.describe() if hasattr(adapter_mod, "describe") else None

    Path("results").mkdir(exist_ok=True)
    Path(f"results/{a.adapter}.json").write_text(
        json.dumps({"summary": summary, "items": items}, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(summary, Path(f"results/{a.adapter}.md"))
    print(Path(f"results/{a.adapter}.md").read_text(encoding="utf-8"))
    if errors:
        first = next(i["pred"]["error"] for i in items if i["pred"].get("error"))
        print(f"WARNUNG: {len(errors)} Dokumente mit Fehler: {errors[:5]}\nErster Fehler: {first}")

    baseline_path = Path(a.baseline or f"eval/baselines/{a.adapter}.json")
    if a.save_baseline:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(
            {"fields": summary["fields"], "review": summary["review"], "adapter": a.adapter}, indent=2))
        print(f"Baseline gespeichert: {baseline_path}")
        return
    bl = baseline_path
    if bl.exists():
        fails = regression_failures(summary, json.loads(bl.read_text()), a.tolerance)
        if fails:
            raise SystemExit("REGRESSION:\n" + "\n".join(fails))
        print("Regressions-Gate: ok")


if __name__ == "__main__":
    main()
