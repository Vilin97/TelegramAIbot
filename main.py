import logging
import os
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

import helper_functions

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
conversation_history = {}
##########################################

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING
)


async def update_globals(update: Update, context):
    await helper_functions.update_globals_(update, context, GLOBALS)


async def send_debug_info(update, context):
    await helper_functions.send_debug_info_(update, context, conversation_history)


async def show_help(update: Update, context):
    await helper_functions.show_help_(update, context, GLOBALS)


async def reset_history(update: Update, context):
    await helper_functions.reset_history_(update, context, conversation_history)


def update_conversation_history(chat_id, message, role):
    if chat_id not in conversation_history:
        conversation_history[chat_id] = [SYSTEM_PROMPT]
        GLOBALS[chat_id] = GLOBALS["DEFAULT"].copy()

    # Add the message to the conversation history
    conversation_history[chat_id].append(
        {
            "role": role,
            "content": message,
        }
    )

    # Limit the history length
    if len(conversation_history[chat_id]) > GLOBALS[chat_id]["HISTORY"]:
        conversation_history[chat_id] = conversation_history[chat_id][
            -GLOBALS[chat_id]["HISTORY"] :
        ]


def generate_response(chat_id):
    # Send the entire conversation history to OpenAI
    response = client.chat.completions.create(
        messages=conversation_history[chat_id],
        model=GLOBALS[chat_id]["MODEL"],
    )
    reply = response.choices[0].message.content

    return reply, response


# Main function to define the bot response
async def respond(update: Update, context):
    chat_id = update.message.chat_id
    user_message = update.message.text

    update_conversation_history(chat_id, user_message, role='user')

    try:
        reply, response = generate_response(chat_id)

        update_conversation_history(chat_id, reply, role="assistant")

        await update.message.reply_text(reply)

        if GLOBALS[chat_id]["DEBUG"]:
            await send_debug_info(update, context)

    except Exception as e:
        error_message = f"Error with OpenAI API: {e}\nRaw response (if any): {response}"
        logging.error(error_message)
        await update.message.reply_text(error_message)



# Main function to run the bot (updated to include /reset command handler)
if __name__ == "__main__":
    # Initialize the bot with the Telegram token
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    application.add_handler(CommandHandler(["ai"], respond))
    application.add_handler(CommandHandler(["settings"], update_globals))
    application.add_handler(CommandHandler(["help"], show_help))
    application.add_handler(CommandHandler(["reset"], reset_history))
    application.add_handler(MessageHandler(filters.REPLY & ~filters.COMMAND, respond))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE, respond))
    application.add_handler(MessageHandler(filters.Mention(BOT_USERNAME), respond))

    # Run the bot
    application.run_polling()
