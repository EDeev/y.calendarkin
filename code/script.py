from datetime import datetime, time
import icalendar

from dateutil.rrule import *
from dateutil.parser import *


def text_ical(user_id, tz):
    date = dt_now(tz)
    path = f'../data/icals/{user_id}.ics'

    e = open(path, 'rb')

    ecal = icalendar.Calendar.from_ical(e.read())
    events = []

    for i, component in enumerate(ecal.walk()):
        if component.name == "VEVENT":

            # НАЧАЛО
            dt = icalendar.vDDDTypes.to_ical(component.get('dtstart')).decode('utf-8')
            dt = dt.split("T")

            dt_start = component.decoded("dtstart")
            dt_end = component.decoded("dtend")

            if len(dt) == 1:
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
                list_rrule = [elem for elem in list_rrule if 'UNTIL' not in elem]

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

                event = {"name": component.get('summary'), "desc": desc if desc else "отсутствует",
                         "org": org if org else "не назначен", "datetime": [dt_start, dt_end]}

                events.append([dt_start.date(), dt_start.time(), i, event])
    e.close()

    return events


def message_form(k, event):
    txt = ""

    if k:
        txt += f"-------\n"
        txt += f"<b>{k}. {event['name']}</b>\n"
    else:
        txt += f"<b>{event['name']}</b>\n"

    txt += f"<b>Описание:</b> {event['desc']}\n"
    txt += f"<b>Организатор:</b> {event['org']}\n\n"
    txt += f"<b>Начало: {event['datetime'][0].strftime('%H:%M - %d.%m.%Y года')}</b>\n"
    txt += f"<b>Конец: {event['datetime'][1].strftime('%H:%M - %d.%m.%Y года')}</b>\n"

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
