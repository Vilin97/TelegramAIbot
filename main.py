import logging
import os
from openai import OpenAI
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv

import helper_functions
import database as db

if os.environ.get("ENV") != "production":
    load_dotenv()

DEFAULTS = {
    # Max number of messages to keep in conversation history
    "history": 30,
    # OpenAI API model to use: "gpt-4o" or "gpt-4o-mini"
    "model": "gpt-4o",
}


def load_system_prompt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return {"role": "system", "content": f.read().strip()}


#### Other globals #######################
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BOT_USERNAME = "@VasChatGPTBot"
SYSTEM_PROMPT = load_system_prompt("system_prompt.txt")
##########################################

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING
)


async def update_settings(update, context):
    await db.update_settings(update, context)


async def show_help(update, context):
    await helper_functions.show_help(update, context)


async def reset_history(update, context):
    await db.reset_history(update, context)


async def get_setting(update, context, setting_name):
    return await db.get_setting(update, context, setting_name, DEFAULTS)


async def generate_response(update, context):

    conversation_history = await db.conversation_history(update, context)
    history = int(await get_setting(update, context, "history"))
    model = await get_setting(update, context, "model")

    response = client.chat.completions.create(
        messages=conversation_history[-history:],
        model=model,
    )
    reply = response.choices[0].message.content

    return reply


# Main function to define the bot response
async def respond(update, context):
    user = update.message.from_user
    prompt = update.message.text.replace(BOT_USERNAME, "").strip()
    prompt = helper_functions.prepend_username(user, prompt)

    await db.save_message_to_db(update, context, "user", prompt)

    try:
        reply = await generate_response(update, context)

        await update.message.reply_text(reply)

        await db.save_message_to_db(update, context, "assistant", reply)

    except Exception as e:
        error_message = f"Error: {e}"
        logging.exception(error_message)
        await update.message.reply_text(error_message)


async def respond_with_image(update, context):
    prompt = update.message.text.replace("/imagine", "").replace(BOT_USERNAME, "").strip()

    try:
        response = client.images.generate(
            prompt=prompt,
            model="dall-e-3",   # dall-e-2 works worse
            size="1024x1024",   # higher quality costs more
            quality="standard", # "hd" costs twice more 
        )

        image_url = response.data[0].url
        revised_prompt = response.data[0].revised_prompt

        await update.message.reply_photo(image_url, caption=revised_prompt)

    except Exception as e:
        error_message = f"Error: {e}"
        logging.exception(error_message)
        await update.message.reply_text(error_message)

async def post_init(application):
    pool = await db.init_db()
    application.bot_data["db_pool"] = pool

    await application.bot.set_my_commands(
        [
            ("imagine", "Generate an image, e.g. /imagine a panda in space"),
            ("reset", "Reset the conversation history"),
            # ("help", "Show available commands and their descriptions"),
            # ("ai", "Summon AI"),
            # ("settings", "Update settings like model=gpt-4o and history=30"),
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
    application.add_handler(CommandHandler(["imagine"], respond_with_image))
    application.add_handler(CommandHandler(["ai"], respond))
    application.add_handler(CommandHandler(["settings"], update_settings))
    application.add_handler(CommandHandler(["help"], show_help))
    application.add_handler(CommandHandler(["reset"], reset_history))
    application.add_handler(MessageHandler(filters.REPLY & ~filters.COMMAND, respond))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE, respond))
    application.add_handler(MessageHandler(filters.Mention(BOT_USERNAME), respond))

    # Run the bot
    application.run_polling()
