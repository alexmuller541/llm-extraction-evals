"""Gemeinsame Konstanten. Feldnamen folgen der Extraktions-Pipeline, die bewertet wird."""
from datetime import date

FIELDS = [
    "po_number",
    "confirmed_delivery_date",
    "confirmed_quantity",
    "unit_price",
    "currency",
    "supplier_name",
]

# Felder, auf denen eine Folgeaktion aufbaut (Zuordnung zur Bestellung, Terminvergleich).
# Ein Fehler hier ist teurer als ein falscher Lieferantenname.
KEY_FIELDS = ["po_number", "confirmed_delivery_date"]

# Stichtag der synthetischen Dokumente. Wird an die Pipeline übergeben, damit
# "Termin liegt in der Vergangenheit"-Regeln nicht vom heutigen Datum abhängen.
GOLD_TODAY = date(2026, 8, 1)

# Ab dieser Konfidenz gilt ein Wert als "sicher"
CONFIDENT = 0.7
