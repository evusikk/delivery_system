import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from models import Customer, Order, OrderItem


def test_customer_requires_name():
    with pytest.raises(ValueError):
        Customer(name="").validate()


def test_order_total_is_calculated():
    order = Order(
        customer_id=1,
        order_date="2025-04-20",
        status="новый",
        items=[
            OrderItem("Пицца", 2, 750),
            OrderItem("Сок", 1, 120),
        ],
    )

    order.validate()

    assert order.total == 1620.0


def test_order_rejects_bad_status():
    order = Order(
        customer_id=1,
        order_date="2025-04-20",
        status="плохой статус",
        items=[
            OrderItem("Пицца", 1, 750),
        ],
    )

    with pytest.raises(ValueError):
        order.validate()