"""Functions to interact with the database.

Tables in the DB:
- `chat_history` holds history of all chats
- `chat_settings` holds the chat settings, like model name and history length
"""

import asyncpg
import os
import json


async def init_db():
    DATABASE_URL = os.getenv("DATABASE_URL")
    pool = await asyncpg.create_pool(DATABASE_URL)
    return pool


async def save_message(context, message, role, properties={}):
    assert role in ["system", "assistant", "user"]

    pool = context.bot_data["db_pool"]
    chat_id = message.chat_id
    user = message.from_user if role == "user" else context.bot
    message_id = message.message_id
    text = message.text

    query = """
        INSERT INTO chat_history (user_id, user_name, chat_id, message, role, properties, message_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
    """

    async with pool.acquire() as conn:
        await conn.execute(
            query,
            user.id,
            user.username,
            chat_id,
            text,
            role,
            json.dumps(properties),
            message_id,
        )


async def save_message_properties(context, message, new_properties):
    pool = context.bot_data["db_pool"]
    chat_id = message.chat_id
    message_id = message.message_id
    
    query = """
        UPDATE chat_history
        SET properties = $1
        WHERE chat_id = $2 AND message_id = $3
    """

    async with pool.acquire() as conn:
        await conn.execute(query, json.dumps(new_properties), chat_id, message_id)


async def messages_with_property(update, context, property_name, property_value):

    pool = context.bot_data["db_pool"]
    chat_id = update.message.chat_id

    query = """
        SELECT *
        FROM chat_history
        WHERE chat_id = $1 AND properties->>$2 = $3
        ORDER BY timestamp ASC
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, chat_id, property_name, property_value)

    return [{"role": row["role"], "content": row["message"]} for row in rows]


async def delete_message_with_id(update, context, message):
    pool = context.bot_data["db_pool"]
    chat_id = update.message.chat_id
    message_id = message.id

    query = """
        DELETE
        FROM chat_history
        WHERE chat_id = $2 AND message_id = $3
    """

    async with pool.acquire() as conn:
        await conn.execute(query, chat_id, message_id)


async def conversation_history(update, context):

    pool = context.bot_data["db_pool"]
    chat_id = update.message.chat_id

    query = """
        SELECT user_name, message, role
        FROM chat_history
        WHERE chat_id = $1
        ORDER BY timestamp ASC
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, chat_id)

    return [{"role": row["role"], "content": row["message"]} for row in rows]


async def reset_history(update, context):

    pool = context.bot_data["db_pool"]
    chat_id = update.message.chat_id

    query = """DELETE FROM chat_history WHERE chat_id = $1;"""

    async with pool.acquire() as conn:
        await conn.execute(query, chat_id)

    await update.message.reply_text("Conversation history has been reset.")


async def update_settings(update, context):
    chat_id = update.message.chat_id
    pool = context.bot_data["db_pool"]
    command = update.message.text.replace("/settings ", "")

    try:
        setting_name, new_value = command.split("=")
        setting_name = setting_name.strip()
        new_value = new_value.strip()

        async with pool.acquire() as conn:
            # Insert or update the setting in the JSONB field
            await conn.execute(
                """
                INSERT INTO chat_settings (chat_id, settings)
                VALUES ($1, jsonb_set('{}', $2, $3::jsonb))
                ON CONFLICT (chat_id) 
                DO UPDATE SET settings = jsonb_set(chat_settings.settings, $2, $3::jsonb);
                """,
                chat_id,
                [setting_name],
                f'"{new_value}"',
            )

        await update.message.reply_text(
            f"{setting_name} has been updated to {new_value}"
        )

    except ValueError:
        await update.message.reply_text(
            "Invalid settings command. Use the format /settings key=value."
        )


async def get_setting(update, context, setting_name):
    """Get a setting from the database or use the default value."""
    defaults = context.bot_data["defaults"]
    chat_id = update.message.chat_id
    pool = context.bot_data["db_pool"]

    async with pool.acquire() as conn:
        result = await conn.fetchval(
            """
            SELECT settings->>$2 
            FROM chat_settings 
            WHERE chat_id = $1
            """,
            chat_id,
            setting_name,
        )

    # If the setting is not found in the DB, use the default value
    if result is None:
        result = defaults[setting_name]

    return result
