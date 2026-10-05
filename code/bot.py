import asyncio, logging, time, wget, os

from init import *
from script import *
from handlers import router


# ПРОВЕРКА НА СОБЫТИЕ
async def alarm(wait_for):
    while True:
        await asyncio.sleep(wait_for)

        users_id = du.all_users()
        for user_id in users_id:
            user_id = user_id[0]

            if dc.clock_exists(user_id):
                if du.get_status(user_id):
                    events = sorted(text_ical(user_id, du.get_tz(user_id)))
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

                            delta_start = delta_time(d_event, 1, 0)
                            if start and delta_start[0] < time_check <= delta_start[1]:
                                await bot.send_message(chat_id=tg_id, disable_web_page_preview=True,
                                                       text=f"<b>Событие начинается!</b>\n\n" + message_form(0, event[3]))

                            delta_alarm1 = delta_time(d_event, alarm[0], alarm[0] - 1)
                            if delta_alarm1[0] < time_check <= delta_alarm1[1]:
                                await bot.send_message(chat_id=tg_id, disable_web_page_preview=True,
                                                       text=f"<b>Напоминаю!</b>\n<i>Через {alarm[0]} минут "
                                                            f"будет событие:</i>\n\n{message_form(0, event[3])}")

                            if alarm2_status:
                                delta_alarm2 = delta_time(d_event, alarm[1], alarm[1] - 1)
                                if delta_alarm2[0] < time_check <= delta_alarm2[1]:
                                    await bot.send_message(chat_id=tg_id, disable_web_page_preview=True,
                                                           text=f"<b>Напоминаю!</b>\n<i>Через {alarm[1]} минут "
                                                                f"будет событие:</i>\n\n{message_form(0, event[3])}")

                    if daily and delta_daily1 <= time_check < delta_daily2:
                        if counter:
                            await bot.send_message(chat_id=tg_id, disable_web_page_preview=True, text=txt)
                        else:
                            await bot.send_message(chat_id=tg_id, disable_web_page_preview=True, text=f"Сегодня событий <b>нет</b>")


async def update(wait_for):
    while True:
        await asyncio.sleep(wait_for)

        users_id = du.all_users()
        for user_id in users_id:
            user_id = user_id[0]

            if du.url_exists(user_id):
                if du.get_status(user_id):
                    wget.download(du.get_url(user_id), f'../data/icals/{str(user_id)}_new.ics')

                    os.remove(f'../data/icals/{str(user_id)}.ics')
                    os.rename(f'../data/icals/{str(user_id)}_new.ics', f'../data/icals/{str(user_id)}.ics')


async def main() -> None:
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(), skipUpdates=True)


async def process() -> None:
    await asyncio.gather(main(),  # ЗАПУСК ОСНОВНОЙ ПРОГРАММЫ
                         alarm(60),  # ПРОВЕРКА КАЖДУЮ 1 МИНУТУ
                         update(780))  # ПРОВЕРКА КАЖДУЮ 13 МИНУТУ


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    try: asyncio.run(process())
    except KeyboardInterrupt: pass
