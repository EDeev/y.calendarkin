from pytz import timezone
import sqlite3


class Users:
    def __init__(self, database):
        """Подключаемся к БД и сохраняем курсор соединения"""
        self.connection = sqlite3.connect(database)
        self.cursor = self.connection.cursor()

    # КОМАНДЫ USER
    def user_exists(self, user_id):
        """Проверяем, есть ли уже пользователь в базе"""
        with self.connection:
            result = self.cursor.execute(f'SELECT * FROM `user` WHERE `user_id` = ?', (user_id,)).fetchall()
            return bool(len(result))

    def all_users(self):
        """Список айди"""
        with self.connection:
            return self.cursor.execute(f'SELECT `id` FROM `user`').fetchall()

    def add_user(self, user_id):
        """Добавляем нового пользователя"""
        with self.connection:
            return self.cursor.execute(f"INSERT INTO `user` (`user_id`) VALUES(?)", (user_id,))

    def get_user_id(self, user_id):
        """Получаем короткое айди юзера"""
        with self.connection:
            return self.cursor.execute(f'SELECT `id` FROM `user` WHERE `user_id` = ?', (user_id,)).fetchone()[0]

    def get_first_user_id(self, user_id):
        """Получаем длинное айди юзера"""
        with self.connection:
            return self.cursor.execute(f'SELECT `user_id` FROM `user` WHERE `id` = ?', (user_id,)).fetchone()[0]

    # КОМАНДЫ URL
    def url_exists(self, user_id):
        """Проверяем, есть ли данные уже в базе"""
        with self.connection:
            result = self.cursor.execute(f'SELECT * FROM `url` WHERE `user_id` = ?', (user_id,)).fetchall()
            return bool(len(result))

    def add_url(self, user_id, url_ical, time_zone):
        """Добавляем ссылку на календарь"""
        with self.connection:
            return self.cursor.execute(f"INSERT INTO `url` (`user_id`, `url_ical`, `time_zone`) VALUES(?, ?, ?)",
                                       (user_id, url_ical, time_zone))

    def update_status(self, user_id):
        """Обновляем статус рассылки уведомлений"""
        with self.connection:
            status = self.cursor.execute(f'SELECT `status` FROM `url` WHERE `user_id` = ?', (user_id,)).fetchone()[0]
            return self.cursor.execute("UPDATE `url` SET `status` = ? WHERE `user_id` = ?", (not status, user_id))

    def update_url(self, user_id, url_ical, time_zone):
        """Обновляем ссылку и часовой пояс в базе"""
        with self.connection:
            return self.cursor.execute("UPDATE `url` SET `url_ical` = ?, `time_zone` = ? WHERE `user_id` = ?",
                                       (url_ical, time_zone, user_id))

    def get_status(self, user_id):
        """Получаем статус работы"""
        with self.connection:
            return self.cursor.execute(f'SELECT `status` FROM `url` WHERE `user_id` = ?', (user_id,)).fetchone()[0]

    def get_url(self, user_id):
        """Получаем ссылку на календарь"""
        with self.connection:
            return self.cursor.execute(f'SELECT `url_ical` FROM `url` WHERE `user_id` = ?', (user_id,)).fetchone()[0]

    def get_tz(self, user_id):
        """Получаем указанный в календаре часовой пояс"""
        with self.connection:
            return timezone(self.cursor.execute(f'SELECT `time_zone` FROM `url` WHERE `user_id` = ?',
                                                (user_id,)).fetchone()[0])

    # ЗАКРЫТИЕ ВЫЗОВА
    def close(self):
        """Закрываем соединение с БД"""
        self.connection.close()


class Clock:
    def __init__(self, database):
        """Подключаемся к БД и сохраняем курсор соединения"""
        self.connection = sqlite3.connect(database)
        self.cursor = self.connection.cursor()

    # КОМАНДЫ ALARM
    def clock_exists(self, user_id):
        """Проверяем, есть ли данные уже в базе"""
        with self.connection:
            result = self.cursor.execute(f'SELECT * FROM `alarm` WHERE `user_id` = ?', (user_id,)).fetchall()
            return bool(len(result))

    def add_clock(self, user_id):
        """Добавляем параметры уведомления"""
        with self.connection:
            return self.cursor.execute(f"INSERT INTO `alarm` (`user_id`, `alarm_1`, `alarm_2`) VALUES(?, ?, ?)",
                                       (user_id, 15, 5))

    # КОМАНДЫ ПОЛУЧЕНИЯ ССЫЛОК
    def get_alarm(self, user_id):
        """Получаем задержки таймера"""
        with self.connection:
            return self.cursor.execute(f'SELECT `alarm_1`, `alarm_2` FROM `alarm` WHERE `user_id` = ?',
                                       (user_id,)).fetchone()

    def get_start(self, user_id):
        """Получаем статус уведомления в момент исполнения"""
        with self.connection:
            return self.cursor.execute(f'SELECT `start` FROM `alarm` WHERE `user_id` = ?', (user_id,)).fetchone()[0]

    def get_daily(self, user_id):
        """Получаем статус ежедневного уведомления"""
        with self.connection:
            return self.cursor.execute(f'SELECT `daily` FROM `alarm` WHERE `user_id` = ?', (user_id,)).fetchone()[0]

    def get_status2(self, user_id):
        """Получаем статус отправки второго уведомления"""
        with self.connection:
            return self.cursor.execute(f'SELECT `status_2` FROM `alarm` WHERE `user_id` = ?', (user_id,)).fetchone()[0]

    # КОМАНДЫ ОБНОВЛЕНИЯ БУЛЕВЫХ СТАТУСОВ
    def update_daily(self, user_id):
        """Обновляем статус ежедневного уведомления"""
        with self.connection:
            daily = self.cursor.execute(f'SELECT `daily` FROM `alarm` WHERE `user_id` = ?', (user_id,)).fetchone()[0]
            return self.cursor.execute("UPDATE `alarm` SET `daily` = ? WHERE `user_id` = ?", (not daily, user_id))

    def update_start(self, user_id):
        """Обновляем статус уведомления в момент исполнения"""
        with self.connection:
            start = self.cursor.execute(f'SELECT `start` FROM `alarm` WHERE `user_id` = ?', (user_id,)).fetchone()[0]
            return self.cursor.execute("UPDATE `alarm` SET `start` = ? WHERE `user_id` = ?", (not start, user_id))

    # КОМАНДЫ ОБНОВЛЕНИЯ ВРЕМЕННОГО ДИАПАЗОНА
    def update_alarm1(self, user_id, alarm_1):
        """Обновляем время первого оповещения"""
        with self.connection:
            return self.cursor.execute("UPDATE `alarm` SET `alarm_1` = ? WHERE `user_id` = ?", (alarm_1, user_id))

    def update_alarm2(self, user_id, alarm_2):
        """Обновляем время второго оповещения"""
        with self.connection:
            return self.cursor.execute("UPDATE `alarm` SET `alarm_2` = ? WHERE `user_id` = ?", (alarm_2, user_id))

    def update_status2(self, user_id):
        """Обновляем статус отправки второго уведомления"""
        with self.connection:
            status_2 = self.cursor.execute(f'SELECT `status_2` FROM `alarm` WHERE `user_id` = ?', (user_id,)).fetchone()[0]
            return self.cursor.execute("UPDATE `alarm` SET `status_2` = ? WHERE `user_id` = ?", (not status_2, user_id))

    # ЗАКРЫТИЕ ВЫЗОВА
    def close(self):
        """Закрываем соединение с БД"""
        self.connection.close()
