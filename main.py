import logging
import os
from openai import OpenAI
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv

import helper_functions
import database as db

# Run `heroku config:get TOKEN_NAME` to get environment variables
# put them in .env in the format `TOKEN_NAME=value`
load_dotenv()

# TODO: move these globals to bot_data so it's available in `context`. Also, save them in the database.
#### globals that the user can change ####
GLOBALS = {
    "DEFAULT": {
        # Max number of messages to keep in conversation history
        "HISTORY": 30,
        # OpenAI API model to use: "gpt-4o" or "gpt-4o-mini"
        "MODEL": "gpt-4o",
        # print more in debug mode
        "DEBUG": False,
    }
}
##########################################


def load_system_prompt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return {"role": "system", "content": f.read().strip()}


#### Other globals #######################
# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BOT_USERNAME = "@VasChatGPTBot"
SYSTEM_PROMPT = load_system_prompt("system_prompt.txt")
##########################################

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING
)


async def update_globals(update, context):
    await helper_functions.update_globals(update, context, GLOBALS)


async def send_debug_info(update, context):
    await helper_functions.send_debug_info(
        update, context, db.conversation_history(update, context)
    )


async def show_help(update, context):
    await helper_functions.show_help(update, context, GLOBALS)


async def reset_history(update, context):
    await db.reset_history(update, context)


async def generate_response(update, context):
    chat_id = update.message.chat_id
    conversation_history = await db.conversation_history(update, context)

    if chat_id not in GLOBALS:
        GLOBALS[chat_id] = GLOBALS["DEFAULT"].copy()

    response = client.chat.completions.create(
        messages=conversation_history[-GLOBALS[chat_id]["HISTORY"] :],
        model=GLOBALS[chat_id]["MODEL"],
    )
    reply = response.choices[0].message.content

    return reply


# Main function to define the bot response
async def respond(update, context):
    chat_id = update.message.chat_id
    user = update.message.from_user
    message = helper_functions.prepend_username(user, update.message.text)

    await db.save_message_to_db(update, context, "user", message)

    try:
        reply = await generate_response(update, context)

        await update.message.reply_text(reply)

        bot_message = helper_functions.prepend_username(context.bot, reply)
        await db.save_message_to_db(update, context, "assistant", bot_message)

        if GLOBALS[chat_id]["DEBUG"]:
            await send_debug_info(update, context)

    except Exception as e:
        error_message = f"Error: {e}"
        logging.exception(error_message)
        await update.message.reply_text(error_message)


if __name__ == "__main__":
    # Initialize the bot with the Telegram token
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # Add handlers
    application.add_handler(CommandHandler(["ai"], respond))
    application.add_handler(CommandHandler(["settings"], update_globals))
    application.add_handler(CommandHandler(["help"], show_help))
    application.add_handler(CommandHandler(["reset"], reset_history))
    application.add_handler(MessageHandler(filters.REPLY & ~filters.COMMAND, respond))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE, respond))
    application.add_handler(MessageHandler(filters.Mention(BOT_USERNAME), respond))

    # Run the bot
    application.run_polling()
