import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
import subprocess
import os

TOKEN = os.environ["BOT_TOKEN"]
ERROR_LOGS_PATH = "logs/grabber_errors.log"
SPIDERS_SCRIPT_PATH = "compose/scrapy/scrapy-dev.sh"
CHAT_ID = os.environ["CHAT_ID"]
TOPIC_SUPPORT_ID = int(os.environ["TOPIC_SUPPORT_ID"])    # 1435

router = Router()
bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode="markdown"))


def cut_log(log: str) -> str:
    """
    Make log shorter if len > 4000
    """
    log = log.split("---SPLIT---")[-1]
    if len(log) > 4000:
        log = f"{log[:4001]}..."
    return log


@router.message(Command(commands=["start"]))
async def command_start_handler(*args, **kwargs) -> None:

    await bot.send_message(
        chat_id=CHAT_ID,
        message_thread_id=TOPIC_SUPPORT_ID,
        text="🕷️🕷️🕷️ Запуск спайдеров 🕷️🕷️🕷️"
    )
    try:
        subprocess.run(["sh", f"{SPIDERS_SCRIPT_PATH}"], check=True)

        with open(ERROR_LOGS_PATH) as file:
            error_log = file.read()

        error_log = cut_log(error_log)
        spider_1 = r'/╲/\(╭•̀ﮧ •́╮)/\╱\ '

        await bot.send_message(
            chat_id=CHAT_ID,
            message_thread_id=TOPIC_SUPPORT_ID,
            text=f"Спайдеры завершили свою работу {spider_1}\nError logs:\n```{error_log}```"
        )
    except subprocess.CalledProcessError as error:
        spider_2 = r"/╲/\╭[ ☉ ﹏ ☉ ]╮/\╱\ "
        await bot.send_message(
            chat_id=CHAT_ID,
            message_thread_id=TOPIC_SUPPORT_ID,
            text=f"{spider_2}\n{error}"
        )


async def main() -> None:
    dp = Dispatcher()
    dp.include_router(router)

    await command_start_handler()
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
