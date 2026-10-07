import logging
import os

from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, ContentType, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command

from init import du, dc
from script import ICAL_DIR, download_ical, dt_now, message_form, parse_ical_url, text_ical

router = Router()

NO_LINK = "Для взаимодействия с событиями вы должны прислать ical-ссылку на календарь! Как её получить — /link"

EDIT_ALARM_TEXT = ("Для изменения времени вам надо в ответ на это сообщение прислать два числа через пробел: "
                   "разница времени первого и второго таймера по ходу времени соответственно")


def user_id_of(msg: Message) -> int:
    """Короткий id пользователя; заводит запись, если человек пишет боту, не нажав /start"""
    tg_id = int(msg.chat.id)
    if not du.user_exists(tg_id):
        du.add_user(tg_id)
    return du.get_user_id(tg_id)


# ПРИВЕТСТВЕННОЕ СООБЩЕНИЕ
@router.message(Command('start', 'help'))
async def helps(msg: Message) -> None:
    user_id_of(msg)

    buttons = [[InlineKeyboardButton(text="КОМАНДЫ", callback_data="com"),
                InlineKeyboardButton(text="АВТОР", callback_data="auth")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await msg.answer(text="<b>Я.Календаркин</b> - бот для оповещения о событиях из <b>Яндекс.Календаря</b>. "
                          "Для начала работы вам нужно всего лишь прислать в чат ссылку экспорта календаря в "
                          "<b>формате ICal</b> (как её получить — /link). После получения ссылки, бот начнёт "
                          "оповещать о всех новых событиях и появится возможность настройки оповещений. О том, "
                          "какие команды есть для настройки, вы можете ознакомиться по кнопке <b>КОМАНДЫ</b>",
                     reply_markup=keyboard)


@router.callback_query(F.data == "auth")
async def author(call: CallbackQuery) -> None:
    await call.message.answer(text='<b>| АВТОР |</b>\n\n<b>>></b> Этот бот не коммерческий проект, для упрощенного '
                                   'получения уведомлений о событиях в Яндекс.Календаре. Не многим этот бот будет '
                                   'полезен, но людям, чья работа подразумевает его использование, он станет лишь '
                                   'удобным инструментом. Я же пишу подобные небольшие проекты, о которых вы можете '
                                   'узнать больше на моём <a href="https://github.com/EDeev">GitHub</a>.')


@router.callback_query(F.data == "com")
async def commands(call: CallbackQuery) -> None:
    await call.message.answer(text='<b>| КОМАНДЫ |</b>\n\n'
                                   '<b>/help</b> - вспомогательная функция для уточнения работы команд\n'
                                   '<b>/link</b> - как получить ссылку на календарь (прислать её можно в любой момент)\n'
                                   '<b>/list</b> - список событий календаря, запланированных на сегодняшний день\n'
                                   '<b>/notif</b> - команда, отключающая рассылку уведомлений, даже при наличии событий в календаре\n'
                                   '<b>/daily</b> - оповещение в 8 утра по вашему часовому поясу со списком событий на день\n'
                                   '<b>/moment</b> - напоминание, приходящее в момент начала события\n'
                                   '<b>/changes</b> - уведомления о новых, удалённых и перенесённых событиях\n\n'
                                   '<b>/get_alarm</b> - информация о времени на которое настроены оповещения\n'
                                   '<b>/edit_alarm</b> - изменение времени оповещений\n'
                                   '<b>/stop_alarm</b> - команда, отключающая второе оповещение о событии\n\n'
                                   '<b>/unsubscribe</b> - удалить подписку на календарь')


# КОМАНДЫ
@router.message(Command('link'))
async def link_help(msg: Message) -> None:
    await msg.answer("<b>Как получить ссылку</b>\n\n"
                     "1. Откройте Яндекс.Календарь в браузере и наведите на нужный календарь в списке слева\n"
                     "2. Нажмите на шестерёнку → <b>Экспорт</b>\n"
                     "3. Выберите формат <b>iCal</b> и скопируйте ссылку\n"
                     "4. Пришлите её сюда — в любой момент, новая ссылка заменит старую")


@router.message(Command('unsubscribe'))
async def unsubscribe(msg: Message) -> None:
    user_id = user_id_of(msg)

    if du.url_exists(user_id):
        du.delete_url(user_id)
        dc.delete_clock(user_id)
        try: os.remove(f"{ICAL_DIR}/{user_id}.ics")
        except FileNotFoundError: pass

        await msg.answer("Подписка на календарь удалена, уведомлений больше не будет. "
                         "Чтобы подписаться снова, пришлите ссылку.")
    else: await msg.answer("Подписки на календарь нет.")


@router.message(Command('list'))
async def check_list(msg: Message) -> None:
    user_id = user_id_of(msg)

    if du.url_exists(user_id):
        txt = "<b>Имеющиеся события на сегодня</b>\n\n"

        lst_events = sorted(text_ical(user_id, du.get_tz(user_id)), key=lambda e: (e[0], e[1], e[2]))
        today = dt_now(du.get_tz(user_id)).date()

        counter = 0
        for event in lst_events:
            if event[0] == today:
                counter += 1
                txt += message_form(counter, event[3])

        if counter: await msg.answer(text=txt, disable_web_page_preview=True)
        else: await msg.answer("<b>В данный момент</b> событий на сегодня найдено не было!")
    else: await msg.answer(NO_LINK)


@router.message(Command('notif'))
async def notif_up(msg: Message) -> None:
    user_id = user_id_of(msg)

    if du.url_exists(user_id):
        if du.get_status(user_id): await msg.answer("Уведомления о событиях выключены!")
        else: await msg.answer("Уведомления о событиях включены!")

        du.update_status(user_id)
    else: await msg.answer(NO_LINK)


@router.message(Command('daily'))
async def daily_up(msg: Message) -> None:
    user_id = user_id_of(msg)

    if dc.clock_exists(user_id):
        if dc.get_daily(user_id): await msg.answer("Ежедневные утренние уведомления выключены!")
        else: await msg.answer("Ежедневные утренние уведомления включены!")

        dc.update_daily(user_id)
    else: await msg.answer(NO_LINK)


@router.message(Command('moment'))
async def moment_up(msg: Message) -> None:
    user_id = user_id_of(msg)

    if dc.clock_exists(user_id):
        if dc.get_start(user_id): await msg.answer("Уведомления в момент события выключены!")
        else: await msg.answer("Уведомления в момент события включены!")

        dc.update_start(user_id)
    else: await msg.answer(NO_LINK)


@router.message(Command('changes'))
async def changes_up(msg: Message) -> None:
    user_id = user_id_of(msg)

    if dc.clock_exists(user_id):
        if dc.get_changes(user_id): await msg.answer("Уведомления об изменениях в календаре выключены!")
        else: await msg.answer("Уведомления об изменениях в календаре включены!")

        dc.update_changes(user_id)
    else: await msg.answer(NO_LINK)


@router.message(Command('get_alarm'))
async def alarm_get(msg: Message) -> None:
    user_id = user_id_of(msg)

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
        await msg.answer(NO_LINK)


@router.message(Command('edit_alarm'))
async def alarm_edit(msg: Message) -> None:
    user_id = user_id_of(msg)

    if dc.clock_exists(user_id):
        await msg.answer_photo(photo=FSInputFile(path="../data/photo_edit_alarm.jpg"), caption=EDIT_ALARM_TEXT)
    else:
        await msg.answer(NO_LINK)


@router.message(Command('stop_alarm'))
async def alarm_stop(msg: Message) -> None:
    user_id = user_id_of(msg)

    if dc.clock_exists(user_id):
        if dc.get_status2(user_id): await msg.answer("Второе уведомление выключено!")
        else: await msg.answer("Второе уведомление включено!")

        dc.update_status2(user_id)
    else: await msg.answer(NO_LINK)


# ЗАГРУЗКА ССЫЛКИ И ИЗМЕНЕНИЕ ВРЕМЕНИ ОПОВЕЩЕНИЙ
@router.message(F.content_type == ContentType.TEXT)
async def downloading_file_ics(msg: Message) -> None:
    user_id = user_id_of(msg)

    if msg.text.startswith("http"):
        url = msg.text.strip()
        time_zone = parse_ical_url(url)
        if time_zone is None:
            await msg.answer("Это не ссылка экспорта Яндекс.Календаря. Как её получить — /link")
            return

        try:
            await download_ical(url, user_id)
        except Exception as err:
            logging.warning("Не удалось скачать календарь пользователя %s: %s", user_id, err)
            await msg.answer("Ошибка скачивания! Проверьте правильность ссылки и пришлите ещё раз")
            return

        if not du.url_exists(user_id):
            du.add_url(user_id, url, time_zone)
            dc.add_clock(user_id)
        else:
            du.update_url(user_id, url, time_zone)

        await msg.answer("Ссылка успешно добавлена! Уведомления уже включены!")
        return

    if msg.reply_to_message is not None and msg.reply_to_message.caption == EDIT_ALARM_TEXT \
            and dc.clock_exists(user_id):
        alarm_new = msg.text.split()

        if len(alarm_new) != 2 or not all(x.isdigit() for x in alarm_new):
            await msg.answer("Пришлите два числа через пробел, например: <b>15 5</b>")
        elif all(0 < int(x) < 60 for x in alarm_new):
            dc.update_alarm1(user_id, int(alarm_new[0]))
            dc.update_alarm2(user_id, int(alarm_new[1]))

            await msg.answer("Время отправки уведомлений успешно обновлено!")
        else:
            await msg.answer("Время отправки уведомлений должно быть от 1 до 59 минут!")
        return

    await msg.answer("Не понял сообщение. Пришлите ссылку на календарь (/link) или посмотрите команды — /help")
