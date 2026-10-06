"""Перенос данных Я.Календаркина из SQLite (users.db, clock.db) в PostgreSQL.

    python scripts/migrate_sqlite.py --sqlite-dir /path/to/db --dsn postgresql://…

Внутренние номера пользователей сохраняются: на них ссылаются файлы календарей data/icals/<номер>.ics.
"""
import argparse
import os
import sqlite3
import sys

import psycopg

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))
from sql import SCHEMA  # noqa: E402


def migrate(sqlite_dir, dsn, force=False):
    users_db = sqlite3.connect(os.path.join(sqlite_dir, "users.db"))
    clock_db = sqlite3.connect(os.path.join(sqlite_dir, "clock.db"))

    users = users_db.execute("SELECT id, user_id FROM user ORDER BY id").fetchall()
    urls = users_db.execute("SELECT user_id, status, url_ical, time_zone FROM url").fetchall()
    alarms = clock_db.execute("SELECT user_id, daily, start, alarm_1, alarm_2, status_2 FROM alarm").fetchall()
    known = {u[0] for u in users}

    with psycopg.connect(dsn) as conn:
        conn.execute(SCHEMA)
        if conn.execute("SELECT count(*) FROM users").fetchone()[0]:
            if not force:
                raise SystemExit("В PostgreSQL уже есть данные — перенос остановлен (--force очистит таблицы)")
            conn.execute("TRUNCATE users, urls, alarms RESTART IDENTITY CASCADE")
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO users (id, tg_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", users)
            cur.executemany("INSERT INTO urls (user_id, status, url_ical, time_zone) VALUES (%s, %s, %s, %s) "
                            "ON CONFLICT DO NOTHING",
                            [(u, bool(s), url, tz) for u, s, url, tz in urls if u in known])
            cur.executemany("INSERT INTO alarms (user_id, daily, start, alarm_1, alarm_2, status_2) "
                            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                            [(u, bool(d), bool(s), a1, a2, bool(s2)) for u, d, s, a1, a2, s2 in alarms if u in known])
            cur.execute("SELECT setval(pg_get_serial_sequence('users', 'id'), GREATEST((SELECT max(id) FROM users), 1))")
        report = {name: (src, conn.execute(f"SELECT count(*) FROM {name}").fetchone()[0])
                  for name, src in (("users", len(users)), ("urls", len(urls)), ("alarms", len(alarms)))}

    for name, (src, dst) in report.items():
        print(f"{name:7} SQLite {src:>5}  PostgreSQL {dst:>5}  {'ok' if src == dst else 'MISMATCH'}")
    return all(a == b for a, b in report.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--sqlite-dir", required=True)
    parser.add_argument("--dsn", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    sys.exit(0 if migrate(args.sqlite_dir, args.dsn, args.force) else 1)


if __name__ == "__main__":
    main()
