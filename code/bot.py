import logging, config, sql, asyncio, wget, os

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ParseMode

from datetime import datetime, time
from script import text_ical, message_form, dt_now, delta_time

# инициализируем токен
logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.TOKEN)
dp = Dispatcher(bot)

# инициализируем соединение с БД
du = sql.Users('../db/users.db')
dc = sql.Clock('../db/clock.db')


# ПРИВЕТСТВЕННОЕ СООБЩЕНИЕ
@dp.message_handler(commands=['start', 'help'])
async def helps(message: types.Message):
    tg_id = int(message.chat.id)
    if not du.user_exists(tg_id):
        du.add_user(tg_id)

    buttons = [types.InlineKeyboardButton(text="КОМАНДЫ", callback_data="com"),
               types.InlineKeyboardButton(text="АВТОР", callback_data="auth")]

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(*buttons)

    await message.answer(text="<b>Я.Календаркин</b> - бот для оповещения о событиях из <b>Яндекс.Календаря</b>. "
                              "Для начала работы вам нужно всего лишь прислать в чат ссылку экспорта календаря в "
                              "<b>формате ICal</b>. После получения ссылки, бот начнёт оповещать о всех новых событиях "
                              "и появится возможность настройки оповещений. О том, какие команды есть для настройки, "
                              "вы можете ознакомиться по кнопке <b>КОМАНДЫ</b>",
                         parse_mode=ParseMode.HTML, reply_markup=keyboard)


@dp.callback_query_handler(text="auth")
async def author(call: types.CallbackQuery):
    await call.message.answer(text='*| АВТОР |*\n\n*>>* Этот бот не коммерческий проект, для упрощенного получения '
                                   'уведомлений о событиях в Яндекс.Календаре. Не многим этот бот будет полезен, но '
                                   'людям, чья работа подразумевает его использование, он станет лишь удобным '
                                   'инструментом. Я же пишу подобные небольшие проекты, о которых вы можете узнать '
                                   'больше на моём [GitHub](https://github.com/IGlek).',
                              parse_mode=ParseMode.MARKDOWN)


@dp.callback_query_handler(text="com")
async def commands(call: types.CallbackQuery):
    await call.message.answer(text='<b>| КОМАНДЫ |</b>\n\n'
                                   '<b>/help</b> - вспомогательная функция для уточнения работы команд\n'
                                   '<b>/list</b> - список событий календаря, запланированных на сегодняшний день\n'
                                   '<b>/notif</b> - команда, отключающая рассылку уведомлений, даже при наличии событий в календаре\n'
                                   '<b>/daily</b> - оповещение в 8 утра по вашему часовому поясу со списком событий на день\n'
                                   '<b>/moment</b> - напоминание, приходящее в момент начала события\n\n'
                                   '<b>/get_alarm</b> - информация о времени на которое настроены оповещения\n'
                                   '<b>/edit_alarm</b> - изменение времени оповещений\n'
                                   '<b>/stop_alarm</b> - команда, отключающая второе оповещение о событии',
                              parse_mode=types.ParseMode.HTML)


# КОМАНДЫ
@dp.message_handler(commands=['list'])
async def check_list(message: types.Message):
    user_id = du.get_user_id(int(message.chat.id))

    if du.url_exists(user_id):
        txt = "<b>Имеющиеся события на сегодня</b>\n\n"

        lst_events = sorted(text_ical(user_id, du.get_tz(user_id)))
        today = dt_now(du.get_tz(user_id)).date()

        counter = 0
        for event in lst_events:
            if event[0] == today:
                counter += 1
                txt += message_form(counter, event[3])

        if counter:
            await message.answer(text=txt, parse_mode=ParseMode.HTML)
        else:
            await message.answer(text="<b>В данный момент</b> событий на сегодня найдено не было!",
                                 parse_mode=ParseMode.HTML)
    else:
        await message.answer("Для отображения событий вы должны прислать ical-ссылку на календарь!")


@dp.message_handler(commands=['notif'])
async def notif_up(message: types.Message):
    user_id = du.get_user_id(int(message.chat.id))

    if du.url_exists(user_id):
        if du.get_status(user_id):
            await message.answer("Уведомления о событиях выключены!")
        else:
            await message.answer("Уведомления о событиях включены!")

        du.update_status(user_id)
    else:
        await message.answer("Для взаимодействия с событиями вы должны прислать ical-ссылку на календарь!")


@dp.message_handler(commands=['daily'])
async def daily_up(message: types.Message):
    user_id = du.get_user_id(int(message.chat.id))

    if dc.clock_exists(user_id):
        if dc.get_daily(user_id):
            await message.answer("Ежедневные утренние уведомления выключены!")
        else:
            await message.answer("Ежедневные утренние уведомления включены!")

        dc.update_daily(user_id)
    else:
        await message.answer("Для взаимодействия с событиями вы должны прислать ical-ссылку на календарь!")


@dp.message_handler(commands=['moment'])
async def start_up(message: types.Message):
    user_id = du.get_user_id(int(message.chat.id))

    if dc.clock_exists(user_id):
        if dc.get_start(user_id):
            await message.answer("Уведомления в момент события выключены!")
        else:
            await message.answer("Уведомления в момент события включены!")

        dc.update_start(user_id)
    else:
        await message.answer("Для взаимодействия с событиями вы должны прислать ical-ссылку на календарь!")


