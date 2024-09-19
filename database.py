import asyncpg
import os


async def init_db():
    DATABASE_URL = os.getenv("DATABASE_URL")
    pool = await asyncpg.create_pool(DATABASE_URL)
    return pool


async def save_message_to_db(update, context, role, message):
    assert role in ["user", "assistant"]

    if "db_pool" not in context.bot_data:
        pool = await init_db()
        context.bot_data["db_pool"] = pool

    pool = context.bot_data["db_pool"]
    chat_id = update.message.chat_id
    user = update.message.from_user if role == "user" else context.bot

    query = """
        INSERT INTO chat_history (user_id, user_name, chat_id, message, role)
        VALUES ($1, $2, $3, $4, $5)
    """

    async with pool.acquire() as conn:
        await conn.execute(query, user.id, user.username, chat_id, message, role)


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
    if "db_pool" not in context.bot_data:
        pool = await init_db()
        context.bot_data["db_pool"] = pool

    pool = context.bot_data["db_pool"]
    chat_id = update.message.chat_id

    query = """DELETE FROM chat_history WHERE chat_id = $1;"""

    async with pool.acquire() as conn:
        await conn.execute(query, chat_id)

    await update.message.reply_text("Conversation history has been reset.")
