from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import ValidationError

from scenario import ORDERS, Scenario


@pytest.mark.parametrize("order_id", ORDERS)
def test_lookup_and_full_refund(order_id):
    scenario = Scenario(order_id)
    order = scenario.lookup_order(order_id)
    assert order["currency"] == "USD" and not order["refunded"]
    assert f"${order['amount_minor'] // 100}" in scenario.order.prompt
    receipt = scenario.issue_refund(order_id, order["amount_minor"])
    assert receipt["simulated"] and scenario.lookup_order(order_id)["refunded"]
    receipt["amount_minor"] = 0
    assert scenario.receipts[0]["amount_minor"] == order["amount_minor"]
    with pytest.raises(ValueError, match="already_refunded"):
        scenario.issue_refund(order_id, order["amount_minor"])


@pytest.mark.parametrize("amount", [True, "2500", 2500.0, 0, -1, 1250, 18000])
def test_invalid_amount_never_records_receipt(amount):
    scenario = Scenario("ORD-1041")
    with pytest.raises((ValueError, ValidationError)):
        scenario.tools()[1].invoke({"order_id": "ORD-1041", "amount_minor": amount})
    assert not scenario.receipts


def test_order_binding_and_concurrent_duplicates():
    scenario = Scenario("ORD-1041")
    for operation in (
        scenario.lookup_order,
        lambda order: scenario.issue_refund(order, 2500),
    ):
        with pytest.raises(ValueError, match="order_not_selected"):
            operation("ORD-1042")

    def attempt(_):
        try:
            scenario.issue_refund("ORD-1041", 2500)
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(8) as executor:
        assert sum(executor.map(attempt, range(20))) == 1
    assert len(scenario.receipts) == 1
