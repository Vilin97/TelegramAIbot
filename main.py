import logging
import openai
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# Set up OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Define the bot response to messages using GPT-4
async def chatgpt_response(update: Update, context):
    user_message = update.message.text
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_message},
        ],
    )
    reply = response['choices'][0]['message']['content']
    await update.message.reply_text(reply)

# Log setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Define start command handler
async def start(update: Update, context):
    await update.message.reply_text('Hello! I am VasChatGPT, now powered by GPT-4. How can I assist you today?')

# Main function
if __name__ == '__main__':
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # Add command and message handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chatgpt_response))

    # Run the bot
    application.run_polling()
