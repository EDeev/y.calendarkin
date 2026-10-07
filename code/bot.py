import asyncio
import logging
from datetime import datetime, time

from init import bot, dp, du, dc
import changes
from script import delta_time, download_ical, dt_now, message_form, read_ical, text_ical
from handlers import router


async def send(tg_id, text):
    await bot.send_message(chat_id=tg_id, disable_web_page_preview=True, text=text)


async def check_user(user_id):
    events = sorted(text_ical(user_id, du.get_tz(user_id)), key=lambda e: (e[0], e[1], e[2]))
    tg_id = str(du.get_first_user_id(user_id))

    start = dc.get_start(user_id)
    daily = dc.get_daily(user_id)
    alarm = dc.get_alarm(user_id)

    alarm2_status = dc.get_status2(user_id)

    today = dt_now(du.get_tz(user_id)).date()
    time_check = dt_now(du.get_tz(user_id)).time()

    # ДЛЯ DAILY
    counter = 0
    txt = "<b>События сегодня</b>\n\n"

    delta_daily1 = time(hour=8, minute=0)
    delta_daily2 = time(hour=8, minute=1)
    # --------------------------------

    for event in events:
        if event[0] == today:
            d_event = datetime.combine(today, event[1])

            if daily and delta_daily1 <= time_check < delta_daily2:
                counter += 1
                txt += message_form(counter, event[3])

            # для событий на весь день напоминания по времени не шлём
            if event[3]["all_day"]:
                continue

            delta_start = delta_time(d_event, 1, 0)
            if start and delta_start[0] < time_check <= delta_start[1]:
                await send(tg_id, "<b>Событие начинается!</b>\n\n" + message_form(0, event[3]))

            delta_alarm1 = delta_time(d_event, alarm[0], alarm[0] - 1)
            if delta_alarm1[0] < time_check <= delta_alarm1[1]:
                await send(tg_id, f"<b>Напоминаю!</b>\n<i>Через {alarm[0]} минут "
                                  f"будет событие:</i>\n\n{message_form(0, event[3])}")

            if alarm2_status:
                delta_alarm2 = delta_time(d_event, alarm[1], alarm[1] - 1)
                if delta_alarm2[0] < time_check <= delta_alarm2[1]:
                    await send(tg_id, f"<b>Напоминаю!</b>\n<i>Через {alarm[1]} минут "
                                      f"будет событие:</i>\n\n{message_form(0, event[3])}")

    if daily and delta_daily1 <= time_check < delta_daily2:
        if counter:
            await send(tg_id, txt)
        else:
            await send(tg_id, "Сегодня событий <b>нет</b>")


# ПРОВЕРКА НА СОБЫТИЕ
async def alarm(wait_for):
    while True:
        await asyncio.sleep(wait_for)

        for (user_id,) in du.all_users():
            # ошибка у одного пользователя (заблокировал бота, битый календарь) не должна
            # останавливать рассылку остальным и весь бот
            try:
                if dc.clock_exists(user_id) and du.get_status(user_id):
                    await check_user(user_id)
            except Exception:
                logging.exception("Ошибка проверки событий пользователя %s", user_id)


async def update(wait_for):
    while True:
        await asyncio.sleep(wait_for)

        for (user_id,) in du.all_users():
            try:
                if not (du.url_exists(user_id) and du.get_status(user_id)):
                    continue
                old = read_ical(user_id)
                new = await download_ical(du.get_url(user_id), user_id)
            except Exception as err:
                # при сбое остаётся прошлая версия календаря
                logging.warning("Не удалось обновить календарь пользователя %s: %s", user_id, err)
                continue

            try:
                if old and old != new and dc.clock_exists(user_id) and dc.get_changes(user_id):
                    text = changes.report(old, new, du.get_tz(user_id))
                    if text:
                        await send(str(du.get_first_user_id(user_id)), text)
            except Exception:
                logging.exception("Ошибка уведомления об изменениях пользователя %s", user_id)


async def main() -> None:
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


async def process() -> None:
    await asyncio.gather(main(),  # ЗАПУСК ОСНОВНОЙ ПРОГРАММЫ
                         alarm(60),  # ПРОВЕРКА КАЖДУЮ 1 МИНУТУ
                         update(780))  # ПРОВЕРКА КАЖДУЮ 13 МИНУТУ


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    try: asyncio.run(process())
    except KeyboardInterrupt: pass
