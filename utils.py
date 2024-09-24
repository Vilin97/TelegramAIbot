"""Utility functions for the bot."""

from telegram import Update
import logging
from functools import wraps
import re

def handle_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logging.exception(e)
    return wrapper


def message_text(update, context):
    message_text = update.message.text
    bot_username = context.bot.username
    stripped_text = re.sub(r'/\S+', '', message_text)
    stripped_text = re.sub(rf'@{bot_username}', '', stripped_text).strip()
    return stripped_text


def prepend_username(user, message):
    return f"{user.first_name} (@{user.username}): {message}"

async def show_help(update: Update, context):
    help_text = (
        "/help - Show available commands and their descriptions"
        "/imagine <prompt> - Generate an image based on prompt\n"
        "/ai <message> - Start a conversation with Компуктер\n"
        f"/settings key=value - Update model or history length (e.g. /settings model=gpt-4o /settings history=30). /settings without key and value will print the current settings.\n"
        "/reset - Reset the conversation history\n"
        "/roll XdY - Roll X dice with Y sides (e.g. /roll 2d6)\n"
    )
    await update.message.reply_text(help_text)
