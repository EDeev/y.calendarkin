"""Уведомления об изменениях в календаре: новые, удалённые и перенесённые события.

При каждом обновлении календаря старая и новая выгрузки сравниваются по UID события.
Отдельное вхождение повторяющегося события Яндекс выгружает так: перенос — отдельным VEVENT
с тем же UID и RECURRENCE-ID (исходное время), удаление — датой в EXDATE основного события.
Яндекс отдаёт всю историю календаря, поэтому прошедшие события не учитываются."""
from datetime import date, datetime, timedelta
from html import escape

import icalendar
import pytz

MAX_ITEMS = 10
WEEKDAYS = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")


def _norm(value, tz):
    """Дата остаётся датой, время приводится к часовому поясу календаря"""
    if isinstance(value, datetime):
        if value.tzinfo is None:  # «плавающее» время — считаем временем календаря
            value = tz.localize(value)
        return value.astimezone(tz)
    return value


def _exdates(component, tz):
    raw = component.get("exdate")
    if raw is None:
        return set()
    lists = raw if isinstance(raw, list) else [raw]
    return {_norm(item.dt, tz) for lst in lists for item in lst.dts}


def snapshot(data, tz):
    """События выгрузки: {(UID, исходное время вхождения или None): описание}"""
    events = {}
    for component in icalendar.Calendar.from_ical(data).walk("VEVENT"):
        if component.get("dtstart") is None:
            continue
        start = _norm(component.decoded("dtstart"), tz)
        if component.get("dtend") is not None:
            end = _norm(component.decoded("dtend"), tz)
        elif component.get("duration") is not None:
            end = start + component.decoded("duration")
        else:
            end = start + timedelta(days=1) if not isinstance(start, datetime) else start

        rrule = component.get("rrule")
        until = rrule.get("UNTIL") if rrule else None
        rid = _norm(component.decoded("recurrence-id"), tz) if component.get("recurrence-id") is not None else None

        events[(str(component.get("uid", "")), rid)] = {
            "name": str(component.get("summary", "")).strip() or "Без названия",
            "start": start, "end": end, "all_day": not isinstance(start, datetime),
            "recurring": rrule is not None, "until": _norm(until[0], tz) if until else None,
            "exdates": _exdates(component, tz),
        }
    return events


def _after(value, now):
    """Момент value ещё не наступил (для дат — день не закончился)"""
    if isinstance(value, datetime):
        return value > now
    return value >= now.date()


def _upcoming(event, now):
    if event["recurring"]:
        return event["until"] is None or _after(event["until"], now)
    end = event["end"]
    if event["all_day"] and isinstance(end, date) and not isinstance(end, datetime):
        end -= timedelta(days=1)  # DTEND у событий на весь день — следующий день
    return _after(end, now)


def diff(old, new, now):
    """Список изменений: (вид, событие, прежнее событие или None); вид — added, deleted, moved"""
    changes = []

    for key, event in new.items():
        uid, rid = key
        before = old.get(key)
        if before is not None:
            moved = (before["start"], before["end"]) != (event["start"], event["end"])
            if moved and (_upcoming(before, now) or _upcoming(event, now)):
                changes.append(("moved", event, before))
            elif event["recurring"]:
                # удалённые вхождения повторяющегося события
                for day in sorted(event["exdates"] - before["exdates"], key=str):
                    if (uid, day) not in new and (uid, day) not in old and _after(day, now):
                        changes.append(("deleted", _occurrence(event, day), None))
            continue

        if rid is not None and (uid, None) in old:
            # вхождение повторяющегося события изменили отдельно — важно, только если сдвинули время
            if event["start"] != rid and (_after(rid, now) or _after(event["start"], now)):
                changes.append(("moved", event, _occurrence(old[(uid, None)], rid)))
        elif _upcoming(event, now):
            changes.append(("added", event, None))

    for key, event in old.items():
        if key in new:
            continue
        uid, rid = key
        if rid is not None and (uid, None) in new:
            master = new[(uid, None)]
            if rid in master["exdates"]:
                if _after(event["start"], now):
                    changes.append(("deleted", event, None))
            elif event["start"] != rid and (_after(rid, now) or _after(event["start"], now)):
                changes.append(("moved", _occurrence(master, rid), event))  # вернули на исходное время
        elif _upcoming(event, now):
            changes.append(("deleted", event, None))

    changes.sort(key=lambda c: _sort_key(c[1]["start"]))
    return changes


def _occurrence(master, start):
    """Отдельное вхождение повторяющегося события, начинающееся в start"""
    return {**master, "start": start, "end": start + (master["end"] - master["start"]),
            "recurring": False, "exdates": set()}


def _sort_key(value):
    if isinstance(value, datetime):
        return value.astimezone(pytz.utc).replace(tzinfo=None)
    return datetime.combine(value, datetime.min.time())


def when(event):
    """Когда событие: «чт 08.10 10:00 — 11:00», «чт 08.10, весь день»"""
    start, end = event["start"], event["end"]
    day = f"{WEEKDAYS[start.weekday()]} {start:%d.%m}"
    if event["all_day"]:
        last = end - timedelta(days=1) if end > start else start
        text = f"{day}, весь день" if last == start else f"{day} — {WEEKDAYS[last.weekday()]} {last:%d.%m}, весь день"
    elif end.date() != start.date():
        text = f"{day} {start:%H:%M} — {WEEKDAYS[end.weekday()]} {end:%d.%m %H:%M}"
    else:
        text = f"{day} {start:%H:%M} — {end:%H:%M}"
    return text + (", повторяется" if event["recurring"] else "")


def report(old_data, new_data, tz, now=None):
    """Текст уведомления об изменениях между двумя выгрузками или None, если важных изменений нет"""
    now = now or datetime.now(tz)
    changes = diff(snapshot(old_data, tz), snapshot(new_data, tz), now)
    if not changes:
        return None

    parts = []
    for kind, event, before in changes[:MAX_ITEMS]:
        name = escape(event["name"])
        if kind == "added":
            parts.append(f"<b>Новое событие:</b> {name}\n{when(event)}")
        elif kind == "deleted":
            parts.append(f"<b>Удалено:</b> {name}\n<s>{when(event)}</s>")
        else:
            parts.append(f"<b>Перенесено:</b> {name}\nбыло: {when(before)}\nстало: {when(event)}")
    if len(changes) > MAX_ITEMS:
        parts.append(f"…и ещё {len(changes) - MAX_ITEMS}")

    return "<b>Изменения в календаре</b>\n\n" + "\n\n".join(parts)
