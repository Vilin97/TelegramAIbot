# utils.py
import re
import logging
from functools import wraps


def handle_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logging.exception(e)
    return wrapper


def message_text(message, bot):
    content = message.content
    bot_username = bot.user.name
    content = re.sub(rf'@\b{bot_username}\b', '', content).strip()
    return content


def get_username(user):
    return user.name


def prepend_username(user, message):
    return f"{user.display_name} ({get_username(user)}): {message}"


async def show_help(ctx):
    help_text = (
        "!help - Show available commands and their descriptions\n"
        "!imagine <prompt> - Generate an image based on prompt\n"
        "!settings key=value - "
        "Update model or history length (e.g. !settings model=gpt-4o)\n"
        "!reset - Reset the conversation history\n"
        "!roll XdY - Roll X dice with Y sides (e.g. !roll 2d6)\n"
        "!delete - Reply to a message with this command to delete it\n"
    )
    await ctx.reply(help_text)
