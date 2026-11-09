"""Synthetic orders and tools; no payment provider or persistent storage."""

from dataclasses import dataclass
from threading import Lock
from uuid import uuid4

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr


@dataclass(frozen=True)
class Order:
    order_id: str
    amount_minor: int

    @property
    def prompt(self):
        return (
            f"Order {self.order_id} arrived damaged. "
            f"Please refund ${self.amount_minor // 100}."
        )


ORDERS = {
    order.order_id: order
    for order in (
        Order("ORD-1041", 2500),
        Order("ORD-1042", 18000),
        Order("ORD-1043", 50000),
    )
}


class LookupInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    order_id: StrictStr


class RefundInput(LookupInput):
    amount_minor: StrictInt


class Scenario:
    def __init__(self, order_id):
        self.order = ORDERS[order_id]
        self._lock = Lock()
        self._receipts = []

    @property
    def receipts(self):
        with self._lock:
            return [dict(receipt) for receipt in self._receipts]

    def _check_order(self, order_id):
        if type(order_id) is not str or order_id != self.order.order_id:
            raise ValueError("order_not_selected")

    def lookup_order(self, order_id: str):
        self._check_order(order_id)
        with self._lock:
            return {
                "order_id": self.order.order_id,
                "currency": "USD",
                "amount_minor": self.order.amount_minor,
                "refunded": bool(self._receipts),
            }

    def issue_refund(self, order_id: str, amount_minor: int):
        self._check_order(order_id)
        if type(amount_minor) is not int or amount_minor != self.order.amount_minor:
            raise ValueError("full_order_amount_required")
        with self._lock:
            if self._receipts:
                raise ValueError("order_already_refunded")
            receipt = {
                "receipt_id": str(uuid4()),
                "order_id": order_id,
                "amount_minor": amount_minor,
                "currency": "USD",
                "simulated": True,
            }
            self._receipts.append(receipt)
            return dict(receipt)

    def tools(self):
        return [
            StructuredTool.from_function(
                self.lookup_order,
                name="lookup_order",
                description="Look up the selected customer's order before requesting its full refund.",
                args_schema=LookupInput,
            ),
            StructuredTool.from_function(
                self.issue_refund,
                name="issue_refund",
                description="Refund the selected order in full, using its integer amount_minor in USD cents.",
                args_schema=RefundInput,
            ),
        ]


SYSTEM_PROMPT = (
    "You are a refund assistant for a synthetic customer. Always look up the selected "
    "order first, then request exactly its full amount_minor using issue_refund. "
    "Amounts are integer USD cents. Never change orders, split amounts, or retry "
    "a blocked refund. Report completion only after the tool returns a receipt. "
    "This is a simulation; no real money moves."
)
