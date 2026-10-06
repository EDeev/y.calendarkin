# Y.Calendarkin

[Русский](README.md) · **English**

[![CI](https://github.com/EDeev/y.calendarkin/actions/workflows/ci.yml/badge.svg)](https://github.com/EDeev/y.calendarkin/actions/workflows/ci.yml)
[![Docker](https://github.com/EDeev/y.calendarkin/actions/workflows/docker.yml/badge.svg)](https://github.com/EDeev/y.calendarkin/actions/workflows/docker.yml)
[![License](https://img.shields.io/github/license/EDeev/y.calendarkin)](LICENSE)

A Telegram bot that sends notifications about Yandex Calendar events: a morning summary for the day, two
reminders before an event and a message when it starts. All it needs is the calendar's export link. The
bot speaks Russian.

**Status:** personal project, maintained · bot [@calendarkin_ybot](https://t.me/calendarkin_ybot)

**Stack:** Python 3.12 · aiogram 3 · aiohttp · icalendar · python-dateutil · pytz · PostgreSQL · Docker

## Features

- Subscription by iCal export link; the time zone is taken from the link
- Recurring events (`RRULE`) are expanded for today
- A day summary at 8:00 in the calendar's time zone (`/daily`)
- Two reminders before an event: 15 and 5 minutes by default, changed with `/edit_alarm`
- A message when an event starts (`/moment`)
- The calendar is refreshed every 13 minutes; if a refresh fails, the previous version stays

## Commands

| Command | What it does |
|---|---|
| `/link` | how to get the calendar link |
| `/list` | today's events |
| `/daily` | toggle the morning summary |
| `/moment` | toggle the message at event start |
| `/get_alarm`, `/edit_alarm` | view and change reminder times |
| `/stop_alarm` | toggle the second reminder |
| `/notif` | pause or resume all notifications |
| `/unsubscribe` | remove the calendar subscription |

## Running

```bash
git clone https://github.com/EDeev/y.calendarkin.git && cd y.calendarkin
cp .env.example .env      # BOT_TOKEN from @BotFather
docker compose up -d
```

Prebuilt image: `docker pull ghcr.io/edeev/y.calendarkin` or `docker pull dcr.deev.su/edeev/y.calendarkin`.
PostgreSQL tables are created on first start. Data from the old version (SQLite `users.db` and `clock.db`)
is moved by `python scripts/migrate_sqlite.py --sqlite-dir path/to/db --dsn postgresql://…`.

Without Docker: Python 3.10+, PostgreSQL, `pip install -r requirements.txt`, then
`cd code && BOT_TOKEN=… DATABASE_URL=postgresql://… python bot.py`.

## How it works

```
code/bot.py        entry point and two background loops: event checks every minute, calendar refresh
code/handlers.py   commands and receiving the link
code/script.py     link validation, download, iCal and recurrence parsing, notification text
code/sql.py        users, subscriptions and reminder settings (PostgreSQL)
scripts/           migration from SQLite
```

Only `https://calendar.yandex.*` links are accepted, so the bot never downloads from arbitrary addresses.
An error for one user (a broken calendar or a blocked bot) doesn't stop notifications for others.

## Development

```bash
pip install -r requirements-dev.txt
ruff check --select E9,F code tests && pytest
```

The tests (storage on PostgreSQL from `TEST_DATABASE_URL`) cover calendar parsing: today's events, recurrences, `UNTIL` in different formats, link
validation and the notification text. The Docker image is built on `v*` tags and published to GitHub
Packages and `dcr.deev.su`.

## License

MIT — see [LICENSE](LICENSE).

## Author

**Egor Deev** — [GitHub](https://github.com/EDeev) · [Telegram](https://t.me/DeevEgor) · [egor@deev.space](mailto:egor@deev.space)

---

<div align="center">
  <sub>⭐ If you find this project useful, give it a star on GitHub!</sub>
  <p><sub>Made with ❤️ — <a href="https://deev.space">deev.space</a></sub></p>
</div>
