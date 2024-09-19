from telegram import Update

def prepend_username(user, message):
    return f"{user.first_name} (@{user.username}): {message}"

async def show_help(update: Update, context):
    help_text = (
        "/help - Show available commands and their descriptions"
        "/ai <message> - Start a conversation with Компуктер\n"
        f"/settings key=value - Update settings like model or history length (e.g. /settings model=gpt-4o /settings history=30)\n"
        "/reset - Reset the conversation history\n"
    )
    await update.message.reply_text(help_text)