@dp.message_handler(commands=['get_alarm'])
async def start_up(message: types.Message):
    user_id = du.get_user_id(int(message.chat.id))

    if dc.clock_exists(user_id):
        alarms = dc.get_alarm(user_id)
        start = dc.get_start(user_id)
        status2 = dc.get_status2(user_id)

        txt = ""

        if status2:
            txt += "<b>У вас работает два оповещения"
        else:
            txt += "<b>У вас работает лишь первое оповещение"

        if start:
            txt += " и сообщение в момент начала события!</b>"
        else:
            txt += "!</b>"

        await message.answer(text=(txt + f"\n\n<b>Первое оповещение</b> приходит за {alarms[0]} минут\n"
                                         f"<b>Второе оповещение</b> приходит за {alarms[1]} минут"),
                             parse_mode=ParseMode.HTML)
    else:
        await message.answer("Для того, чтобы получить таймеры, вы должны прислать ical-ссылку на свой календарь!")


@dp.message_handler(commands=['edit_alarm'])
async def start_up(message: types.Message):
    user_id = du.get_user_id(int(message.chat.id))

    if dc.clock_exists(user_id):
        await message.bot.send_photo(chat_id=message.chat.id, photo=open("../data/photo_edit_alarm.jpg", "rb"),
                                     caption="Для изменения времени вам надо в ответ на это сообщение прислать два "
                                             "числа через пробел: разница времени первого и второго таймера по ходу "
                                             "времени соответственно")
    else:
        await message.answer("Для того, чтобы изменить таймеры, вы должны прислать ical-ссылку на свой календарь!")


@dp.message_handler(commands=['stop_alarm'])
async def daily_up(message: types.Message):
    user_id = du.get_user_id(int(message.chat.id))

    if dc.clock_exists(user_id):
        if dc.get_status2(user_id):
            await message.answer("Второе уведомление выключено!")
        else:
            await message.answer("Второе уведомление включено!")

        dc.update_status2(user_id)
    else:
        await message.answer("Для взаимодействия с событиями вы должны прислать ical-ссылку на календарь!")


# ЗАГРУЗКА ССЫЛКИ
@dp.message_handler(content_types=['text'])
async def downloading_file_ics(message: types.Message):
    user_id = du.get_user_id(int(message.chat.id))

    if message.text[:5] == "https":
        try:
            wget.download(message.text, f'../data/icals/{str(user_id)}_new.ics')

            try:
                os.remove(f'../data/icals/{str(user_id)}.ics')
            except FileNotFoundError:
                pass

            os.rename(f'../data/icals/{str(user_id)}_new.ics', f'../data/icals/{str(user_id)}.ics')

            time_zone = message.text.split("=")[-1]
            if not du.url_exists(user_id):
                du.add_url(user_id, message.text, time_zone)
                dc.add_clock(user_id)
            else:
                du.update_url(user_id, message.text, time_zone)

            await message.answer("Ссылка успешно добавлена! Уведомления уже включены!")
        except Exception:
            await message.answer("Ошибка скачивания! Проверьте правильность ссылки и пришлите ещё раз")

    if 'reply_to_message' in message and dc.clock_exists(user_id):
        text = "Для изменения времени вам надо в ответ на это сообщение прислать два числа через " \
               "пробел: разница времени первого и второго таймера по ходу времени соответственно"

        if message.reply_to_message.caption == text:
            alarm_new = message.text.split()

            if int(alarm_new[0]) < 60 and int(alarm_new[1]) < 60:
                dc.update_alarm1(user_id, int(alarm_new[0]))
                dc.update_alarm2(user_id, int(alarm_new[1]))

                await message.answer("Время отправки уведомлений успешно обновлено!")
            else:
                await message.answer("Время отправки уведомлений должно быть меньше 60 минут!")


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
                                await bot.send_message(chat_id=tg_id, parse_mode=ParseMode.HTML,
                                                       text=f"<b>Событие начинается!</b>\n\n" + message_form(0, event[3]))

                            delta_alarm1 = delta_time(d_event, alarm[0], alarm[0] - 1)
                            if delta_alarm1[0] < time_check <= delta_alarm1[1]:
                                await bot.send_message(chat_id=tg_id, parse_mode=ParseMode.HTML,
                                                       text=f"<b>Напоминаю!</b>\n<i>Через {alarm[0]} минут "
                                                            f"будет событие:</i>\n\n{message_form(0, event[3])}")

                            if alarm2_status:
                                delta_alarm2 = delta_time(d_event, alarm[1], alarm[1] - 1)
                                if delta_alarm2[0] < time_check <= delta_alarm2[1]:
                                    await bot.send_message(chat_id=tg_id, parse_mode=ParseMode.HTML,
                                                           text=f"<b>Напоминаю!</b>\n<i>Через {alarm[1]} минут "
                                                                f"будет событие:</i>\n\n{message_form(0, event[3])}")

                    if daily and delta_daily1 <= time_check < delta_daily2:
                        if counter:
                            await bot.send_message(chat_id=tg_id, parse_mode=ParseMode.HTML,
                                                   text=txt)
                        else:
                            await bot.send_message(chat_id=tg_id, parse_mode=ParseMode.HTML,
                                                   text=f"Сегодня событий <b>нет</b>")


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


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(alarm(60))  # ПРОВЕРКА КАЖДУЮ 1 МИНУТУ
    loop.create_task(update(780))  # ПРОВЕРКА КАЖДУЮ 13 МИНУТУ
    executor.start_polling(dp, skip_updates=True)
