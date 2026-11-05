# 💰 BudgetWise

[![Tests](https://github.com/nickolaimakaronok/budgetwise/actions/workflows/tests.yml/badge.svg)](https://github.com/nickolaimakaronok/budgetwise/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue)

A personal finance desktop app written in Python. Track income and expenses, set monthly budgets, plan savings goals and see where the money goes.
Everything stays on your computer in a local SQLite database.

![Dashboard](screenshots/Dashboard_screenshot.png)

▶️ [Demo video](https://youtu.be/-BR_jM5aqeQ) (recorded with v1.x)

---

## Features

- **Dashboard** — monthly balance, income, expenses and savings, latest transactions
- **Transactions** — add, edit, delete; filter by type, category, dates and #tags; search by note, category or tag; quick add with ⌘N / Ctrl+N
- **Recurring payments** — rent, subscriptions and salary are added every month automatically; missed months are caught up and the day never drifts (31 Jan → 28 Feb → 31 Mar)
- **Bank CSV import** — choose the columns, date format and how the amount sign is read; the file encoding is detected automatically (UTF-8, UTF-16, Windows-1251 Cyrillic, Windows-1255 Hebrew)
- **Export** — CSV that opens correctly in Excel and can be imported back, plus a monthly PDF report
- **Budgets** — monthly limit per category, warning at 80 % and alert at 100 %, copy last month's limits in one click, system notifications when a limit is exceeded
- **Analytics** — spending by category, by day and income vs. expenses over the year
- **Goals** — savings goals with contributions, deadlines and how much to save per month
- **Settings** — currency (₪ $ € £ ₽), light / dark / system theme, English / Russian / German, custom categories, one-click backup

<table>
  <tr>
    <td><img src="screenshots/Transactions_screenshot.png" alt="Transactions"><br><sub>Transactions — search and filters</sub></td>
    <td><img src="screenshots/Repeat_transactions_screenshot.png" alt="Add transaction"><br><sub>Adding a monthly recurring payment</sub></td>
  </tr>
  <tr>
    <td><img src="screenshots/Budget_screenshot.png" alt="Budget"><br><sub>Budget limits per category</sub></td>
    <td><img src="screenshots/Goals_screenshot.png" alt="Goals"><br><sub>Savings goals with deadlines</sub></td>
  </tr>
  <tr>
    <td><img src="screenshots/Analytics_screenshot1.png" alt="Analytics"><br><sub>Analytics — spending by category</sub></td>
    <td><img src="screenshots/Analytics_screenshot2.png" alt="Analytics breakdown"><br><sub>Analytics — daily spending and breakdown</sub></td>
  </tr>
  <tr>
    <td><img src="screenshots/Settings_screenshot1.png" alt="Settings"><br><sub>Settings — profile and appearance</sub></td>
    <td><img src="screenshots/Settings_screenshot2.png" alt="Settings data"><br><sub>Settings — categories and backups</sub></td>
  </tr>
</table>

---

## Under the hood

- **Layered architecture.** `ui/` only displays data, `services/` holds all business logic, `models/` defines the Peewee ORM models. The UI never queries the database directly, so the logic is tested without opening a window.
- **Money is stored as integer cents.** No floating-point rounding anywhere, including CSV import and export.
- **Data safety**
  - Automatic backup on every start using the SQLite backup API (it includes data still in the WAL file); the newest 10 are kept, manual backups are never deleted.
  - Versioned schema migrations (`PRAGMA user_version`) upgrade old databases in place. A regression test covers a real bug where adding a column after `create_tables()` corrupted the database file.
  - On upgrade, user data is moved from `~/Documents` to the OS app-data folder with a one-time migration: copy → integrity check → row-count check → atomic rename. The old file is kept, nothing is deleted.
- **Recurring transactions as a series.** One template, generated copies and a "last generated month" counter: running it twice creates nothing new, missed months are caught up, and editing or deleting a copy never causes a double charge.
- **Cross-platform.** Everything OS-specific lives in `utils/platform_utils.py`: the data folder, keyboard shortcuts, opening folders, and notifications (`osascript` on macOS, `plyer` on Windows and Linux).
- **Performance.** Transactions render in pages of 200 rows, totals are calculated with SQL `SUM … GROUP BY`, and tags load in one query instead of one per row.
- **Tests and CI.** 260+ pytest tests. GitHub Actions runs them on macOS, Windows and Linux with Python 3.12, 3.13 and 3.14 on every push. Tests use in-memory or temporary databases and never touch real user data.

---

## Run from source

Requires **Python 3.12 – 3.14** with Tk (included in the python.org installers; with Homebrew install `python-tk`, on Linux `python3-tk`).

**macOS / Linux**

```bash
git clone https://github.com/nickolaimakaronok/budgetwise.git
cd budgetwise
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/nickolaimakaronok/budgetwise.git
cd budgetwise
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

On the first start a short onboarding asks for your name, currency and language, and 18 default categories are created.

> On Linux, desktop notifications need `notify-send` (package `libnotify-bin`).

### Run the tests

```bash
python -m pytest tests/ -q
```

Use `python -m pytest` rather than plain `pytest`, so the tests run with the Python from `.venv`.

---

## Where your data lives

| OS | Folder |
|---|---|
| macOS | `~/Library/Application Support/BudgetWise/` |
| Windows | `%LOCALAPPDATA%\BudgetWise\` |
| Linux | `~/.local/share/BudgetWise/` |

The folder contains `budget.db`, the `backups/` folder and `budgetwise.log`. The exact path is shown in **Settings**, and **Open Backup Folder** opens the backups inside it.
To keep the data somewhere else, set the `BUDGETWISE_DATA_DIR` environment variable.

> **Upgrading from 1.x:** data in `~/Documents/BudgetWise` is moved automatically on the first start. The old database stays there as `budget.db.moved`.

---

## Project structure

```
budgetwise/
├── main.py                     # entry point: logging → migrations → onboarding → main window
├── requirements.txt
├── db/
│   ├── database.py             # SQLite connection (Peewee) in the app-data folder
│   ├── migrations.py           # tables, schema upgrades, default categories
│   ├── backup.py               # backups via the SQLite backup API + rotation
│   └── data_move.py            # one-time move of the data out of ~/Documents
├── models/
│   └── models.py               # User, Category, Transaction, Budget, Goal, Tag
├── services/                   # business logic — the UI never touches the database
│   ├── transaction_service.py  # CRUD, filters, totals, recurring series
│   ├── budget_service.py       # limits, status, copy from last month
│   ├── analytics_service.py    # totals by category, day and year
│   ├── goal_service.py         # goals, contributions, deadlines
│   ├── tag_service.py          # #tags
│   ├── csv_import_service.py   # bank CSV: encodings, delimiters, amount formats
│   ├── csv_export_service.py
│   └── pdf_service.py          # monthly PDF report
├── ui/
│   ├── app.py                  # main window, sidebar, keyboard shortcuts
│   └── pages/                  # dashboard, transactions, budget, analytics, goals, settings, onboarding
├── utils/
│   ├── platform_utils.py       # everything that differs between macOS, Windows and Linux
│   ├── notifications.py        # background budget checks
│   ├── i18n.py                 # English / Russian / German texts
│   ├── formatters.py           # money and date formatting and parsing
│   └── ...                     # theme, constants, logging, category translations
└── tests/                      # pytest suite; conftest.py points the app at a temporary folder
```

---

## Tech stack

| Layer | Technology |
|---|---|
| UI | CustomTkinter |
| Charts | Matplotlib (embedded in Tk) |
| Database | SQLite + Peewee ORM |
| PDF | ReportLab |
| Notifications | `osascript` on macOS, plyer on Windows / Linux |
| Tests and CI | pytest, GitHub Actions |
| Packaging | PyInstaller |

---

## Roadmap

- [ ] Downloadable builds for macOS (`.app`) and Windows (`.exe`) via GitHub Actions and Releases
- [ ] Layout polish for high-DPI Windows screens
- [ ] Stricter amount validation in forms
- [ ] Translated notification texts and PDF fonts for Cyrillic and Hebrew
- [ ] Hebrew interface (right-to-left)

---

## Changelog

### 2.0.0 — November 2026
- Cross-platform: Ctrl+N on Windows and Linux, opening folders and system notifications on every OS
- Data moved to the OS app-data folder with a safe automatic migration; a clear error window if the data can't be opened
- Reliable backups through the SQLite backup API, with rotation
- Recurring transactions rebuilt as series: no day drift, no double charges, missed months caught up
- All transactions are listed (in pages), not only the latest 200; faster totals and tag loading
- Bank CSV import with column mapping, sign modes and encoding detection (incl. Hebrew); CSV export with signed amounts and a UTF-8 BOM for Excel
- Python 3.12 – 3.14 and Tk 9 support; CI on macOS, Windows and Linux; 260+ tests

### Earlier versions
- **1.8.0** — first-start onboarding: name, currency, language
- **1.7.0** — English, Russian and German interface; system categories translated
- **1.6.0** — dark theme, monthly PDF report, yearly income vs. expenses chart
- **1.5.0** — search by category and note, goal deadlines
- **1.4.0** — recurring monthly transactions, database migrations for existing users
- **1.3.0** — goal service, logging to a file, GitHub Actions CI
- **1.2.0** — background budget notifications
- **1.1.0** — editing transactions, filters, CSV export, month selectors
- **1.0.0** — dashboard, transactions, budgets, analytics, goals, settings

---

Made by Nickolai Makaronok [nickolaimakaronok](https://github.com/nickolaimakaronok), Computer Science student at Tel Aviv University.
