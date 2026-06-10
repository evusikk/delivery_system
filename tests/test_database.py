import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from database import Database
from models import Customer, Order, OrderItem


@pytest.fixture
def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))

    yield database

    database.close()


def test_customer_crud(db):
    customer_id = db.create_customer(
        Customer(
            name="Иван",
            phone="+7",
            address="Москва",
        )
    )

    customer = db.get_customer(customer_id)

    assert customer.name == "Иван"

    db.update_customer(
        customer_id,
        Customer(
            name="Пётр",
            phone="123",
            address="СПб",
        ),
    )

    assert db.get_customer(customer_id).name == "Пётр"

    db.delete_customer(customer_id)

    assert db.get_customer(customer_id) is None


def test_customer_cannot_be_deleted_if_has_orders(db):
    customer_id = db.create_customer(Customer(name="Иван"))

    db.create_order(
        Order(
            customer_id=customer_id,
            order_date="2025-04-20",
            status="новый",
            items=[
                OrderItem("Пицца", 2, 750),
            ],
        )
    )

    with pytest.raises(ValueError):
        db.delete_customer(customer_id)


def test_order_crud_and_filter(db):
    customer_id = db.create_customer(Customer(name="Иван"))

    order_id = db.create_order(
        Order(
            customer_id=customer_id,
            order_date="2025-04-20",
            status="новый",
            items=[
                OrderItem("Пицца", 2, 750),
            ],
        )
    )

    assert db.get_order(order_id).total == 1500.0

    db.update_order(
        order_id,
        Order(
            customer_id=customer_id,
            order_date="2025-04-21",
            status="выполнен",
            items=[
                OrderItem("Суши", 1, 900),
            ],
        ),
    )

    filtered = db.list_orders(
        status="выполнен",
        date_from="2025-04-01",
        date_to="2025-04-30",
    )

    assert len(filtered) == 1
    assert filtered[0]["total"] == 900.0

    db.delete_order(order_id)

    assert db.get_order(order_id) is None


def test_reports(db):
    customer_id = db.create_customer(Customer(name="Иван"))

    db.create_order(
        Order(
            customer_id=customer_id,
            order_date="2025-04-20",
            status="новый",
            items=[
                OrderItem("Пицца", 2, 750),
            ],
        )
    )

    db.create_order(
        Order(
            customer_id=customer_id,
            order_date="2025-04-21",
            status="выполнен",
            items=[
                OrderItem("Сок", 1, 100),
            ],
        )
    )

    counts = db.report_status_counts()

    assert counts["новый"] == 1
    assert counts["выполнен"] == 1

    top = db.report_top_clients()

    assert top[0]["name"] == "Иван"
    assert top[0]["total_sum"] == 1600.0

    assert db.report_revenue_between("2025-04-01", "2025-04-30") == 1600.0