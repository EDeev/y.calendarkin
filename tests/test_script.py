from datetime import datetime, timedelta

import pytz

import script

TZ = pytz.timezone("Europe/Moscow")


def make_ics(events):
    body = "\r\n".join(events)
    return ("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//EN\r\n" + body + "\r\nEND:VCALENDAR\r\n").encode()


def vevent(uid, start, end, summary, extra=""):
    return (f"BEGIN:VEVENT\r\nUID:{uid}\r\nDTSTART;TZID=Europe/Moscow:{start:%Y%m%dT%H%M%S}\r\n"
            f"DTEND;TZID=Europe/Moscow:{end:%Y%m%dT%H%M%S}\r\nSUMMARY:{summary}\r\n{extra}END:VEVENT")


def test_parse_ical_url_accepts_only_yandex_export():
    ok = "https://calendar.yandex.ru/export/ics.xml?private_token=abc&tz_id=Asia/Krasnoyarsk"
    assert script.parse_ical_url(ok) == "Asia/Krasnoyarsk"
    assert script.parse_ical_url("https://calendar.yandex.ru/export/ics.xml?private_token=abc") == "Europe/Moscow"
    assert script.parse_ical_url("https://calendar.yandex.ru/x?tz_id=Not/AZone") == "Europe/Moscow"
    for bad in ("http://calendar.yandex.ru/export/ics.xml", "https://127.0.0.1/ics", "file:///etc/passwd",
                "https://calendar.yandex.ru.evil.com/ics", "https://example.com/?tz_id=Europe/Moscow"):
        assert script.parse_ical_url(bad) is None, bad


def test_text_ical_today_events_and_recurrence(tmp_path, monkeypatch):
    monkeypatch.setattr(script, "ICAL_DIR", str(tmp_path))
    now = datetime.now(TZ).replace(tzinfo=None, second=0, microsecond=0)
    today = now.replace(hour=10, minute=0)

    events = [
        vevent("once", today, today + timedelta(hours=1), "Разовое <важное> & срочное",
               "DESCRIPTION:Описание\r\nORGANIZER:mailto:boss@example.com\r\n"),
        vevent("weekly", today.replace(hour=12) - timedelta(weeks=3),
               today.replace(hour=13) - timedelta(weeks=3), "Еженедельное", "RRULE:FREQ=WEEKLY\r\n"),
        vevent("tomorrow", today + timedelta(days=1), today + timedelta(days=1, hours=1), "Завтра"),
    ]
    (tmp_path / "1.ics").write_bytes(make_ics(events))

    found = {e[3]["name"]: e for e in script.text_ical(1, TZ)}
    assert set(found) == {"Разовое <важное> & срочное", "Еженедельное"}
    assert found["Еженедельное"][1].hour == 12

    text = script.message_form(1, found["Разовое <важное> & срочное"][3])
    assert "&lt;важное&gt; &amp; срочное" in text
    assert "boss@example.com" in text and "mailto:" not in text
    assert "10:00 — 11:00" in text and str(now.year) not in text


def test_message_form_hides_empty_fields():
    event = {"name": "Встреча", "desc": "", "org": "", "all_day": False,
             "datetime": [datetime(2026, 1, 1, 9, 0), datetime(2026, 1, 1, 9, 30)]}
    text = script.message_form(0, event)
    assert "Описание" not in text and "Организатор" not in text
    assert "09:00 — 09:30" in text


def test_missing_calendar_file_gives_no_events(tmp_path, monkeypatch):
    monkeypatch.setattr(script, "ICAL_DIR", str(tmp_path))
    assert script.text_ical(42, TZ) == []


def test_until_not_in_utc(tmp_path, monkeypatch):
    # повторяющиеся события с UNTIL местным временем или датой раньше роняли разбор календаря
    monkeypatch.setattr(script, "ICAL_DIR", str(tmp_path))
    now = datetime.now(TZ).replace(tzinfo=None, second=0, microsecond=0)
    first = now.replace(hour=9, minute=0) - timedelta(weeks=5)
    events = [
        vevent("ended-local", first, first + timedelta(hours=1), "Закончилось",
               f"RRULE:FREQ=WEEKLY;UNTIL={first + timedelta(weeks=2):%Y%m%dT%H%M%S}\r\n"),
        vevent("ended-date", first, first + timedelta(hours=1), "Закончилось датой",
               f"RRULE:FREQ=WEEKLY;UNTIL={first + timedelta(weeks=2):%Y%m%d}\r\n"),
        vevent("running", first, first + timedelta(hours=1), "Идёт",
               f"RRULE:FREQ=WEEKLY;UNTIL={now + timedelta(weeks=4):%Y%m%dT%H%M%S}\r\n"),
    ]
    (tmp_path / "2.ics").write_bytes(make_ics(events))

    names = {e[3]["name"] for e in script.text_ical(2, TZ)}
    assert names == {"Идёт"}
    assert script.until_utc("20260101", TZ) == "20260101T205959Z"
