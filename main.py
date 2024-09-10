import logging
import os
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, filters

# Initialize the OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

# Define the bot response using the new OpenAI API
async def respond(update: Update, context):
    # Extract the message text after the command
    user_message = ' '.join(context.args)
    
    if not user_message:
        await update.message.reply_text("Please provide a prompt after the command.")
        return

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
        error_message = f"Error with OpenAI API: {e}\nRaw response (if any): {response if 'response' in locals() else 'None'}"
        logging.error(error_message)
        await update.message.reply_text(error_message)

# Log setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Main function to run the bot
if __name__ == '__main__':
    # Initialize the bot with the Telegram token
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # Add handlers for the /ai and /ии commands
    application.add_handler(CommandHandler(['ai'], respond))

    # Run the bot
    application.run_polling()
