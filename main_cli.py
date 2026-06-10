import argparse
from datetime import date

from data_export import export_data, import_data
from database import Database
from logger_config import setup_logging
from models import Customer, Order, OrderItem, VALID_STATUSES

logger = setup_logging()


def parse_items(items_text: str):
    items = []

    for part in items_text.split(","):
        fields = [field.strip() for field in part.split(":")]

        if len(fields) != 3:
            raise ValueError("Товары задаются так: 'Пицца:2:750,Сок:1:120'")

        items.append(
            OrderItem(
                product_name=fields[0],
                quantity=int(fields[1]),
                price=float(fields[2]),
            )
        )

    return items


def print_orders(orders):
    if not orders:
        print("Заказы не найдены")
        return

    for order in orders:
        print(
            f"#{order['id']} | {order['order_date']} | "
            f"{order['customer_name']} | {order['status']} | {order['total']:.2f}"
        )

        for item in order["items"]:
            print(
                f"  - {item['product_name']}: "
                f"{item['quantity']} x {item['price']}"
            )


def cmd_customer_add(args):
    db = Database(args.db)

    try:
        customer_id = db.create_customer(
            Customer(
                name=args.name,
                phone=args.phone or "",
                address=args.address or "",
            )
        )

        logger.info("Создан клиент id=%s", customer_id)
        print(f"Клиент создан: id={customer_id}")

    finally:
        db.close()


def cmd_customer_list(args):
    db = Database(args.db)

    try:
        customers = db.list_customers()

        if not customers:
            print("Клиенты не найдены")
            return

        for customer in customers:
            print(
                f"#{customer.id} | {customer.name} | "
                f"{customer.phone} | {customer.address}"
            )

    finally:
        db.close()


def cmd_customer_edit(args):
    db = Database(args.db)

    try:
        old = db.get_customer(args.id)

        if old is None:
            raise ValueError("Клиент не найден")

        updated = Customer(
            name=args.name if args.name is not None else old.name,
            phone=args.phone if args.phone is not None else old.phone,
            address=args.address if args.address is not None else old.address,
        )

        db.update_customer(args.id, updated)

        logger.info("Обновлён клиент id=%s", args.id)
        print("Клиент обновлён")

    finally:
        db.close()


def cmd_customer_delete(args):
    db = Database(args.db)

    try:
        db.delete_customer(args.id)

        logger.info("Удалён клиент id=%s", args.id)
        print("Клиент удалён")

    finally:
        db.close()


def cmd_order_add(args):
    db = Database(args.db)

    try:
        order = Order(
            customer_id=args.customer_id,
            order_date=args.date,
            status=args.status,
            items=parse_items(args.items),
        )

        order_id = db.create_order(order)

        logger.info("Создан заказ id=%s", order_id)
        print(f"Заказ создан: id={order_id}, сумма={order.total:.2f}")

    finally:
        db.close()


def cmd_order_list(args):
    db = Database(args.db)

    try:
        orders = db.list_orders(
            status=args.status,
            date_from=args.date_from,
            date_to=args.date_to,
        )

        print_orders(orders)

    finally:
        db.close()


def cmd_order_edit(args):
    db = Database(args.db)

    try:
        old = db.get_order(args.id)

        if old is None:
            raise ValueError("Заказ не найден")

        order = Order(
            customer_id=(
                args.customer_id
                if args.customer_id is not None
                else old.customer_id
            ),
            order_date=args.date if args.date is not None else old.order_date,
            status=args.status if args.status is not None else old.status,
            items=parse_items(args.items) if args.items is not None else old.items,
        )

        db.update_order(args.id, order)

        logger.info("Обновлён заказ id=%s", args.id)
        print("Заказ обновлён")

    finally:
        db.close()


def cmd_order_delete(args):
    db = Database(args.db)

    try:
        db.delete_order(args.id)

        logger.info("Удалён заказ id=%s", args.id)
        print("Заказ удалён")

    finally:
        db.close()


def cmd_report(args):
    db = Database(args.db)

    try:
        print("Количество заказов по статусам:")

        for status, count in db.report_status_counts().items():
            print(f"- {status}: {count}")

        print("\nТоп-3 клиента по сумме заказов:")

        top_clients = db.report_top_clients()

        if not top_clients:
            print("Нет данных")

        for row in top_clients:
            print(
                f"- {row['name']}: {row['total_sum']:.2f} "
                f"({row['orders_count']} заказов)"
            )

        print(
            f"\nВыручка за период {args.period}: "
            f"{db.report_revenue(args.period):.2f}"
        )

    finally:
        db.close()


