import logging
import os
from openai import OpenAI
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv

import helper_functions
from helper_functions import handle_errors
import database as db

if os.environ.get("ENV") != "production":
    load_dotenv()


def load_prompt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()


############### GLOBALS ##################
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEFAULTS = {"history": 30, "model": "gpt-4o"}
BOT_USERNAME = "@VasChatGPTBot"
SYSTEM_PROMPT = load_prompt("system_prompt.txt")
REWORD_PROMPT = load_prompt("reword_prompt.txt")
##########################################

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING
)


@handle_errors
async def show_help(update, context):
    await helper_functions.show_help(update, context)


@handle_errors
async def reset_history(update, context):
    await db.reset_history(update, context)


@handle_errors
async def get_setting(update, context, setting_name):
    return await db.get_setting(update, context, setting_name, DEFAULTS)


async def generate_response_(update, context):
    conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    conversation_history += await db.conversation_history(update, context)

    history = int(await get_setting(update, context, "history"))
    model = await get_setting(update, context, "model")

    response = client.chat.completions.create(
        messages=conversation_history[-history:],
        model=model,
    )
    reply = response.choices[0].message.content

    return reply


@handle_errors
async def respond(update, context):
    user = update.message.from_user
    prompt = update.message.text.replace(BOT_USERNAME, "").strip()
    prompt = helper_functions.prepend_username(user, prompt)
    await db.save_message_to_db(update, context, "user", prompt)
    reply = await generate_response_(update, context)
    await update.message.reply_text(reply)
    await db.save_message_to_db(update, context, "assistant", reply)


async def imagine_(update, context, prompt):
    response = client.images.generate(
        prompt=prompt,
        model="dall-e-3",  # dall-e-2 works worse
        size="1024x1024",  # higher quality costs more
        quality="standard",  # "hd" costs twice more
    )
    image_url = response.data[0].url
    revised_prompt = response.data[0].revised_prompt
    await update.message.reply_photo(image_url, caption=revised_prompt)


@handle_errors
async def imagine(update, context):
    prompt = update.message.text
    prompt = prompt.replace("/imagine", "").replace(BOT_USERNAME, "").strip()
    if prompt:
        await imagine_(update, context, prompt)
    else:
        await update.message.reply_text("Please provide a prompt for the image.")


@handle_errors
async def reword_and_imagine(update, context):
    original_message_text = update.message.reply_to_message.text
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": REWORD_PROMPT},
            {"role": "user", "content": original_message_text},
        ],
        model=DEFAULTS["model"],
    )
    # prevent further rewording to avoid losing the original meaning
    prompt = (
        "DO NOT add any detail, just use this prompt AS-IS: "
        + response.choices[0].message.content
    )

    await imagine_(update, context, prompt)


@handle_errors
async def settings(update, context):
    # if "/settings" called without args, show current settings
    if update.message.text.strip() == "/settings":
        model = await get_setting(update, context, "model")
        history = await get_setting(update, context, "history")
        await update.message.reply_text(f"Current model={model}, history={history}")
    else:
        await db.update_settings(update, context)


@handle_errors
async def post_init(application):
    pool = await db.init_db()
    application.bot_data["db_pool"] = pool

    await application.bot.set_my_commands(
        [
            ("imagine", "Generate an image, e.g. /imagine a panda in space"),
            ("reset", "Reset the conversation history"),
            ("help", "Show available commands and their descriptions"),
        ]
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
    reply_imagine_filter = filters.REPLY & filters.Text(
        ["/imagine", f"/imagine{BOT_USERNAME}"]
    )
    application.add_handler(MessageHandler(reply_imagine_filter, reword_and_imagine))
    application.add_handler(CommandHandler(["imagine"], imagine))
    application.add_handler(CommandHandler(["ai"], respond))
    application.add_handler(CommandHandler(["settings"], settings))
    application.add_handler(CommandHandler(["help"], show_help))
    application.add_handler(CommandHandler(["reset"], reset_history))

    application.add_handler(MessageHandler(filters.REPLY & ~filters.COMMAND, respond))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE, respond))
    application.add_handler(MessageHandler(filters.Mention(BOT_USERNAME), respond))

    # Run the bot
    application.run_polling()
