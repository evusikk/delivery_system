import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from models import Customer, Order, OrderItem, VALID_STATUSES


class Database:
    def __init__(self, db_path: str = "data/delivery.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

        self.init_db()

    def close(self) -> None:
        self.conn.close()

    def init_db(self) -> None:
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    phone TEXT,
                    address TEXT
                )
                """
            )

            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY,
                    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
                    order_date TEXT NOT NULL,
                    status TEXT CHECK(status IN ('новый','в доставке','выполнен','отменён')) NOT NULL,
                    total REAL NOT NULL
                )
                """
            )

            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY,
                    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL
                )
                """
            )

            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_orders_status_date ON orders(status, order_date)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_items_order ON order_items(order_id)"
            )

    #CRUD клиентов 

    def create_customer(self, customer: Customer) -> int:
        customer.validate()

        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO customers(name, phone, address) VALUES (?, ?, ?)",
                (customer.name.strip(), customer.phone, customer.address),
            )

        return int(cur.lastrowid)

    def get_customer(self, customer_id: int) -> Optional[Customer]:
        row = self.conn.execute(
            """
            SELECT id, name, phone, address
            FROM customers
            WHERE id = ?
            """,
            (customer_id,),
        ).fetchone()

        if row is None:
            return None

        return Customer(
            id=row["id"],
            name=row["name"],
            phone=row["phone"] or "",
            address=row["address"] or "",
        )

    def list_customers(self) -> List[Customer]:
        rows = self.conn.execute(
            """
            SELECT id, name, phone, address
            FROM customers
            ORDER BY id
            """
        ).fetchall()

        return [
            Customer(
                id=row["id"],
                name=row["name"],
                phone=row["phone"] or "",
                address=row["address"] or "",
            )
            for row in rows
        ]

    def update_customer(self, customer_id: int, customer: Customer) -> None:
        customer.validate()

        with self.conn:
            cur = self.conn.execute(
                """
                UPDATE customers
                SET name = ?, phone = ?, address = ?
                WHERE id = ?
                """,
                (customer.name.strip(), customer.phone, customer.address, customer_id),
            )

            if cur.rowcount == 0:
                raise ValueError("Клиент не найден")

    def delete_customer(self, customer_id: int) -> None:
        try:
            with self.conn:
                cur = self.conn.execute(
                    "DELETE FROM customers WHERE id = ?",
                    (customer_id,),
                )

                if cur.rowcount == 0:
                    raise ValueError("Клиент не найден")

        except sqlite3.IntegrityError as exc:
            raise ValueError("Клиента нельзя удалить, если есть заказы") from exc

    #CRUD заказов

    def create_order(self, order: Order) -> int:
        order.validate()

        if self.get_customer(order.customer_id) is None:
            raise ValueError("Клиент для заказа не найден")

        with self.conn:
            cur = self.conn.execute(
                """
                INSERT INTO orders(customer_id, order_date, status, total)
                VALUES (?, ?, ?, ?)
                """,
                (order.customer_id, order.order_date, order.status, order.total),
            )

            order_id = int(cur.lastrowid)
            self._insert_items(order_id, order.items)

        return order_id

    def _insert_items(self, order_id: int, items: List[OrderItem]) -> None:
        self.conn.executemany(
            """
            INSERT INTO order_items(order_id, product_name, quantity, price)
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    order_id,
                    item.product_name.strip(),
                    int(item.quantity),
                    float(item.price),
                )
                for item in items
            ],
        )

    def get_order(self, order_id: int) -> Optional[Order]:
        row = self.conn.execute(
            """
            SELECT id, customer_id, order_date, status, total
            FROM orders
            WHERE id = ?
            """,
            (order_id,),
        ).fetchone()

        if row is None:
            return None

        return Order(
            id=row["id"],
            customer_id=row["customer_id"],
            order_date=row["order_date"],
            status=row["status"],
            total=row["total"],
            items=self._get_order_items(order_id),
        )

    def _get_order_items(self, order_id: int) -> List[OrderItem]:
        rows = self.conn.execute(
            """
            SELECT id, product_name, quantity, price
            FROM order_items
            WHERE order_id = ?
            ORDER BY id
            """,
            (order_id,),
        ).fetchall()

        return [
            OrderItem(
                id=row["id"],
                product_name=row["product_name"],
                quantity=row["quantity"],
                price=row["price"],
            )
            for row in rows
        ]

    def list_orders(
        self,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Dict]:
        if status and status not in VALID_STATUSES:
            raise ValueError("Недопустимый статус")

        query = """
            SELECT
                o.id,
                o.customer_id,
                c.name AS customer_name,
                o.order_date,
                o.status,
                o.total
            FROM orders o
            JOIN customers c ON c.id = o.customer_id
            WHERE 1 = 1
        """

        params = []

        if status:
            query += " AND o.status = ?"
            params.append(status)

        if date_from:
            query += " AND o.order_date >= ?"
            params.append(date_from)

        if date_to:
            query += " AND o.order_date <= ?"
            params.append(date_to)

        query += " ORDER BY o.order_date DESC, o.id DESC"

        rows = self.conn.execute(query, params).fetchall()

        result = []

        for row in rows:
            data = dict(row)
            data["items"] = [
                item.__dict__
                for item in self._get_order_items(row["id"])
            ]
            result.append(data)

        return result

    def update_order(self, order_id: int, order: Order) -> None:
        order.validate()

        if self.get_customer(order.customer_id) is None:
            raise ValueError("Клиент для заказа не найден")

        with self.conn:
            cur = self.conn.execute(
                """
                UPDATE orders
                SET customer_id = ?, order_date = ?, status = ?, total = ?
                WHERE id = ?
                """,
                (
                    order.customer_id,
                    order.order_date,
                    order.status,
                    order.total,
                    order_id,
                ),
            )

            if cur.rowcount == 0:
                raise ValueError("Заказ не найден")

            self.conn.execute(
                "DELETE FROM order_items WHERE order_id = ?",
                (order_id,),
            )

            self._insert_items(order_id, order.items)

    def delete_order(self, order_id: int) -> None:
        with self.conn:
            cur = self.conn.execute(
                "DELETE FROM orders WHERE id = ?",
                (order_id,),
            )

            if cur.rowcount == 0:
                raise ValueError("Заказ не найден")

    #отчёты 

    def report_status_counts(self) -> Dict[str, int]:
        result = {status: 0 for status in VALID_STATUSES}

        rows = self.conn.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM orders
            GROUP BY status
            """
        ).fetchall()

        for row in rows:
            result[row["status"]] = row["count"]

        return result

    def report_top_clients(self, limit: int = 3) -> List[Dict]:
        rows = self.conn.execute(
            """
            SELECT
                c.id,
                c.name,
                ROUND(TOTAL(o.total), 2) AS total_sum,
                COUNT(o.id) AS orders_count
            FROM customers c
            JOIN orders o ON o.customer_id = c.id
            GROUP BY c.id, c.name
            ORDER BY total_sum DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [dict(row) for row in rows]

    def report_revenue(self, period: str) -> float:
        if period not in ("day", "week", "month"):
            raise ValueError("Период должен быть day, week или month")

        if period == "day":
            condition = "date(order_date) = date('now','localtime')"
        elif period == "week":
            condition = (
                "strftime('%Y-%W', order_date) = "
                "strftime('%Y-%W', date('now','localtime'))"
            )
        else:
            condition = (
                "strftime('%Y-%m', order_date) = "
                "strftime('%Y-%m', date('now','localtime'))"
            )

        row = self.conn.execute(
            f"""
            SELECT ROUND(TOTAL(total), 2) AS revenue
            FROM orders
            WHERE {condition}
            """
        ).fetchone()

        return float(row["revenue"])

    def report_revenue_between(self, date_from: str, date_to: str) -> float:
        row = self.conn.execute(
            """
            SELECT ROUND(TOTAL(total), 2) AS revenue
            FROM orders
            WHERE order_date BETWEEN ? AND ?
            """,
            (date_from, date_to),
        ).fetchone()

        return float(row["revenue"])

    #импорт/ экспорт 

    def export_bundle(self) -> Dict:
        customers = [customer.__dict__ for customer in self.list_customers()]
        orders = self.list_orders()

        return {
            "customers": customers,
            "orders": orders,
        }

    def import_bundle(self, bundle: Dict) -> None:
        customers = bundle.get("customers", [])
        orders = bundle.get("orders", [])

        if not isinstance(customers, list) or not isinstance(orders, list):
            raise ValueError("Файл должен содержать списки customers и orders")

        with self.conn:
            customer_map = {}

            for raw_customer in customers:
                customer = Customer(
                    name=str(raw_customer.get("name", "")),
                    phone=str(raw_customer.get("phone", "")),
                    address=str(raw_customer.get("address", "")),
                )
                customer.validate()

                cur = self.conn.execute(
                    """
                    INSERT INTO customers(name, phone, address)
                    VALUES (?, ?, ?)
                    """,
                    (
                        customer.name.strip(),
                        customer.phone,
                        customer.address,
                    ),
                )

                if raw_customer.get("id") is not None:
                    customer_map[int(raw_customer["id"])] = int(cur.lastrowid)

            for raw_order in orders:
                old_customer_id = int(raw_order.get("customer_id", 0))
                new_customer_id = customer_map.get(old_customer_id, old_customer_id)

                items = [
                    OrderItem(
                        product_name=str(raw_item.get("product_name", "")),
                        quantity=int(raw_item.get("quantity", 0)),
                        price=float(raw_item.get("price", 0)),
                    )
                    for raw_item in raw_order.get("items", [])
                ]

                order = Order(
                    customer_id=new_customer_id,
                    order_date=str(raw_order.get("order_date", "")),
                    status=str(raw_order.get("status", "")),
                    items=items,
                )
                order.validate()

                if self.get_customer(order.customer_id) is None:
                    raise ValueError(
                        "В импортируемом заказе указан несуществующий клиент"
                    )

                cur = self.conn.execute(
                    """
                    INSERT INTO orders(customer_id, order_date, status, total)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        order.customer_id,
                        order.order_date,
                        order.status,
                        order.total,
                    ),
                )

                self._insert_items(int(cur.lastrowid), order.items)