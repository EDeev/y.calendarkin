from datetime import datetime, time
import icalendar

from dateutil.relativedelta import *
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

                for i, elem in enumerate(list_rrule):
                    if 'UNTIL' in elem:
                        list_rrule.pop(i)

                now_date = "".join(date.date().isoformat().split("-"))

                until = "UNTIL=" + now_date + "T235900Z"
                date_iso = "".join(dt_start.isoformat().split("-"))
                time_iso = "".join(date_iso.split(":")).split("+")[0] + "Z"
                list_rrule.append(until)

                list_rrule = ";".join(list_rrule)
                print(dt_start.date(), list(rrulestr(list_rrule, dtstart=parse(time_iso))))


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


def recur_rule(create_date, now_date, rules):
    freq = rules['FREQ'][0]
    inter = rules['INTERVAL'][0]

    if 'UNTIL' in rules.keys():
        until = rules['UNTIL'][0]
        until = until if type(until) == type(now_date) else until.date()

        if until < now_date: return False

    count_day = now_date - create_date

    print(create_date, rules)
    print(freq, inter)

    if freq == 'DAILY':
        if count_day.days % inter == 0: return True

    elif freq == 'WEEKLY':
        weekday = now_date.strftime('%a').upper()[:2]
        days = rules['BYDAY']

        if weekday in days:
            week = count_day.days // 7  # получаем чётность недели
            if week % inter == 0: return True

    elif freq == 'MONTHLY':
        if 'BYMONTHDAY' in rules.keys():
            dates = list(rrule(MONTHLY, dtstart=create_date, interval=inter,
                               bymonthday=rules['BYMONTHDAY'][0], until=now_date))
            if now_date in dates: return True
        else:
            moment = rules['BYDAY'][0][:-2]
            day = rules['BYDAY'][0][-2:]

            dates = list(rrule(MONTHLY, dtstart=create_date, interval=inter,
                               byweekday=day(moment), until=now_date))
            if now_date in dates: return True

    elif freq == 'YEARLY':
        dates = list(rrule(YEARLY, dtstart=create_date, interval=inter, bymonth=rules['BYMONTH'][0],
                           bymonthday=rules['BYMONTHDAY'][0], until=now_date))
        if now_date in dates: return True

    return False
