import logging
import os
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Dictionary to store conversation history for each chat
conversation_history = {}

# Max number of messages to keep in conversation history
MAX_HISTORY_LENGTH = 10

# Define the bot response using the new OpenAI API
async def respond(update: Update, context):
    chat_id = update.message.chat_id
    user_message = update.message.text

    # Initialize the conversation history if it doesn't exist for this chat
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []

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
            model="gpt-4o-mini",
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

    # Run the bot
    application.run_polling()
