#!/usr/bin/env python3
import subprocess, os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

from dotenv import load_dotenv
from pathlib import Path


# Загружаем .env из той же директории, что скрипт
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в .env")

(
    MENU,
    ADD_INCOMING_ARGS,
    ADD_OUTGOING_ARGS,
    DELETE_ARGS
) = range(4)

def run_ansible(args_list):
    """Запуск ansible команды и возврат stdout/stderr"""
    cmd = ["ansible", "testansible", "-m", "command", "-a", f"/root/rt_many {' '.join(args_list)}"]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError as e:
        out = f"Ошибка: {e.output}"
    return out

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["Добавить входящий номер"],
        ["Добавить исходящий маршрут"],
        ["Удалить номер или маршрут"],
        ["Помощь"],
        ["Заново"]
    ]
    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Добавить входящий номер":
        await update.message.reply_text("Введите 2 аргумента через пробел (например: 7895 mtt)")
        return ADD_INCOMING_ARGS
    elif text == "Добавить исходящий маршрут":
        await update.message.reply_text("Введите 3 аргумента через пробел")
        return ADD_OUTGOING_ARGS
    elif text == "Удалить номер или маршрут":
        await update.message.reply_text("Введите 2 аргумента через пробел")
        return DELETE_ARGS
    elif text == "Помощь":
        # Запускаем скрипт с аргументом help
        output = run_ansible(["help"])
        await update.message.reply_text(f"Результат:\n{output}")
        return await start(update, context)
    elif text == "Заново":
        return await start(update, context)
    else:
        await update.message.reply_text("Неизвестная команда.")
        return MENU

async def add_incoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = update.message.text.split()
    if len(args) != 2:
        await update.message.reply_text("Нужно ровно 2 аргумента.")
    else:
        output = run_ansible(args)
        await update.message.reply_text(f"Результат:\n{output}")
    return await start(update, context)

async def add_outgoing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = update.message.text.split()
    if len(args) != 3:
        await update.message.reply_text("Нужно ровно 3 аргумента.")
    else:
        output = run_ansible(args)
        await update.message.reply_text(f"Результат:\n{output}")
    return await start(update, context)

async def delete_route(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = update.message.text.split()
    if len(args) != 2:
        await update.message.reply_text("Нужно ровно 2 аргумента.")
    else:
        output = run_ansible(args)
        await update.message.reply_text(f"Результат:\n{output}")
    return await start(update, context)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler)],
            ADD_INCOMING_ARGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_incoming)],
            ADD_OUTGOING_ARGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_outgoing)],
            DELETE_ARGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_route)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()
