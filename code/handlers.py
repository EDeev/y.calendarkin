from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, ContentType, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command

import wget, os

from init import *
from script import *

router = Router()


# ПРИВЕТСТВЕННОЕ СООБЩЕНИЕ
@router.message(Command('start', 'help'))
async def helps(msg: Message) -> None:
    tg_id = int(msg.chat.id)
    if not du.user_exists(tg_id):
        du.add_user(tg_id)

    buttons = [[InlineKeyboardButton(text="КОМАНДЫ", callback_data="com"),
                InlineKeyboardButton(text="АВТОР", callback_data="auth")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons, row_width=2)

    await msg.answer(text="<b>Я.Календаркин</b> - бот для оповещения о событиях из <b>Яндекс.Календаря</b>. "
                          "Для начала работы вам нужно всего лишь прислать в чат ссылку экспорта календаря в "
                          "<b>формате ICal</b>. После получения ссылки, бот начнёт оповещать о всех новых событиях "
                          "и появится возможность настройки оповещений. О том, какие команды есть для настройки, "
                          "вы можете ознакомиться по кнопке <b>КОМАНДЫ</b>", reply_markup=keyboard)


@router.callback_query(F.data == "auth")
async def author(call: CallbackQuery) -> None:
    await call.message.answer(text='<b>| АВТОР |</b>\n\n<b>>></b> Этот бот не коммерческий проект, для упрощенного '
                                   'получения уведомлений о событиях в Яндекс.Календаре. Не многим этот бот будет '
                                   'полезен, но людям, чья работа подразумевает его использование, он станет лишь '
                                   'удобным инструментом. Я же пишу подобные небольшие проекты, о которых вы можете '
                                   'узнать больше на моём <a href="https://github.com/IGlek">GitHub</a>.')


@router.callback_query(F.data == "com")
async def commands(call: CallbackQuery) -> None:
    await call.message.answer(text='<b>| КОМАНДЫ |</b>\n\n'
                                   '<b>/help</b> - вспомогательная функция для уточнения работы команд\n'
                                   '<b>/list</b> - список событий календаря, запланированных на сегодняшний день\n'
                                   '<b>/notif</b> - команда, отключающая рассылку уведомлений, даже при наличии событий в календаре\n'
                                   '<b>/daily</b> - оповещение в 8 утра по вашему часовому поясу со списком событий на день\n'
                                   '<b>/moment</b> - напоминание, приходящее в момент начала события\n\n'
                                   '<b>/get_alarm</b> - информация о времени на которое настроены оповещения\n'
                                   '<b>/edit_alarm</b> - изменение времени оповещений\n'
                                   '<b>/stop_alarm</b> - команда, отключающая второе оповещение о событии')


# КОМАНДЫ
@router.message(Command('list'))
async def check_list(msg: Message) -> None:
    user_id = du.get_user_id(int(msg.chat.id))

    if du.url_exists(user_id):
        txt = "<b>Имеющиеся события на сегодня</b>\n\n"

        lst_events = sorted(text_ical(user_id, du.get_tz(user_id)))
        today = dt_now(du.get_tz(user_id)).date()

        counter = 0
        for event in lst_events:
            if event[0] == today:
                counter += 1
                txt += message_form(counter, event[3])

        if counter: await msg.answer(text=txt, disable_web_page_preview=True)
        else: await msg.answer("<b>В данный момент</b> событий на сегодня найдено не было!")
    else: await msg.answer("Для отображения событий вы должны прислать ical-ссылку на календарь!")


@router.message(Command('notif'))
async def notif_up(msg: Message) -> None:
    user_id = du.get_user_id(int(msg.chat.id))

    if du.url_exists(user_id):
        if du.get_status(user_id): await msg.answer("Уведомления о событиях выключены!")
        else: await msg.answer("Уведомления о событиях включены!")

        du.update_status(user_id)
    else: await msg.answer("Для взаимодействия с событиями вы должны прислать ical-ссылку на календарь!")


@router.message(Command('daily'))
async def daily_up(msg: Message) -> None:
    user_id = du.get_user_id(int(msg.chat.id))

    if dc.clock_exists(user_id):
        if dc.get_daily(user_id): await msg.answer("Ежедневные утренние уведомления выключены!")
        else: await msg.answer("Ежедневные утренние уведомления включены!")

        dc.update_daily(user_id)
    else: await msg.answer("Для взаимодействия с событиями вы должны прислать ical-ссылку на календарь!")


@router.message(Command('moment'))
async def moment_up(msg: Message) -> None:
    user_id = du.get_user_id(int(msg.chat.id))

    if dc.clock_exists(user_id):
        if dc.get_start(user_id): await msg.answer("Уведомления в момент события выключены!")
        else: await msg.answer("Уведомления в момент события включены!")

        dc.update_start(user_id)
    else: await msg.answer("Для взаимодействия с событиями вы должны прислать ical-ссылку на календарь!")


@router.message(Command('get_alarm'))
async def alarm_get(msg: Message) -> None:
    user_id = du.get_user_id(int(msg.chat.id))

    if dc.clock_exists(user_id):
        alarms = dc.get_alarm(user_id)
        start = dc.get_start(user_id)
        status2 = dc.get_status2(user_id)

        txt = ""

        if status2: txt += "<b>У вас работает два оповещения"
        else: txt += "<b>У вас работает лишь первое оповещение"

        if start: txt += " и сообщение в момент начала события!</b>"
        else: txt += "!</b>"

        await msg.answer(txt + f"\n\n<b>Первое оповещение</b> приходит за {alarms[0]} минут\n"
                               f"<b>Второе оповещение</b> приходит за {alarms[1]} минут")
    else:
        await msg.answer("Для того, чтобы получить таймеры, вы должны прислать ical-ссылку на свой календарь!")


@router.message(Command('edit_alarm'))
async def alarm_edit(msg: Message) -> None:
    user_id = du.get_user_id(int(msg.chat.id))

    if dc.clock_exists(user_id):
        await msg.answer_photo(photo=FSInputFile(path="../data/photo_edit_alarm.jpg"),
                               caption="Для изменения времени вам надо в ответ на это сообщение прислать два "
                                       "числа через пробел: разница времени первого и второго таймера по ходу "
                                       "времени соответственно")
    else:
        await msg.answer("Для того, чтобы изменить таймеры, вы должны прислать ical-ссылку на свой календарь!")


@router.message(Command('stop_alarm'))
async def alarm_stop(msg: Message) -> None:
    user_id = du.get_user_id(int(msg.chat.id))

    if dc.clock_exists(user_id):
        if dc.get_status2(user_id): await msg.answer("Второе уведомление выключено!")
        else: await msg.answer("Второе уведомление включено!")

        dc.update_status2(user_id)
    else: await msg.answer("Для взаимодействия с событиями вы должны прислать ical-ссылку на календарь!")


# ЗАГРУЗКА ССЫЛКИ
@router.message(F.content_type == ContentType.TEXT)
async def downloading_file_ics(msg: Message) -> None:
    user_id = du.get_user_id(int(msg.chat.id))

    if msg.text[:5] == "https":
        try:
            wget.download(msg.text, f'../data/icals/{str(user_id)}_new.ics')

            try: os.remove(f'../data/icals/{str(user_id)}.ics')
            except FileNotFoundError: pass

            os.rename(f'../data/icals/{str(user_id)}_new.ics', f'../data/icals/{str(user_id)}.ics')

            time_zone = msg.text.split("=")[-1]
            if not du.url_exists(user_id):
                du.add_url(user_id, msg.text, time_zone)
                dc.add_clock(user_id)
            else:
                du.update_url(user_id, msg.text, time_zone)

            await msg.answer("Ссылка успешно добавлена! Уведомления уже включены!")
        except Exception:
            await msg.answer("Ошибка скачивания! Проверьте правильность ссылки и пришлите ещё раз")

    if (msg.reply_to_message is not None) and dc.clock_exists(user_id):
        text = "Для изменения времени вам надо в ответ на это сообщение прислать два числа через " \
               "пробел: разница времени первого и второго таймера по ходу времени соответственно"

        if msg.reply_to_message.caption == text:
            alarm_new = msg.text.split()

            if int(alarm_new[0]) < 60 and int(alarm_new[1]) < 60:
                dc.update_alarm1(user_id, int(alarm_new[0]))
                dc.update_alarm2(user_id, int(alarm_new[1]))

                await msg.answer("Время отправки уведомлений успешно обновлено!")
            else:
                await msg.answer("Время отправки уведомлений должно быть меньше 60 минут!")
