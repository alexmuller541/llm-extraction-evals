"""Regelbasierte Baseline ohne LLM.

Bewusst einfach gehalten: Sie nimmt das erste Datum in einer Zeile mit "liefer|deliver|ship" und
unterscheidet weder Wunsch- noch bestätigten Termin, noch prüft sie Mehrdeutigkeit.
Ihr Zweck ist der Vergleich: Wo gewinnt ein LLM wirklich gegenüber einfachen Regeln?
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

MONTHS = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"])}

DATE_RE = re.compile(
    r"(\d{1,2}\.\d{1,2}\.\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|\d{1,2} [A-Za-z]+ \d{4}|[A-Za-z]+ \d{1,2}, \d{4})")
PO_RE = re.compile(r"\b(PO-\d{3,6}|45\d{8}|B-\d{4}-\d{4})\b")


def _to_iso(s: str) -> Optional[str]:
    s = s.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):  # naiv: Schrägstrich immer tagesweise
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    m = re.match(r"(\d{1,2}) ([A-Za-z]+) (\d{4})", s)
    if m and m.group(2).lower() in MONTHS:
        return date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1))).isoformat()
    m = re.match(r"([A-Za-z]+) (\d{1,2}), (\d{4})", s)
    if m and m.group(1).lower() in MONTHS:
        return date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2))).isoformat()
    return None


def _num(raw: str) -> Optional[float]:
    t = raw.strip().replace(" ", "")
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
    elif "," in t:
        t = t.replace(",", ".") if len(t.split(",")[-1]) <= 2 else t.replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None


def _f(value, evidence=None, conf=0.9):
    return {"value": value, "confidence": conf if value is not None else 0.0, "evidence": evidence}


async def extract(text: str, today: date) -> dict:
    po = PO_RE.search(text)
    eta, eta_line = None, None
    for line in text.split("\n"):
        if re.search(r"liefer|deliver|ship", line, re.I):
            m = DATE_RE.search(line)
            if m and _to_iso(m.group(1)):
                eta, eta_line = _to_iso(m.group(1)), line.strip()
                break
    qty = re.search(r"(\d[\d.,]*)\s*(?:Stk|Stück|pcs|pieces)", text)
    price = re.search(r"(?:Preis/Stk|Unit price|Preis(?: beträgt)?|price is)[:\s]*([\d.,]+)\s*([A-Z]{3})", text)
    sup = re.search(r"(?:Lieferant|Supplier|From)\s*:\s*(.+)", text)
    supplier = sup.group(1).strip() if sup else None
    if supplier is None:  # E-Mail: Unterschrift in der letzten Zeile
        last = [l for l in text.split("\n") if l.strip()]
        supplier = last[-1].strip() if last and re.search(r"(Viele Gr|Best regards)", text) else None

    fields = {
        "po_number": _f(po.group(1) if po else None, po.group(0) if po else None),
        "confirmed_delivery_date": _f(eta, eta_line),
        "confirmed_quantity": _f(_num(qty.group(1)) if qty else None, qty.group(0) if qty else None),
        "unit_price": _f(_num(price.group(1)) if price else None, price.group(0) if price else None),
        "currency": _f(price.group(2) if price else None, price.group(0) if price else None),
        "supplier_name": _f(supplier, supplier),
    }
    reasons = []
    if not po:
        reasons.append("no po")
    if not eta:
        reasons.append("no date")
    return {"fields": fields, "needs_review": bool(reasons)}
