import os

from aiogram import Bot, Dispatcher
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.bot import DefaultBotProperties

from config import botToken
from sql import Users, Clock

bot = Bot(token=botToken, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

os.makedirs("../db", exist_ok=True)
du = Users('../db/users.db')
dc = Clock('../db/clock.db')
