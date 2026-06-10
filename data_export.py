import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict


def export_data(db, file_path: str) -> None:
    data = db.export_bundle()
    suffix = Path(file_path).suffix.lower()

    if suffix == ".json":
        _export_json(data, file_path)
    elif suffix == ".xml":
        _export_xml(data, file_path)
    else:
        raise ValueError("Поддерживаются только файлы .json и .xml")


def import_data(db, file_path: str) -> None:
    suffix = Path(file_path).suffix.lower()

    if suffix == ".json":
        data = _import_json(file_path)
    elif suffix == ".xml":
        data = _import_xml(file_path)
    else:
        raise ValueError("Поддерживаются только файлы .json и .xml")

    _validate_bundle_shape(data)
    db.import_bundle(data)


def _export_json(data: Dict, file_path: str) -> None:
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def _import_json(file_path: str) -> Dict:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Некорректный JSON: строка {exc.lineno}, колонка {exc.colno}"
        ) from exc


def _export_xml(data: Dict, file_path: str) -> None:
    root = ET.Element("delivery_data")

    customers_el = ET.SubElement(root, "customers")

    for customer in data["customers"]:
        customer_el = ET.SubElement(customers_el, "customer")

        for field in ("id", "name", "phone", "address"):
            child = ET.SubElement(customer_el, field)
            child.text = "" if customer.get(field) is None else str(customer.get(field))

    orders_el = ET.SubElement(root, "orders")

    for order in data["orders"]:
        order_el = ET.SubElement(orders_el, "order")

        for field in ("id", "customer_id", "order_date", "status", "total"):
            child = ET.SubElement(order_el, field)
            child.text = "" if order.get(field) is None else str(order.get(field))

        items_el = ET.SubElement(order_el, "items")

        for item in order.get("items", []):
            item_el = ET.SubElement(items_el, "item")

            for field in ("product_name", "quantity", "price"):
                child = ET.SubElement(item_el, field)
                child.text = "" if item.get(field) is None else str(item.get(field))

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(file_path, encoding="utf-8", xml_declaration=True)


def _import_xml(file_path: str) -> Dict:
    try:
        root = ET.parse(file_path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"Некорректный XML: {exc}") from exc

    if root.tag != "delivery_data":
        raise ValueError("Корневой XML-элемент должен называться delivery_data")

    customers = []

    for customer_el in root.findall("./customers/customer"):
        customers.append(
            {
                "id": _optional_int(_text(customer_el, "id")),
                "name": _text(customer_el, "name"),
                "phone": _text(customer_el, "phone"),
                "address": _text(customer_el, "address"),
            }
        )

    orders = []

    for order_el in root.findall("./orders/order"):
        items = []

        for item_el in order_el.findall("./items/item"):
            items.append(
                {
                    "product_name": _text(item_el, "product_name"),
                    "quantity": int(_text(item_el, "quantity") or 0),
                    "price": float(_text(item_el, "price") or 0),
                }
            )

        orders.append(
            {
                "id": _optional_int(_text(order_el, "id")),
                "customer_id": int(_text(order_el, "customer_id") or 0),
                "order_date": _text(order_el, "order_date"),
                "status": _text(order_el, "status"),
                "total": float(_text(order_el, "total") or 0),
                "items": items,
            }
        )

    return {
        "customers": customers,
        "orders": orders,
    }


def _text(parent, tag: str) -> str:
    element = parent.find(tag)

    if element is None or element.text is None:
        return ""

    return element.text


def _optional_int(value: str):
    if value == "":
        return None

    return int(value)


def _validate_bundle_shape(data: Dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("Импортируемый файл должен содержать объект")

    if "customers" not in data or "orders" not in data:
        raise ValueError("Файл должен содержать customers и orders")

    if not isinstance(data["customers"], list) or not isinstance(data["orders"], list):
        raise ValueError("customers и orders должны быть списками")