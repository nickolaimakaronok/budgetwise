# 💰 BudgetWise Desktop

Десктопное приложение для ведения бюджета. Python + CustomTkinter + SQLite.

## Быстрый старт (Mac)

### 1. Клонировать / открыть проект
Открой папку `budgetwise/` в PyCharm или VSCode.

### 2. Создать виртуальное окружение
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Установить зависимости
```bash
pip install -r requirements.txt
```

### 4. Запустить (инициализация БД)
```bash
python main.py
```
При первом запуске автоматически создаётся `budget.db` и системные категории.

### 5. Запустить тесты
```bash
pytest tests/ -v
```

## Структура проекта
```
budgetwise/
├── main.py              # Точка входа
├── budget.db            # База данных (создаётся автоматически)
├── requirements.txt
├── db/
│   ├── database.py      # Подключение SQLite
│   └── migrations.py    # Создание таблиц + системные категории
├── models/
│   └── models.py        # Peewee-модели (User, Transaction, Category, Budget, Goal)
├── services/            # Бизнес-логика (Этап 1)
├── ui/
│   ├── app.py           # Главное окно (Этап 1)
│   ├── pages/           # Страницы: dashboard, transactions, budget, ...
│   └── components/      # Переиспользуемые виджеты
├── utils/
│   ├── constants.py     # Цвета, размеры, константы
│   └── formatters.py    # Форматирование денег и дат
└── tests/
    └── test_formatters.py
```

## Стек
| Слой | Технология |
|------|-----------|
| UI | CustomTkinter |
| Графики | Matplotlib |
| БД | SQLite (встроен в Python) |
| ORM | Peewee |
| Уведомления | plyer |
| Сборка | PyInstaller |
| Тесты | pytest |

## ⚠️ Важно: деньги в копейках
Все суммы хранятся как **целые числа в копейках** (не float!).
- Сохранить: `amount_cents = round(1500.50 * 100)` → `150050`
- Отобразить: `amount_cents / 100` → `1500.5`
