import logging
import os
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# Initialize the OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

# Define the bot response using the new OpenAI API
async def chatgpt_response(update: Update, context):
    user_message = update.message.text
    try:
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": user_message,
                }
            ],
            model="gpt-4o-mini",
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(reply)
    except Exception as e:
        error_message = f"Error with OpenAI API: {e}\nRaw response (if any): {response}"
        logging.error(error_message)
        await update.message.reply_text(error_message)

# Log setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Define start command handler
async def start(update: Update, context):
    await update.message.reply_text('Hello! I am VasChatGPT, how can I assist you today?')

# Main function to run the bot
if __name__ == '__main__':
    # Initialize the bot with the Telegram token
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # Add command and message handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chatgpt_response))

    # Run the bot
    application.run_polling()
