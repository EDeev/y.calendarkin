import os
import sqlite3
import sys

import psycopg
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

DSN = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DSN, reason="нужен TEST_DATABASE_URL (PostgreSQL)")


@pytest.fixture
def pool():
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    import sql
    p = sql.connect(DSN)
    yield p
    p.close()


def test_users_and_alarms(pool):
    from sql import Clock, Users
    du, dc = Users(pool), Clock(pool)
    du.add_user(555)
    du.add_user(555)  # повторно — без ошибки
    uid = du.get_user_id(555)
    assert du.user_exists(555) and du.get_first_user_id(uid) == 555
    du.add_url(uid, "https://calendar.yandex.ru/x", "Asia/Krasnoyarsk")
    dc.add_clock(uid)
    assert du.get_tz(uid).zone == "Asia/Krasnoyarsk" and du.get_status(uid) is True
    du.update_status(uid)
    assert du.get_status(uid) is False
    assert dc.get_alarm(uid) == (15, 5) and dc.get_start(uid) is True and dc.get_daily(uid) is False
    dc.update_alarm1(uid, 30)
    dc.update_daily(uid)
    assert dc.get_alarm(uid) == (30, 5) and dc.get_daily(uid) is True
    assert dc.get_changes(uid) is True
    dc.update_changes(uid)
    assert dc.get_changes(uid) is False
    du.delete_url(uid)
    assert not du.url_exists(uid)
    assert du.all_users() == [(uid,)]


def test_migration(pool, tmp_path):
    import migrate_sqlite
    users = sqlite3.connect(tmp_path / "users.db")
    users.executescript("""
        CREATE TABLE user (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL);
        CREATE TABLE url (user_id INTEGER NOT NULL, status BOOLEAN NOT NULL DEFAULT (True), url_ical STRING, time_zone STRING);
        INSERT INTO user VALUES (1, 111), (5, 555);
        INSERT INTO url VALUES (5, 1, 'https://calendar.yandex.ru/a', 'Europe/Moscow');
    """)
    users.commit()
    clock = sqlite3.connect(tmp_path / "clock.db")
    clock.executescript("""
        CREATE TABLE alarm (user_id INTEGER NOT NULL, daily BOOLEAN NOT NULL DEFAULT (False), start BOOLEAN NOT NULL DEFAULT (True),
                            alarm_1 INTEGER, alarm_2 INTEGER, status_2 BOOLEAN NOT NULL DEFAULT (True));
        INSERT INTO alarm VALUES (5, 1, 0, 20, 10, 1);
    """)
    clock.commit()
    assert migrate_sqlite.migrate(str(tmp_path), DSN, force=True)

    from sql import Clock, Users
    du, dc = Users(pool), Clock(pool)
    assert du.get_user_id(555) == 5  # внутренний номер сохранён — на него ссылаются файлы календарей
    assert dc.get_alarm(5) == (20, 10) and dc.get_daily(5) is True and dc.get_start(5) is False
    assert dc.get_changes(5) is True  # новая настройка включена и у перенесённых пользователей
    du.add_user(777)
    assert du.get_user_id(777) == 6
