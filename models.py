from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

VALID_STATUSES = ("новый", "в доставке", "выполнен", "отменён")

@dataclass
class Customer:
    name: str
    phone: str = ""
    address: str = ""
    id: Optional[int] = None

    def validate(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Имя клиента обязательно")


@dataclass
class OrderItem:
    product_name: str
    quantity: int
    price: float
    id: Optional[int] = None

    def validate(self) -> None:
        if not self.product_name or not self.product_name.strip():
            raise ValueError("Название товара обязательно")
        if int(self.quantity) <= 0:
            raise ValueError("Количество должно быть больше 0")
        if float(self.price) < 0:
            raise ValueError("Цена не может быть отрицательной")

    @property
    def amount(self) -> float:
        return round(int(self.quantity) * float(self.price), 2)


@dataclass
class Order:
    customer_id: int
    order_date: str
    status: str
    items: List[OrderItem] = field(default_factory=list)
    total: float = 0.0
    id: Optional[int] = None

    def validate(self) -> None:
        if int(self.customer_id) <= 0:
            raise ValueError("customer_id должен быть положительным")
        try:
            datetime.strptime(self.order_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("Дата заказа должна быть в формате YYYY-MM-DD") from exc
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Недопустимый статус: {self.status}")
        if not self.items:
            raise ValueError("В заказе должен быть хотя бы один товар")
        for item in self.items:
            item.validate()
        self.total = self.calculate_total()

    def calculate_total(self) -> float:
        return round(sum(item.amount for item in self.items), 2)