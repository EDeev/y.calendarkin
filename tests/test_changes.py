from datetime import datetime, timedelta

import pytz

import changes

TZ = pytz.timezone("Europe/Moscow")
NOW = TZ.localize(datetime(2026, 10, 7, 12, 0))  # среда


def ics(*events):
    body = "\r\n".join(events)
    return ("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//EN\r\n" + body + "\r\nEND:VCALENDAR\r\n").encode()


def vevent(uid, start, minutes=60, summary="Встреча", extra=""):
    end = start + timedelta(minutes=minutes)
    return (f"BEGIN:VEVENT\r\nUID:{uid}\r\nDTSTAMP:20261007T090000Z\r\n"
            f"DTSTART;TZID=Europe/Moscow:{start:%Y%m%dT%H%M%S}\r\nDTEND;TZID=Europe/Moscow:{end:%Y%m%dT%H%M%S}\r\n"
            f"SUMMARY:{summary}\r\n{extra}END:VEVENT")


def at(day, hour, minute=0):
    return datetime(2026, 10, day, hour, minute)


def report(old, new):
    return changes.report(ics(*old), ics(*new), TZ, now=NOW)


def test_no_changes_and_dtstamp_ignored():
    event = vevent("a", at(8, 10))
    assert report([event], [event.replace("DTSTAMP:20261007T090000Z", "DTSTAMP:20261007T091300Z")]) is None


def test_renamed_event_is_not_reported():
    assert report([vevent("a", at(8, 10), summary="Старое")], [vevent("a", at(8, 10), summary="Новое")]) is None


def test_added_event():
    text = report([], [vevent("a", at(8, 10), summary="Созвон <важный> & срочный")])
    assert text.startswith("<b>Изменения в календаре</b>")
    assert "<b>Новое событие:</b> Созвон &lt;важный&gt; &amp; срочный" in text
    assert "чт 08.10 10:00 — 11:00" in text


def test_past_events_are_ignored():
    # Яндекс выгружает всю историю: правка старого события не должна приходить уведомлением
    assert report([], [vevent("old", at(1, 10))]) is None
    assert report([vevent("old", at(1, 10))], []) is None
    assert report([vevent("old", at(1, 10))], [vevent("old", at(2, 10))]) is None


def test_event_in_progress_counts_as_upcoming():
    assert "Удалено" in report([vevent("now", at(7, 11, 30))], [])


def test_deleted_event():
    text = report([vevent("a", at(9, 15), summary="Планёрка")], [])
    assert "<b>Удалено:</b> Планёрка\n<s>пт 09.10 15:00 — 16:00</s>" in text


def test_moved_event():
    text = report([vevent("a", at(8, 10), summary="Планёрка")], [vevent("a", at(9, 14, 30), summary="Планёрка")])
    assert "<b>Перенесено:</b> Планёрка\nбыло: чт 08.10 10:00 — 11:00\nстало: пт 09.10 14:30 — 15:30" in text


def test_moved_from_past_to_future():
    assert "Перенесено" in report([vevent("a", at(6, 10))], [vevent("a", at(12, 10))])


def test_all_day_event():
    event = ("BEGIN:VEVENT\r\nUID:day\r\nDTSTART;VALUE=DATE:20261010\r\nDTEND;VALUE=DATE:20261011\r\n"
             "SUMMARY:Выходной\r\nEND:VEVENT")
    assert "сб 10.10, весь день" in report([], [event])

    today = event.replace("20261010", "20261007").replace("20261011", "20261008")
    assert "ср 07.10, весь день" in report([today], [])  # день ещё не закончился


def test_recurring_occurrence_deleted():
    weekly = vevent("w", at(1, 9), summary="Стендап", extra="RRULE:FREQ=WEEKLY\r\n")
    without = weekly.replace("RRULE:FREQ=WEEKLY\r\n", "RRULE:FREQ=WEEKLY\r\nEXDATE;TZID=Europe/Moscow:20261015T090000\r\n")
    text = report([weekly], [without])
    assert "<b>Удалено:</b> Стендап\n<s>чт 15.10 09:00 — 10:00</s>" in text
    assert "повторяется" not in text


def test_recurring_occurrence_moved_and_moved_back():
    weekly = vevent("w", at(1, 9), summary="Стендап", extra="RRULE:FREQ=WEEKLY\r\n")
    override = vevent("w", at(15, 11), summary="Стендап", extra="RECURRENCE-ID;TZID=Europe/Moscow:20261015T090000\r\n")

    text = report([weekly], [weekly, override])
    assert "было: чт 15.10 09:00 — 10:00\nстало: чт 15.10 11:00 — 12:00" in text

    text = report([weekly, override], [weekly])
    assert "было: чт 15.10 11:00 — 12:00\nстало: чт 15.10 09:00 — 10:00" in text


def test_recurring_override_deleted():
    override = vevent("w", at(15, 11), extra="RECURRENCE-ID;TZID=Europe/Moscow:20261015T090000\r\n")
    weekly = vevent("w", at(1, 9), extra="RRULE:FREQ=WEEKLY\r\n")
    without = weekly.replace("RRULE:FREQ=WEEKLY\r\n", "RRULE:FREQ=WEEKLY\r\nEXDATE;TZID=Europe/Moscow:20261015T090000\r\n")
    text = report([weekly, override], [without])
    assert text.count("Удалено") == 1 and "чт 15.10 11:00 — 12:00" in text


def test_recurring_series():
    weekly = vevent("w", at(1, 9), summary="Стендап", extra="RRULE:FREQ=WEEKLY\r\n")
    assert "чт 01.10 09:00 — 10:00, повторяется" in report([], [weekly])
    assert "Удалено" in report([weekly], [])

    ended = vevent("e", at(1, 9), extra="RRULE:FREQ=WEEKLY;UNTIL=20261005T060000Z\r\n")
    assert report([ended], []) is None


def test_many_changes_are_capped():
    text = report([], [vevent(f"e{i}", at(10, 8) + timedelta(hours=i)) for i in range(13)])
    assert text.count("Новое событие") == changes.MAX_ITEMS
    assert text.endswith("…и ещё 3")
    assert text.index("08:00") < text.index("09:00")  # по времени события


def test_floating_time_uses_calendar_zone():
    event = "BEGIN:VEVENT\r\nUID:f\r\nDTSTART:20261008T100000\r\nDTEND:20261008T110000\r\nSUMMARY:X\r\nEND:VEVENT"
    assert "чт 08.10 10:00 — 11:00" in report([], [event])
