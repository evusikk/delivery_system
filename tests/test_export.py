import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from data_export import export_data, import_data
from database import Database
from models import Customer, Order, OrderItem


@pytest.fixture
def filled_db(tmp_path):
    database = Database(str(tmp_path / "source.db"))

    customer_id = database.create_customer(
        Customer(
            name="Иван",
            phone="+7",
            address="Москва",
        )
    )

    database.create_order(
        Order(
            customer_id=customer_id,
            order_date="2025-04-20",
            status="новый",
            items=[
                OrderItem("Пицца", 2, 750),
            ],
        )
    )

    yield database

    database.close()


def test_json_export_import_roundtrip(tmp_path, filled_db):
    file_path = tmp_path / "orders.json"

    export_data(filled_db, str(file_path))

    target = Database(str(tmp_path / "target.db"))

    import_data(target, str(file_path))

    assert len(target.list_customers()) == 1
    assert len(target.list_orders()) == 1
    assert target.list_orders()[0]["total"] == 1500.0

    target.close()


def test_xml_export_import_roundtrip(tmp_path, filled_db):
    file_path = tmp_path / "orders.xml"

    export_data(filled_db, str(file_path))

    target = Database(str(tmp_path / "target_xml.db"))

    import_data(target, str(file_path))

    assert len(target.list_customers()) == 1
    assert len(target.list_orders()) == 1

    target.close()


def test_bad_json_is_rejected(tmp_path, filled_db):
    file_path = tmp_path / "bad.json"
    file_path.write_text("{bad json", encoding="utf-8")

    with pytest.raises(ValueError):
        import_data(filled_db, str(file_path))