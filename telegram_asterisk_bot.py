#!/usr/bin/env python3
import os
import shlex
import subprocess
from pathlib import Path

import httpx
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в .env")

allowed_raw = os.getenv("ALLOWED_USER_IDS", "").strip()
ALLOWED_USER_IDS = {
    int(value.strip()) for value in allowed_raw.split(",") if value.strip()
}

ROUTE_SCRIPT = BASE_DIR / "rt_many"
PJSIP_SCRIPT = BASE_DIR / "pjsip_trunk_upsert"

(
    MENU,
    ADD_INCOMING_ARGS,
    ADD_OUTGOING_ARGS,
    DELETE_ARGS,
    ADD_TRUNK_ARGS,
    ADD_IP_TRUNK_ARGS,
    DELETE_TRUNK_ARGS,
) = range(7)


def build_ipv6_request() -> HTTPXRequest:
    """Create a Telegram client bound to the server's working IPv6 route."""
    transport = httpx.AsyncHTTPTransport(
        local_address="::",
        retries=3,
        limits=httpx.Limits(
            max_connections=64,
            max_keepalive_connections=16,
            keepalive_expiry=30.0,
        ),
    )
    return HTTPXRequest(
        connection_pool_size=64,
        connect_timeout=15.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=10.0,
        httpx_kwargs={"transport": transport},
    )


def is_allowed(update: Update) -> bool:
    user = update.effective_user
    return bool(user) and (not ALLOWED_USER_IDS or user.id in ALLOWED_USER_IDS)


async def reject_if_needed(update: Update) -> bool:
    if is_allowed(update):
        return False
    if update.effective_message:
        await update.effective_message.reply_text("Доступ запрещён.")
    return True


