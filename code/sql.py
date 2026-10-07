"""Хранилище бота — PostgreSQL (до 2026-10 — два файла SQLite users.db и clock.db).

Таблица users хранит короткий внутренний номер пользователя (id) и его id в Telegram (tg_id);
остальные таблицы ссылаются на внутренний номер, как и раньше."""
from psycopg_pool import ConnectionPool
from pytz import timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id    SERIAL PRIMARY KEY,
    tg_id BIGINT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS urls (
    user_id   INTEGER PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
    status    BOOLEAN NOT NULL DEFAULT TRUE,
    url_ical  TEXT,
    time_zone TEXT
);
CREATE TABLE IF NOT EXISTS alarms (
    user_id  INTEGER PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
    daily    BOOLEAN NOT NULL DEFAULT FALSE,
    start    BOOLEAN NOT NULL DEFAULT TRUE,
    alarm_1  INTEGER,
    alarm_2  INTEGER,
    status_2 BOOLEAN NOT NULL DEFAULT TRUE
);
ALTER TABLE alarms ADD COLUMN IF NOT EXISTS changes BOOLEAN NOT NULL DEFAULT TRUE;
"""


def connect(dsn):
    """Пул соединений сам переподключается, если PostgreSQL перезапускали"""
    pool = ConnectionPool(dsn, min_size=1, max_size=4, kwargs={"autocommit": True}, open=True)
    with pool.connection() as conn:
        conn.execute(SCHEMA)
    return pool


class _Base:
    def __init__(self, pool):
        self.pool = pool

    def _one(self, query, args=()):
        with self.pool.connection() as conn:
            row = conn.execute(query, args).fetchone()
            return row[0] if row else None

    def _all(self, query, args=()):
        with self.pool.connection() as conn:
            return conn.execute(query, args).fetchall()

    def _run(self, query, args=()):
        with self.pool.connection() as conn:
            conn.execute(query, args)


class Users(_Base):
    # КОМАНДЫ USER
    def user_exists(self, user_id):
        """Проверяем, есть ли уже пользователь в базе (по id Telegram)"""
        return bool(self._one("SELECT 1 FROM users WHERE tg_id = %s", (user_id,)))

    def all_users(self):
        """Список внутренних номеров"""
        return self._all("SELECT id FROM users ORDER BY id")

    def add_user(self, user_id):
        """Добавляем нового пользователя"""
        self._run("INSERT INTO users (tg_id) VALUES (%s) ON CONFLICT DO NOTHING", (user_id,))

    def get_user_id(self, user_id):
        """Внутренний номер по id Telegram"""
        return self._one("SELECT id FROM users WHERE tg_id = %s", (user_id,))

    def get_first_user_id(self, user_id):
        """id Telegram по внутреннему номеру"""
        return self._one("SELECT tg_id FROM users WHERE id = %s", (user_id,))

    # КОМАНДЫ URL
    def url_exists(self, user_id):
        return bool(self._one("SELECT 1 FROM urls WHERE user_id = %s", (user_id,)))

    def add_url(self, user_id, url_ical, time_zone):
        """Добавляем ссылку на календарь"""
        self._run("INSERT INTO urls (user_id, url_ical, time_zone) VALUES (%s, %s, %s)", (user_id, url_ical, time_zone))

    def update_status(self, user_id):
        """Переключаем рассылку уведомлений"""
        self._run("UPDATE urls SET status = NOT status WHERE user_id = %s", (user_id,))

    def update_url(self, user_id, url_ical, time_zone):
        """Обновляем ссылку и часовой пояс"""
        self._run("UPDATE urls SET url_ical = %s, time_zone = %s WHERE user_id = %s", (url_ical, time_zone, user_id))

    def get_status(self, user_id):
        return self._one("SELECT status FROM urls WHERE user_id = %s", (user_id,))

    def get_url(self, user_id):
        return self._one("SELECT url_ical FROM urls WHERE user_id = %s", (user_id,))

    def delete_url(self, user_id):
        """Удаляем подписку на календарь"""
        self._run("DELETE FROM urls WHERE user_id = %s", (user_id,))

    def get_tz(self, user_id):
        """Часовой пояс календаря"""
        return timezone(self._one("SELECT time_zone FROM urls WHERE user_id = %s", (user_id,)))


class Clock(_Base):
    # КОМАНДЫ ALARM
    def clock_exists(self, user_id):
        return bool(self._one("SELECT 1 FROM alarms WHERE user_id = %s", (user_id,)))

    def add_clock(self, user_id):
        """Добавляем параметры уведомления: напоминания за 15 и 5 минут"""
        self._run("INSERT INTO alarms (user_id, alarm_1, alarm_2) VALUES (%s, 15, 5) ON CONFLICT DO NOTHING", (user_id,))

    def delete_clock(self, user_id):
        self._run("DELETE FROM alarms WHERE user_id = %s", (user_id,))

    def get_alarm(self, user_id):
        """Задержки напоминаний (первое, второе)"""
        rows = self._all("SELECT alarm_1, alarm_2 FROM alarms WHERE user_id = %s", (user_id,))
        return tuple(rows[0]) if rows else None

    def get_start(self, user_id):
        return self._one("SELECT start FROM alarms WHERE user_id = %s", (user_id,))

    def get_daily(self, user_id):
        return self._one("SELECT daily FROM alarms WHERE user_id = %s", (user_id,))

    def get_status2(self, user_id):
        return self._one("SELECT status_2 FROM alarms WHERE user_id = %s", (user_id,))

    def get_changes(self, user_id):
        """Присылать ли уведомления о новых, удалённых и перенесённых событиях"""
        return self._one("SELECT changes FROM alarms WHERE user_id = %s", (user_id,))

    # ПЕРЕКЛЮЧАТЕЛИ
    def update_daily(self, user_id):
        self._run("UPDATE alarms SET daily = NOT daily WHERE user_id = %s", (user_id,))

    def update_start(self, user_id):
        self._run("UPDATE alarms SET start = NOT start WHERE user_id = %s", (user_id,))

    def update_alarm1(self, user_id, alarm_1):
        self._run("UPDATE alarms SET alarm_1 = %s WHERE user_id = %s", (alarm_1, user_id))

    def update_alarm2(self, user_id, alarm_2):
        self._run("UPDATE alarms SET alarm_2 = %s WHERE user_id = %s", (alarm_2, user_id))

    def update_status2(self, user_id):
        self._run("UPDATE alarms SET status_2 = NOT status_2 WHERE user_id = %s", (user_id,))

    def update_changes(self, user_id):
        self._run("UPDATE alarms SET changes = NOT changes WHERE user_id = %s", (user_id,))
