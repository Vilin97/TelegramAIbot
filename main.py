import logging
import os
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

import helper_functions
import database as db

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


async def update_globals(update: Update, context):
    await helper_functions.update_globals_(update, context, GLOBALS)


async def send_debug_info(update, context):
    await helper_functions.send_debug_info_(update, context, db.conversation_history(update, context))


async def show_help(update: Update, context):
    await helper_functions.show_help_(update, context, GLOBALS)

# TODO: Wipe the chat history from the database. This will require a new database function.
async def reset_history(update: Update, context):
    await helper_functions.reset_history_(update, context, conversation_history)


async def generate_response(update, context):
    chat_id = update.message.chat_id
    conversation_history = db.conversation_history(update, context)

    # Send the entire conversation history to OpenAI
    response = await client.chat.completions.create(
        messages=conversation_history,
        model=GLOBALS[chat_id]["MODEL"],
    )
    reply = response.choices[0].message.content

    return reply


# Main function to define the bot response
async def respond(update: Update, context):
    chat_id = update.message.chat_id
    user = update.message.from_user
    message = helper_functions.prepend_username(user, update.message.text)

    await db.save_message_to_db(update, context, "user", message)

    try:
        reply = await generate_response(chat_id)

        await update.message.reply_text(reply)

        bot_user = context.bot
        bot_message = helper_functions.prepend_username(bot_user, reply)
        await db.save_message_to_db(update, context, "bot", bot_message)

        if GLOBALS[chat_id]["DEBUG"]:
            await send_debug_info(update, context)

    except Exception as e:
        error_message = f"Error with OpenAI API: {e}"
        logging.error(error_message)
        await update.message.reply_text(error_message)


async def on_startup(application):
    # Initialize the database connection pool
    pool = await db.init_db()
    # Store the pool in the bot's context
    application.bot_data["db_pool"] = pool


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

    # Set up post-init hook for database connection
    application.post_init(on_startup)

    # Run the bot
    application.run_polling()
