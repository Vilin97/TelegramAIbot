from telegram import Update

async def update_globals_(update: Update, context, globals):
    chat_id = update.message.chat_id
    command = update.message.text.replace("/settings ", "")
    try:
        key, value = command.split("=")
        key = key.strip().upper()
        value = value.strip().lower()

        if chat_id not in globals:
            globals[chat_id] = globals["DEFAULT"].copy()

        if key in globals[chat_id]:
            if key == "HISTORY":
                globals[chat_id][key] = int(value)
            elif key == "MODEL":
                globals[chat_id][key] = value
            elif key == "DEBUG":
                globals[chat_id][key] = value == "true"
            await update.message.reply_text(
                f"{key} has been updated to {globals[chat_id][key]}"
            )
        else:
            await update.message.reply_text(f"Unknown setting: {key}")
    except ValueError:
        await update.message.reply_text(
            "Invalid settings command. Use the format /settings key=value."
        )


async def send_debug_info_(update, context, conversation_history):
    chat_id = update.message.chat_id
    debug_info = f"DEBUG INFO: \nconversation_history={conversation_history[chat_id][1:]}\nupdate.message={update.message}"
    await update.message.reply_text(debug_info)

async def show_help_(update: Update, context, globals):
    chat_id = update.message.chat_id
    help_text = (
        "/help - Show available commands and their descriptions"
        "/ai <message> - Start a conversation with Компуктер\n"
        f"/settings key=value - Update settings like model or history length  (e.g. /settings history=50). Current settings are model={globals[chat_id]['MODEL']}, history={globals[chat_id]['HISTORY']}, debug={globals[chat_id]['DEBUG']})\n"
        "/reset - Reset the conversation history\n"
    )
    await update.message.reply_text(help_text)

# Function to handle resetting the conversation history
async def reset_history_(update: Update, context, conversation_history):
    chat_id = update.message.chat_id
    conversation_history.pop(chat_id, None)  # Remove the chat history if it exists
    await update.message.reply_text("Conversation history has been reset.")
