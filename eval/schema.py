from datetime import date
from typing import Optional

from pydantic import BaseModel

FIELDS = ["supplier", "order_no", "delivery_date", "quantity", "unit_price", "currency", "incoterm"]


class OrderConfirmation(BaseModel):
    supplier: Optional[str] = None
    order_no: Optional[str] = None
    delivery_date: Optional[date] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    currency: Optional[str] = None
    incoterm: Optional[str] = None
