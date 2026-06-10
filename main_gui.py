import tkinter as tk
from datetime import date
from tkinter import messagebox, simpledialog, ttk

from database import Database
from logger_config import setup_logging
from models import Customer, Order, OrderItem, VALID_STATUSES

logger = setup_logging()


class OrderDialog(simpledialog.Dialog):
    def __init__(self, parent, db, title, order=None):
        self.db = db
        self.order = order
        self.result = None

        super().__init__(parent, title)

    def body(self, master):
        customers = self.db.list_customers()

        if not customers:
            messagebox.showwarning(
                "Нет клиентов",
                "Сначала создайте хотя бы одного клиента",
            )
            self.cancel()
            return None

        self.customer_map = {
            f"{customer.id}: {customer.name}": customer.id
            for customer in customers
        }

        ttk.Label(master, text="Клиент").grid(
            row=0,
            column=0,
            sticky="w",
            padx=5,
            pady=5,
        )

        self.customer_var = tk.StringVar()

        self.customer_box = ttk.Combobox(
            master,
            textvariable=self.customer_var,
            values=list(self.customer_map.keys()),
            state="readonly",
            width=35,
        )
        self.customer_box.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(master, text="Дата YYYY-MM-DD").grid(
            row=1,
            column=0,
            sticky="w",
            padx=5,
            pady=5,
        )

        self.date_var = tk.StringVar(value=date.today().isoformat())

        ttk.Entry(
            master,
            textvariable=self.date_var,
            width=38,
        ).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(master, text="Статус").grid(
            row=2,
            column=0,
            sticky="w",
            padx=5,
            pady=5,
        )

        self.status_var = tk.StringVar(value="новый")

        ttk.Combobox(
            master,
            textvariable=self.status_var,
            values=VALID_STATUSES,
            state="readonly",
            width=35,
        ).grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(
            master,
            text="Товары\nпо одному в строке:\nНазвание;Количество;Цена",
        ).grid(row=3, column=0, sticky="nw", padx=5, pady=5)

        self.items_text = tk.Text(master, width=38, height=7)
        self.items_text.grid(row=3, column=1, padx=5, pady=5)

        if self.order:
            current_customer = self.db.get_customer(self.order.customer_id)

            if current_customer:
                self.customer_var.set(
                    f"{current_customer.id}: {current_customer.name}"
                )

            self.date_var.set(self.order.order_date)
            self.status_var.set(self.order.status)

            self.items_text.insert(
                "1.0",
                "\n".join(
                    f"{item.product_name};{item.quantity};{item.price}"
                    for item in self.order.items
                ),
            )

        else:
            self.customer_box.current(0)
            self.items_text.insert("1.0", "Пицца;2;750")

        return self.customer_box

    def apply(self):
        try:
            items = []

            for line in self.items_text.get("1.0", "end").strip().splitlines():
                fields = [field.strip() for field in line.split(";")]

                if len(fields) != 3:
                    raise ValueError(
                        "Каждая строка товара: Название;Количество;Цена"
                    )

                items.append(
                    OrderItem(
                        product_name=fields[0],
                        quantity=int(fields[1]),
                        price=float(fields[2]),
                    )
                )

            order = Order(
                customer_id=self.customer_map[self.customer_var.get()],
                order_date=self.date_var.get().strip(),
                status=self.status_var.get(),
                items=items,
            )
            order.validate()

            self.result = order

        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc))
            self.result = None


class DeliveryApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Быстрая доставка — учёт заказов")
        self.geometry("900x500")

        self.db = Database()

        self.create_widgets()
        self.refresh_orders()

    def create_widgets(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Label(top, text="Статус:").pack(side="left")

        self.status_filter = tk.StringVar(value="Все")

        ttk.Combobox(
            top,
            textvariable=self.status_filter,
            values=["Все"] + list(VALID_STATUSES),
            state="readonly",
            width=18,
        ).pack(side="left", padx=5)

        ttk.Button(
            top,
            text="Применить фильтр",
            command=self.refresh_orders,
        ).pack(side="left", padx=5)

        ttk.Button(
            top,
            text="Добавить",
            command=self.add_order,
        ).pack(side="left", padx=5)

        ttk.Button(
            top,
            text="Редактировать",
            command=self.edit_order,
        ).pack(side="left", padx=5)

        ttk.Button(
            top,
            text="Удалить",
            command=self.delete_order,
        ).pack(side="left", padx=5)

        ttk.Button(
            top,
            text="Показать отчёт",
            command=self.show_report,
        ).pack(side="left", padx=5)

        ttk.Button(
            top,
            text="Добавить клиента",
            command=self.add_customer,
        ).pack(side="right", padx=5)

        columns = ("id", "date", "customer", "status", "total")

        self.tree = ttk.Treeview(
            self,
            columns=columns,
            show="headings",
        )

        self.tree.heading("id", text="ID")
        self.tree.heading("date", text="Дата")
        self.tree.heading("customer", text="Клиент")
        self.tree.heading("status", text="Статус")
        self.tree.heading("total", text="Сумма")

        self.tree.column("id", width=60)
        self.tree.column("date", width=120)
        self.tree.column("customer", width=250)
        self.tree.column("status", width=140)
        self.tree.column("total", width=100)

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

    def selected_order_id(self):
        selected = self.tree.selection()

        if not selected:
            messagebox.showwarning("Выбор", "Выберите заказ")
            return None

        return int(self.tree.item(selected[0], "values")[0])

    def refresh_orders(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        status = self.status_filter.get()
        status = None if status == "Все" else status

        orders = self.db.list_orders(status=status)

        for order in orders:
            self.tree.insert(
                "",
                "end",
                values=(
                    order["id"],
                    order["order_date"],
                    order["customer_name"],
                    order["status"],
                    f"{order['total']:.2f}",
                ),
            )

    def add_customer(self):
        name = simpledialog.askstring("Клиент", "Имя клиента:")

        if not name:
            return

        phone = simpledialog.askstring("Клиент", "Телефон:") or ""
        address = simpledialog.askstring("Клиент", "Адрес:") or ""

        try:
            self.db.create_customer(
                Customer(
                    name=name,
                    phone=phone,
                    address=address,
                )
            )
            self.refresh_orders()

        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc))

    def add_order(self):
        dialog = OrderDialog(self, self.db, "Добавить заказ")

        if dialog.result:
            try:
                self.db.create_order(dialog.result)
                logger.info("Заказ добавлен через GUI")
                self.refresh_orders()

            except Exception as exc:
                messagebox.showerror("Ошибка", str(exc))

    def edit_order(self):
        order_id = self.selected_order_id()

        if order_id is None:
            return

        order = self.db.get_order(order_id)
        dialog = OrderDialog(self, self.db, "Редактировать заказ", order)

        if dialog.result:
            try:
                self.db.update_order(order_id, dialog.result)
                logger.info("Заказ обновлён через GUI id=%s", order_id)
                self.refresh_orders()

            except Exception as exc:
                messagebox.showerror("Ошибка", str(exc))

    def delete_order(self):
        order_id = self.selected_order_id()

        if order_id is None:
            return

        if messagebox.askyesno("Удаление", "Удалить выбранный заказ?"):
            try:
                self.db.delete_order(order_id)
                logger.info("Заказ удалён через GUI id=%s", order_id)
                self.refresh_orders()

            except Exception as exc:
                messagebox.showerror("Ошибка", str(exc))

    def show_report(self):
        window = tk.Toplevel(self)
        window.title("Отчёт")

        text = tk.Text(window, width=60, height=20)
        text.pack(padx=10, pady=10)

        text.insert("end", "Количество заказов по статусам:\n")

        for status, count in self.db.report_status_counts().items():
            text.insert("end", f"- {status}: {count}\n")

        text.insert("end", "\nТоп-3 клиента:\n")

        top_clients = self.db.report_top_clients()

        if not top_clients:
            text.insert("end", "Нет данных\n")

        for row in top_clients:
            text.insert("end", f"- {row['name']}: {row['total_sum']:.2f}\n")

        text.insert("end", f"\nВыручка за день: {self.db.report_revenue('day'):.2f}\n")
        text.insert("end", f"Выручка за неделю: {self.db.report_revenue('week'):.2f}\n")
        text.insert("end", f"Выручка за месяц: {self.db.report_revenue('month'):.2f}\n")

        text.config(state="disabled")

    def destroy(self):
        self.db.close()
        super().destroy()


if __name__ == "__main__":
    app = DeliveryApp()
    app.mainloop()