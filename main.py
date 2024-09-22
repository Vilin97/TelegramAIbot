import logging
import os

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from telegram.ext.filters import REPLY, COMMAND, ChatType, Mention, Text

import ai
import database as db
import dnd
import utils
from utils import handle_errors


############### GLOBALS ##################
DEFAULTS = {"history": 50, "model": "gpt-4o-2024-08-06"} # twice cheaper than gpt-4o
BOT_USERNAME = "@VasChatGPTBot"
##########################################

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING
)


@handle_errors
async def show_help(update, context):
    await utils.show_help(update, context)


@handle_errors
async def reset_history(update, context):
    await db.reset_history(update, context)


@handle_errors
async def respond(update, context):
    prompt = utils.message_text(update, context)
    prompt = utils.prepend_username(update.message.from_user, prompt)

    await db.save_message_to_db(update, context, "user", prompt)
    content, tokens = await ai.generate_response(update, context)
    await update.message.reply_text(content + f"\n({tokens} tokens)")
    await db.save_message_to_db(update, context, "assistant", content)


@handle_errors
async def imagine(update, context):
    prompt = utils.message_text(update, context)
    if prompt:
        await ai.imagine(update, context, prompt)
    else:
        await update.message.reply_text("Please provide a prompt for the image.")


@handle_errors
async def reword_and_imagine(update, context):
    prompt = await ai.reword(update, context)
    await ai.imagine(update, context, prompt)


@handle_errors
async def settings(update, context):
    # if "/settings" called without args, show current settings
    if update.message.text.strip() == "/settings":
        model = await db.get_setting(update, context, "model")
        history = await db.get_setting(update, context, "history")
        conversation_history = await db.conversation_history(update, context)
        hisory_length = len(conversation_history)
        await update.message.reply_text(f"model={model}, history={history} ({hisory_length} messages total).")
    else:
        await db.update_settings(update, context)


@handle_errors
async def post_init(application):
    pool = await db.init_db()
    application.bot_data["db_pool"] = pool
    application.bot_data["defaults"] = DEFAULTS

    await application.bot.set_my_commands(
        [
            ("imagine", "Generate an image, e.g. /imagine panda. Takes ~15 seconds."),
            ("roll", "Roll dice, e.g. /roll 2d6."),
            ("reset", "Reset the conversation history."),
            ("help", "Show available commands and their descriptions."),
            ("settings", "Update model or history length, e.g. /settings history=30."),
        ]
    )


class BotReplyFilter(filters.MessageFilter):
    def filter(self, message):
        return (
            message.reply_to_message
            and message.reply_to_message.from_user.username == BOT_USERNAME
        )


if __name__ == "__main__":
    # Initialize the bot with the Telegram token
    application = (
        ApplicationBuilder()
        .token(os.getenv("TELEGRAM_TOKEN"))
        .post_init(post_init)
        .build()
    )

    # Add handlers
    application.add_handler(
        CommandHandler("imagine", reword_and_imagine, filters=REPLY)
    )
    application.add_handler(CommandHandler("imagine", imagine))
    application.add_handler(CommandHandler("settings", settings))
    application.add_handler(CommandHandler("help", show_help))
    application.add_handler(CommandHandler("reset", reset_history))
    application.add_handler(CommandHandler("roll", dnd.roll))

    # respond if being mentioned OR replied to OR in private chat
    reply_filter = Mention(BOT_USERNAME) | BotReplyFilter() | ChatType.PRIVATE
    application.add_handler(MessageHandler(reply_filter, respond))

    # Run the bot
    application.run_polling()
