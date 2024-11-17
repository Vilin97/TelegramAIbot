"""AI logic for the bot."""

from openai import OpenAI
from dotenv import load_dotenv
import os

import database as db

if os.environ.get("ENV") != "production":
    load_dotenv()


def load_prompt(file_name):
    file_path = os.path.join("prompts", file_name)
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = load_prompt("system_prompt.txt")
REWORD_PROMPT = load_prompt("reword_prompt.txt")
SUMMARY_PROMPT = load_prompt("summary_prompt.txt")


async def build_prompt(update, context):
    history = int(await db.get_setting(update, context, "history"))
    conversation_history = await db.conversation_history(update, context)
    recent_messages = conversation_history[-history:]

    language = await db.get_setting(update, context, "language")
    system_prompt = SYSTEM_PROMPT + f"\nYou MUST respond in {language}."
    prompt = [{"role": "system", "content": system_prompt}]
    pinned_messages = await db.messages_with_property(update, context, "pinned", "true")
    prompt += [msg for msg in pinned_messages if msg not in recent_messages]
    if len(conversation_history) > history:
        summary = await summarize(update, context)
        prompt.append({"role": "assistant", "content": summary})
    prompt += recent_messages
    return prompt

async def generate_response(update, context):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    model = await db.get_setting(update, context, "model")
    prompt = await build_prompt(update, context)
    response = client.chat.completions.create(
        messages=prompt,
        model=model,
    )
    content = response.choices[0].message.content
    tokens = response.usage.total_tokens
    return content, tokens


async def summarize(update, context):
    history = int(await db.get_setting(update, context, "history"))
    pre_history = (await db.conversation_history(update, context))[:-history]

    pre_history_messages = [
        ("Bot: " if message["role"] == "assistant" else "") + message["content"]
        for message in pre_history
    ]
    pre_history_messages = "\n".join(pre_history_messages)

    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": pre_history_messages},
        ],
        model="gpt-4o-mini",  # ~30x cheaper than gpt-4o
    )
    summary = response.choices[0].message.content
    return summary


async def imagine(update, context, prompt):
    chat_id = update.effective_chat.id
    bot = context.bot

    generating = await update.message.reply_text("Генерирую изображение...")
    try:
        await bot.send_chat_action(chat_id=chat_id, action="upload_photo")
        response = client.images.generate(
            prompt=prompt,
            model="dall-e-3",  # dall-e-2 works worse
            size="1024x1024",  # higher quality costs more
            quality="standard",  # "hd" costs twice more
        )
        image_url = response.data[0].url
        revised_prompt = response.data[0].revised_prompt
        await update.message.reply_photo(image_url, caption=revised_prompt)
    except Exception as e:
        await update.message.reply_text("Я не смог сгенерировать изображение.")
    finally:
        await bot.delete_message(chat_id=chat_id, message_id=generating.message_id)


async def reword(update, context):
    original_message_text = update.message.reply_to_message.text
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": REWORD_PROMPT},
            {"role": "user", "content": original_message_text},
        ],
        model="gpt-4o",
    )
    # prevent further rewording to avoid losing the original meaning
    prompt = (
        "DO NOT add any detail, just use this prompt AS-IS: "
        + response.choices[0].message.content
    )
    return prompt
