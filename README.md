установка проекта

Клонировать репозиторий:
git clone https://github.com/evusikk/delivery_system.git
cd delivery_system

Создать виртуальное окружение:
python -m venv venv

Активировать виртуальное окружение.
venv\Scripts\activate

Установить зависимости:
pip install -r requirements.txt

CLI-режим

Основной файл для запуска:
python main_cli.py

Примеры CLI-запуска

Добавить клиента:
python main_cli.py customer-add --name "Иван" --phone "+79990000000" --address "Москва"

Показать список клиентов:
python main_cli.py customer-list

Изменить клиента:
python main_cli.py customer-edit --id 1 --name "Иван Петров" --phone "+79991112233" --address "Москва, ул. Центральная"

Удалить клиента:
python main_cli.py customer-delete --id 1

(если у клиента есть заказы удалить его нельзя)

Добавить заказ:
python main_cli.py order-add --customer-id 1 --date 2025-04-20 --status "новый" --items "Пицца:2:750,Сок:1:120"

Формат товаров для CLI:
Название:Количество:Цена,Название:Количество:Цена

Пример:
Пицца:2:750,Сок:1:120

Итоговая сумма заказа рассчитывается автоматически на основе количества и цены товаров.

Показать список заказов:
python main_cli.py order-list

Фильтр заказов по статусу:
python main_cli.py order-list --status "выполнен"

Фильтр заказов по дате:
python main_cli.py order-list --date-from 2025-04-01 --date-to 2025-04-30

Фильтр заказов по статусу и дате
python main_cli.py order-list --status "новый" --date-from 2025-04-01 --date-to 2025-04-30

Изменить заказ

Изменить только статус заказа:
python main_cli.py order-edit --id 1 --status "выполнен"

Изменить клиента, дату, статус и список товаров:
python main_cli.py order-edit --id 1 --customer-id 1 --date 2025-04-21 --status "в доставке" --items "Суши:1:900,Сок:2:100"

Удалить заказ:
python main_cli.py order-delete --id 1

Отчёты

Команда отчёта:
python main_cli.py report --period month

Доступные значения периода:
day, week,month

Отчёт за день:
python main_cli.py report --period day

Отчёт за неделю:
python main_cli.py report --period week

Отчёт за месяц:
python main_cli.py report --period month

В отчёте выводятся:
количество заказов по каждому статусу;
топ-3 клиента по сумме заказов;
выручка за выбранный период.

Экспорт данных
(экспортируются клиенты, заказы и позиции заказов)

Экспорт в JSON:
python main_cli.py export --file orders_backup.json

Экспорт в XML:
python main_cli.py export --file orders_backup.xml

Импорт данных

Импорт из JSON:
python main_cli.py import --file orders_backup.json

Импорт из XML:
python main_cli.py import --file orders_backup.xml

GUI-режим

Запуск графического интерфейса:
python main_gui.py

В форме заказа товары вводятся по одному в строке в формате:
Название;Количество;Цена

Логи сохраняются в файл:
logs/app.log

Тесты

Запуск тестов:
pytest

Проверка покрытия тестами:
coverage run -m pytest
coverage report

Проверка покрытия с минимальным порогом 60%:
coverage run -m pytest
coverage report --fail-under=60
