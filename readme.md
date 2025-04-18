# Telegram «Утренний брифинг»

**Описание:**

«Утренний брифинг» — это Telegram‑бот, который еженедельно/ежечасно (по выбору) или в заданное пользователем время отправляет дайджест:
- **Курс USD/RUB** (по данным ЦБ РФ)
- **Топ‑3 новости** (через RSS РБК)

Пользователь может:
- Задать время рассылки (по умолчанию 09:00)
- Включить/отключить модули «Курс валют» и «Новости»
- Получить брифинг мгновенно кнопкой «📨 Получить брифинг сейчас»
- Настроить параметры через кнопку «⚙️ Настройки»

На сервере бот работает в режиме **webhook** через **aiohttp**, проксируется **Nginx** и запущен в **Docker**. Для локальной отладки используется **polling**.

---

## Функционал

- `/start` — регистрация и главное меню
- «📨 Получить брифинг сейчас» — немедленная отправка выбранных модулей
- «⚙️ Настройки» — FSM‑диалог для выбора времени и модулей
- Ежечасная проверка (или в указанное время) и рассылка пользователям

---

## Стек технологий

- ### Язык и фреймворки
  - **Python 3.13**
  - **Aiogram v3** с поддержкой **asyncio**, **middlewares**, **routers**, **FSMContext**
  - **aiohttp** (webhook‑сервер)
  - **APScheduler** — планировщик задач

- ### Работа с данными
  - **PostgreSQL** + **asyncpg** (Pool)
  - **python-dotenv** — загрузка переменных окружения

- ### Внешние API
  - **РБК RSS** (новости через `feedparser` + `aiohttp`)
  - **ЦБ РФ** (курс валют)

- ### Инфраструктура
  - **Docker** + **Docker Compose** (для локальной среды и продакшена)
  - **Nginx** (проксирование / SSL)

- ### CI/CD
  - **GitHub Actions**: сборка multi‑arch образа, пуш в Docker Hub, деплой по SSH

- ### Мониторинг и логирование
  - Встроенный **logging**

---

## Быстрый старт

1. Клонировать репозиторий и создать `.env`:
    ```dotenv
    BOT_TOKEN=ВАШ_ТОКЕН
    DATABASE_URL=postgresql://botuser:pass@host:5432/db
    TIMEZONE=Asia/Dhaka
    DOMAIN=ваш.домен
    USE_WEBHOOK=true
    PORT=8000
    WEBHOOK_SECRET=<любая_случайная_строка>
    ```
2. Собрать Docker‑образ:
    ```bash
    docker build -t telegram-briefing-bot .
    ```
3. Запустить контейнер:
    ```bash
    docker run -d --name briefing-bot \
      --restart always --env-file .env -p 8000:8000 telegram-briefing-bot
    ```
4. Настроить Nginx и SSL (Let's Encrypt + прокси на `/webhook/`).
5. Установить webhook:
    ```bash
    curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
      -d "url=https://${DOMAIN}/webhook/" \
      -d "secret_token=${WEBHOOK_SECRET}"
    ```
6. Готово! Пишите `/start` или нажимайте кнопку «Начать» в меню бота.

---