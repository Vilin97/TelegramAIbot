import logging
import os
import random
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

#### globals that the user can change ####
GLOBALS = {
    # Max number of messages to keep in conversation history
    "HISTORY": 30,
    # OpenAI API model to use: "gpt-4o" or "gpt-4o-mini"
    "MODEL": "gpt-4o",
    # print more in debug mode
    "DEBUG": False,
}
##########################################


#### Other globals #######################
# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Dictionary to store conversation history for each chat
conversation_history = {}


def load_system_prompt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return {"role": "system", "content": f.read().strip()}


# Load system prompt from the file
SYSTEM_PROMPT = load_system_prompt("system_prompt.txt")
##########################################


# Function to handle commands and settings
async def update_globals(update: Update, context):
    command = update.message.text.replace("/settings ", "")
    try:
        key, value = command.split("=")
        key = key.strip().upper()
        value = value.strip().lower()

        if key in GLOBALS:
            if key == "HISTORY":
                GLOBALS[key] = int(value)
            elif key == "MODEL":
                GLOBALS[key] = value
            elif key == "DEBUG":
                GLOBALS[key] = value == "true"
            await update.message.reply_text(f"{key} has been updated to {GLOBALS[key]}")
        else:
            await update.message.reply_text(f"Unknown setting: {key}")
    except ValueError:
        await update.message.reply_text(
            "Invalid settings command. Use the format /settings key=value."
        )


# Function to handle rolling dice within the user message
def roll_dice(user_message):
    try:
        dice_command = user_message.lower().replace("/roll ", "")
        number, dice_type = map(int, dice_command.split("d"))
        dice_results = [random.randint(1, dice_type) for _ in range(number)]
        result_str = ", ".join(map(str, dice_results))
        user_message = f"Выпало {result_str}. Сумма {sum(dice_results)}."
        return user_message
    except ValueError:
        return None


# Function to handle conversation history for the chat
def update_conversation_history(chat_id, user_message):
    if chat_id not in conversation_history:
        conversation_history[chat_id] = [SYSTEM_PROMPT]

    # Add the user's message to the conversation history
    conversation_history[chat_id].append(
        {
            "role": "user",
            "content": user_message,
        }
    )

    # Limit the history length
    if len(conversation_history[chat_id]) > GLOBALS["HISTORY"]:
        conversation_history[chat_id] = conversation_history[chat_id][
            -GLOBALS["HISTORY"] :
        ]


# Function to handle debug information
async def send_debug_info(chat_id, update, context):
    debug_info = f"DEBUG INFO: conversation_history={conversation_history[chat_id]}"
    await update.message.reply_text(debug_info)


def generate_response(chat_id):
    # Send the entire conversation history to OpenAI
    response = client.chat.completions.create(
        messages=conversation_history[chat_id],
        model=GLOBALS["MODEL"],
    )
    reply = response.choices[0].message.content

    # Add the assistant's reply to the conversation history
    conversation_history[chat_id].append(
        {
            "role": "assistant",
            "content": reply,
        }
    )

    return reply, response


# Main function to define the bot response
async def respond(update: Update, context, user_message=None):
    chat_id = update.message.chat_id
    user_message = user_message or update.message.text

    # show help if this is the first message
    if chat_id not in conversation_history:
        await update.message.reply_text(
            "Привет! Я Компуктер. Используй /help для списка команд."
        )

    # Handle dice rolling
    roll_message = ""
    if "/roll" in user_message.lower():
        roll_message = roll_dice(user_message)
        user_message = roll_message
        if user_message is None:
            error_message = "Invalid roll command. Please use the format /roll XdY (e.g., /roll 1d20)."
            await update.message.reply_text(error_message)
            return

    # Update conversation history
    update_conversation_history(chat_id, user_message)

    try:
        # reply is the first option in the response
        reply, response = generate_response(chat_id)

        # Reply to the user
        await update.message.reply_text(roll_message + "\n\n" + reply)

        # Send debug info if applicable
        if GLOBALS["DEBUG"]:
            await send_debug_info(chat_id, update, context)

    except Exception as e:
        error_message = f"Error with OpenAI API: {e}\nRaw response (if any): {response if 'response' in locals() else 'None'}"
        logging.error(error_message)
        await update.message.reply_text(error_message)


# Custom filter to check if there are exactly 2 members (including the bot)
class FilterTwoMembers(filters.BaseFilter):
    async def __call__(self, update: Update, context):
        chat_id = update.message.chat_id
        chat_members_count = await context.bot.get_chat_member_count(chat_id)
        return chat_members_count <= 2


# Log setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


# Function to handle resetting the conversation history
async def reset_history(update: Update, context):
    chat_id = update.message.chat_id
    conversation_history.pop(chat_id, None)  # Remove the chat history if it exists
    await update.message.reply_text("Conversation history has been reset.")


# Updated help command to include the /reset command
async def show_help(update: Update, context):
    help_text = (
        "/ai <message> - Start a conversation with Компуктер\n"
        "/roll XdY - Roll X dice with Y sides (e.g., /roll 1d20)\n"
        f"/settings key=value - Update settings like model or history length  (e.g. /settings history=50). Current settings are model={GLOBALS['MODEL']}, history={GLOBALS['HISTORY']}, debug={GLOBALS['DEBUG']})\n"
        "/reset - Reset the conversation history\n"
        "/help - Show available commands and their descriptions"
    )
    await update.message.reply_text(help_text)


# Main function to run the bot (updated to include /reset command handler)
if __name__ == "__main__":
    # Initialize the bot with the Telegram token
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # Add a message handler to handle replies that are not commands
    application.add_handler(
        MessageHandler(filters.TEXT & filters.REPLY & ~filters.COMMAND, respond)
    )

    # Add a command handler for the /roll command
    application.add_handler(CommandHandler("roll", respond))

    # Add handlers for the /ai command
    application.add_handler(CommandHandler(["ai"], respond))

    # Add a command handler for the /settings command
    application.add_handler(CommandHandler(["settings"], update_globals))

    # Add a command handler for the /help command
    application.add_handler(CommandHandler(["help"], show_help))

    # Add a command handler for the /reset command
    application.add_handler(CommandHandler(["reset"], reset_history))

    # Handler for messages when there are exactly 2 members
    application.add_handler(MessageHandler(filters.TEXT & FilterTwoMembers(), respond))

    # Run the bot
    application.run_polling()
