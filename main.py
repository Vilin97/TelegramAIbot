import logging
import os
import random
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Dictionary to store conversation history for each chat
conversation_history = {}

# Max number of messages to keep in conversation history
MAX_HISTORY_LENGTH = 30

# System prompt for the AI
SYSTEM_PROMPT = {"role": "system", "content": "Меня зовут Компуктер."}

# Function to roll dice based on a string like "1d20" or "3d6"
def roll_dice(dice_command):
    try:
        number, dice_type = map(int, dice_command.lower().split('d'))
        results = [random.randint(1, dice_type) for _ in range(number)]
        return results
    except ValueError:
        return None

# Function to handle rolling dice and passing the result to the AI conversation
async def roll_and_respond(update: Update, context):
    dice_command = update.message.text.replace('/roll ', '')

    # Perform the dice roll
    dice_results = roll_dice(dice_command)
    if dice_results is not None:
        result_str = ', '.join(map(str, dice_results))
        rolled_prompt = f"I rolled {result_str}"

        # Call respond function to continue the conversation with the AI
        await respond(update, context, user_message=rolled_prompt)

    else:
        await update.message.reply_text("Invalid roll command. Please use the format /roll XdY (e.g., /roll 1d20).")

# Define the bot response using the new OpenAI API
async def respond(update: Update, context, user_message=None):
    chat_id = update.message.chat_id
    user_message = user_message or update.message.text

    # Initialize the conversation history if it doesn't exist for this chat
    if chat_id not in conversation_history:
        conversation_history[chat_id] = [SYSTEM_PROMPT]

    # Add the user's message to the conversation history
    conversation_history[chat_id].append({
        "role": "user",
        "content": user_message,
    })

    # Limit the history length
    if len(conversation_history[chat_id]) > MAX_HISTORY_LENGTH:
        conversation_history[chat_id] = conversation_history[chat_id][-MAX_HISTORY_LENGTH:]

    try:
        # Send the entire conversation history to OpenAI
        response = client.chat.completions.create(
            messages=conversation_history[chat_id],
            model="gpt-4o",
        )
        reply = response.choices[0].message.content

        # Add the assistant's reply to the conversation history
        conversation_history[chat_id].append({
            "role": "assistant",
            "content": reply,
        })

        # Reply to the user
        await update.message.reply_text(reply)

    except Exception as e:
        error_message = f"Error with OpenAI API: {e}\nRaw response (if any): {response if 'response' in locals() else 'None'}"
        logging.error(error_message)
        await update.message.reply_text(error_message)

# Command to reset the conversation history
async def reset_history(update: Update, context):
    chat_id = update.message.chat_id
    conversation_history.pop(chat_id, None)
    await update.message.reply_text("Conversation history has been reset.")

# Command to show all available commands and their descriptions
async def show_help(update: Update, context):
    help_text = (
        "/ai <message> - Start a conversation with Компуктер\n"
        "/roll <XdY> - Roll X dice with Y sides (e.g., /roll 1d20 or /roll 3d6)\n"
        "/reset - Reset the conversation history\n"
        "/help - Show available commands and their descriptions"
    )
    await update.message.reply_text(help_text)

# Log setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Main function to run the bot
if __name__ == '__main__':
    # Initialize the bot with the Telegram token
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # Add handlers for the /ai command
    application.add_handler(CommandHandler(['ai'], respond))

    # Add a message handler to handle replies to bot messages
    application.add_handler(MessageHandler(filters.TEXT & filters.REPLY, respond))

    # Add a command handler to reset the conversation history
    application.add_handler(CommandHandler(['reset'], reset_history))

    # Add a command handler for the /help command
    application.add_handler(CommandHandler(['help'], show_help))

    # Add a handler for the /roll command
    application.add_handler(CommandHandler(['roll'], roll_and_respond))

    # Run the bot
    application.run_polling()