def run_script(script: Path, args: list[str]) -> str:
    if not script.is_file():
        return f"Ошибка: скрипт {script} не найден"
    try:
        result = subprocess.run(
            [str(script), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=45,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "Ошибка: скрипт не завершился за 45 секунд"
    output = result.stdout.strip() or "Команда завершена без вывода"
    if result.returncode:
        return f"Ошибка (код {result.returncode}):\n{output}"
    return output


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await reject_if_needed(update):
        return ConversationHandler.END
    keyboard = [
        ["Добавить транк с регистрацией"],
        ["Добавить транк без регистрации"],
        ["Удалить транк"],
        ["Добавить входящий номер"],
        ["Добавить исходящий маршрут"],
        ["Удалить номер или маршрут"],
        ["Помощь"],
        ["Заново"],
    ]
    await update.effective_message.reply_text(
        "Выберите действие:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return MENU


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await reject_if_needed(update):
        return ConversationHandler.END
    text = update.effective_message.text
    if text == "Добавить транк с регистрацией":
        await update.effective_message.reply_text(
            "Введите 5 аргументов: имя_транка хост логин пароль контекст\n"
            "Пример: provider1 203.0.113.10 sip-login sip-password from-provider1"
        )
        return ADD_TRUNK_ARGS
    if text == "Добавить транк без регистрации":
        await update.effective_message.reply_text(
            "Введите 3 аргумента: имя_транка хост контекст\n"
            "Пример: provider-ip 203.0.113.20 from-provider-ip"
        )
        return ADD_IP_TRUNK_ARGS
    if text == "Удалить транк":
        await update.effective_message.reply_text(
            "Введите 2 аргумента: имя_транка remove\n"
            "Пример: provider1 remove"
        )
        return DELETE_TRUNK_ARGS
    if text == "Добавить входящий номер":
        await update.effective_message.reply_text(
            "Введите номер и направление.\n"
            "Примеры:\n"
            "7895 mtt\n"
            "7895 mts\n"
            "7895 from-provider — добавит номер прямо в этот контекст extensions.conf"
        )
        return ADD_INCOMING_ARGS
    if text == "Добавить исходящий маршрут":
        await update.effective_message.reply_text("Введите 3 аргумента")
        return ADD_OUTGOING_ARGS
    if text == "Удалить номер или маршрут":
        await update.effective_message.reply_text("Введите 2 аргумента")
        return DELETE_ARGS
    if text == "Помощь":
        output = run_script(ROUTE_SCRIPT, ["help"])
        await update.effective_message.reply_text(
            "PJSIP с регистрацией: имя_транка хост логин пароль контекст\n"
            "PJSIP без регистрации: имя_транка хост контекст\n\n"
            "Удаление PJSIP-транка: имя_транка remove\n\n"
            f"{output}"
        )
        return await start(update, context)
    if text == "Заново":
        return await start(update, context)
    await update.effective_message.reply_text("Неизвестная команда.")
    return MENU


async def run_route_with_count(update: Update, context: ContextTypes.DEFAULT_TYPE, count: int):
    if await reject_if_needed(update):
        return ConversationHandler.END
    args = update.effective_message.text.split()
    if len(args) != count:
        await update.effective_message.reply_text(f"Нужно ровно {count} аргумента(ов).")
    else:
        output = run_script(ROUTE_SCRIPT, args)
        await update.effective_message.reply_text(f"Результат:\n{output}")
    return await start(update, context)


async def add_incoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await run_route_with_count(update, context, 2)


async def add_outgoing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await run_route_with_count(update, context, 3)


async def delete_route(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await run_route_with_count(update, context, 2)


async def add_trunk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await reject_if_needed(update):
        return ConversationHandler.END
    try:
        args = shlex.split(update.effective_message.text)
    except ValueError as exc:
        await update.effective_message.reply_text(f"Ошибка в кавычках: {exc}")
        return ADD_TRUNK_ARGS
    if len(args) != 5:
        await update.effective_message.reply_text("Нужно ровно 5 аргументов.")
        return ADD_TRUNK_ARGS

    # The message contains a SIP password. Try to remove it from the chat.
    try:
        await update.effective_message.delete()
    except Exception:
        pass

    output = run_script(PJSIP_SCRIPT, args)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Результат:\n{output}",
    )
    return await start(update, context)


async def add_ip_trunk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await reject_if_needed(update):
        return ConversationHandler.END
    try:
        args = shlex.split(update.effective_message.text)
    except ValueError as exc:
        await update.effective_message.reply_text(f"Ошибка в кавычках: {exc}")
        return ADD_IP_TRUNK_ARGS
    if len(args) != 3:
        await update.effective_message.reply_text("Нужно ровно 3 аргумента.")
        return ADD_IP_TRUNK_ARGS

    output = run_script(PJSIP_SCRIPT, args)
    await update.effective_message.reply_text(f"Результат:\n{output}")
    return await start(update, context)


async def delete_trunk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await reject_if_needed(update):
        return ConversationHandler.END
    try:
        args = shlex.split(update.effective_message.text)
    except ValueError as exc:
        await update.effective_message.reply_text(f"Ошибка в кавычках: {exc}")
        return DELETE_TRUNK_ARGS
    if len(args) != 2 or args[1] != "remove":
        await update.effective_message.reply_text(
            "Нужно ровно 2 аргумента: имя_транка remove"
        )
        return DELETE_TRUNK_ARGS

    output = run_script(PJSIP_SCRIPT, args)
    await update.effective_message.reply_text(f"Результат:\n{output}")
    return await start(update, context)


def main() -> None:
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .request(build_ipv6_request())
        .get_updates_request(build_ipv6_request())
        .build()
    )
    conversation = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler)],
            ADD_INCOMING_ARGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_incoming)],
            ADD_OUTGOING_ARGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_outgoing)],
            DELETE_ARGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_route)],
            ADD_TRUNK_ARGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_trunk)],
            ADD_IP_TRUNK_ARGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ip_trunk)],
            DELETE_TRUNK_ARGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_trunk)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    app.add_handler(conversation)
    app.run_polling()


if __name__ == "__main__":
    main()
