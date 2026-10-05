# Я.Календаркин

**Русский** · [English](README.en.md)

[![CI](https://github.com/EDeev/y.calendarkin/actions/workflows/ci.yml/badge.svg)](https://github.com/EDeev/y.calendarkin/actions/workflows/ci.yml)
[![Docker](https://github.com/EDeev/y.calendarkin/actions/workflows/docker.yml/badge.svg)](https://github.com/EDeev/y.calendarkin/actions/workflows/docker.yml)
[![License](https://img.shields.io/github/license/EDeev/y.calendarkin)](LICENSE)

Telegram-бот, который присылает уведомления о событиях из Яндекс.Календаря: утреннюю сводку на день,
два напоминания перед событием и сообщение в момент начала. Достаточно прислать ссылку экспорта календаря.

**Статус:** личный проект, поддерживается · бот [@calendarkin_ybot](https://t.me/calendarkin_ybot)

**Стек:** Python 3.12 · aiogram 3 · aiohttp · icalendar · python-dateutil · pytz · SQLite · Docker

## Возможности

- Подписка по ссылке экспорта iCal; часовой пояс берётся из ссылки
- Повторяющиеся события (`RRULE`) разворачиваются на сегодняшний день
- Сводка на день в 8:00 по часовому поясу календаря (`/daily`)
- Два напоминания перед событием: по умолчанию за 15 и 5 минут, меняются в `/edit_alarm`
- Сообщение в момент начала события (`/moment`)
- Календарь обновляется раз в 13 минут; если обновление не удалось, остаётся прошлая версия

Пример уведомления:

```
Напоминаю!
Через 15 минут будет событие:

Созвон по проекту
Организатор: boss@example.com

10:00 — 11:00
```

## Команды

| Команда | Что делает |
|---|---|
| `/link` | как получить ссылку на календарь |
| `/list` | события на сегодня |
| `/daily` | включить или выключить утреннюю сводку |
| `/moment` | включить или выключить сообщение в момент начала |
| `/get_alarm`, `/edit_alarm` | посмотреть и изменить время напоминаний |
| `/stop_alarm` | включить или выключить второе напоминание |
| `/notif` | приостановить или возобновить все уведомления |
| `/unsubscribe` | удалить подписку на календарь |

## Запуск

```bash
git clone https://github.com/EDeev/y.calendarkin.git && cd y.calendarkin
cp .env.example .env      # BOT_TOKEN от @BotFather
docker compose up -d
```

Готовый образ: `docker pull ghcr.io/edeev/y.calendarkin` или `docker pull dcr.deev.su/edeev/y.calendarkin`.
Базы SQLite создаются при первом запуске.

Без Docker: Python 3.12, `pip install -r requirements.txt`, затем `cd code && BOT_TOKEN=… python bot.py`.

## Как устроено

```
code/bot.py        запуск и два фоновых цикла: проверка событий раз в минуту, обновление календарей
code/handlers.py   команды и приём ссылки
code/script.py     проверка ссылки, скачивание, разбор iCal и повторений, текст уведомления
code/sql.py        пользователи, подписки и настройки напоминаний (SQLite)
```

Принимаются только ссылки `https://calendar.yandex.*`: бот не скачивает файлы по произвольным адресам.
Ошибка у одного пользователя — битый календарь или заблокированный бот — не останавливает рассылку
остальным.

## Разработка

```bash
pip install -r requirements-dev.txt
ruff check --select E9,F code tests && pytest
```

Тесты проверяют разбор календаря: события на сегодня, повторения, `UNTIL` в разных форматах, проверку
ссылки и текст уведомления. Docker-образ собирается по тегу `v*` и публикуется в GitHub Packages и
`dcr.deev.su`.

## Лицензия

MIT — см. [LICENSE](LICENSE).

## Автор

**Деев Егор Викторович** — [GitHub](https://github.com/EDeev) · [Telegram](https://t.me/DeevEgor) · [egor@deev.space](mailto:egor@deev.space)

---

<div align="center">
  <sub>⭐ Если проект оказался полезным, поставьте звёздочку на GitHub!</sub>
  <p><sub>Сделано с ❤️ — <a href="https://deev.space">deev.space</a></sub></p>
</div>