def cmd_export(args):
    db = Database(args.db)

    try:
        export_data(db, args.file)

        logger.info("Экспорт выполнен в файл %s", args.file)
        print(f"Экспорт выполнен: {args.file}")

    finally:
        db.close()


def cmd_import(args):
    db = Database(args.db)

    try:
        import_data(db, args.file)

        logger.info("Импорт выполнен из файла %s", args.file)
        print(f"Импорт выполнен: {args.file}")

    finally:
        db.close()


def build_parser():
    parser = argparse.ArgumentParser(
        description="Система учёта заказов доставки"
    )

    parser.add_argument(
        "--db",
        default="data/delivery.db",
        help="Путь к SQLite-БД",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    parser_customer_add = subparsers.add_parser(
        "customer-add",
        help="Создать клиента",
    )
    parser_customer_add.add_argument("--name", required=True)
    parser_customer_add.add_argument("--phone", default="")
    parser_customer_add.add_argument("--address", default="")
    parser_customer_add.set_defaults(func=cmd_customer_add)

    parser_customer_list = subparsers.add_parser(
        "customer-list",
        help="Показать клиентов",
    )
    parser_customer_list.set_defaults(func=cmd_customer_list)

    parser_customer_edit = subparsers.add_parser(
        "customer-edit",
        help="Редактировать клиента",
    )
    parser_customer_edit.add_argument("--id", type=int, required=True)
    parser_customer_edit.add_argument("--name")
    parser_customer_edit.add_argument("--phone")
    parser_customer_edit.add_argument("--address")
    parser_customer_edit.set_defaults(func=cmd_customer_edit)

    parser_customer_delete = subparsers.add_parser(
        "customer-delete",
        help="Удалить клиента",
    )
    parser_customer_delete.add_argument("--id", type=int, required=True)
    parser_customer_delete.set_defaults(func=cmd_customer_delete)

    parser_order_add = subparsers.add_parser(
        "order-add",
        help="Создать заказ",
    )
    parser_order_add.add_argument("--customer-id", type=int, required=True)
    parser_order_add.add_argument("--date", default=date.today().isoformat())
    parser_order_add.add_argument(
        "--status",
        choices=VALID_STATUSES,
        default="новый",
    )
    parser_order_add.add_argument(
        "--items",
        required=True,
        help="Например: 'Пицца:2:750,Сок:1:120'",
    )
    parser_order_add.set_defaults(func=cmd_order_add)

    parser_order_list = subparsers.add_parser(
        "order-list",
        help="Показать заказы",
    )
    parser_order_list.add_argument("--status", choices=VALID_STATUSES)
    parser_order_list.add_argument("--date-from")
    parser_order_list.add_argument("--date-to")
    parser_order_list.set_defaults(func=cmd_order_list)

    parser_order_edit = subparsers.add_parser(
        "order-edit",
        help="Редактировать заказ",
    )
    parser_order_edit.add_argument("--id", type=int, required=True)
    parser_order_edit.add_argument("--customer-id", type=int)
    parser_order_edit.add_argument("--date")
    parser_order_edit.add_argument("--status", choices=VALID_STATUSES)
    parser_order_edit.add_argument(
        "--items",
        help="Например: 'Пицца:2:750,Сок:1:120'",
    )
    parser_order_edit.set_defaults(func=cmd_order_edit)

    parser_order_delete = subparsers.add_parser(
        "order-delete",
        help="Удалить заказ",
    )
    parser_order_delete.add_argument("--id", type=int, required=True)
    parser_order_delete.set_defaults(func=cmd_order_delete)

    parser_report = subparsers.add_parser(
        "report",
        help="Показать отчёт",
    )
    parser_report.add_argument(
        "--period",
        choices=("day", "week", "month"),
        required=True,
    )
    parser_report.set_defaults(func=cmd_report)

    parser_export = subparsers.add_parser(
        "export",
        help="Экспорт в JSON/XML",
    )
    parser_export.add_argument("--file", required=True)
    parser_export.set_defaults(func=cmd_export)

    parser_import = subparsers.add_parser(
        "import",
        help="Импорт из JSON/XML",
    )
    parser_import.add_argument("--file", required=True)
    parser_import.set_defaults(func=cmd_import)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        args.func(args)

    except Exception as exc:
        logger.exception("Ошибка выполнения команды")
        parser.exit(1, f"Ошибка: {exc}\n")


if __name__ == "__main__":
    main()