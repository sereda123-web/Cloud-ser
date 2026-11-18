# Лабораторна робота №5 — Комплексне розгортання хмарного застосунку

**Виконав:** Середа Іван, група ІПЗ · **Варіант 1:** Електронний журнал
(таблиця `journal_records`, endpoint `/api/records`)

Архітектура: `код → Git → GitHub Actions (compile → pytest → deploy hook) → Render Web Service (Flask + Gunicorn) → Cloud PostgreSQL (Neon)`

## Вміст

| Файл | Призначення |
| --- | --- |
| `app.py` | Flask-застосунок: публічні та захищені (Bearer token) endpoint, `/health` з перевіркою БД |
| `schema.sql` | Таблиця `journal_records` і 3 демо-записи |
| `tests/test_app.py` | 8 тестів, яким не потрібна реальна БД |
| `.github/workflows/ci-cd.yml` | CI/CD: syntax check → pytest → Render Deploy Hook |
| `scripts/demo.ps1`, `scripts/demo.sh` | Готові запити для скріншотів (токен у вивід не потрапляє) |
| `.env.example` | Шаблон змінних середовища (реальний `.env` у Git не додається) |
| `screenshots/` | Сюди зберігайте скріншоти (папка в `.gitignore`) |

## Розпакування

Розпакуйте архів **у корінь вашого локального репозиторію** (у архіві немає зовнішньої папки).
Якщо в репозиторії вже є `.gitignore` або `requirements.txt` — вони будуть замінені.

## Крок 1. База даних

1. У Neon відкрийте **SQL Editor** і виконайте `schema.sql` **один раз** (повторний запуск продублює демо-записи).
2. Скопіюйте connection string (`postgresql://...?sslmode=require`).

## Крок 2. Локальні змінні та запуск (PowerShell)

```powershell
Copy-Item .env.example .env          # відкрийте .env і підставте DATABASE_URL
python -c "import secrets; print(secrets.token_urlsafe(48))"   # це значення — у ADMIN_TOKEN

python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt

pytest -v                            # скріншот 3
python app.py                        # в іншому вікні PowerShell:
.\scripts\demo.ps1                   # скріншот 4
```

Якщо PowerShell забороняє запуск скриптів: `Set-ExecutionPolicy -Scope Process Bypass`.
Linux/macOS/Git Bash: `bash scripts/demo.sh`.

## Крок 3. GitHub

```powershell
git add .
git commit -m "Prepare protected cloud mini project"
git push
```

Перевірте, що `.env` у репозиторії **відсутній** (скріншот 1).
У GitHub: *Settings → Secrets and variables → Actions → New repository secret* → ім'я `RENDER_DEPLOY_HOOK_URL`, значення — Deploy Hook URL із Render (скріншот 6: має бути видно лише ім'я).

## Крок 4. Render Web Service

| Параметр | Значення |
| --- | --- |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app` |
| Health Check Path | `/health` |
| `APP_TITLE` | Електронний журнал |
| `APP_VERSION` | 1.0 |
| `DATABASE_URL` | секретний connection string |
| `ADMIN_TOKEN` | довгий випадковий токен |

Рекомендація: у Render вимкніть автодеплой при push (*Auto-Deploy: Off*), щоб деплой запускав лише Deploy Hook після успішних тестів.

## Крок 5. Перевірка публічного URL

```powershell
.\scripts\demo.ps1 -BaseUrl https://ВАШ-СЕРВІС.onrender.com
```

Безкоштовний план Render «засинає» — перший запит може тривати до ~1 хв.

## Крок 6. Експеримент (варіант «зламати pytest»)

1. У `tests/test_app.py` у функції `test_admin_stats_requires_token` змініть `401` на `200` (там є коментар `EXPERIMENT`).
2. `git add . ; git commit -m "Experiment: break test" ; git push`
3. На GitHub → Actions: крок **Run tests** червоний, **Trigger Render deployment** — skipped (скріншот 16).
   У Render новий deploy не з'явився.
4. Поверніть `401`, зробіть commit і push — CI зелений, deploy запущено (скріншот 17).

## Скріншоти для звіту

Зберігайте у `screenshots/` під такими іменами (номер = «Рисунок N» у звіті). **Токен, DATABASE_URL, Deploy Hook URL на екрані бути не повинні.**

| № | Файл | Що знімати |
| --- | --- | --- |
| 1 | `01_repo.png` | Список файлів репозиторію на GitHub (без `.env`) |
| 2 | `02_db.png` | SQL Editor: виконаний `schema.sql` і результат `SELECT` |
| 3 | `03_pytest.png` | `pytest -v` — 8 passed |
| 4 | `04_local.png` | Вивід `scripts/demo.ps1` локально |
| 5 | `05_render_config.png` | Render: Build/Start/Health Path, назви змінних (значення приховані) |
| 6 | `06_github_secret.png` | GitHub Secrets: видно лише ім'я `RENDER_DEPLOY_HOOK_URL` |
| 7 | `07_actions_ok.png` | Успішний workflow (всі кроки зелені) |
| 8 | `08_render_deploy.png` | Render: Deploy «Live» + health check passed |
| 9 | `09_health.png` | `https://…onrender.com/health` → status ok, database ok |
| 10 | `10_records.png` | `GET /api/records` у браузері |
| 11 | `11_401.png` | Запит без токена → HTTP 401 |
| 12 | `12_stats_200.png` | Запит з токеном (`Bearer ****`) → HTTP 200 |
| 13 | `13_post_201.png` | POST з токеном → HTTP 201 |
| 14 | `14_records_after.png` | `GET /api/records` — новий запис є |
| 15 | `15_logs.png` | Render Logs: звичайний запит, 401, deploy/health event |
| 16 | `16_exp_fail.png` | Експеримент: GitHub Actions з помилкою на pytest |
| 17 | `17_exp_restore.png` | Після відновлення: CI зелений, deploy виконано |

## Після завершення

Видаліть або відкличте тестовий `ADMIN_TOKEN`, непотрібні Deploy Hook і тестові ресурси.
