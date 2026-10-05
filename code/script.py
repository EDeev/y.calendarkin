import os
import re
from html import escape
from datetime import datetime, time
from urllib.parse import parse_qs, urlparse

import aiohttp
import icalendar
import pytz
from dateutil.parser import isoparse, parse
from dateutil.rrule import rrulestr

ICAL_DIR = "../data/icals"

# только экспорт Яндекс.Календаря: произвольная ссылка позволила бы заставить бота ходить по любым
# адресам, в том числе внутренним адресам сервера
YANDEX_HOST = re.compile(r"^calendar\.yandex\.(ru|com|by|kz|uz|com\.tr)$")


def parse_ical_url(url):
    """Проверяет ссылку экспорта и возвращает часовой пояс из неё или None, если ссылка не подходит"""
    parts = urlparse(url.strip())
    if parts.scheme != "https" or not YANDEX_HOST.match(parts.hostname or ""):
        return None

    tz = parse_qs(parts.query).get("tz_id", ["Europe/Moscow"])[0]
    return tz if tz in pytz.all_timezones_set else "Europe/Moscow"


async def download_ical(url, user_id):
    """Скачивает календарь, проверяет, что это iCal, и только потом заменяет старый файл"""
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, allow_redirects=False) as response:
            response.raise_for_status()
            data = await response.read()

    icalendar.Calendar.from_ical(data)  # бросит исключение, если пришёл не календарь

    os.makedirs(ICAL_DIR, exist_ok=True)
    path_new = f"{ICAL_DIR}/{user_id}_new.ics"
    with open(path_new, "wb") as f:
        f.write(data)
    os.replace(path_new, f"{ICAL_DIR}/{user_id}.ics")


def text_ical(user_id, tz):
    date = dt_now(tz)
    path = f"{ICAL_DIR}/{user_id}.ics"

    if not os.path.exists(path):
        return []

    with open(path, "rb") as e:
        ecal = icalendar.Calendar.from_ical(e.read())
    events = []

    for i, component in enumerate(ecal.walk()):
        if component.name == "VEVENT":

            # НАЧАЛО
            dt = icalendar.vDDDTypes.to_ical(component.get('dtstart')).decode('utf-8')
            dt = dt.split("T")

            dt_start = component.decoded("dtstart")
            dt_end = component.decoded("dtend")

            all_day = len(dt) == 1
            if all_day:
                dt_start = datetime.combine(dt_start, time(minute=1))
                dt_end = datetime.combine(dt_end, time(minute=1))
            else:
                dt_start.replace(tzinfo=None)
                dt_start = dt_start.astimezone(tz)

                dt_end.replace(tzinfo=None)
                dt_end = dt_end.astimezone(tz)

            # НАСТРОЙКА
            r_rule = component.get('rrule')
            if r_rule:
                list_rrule = icalendar.vRecur.to_ical(r_rule).decode('utf-8').split(';')

                until, u_flag = [elem for elem in list_rrule if 'UNTIL' in elem], True
                list_rrule = [elem for elem in list_rrule if 'UNTIL' not in elem]

                if until:
                    until_old = until[0].split('=')[1]
                    until = isoparse(until_old).replace(tzinfo=None)

                    if until.replace(tzinfo=None) <= date.replace(tzinfo=None):
                        until, u_flag = "UNTIL=" + until_utc(until_old, tz), False

                if u_flag:
                    until = "UNTIL=" + "".join(date.date().isoformat().split("-")) + "T235900Z"

                list_rrule.append(until)
                list_rrule = ";".join(list_rrule)

                date_iso = "".join(dt_start.isoformat().split("-"))
                iso = "".join(date_iso.split(":")).split("+")[0] + "Z"

                dates = list(map(lambda x: x.replace(tzinfo=None), list(rrulestr(list_rrule, dtstart=parse(iso)))))

                if dates:
                    dif = dt_end - dt_start

                    dt_start = dates[-1]
                    dt_end = dt_start + dif

            if date.date() == dt_start.date():
                org = component.get("organizer")
                desc = component.get("description")

                event = {"name": component.get('summary'), "desc": str(desc).strip() if desc else "",
                         "org": str(org).removeprefix("mailto:") if org else "", "all_day": all_day,
                         "datetime": [dt_start, dt_end]}

                events.append([dt_start.date(), dt_start.time(), i, event])

    return events


def until_utc(value, tz):
    """UNTIL в UTC: dateutil требует его, когда начало события задано с часовым поясом,
    а Яндекс иногда отдаёт UNTIL местным временем или просто датой"""
    if value.endswith("Z"):
        return value

    until = isoparse(value)
    if "T" not in value:  # только дата — повторения включительно по этот день
        until = until.replace(hour=23, minute=59, second=59)
    if until.tzinfo is None:
        until = tz.localize(until)
    return until.astimezone(pytz.utc).strftime("%Y%m%dT%H%M%SZ")


def message_form(k, event):
    txt = ""

    if k:
        txt += "-------\n"
        txt += f"<b>{k}. {escape(str(event['name']))}</b>\n"
    else:
        txt += f"<b>{escape(str(event['name']))}</b>\n"

    # пустые описание и организатора не показываем
    if event["desc"]:
        txt += f"<b>Описание:</b> {escape(event['desc'])}\n"
    if event["org"]:
        txt += f"<b>Организатор:</b> {escape(event['org'])}\n"

    # события всегда сегодняшние, поэтому дата не нужна — только время
    start, end = event["datetime"]
    if event["all_day"]:
        txt += "\n<b>Весь день</b>\n"
    elif end.date() != start.date():
        txt += f"\n<b>{start.strftime('%H:%M')} — {end.strftime('%d.%m %H:%M')}</b>\n"
    else:
        txt += f"\n<b>{start.strftime('%H:%M')} — {end.strftime('%H:%M')}</b>\n"

    return txt


def delta_time(d_event, start, end):
    d_start = datetime.combine(d_event.date(), time(hour=0, minute=start))
    d_end = datetime.combine(d_event.date(), time(hour=0, minute=end))

    zero = datetime.combine(d_event.date(), time(0, 0, 0, 0))

    dt_start = zero + (d_event - d_start)
    dt_end = zero + (d_event - d_end)

    return [dt_start.time(), dt_end.time()]


def dt_now(tz):
    return datetime.now(tz=tz)
