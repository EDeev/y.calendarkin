import os

from aiogram import Bot, Dispatcher
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.bot import DefaultBotProperties

from config import botToken
from sql import Users, Clock, connect

bot = Bot(token=botToken, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

pool = connect(os.getenv("DATABASE_URL", "postgresql://yacal:yacal@localhost:5432/yacal"))
du = Users(pool)
dc = Clock(pool)
