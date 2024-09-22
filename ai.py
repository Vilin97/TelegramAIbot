from openai import OpenAI
from dotenv import load_dotenv
import os

import database as db

if os.environ.get("ENV") != "production":
    load_dotenv()

def load_prompt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = load_prompt("system_prompt.txt")
REWORD_PROMPT = load_prompt("reword_prompt.txt")

async def generate_response(update, context):
    conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    conversation_history += await db.conversation_history(update, context)

    history = int(await db.get_setting(update, context, "history"))
    model = await db.get_setting(update, context, "model")

    response = client.chat.completions.create(
        messages=conversation_history[-history:],
        model=model,
    )
    reply = response.choices[0].message.content

    return reply

async def imagine(update, context, prompt):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
    response = client.images.generate(
        prompt=prompt,
        model="dall-e-3",  # dall-e-2 works worse
        size="1024x1024",  # higher quality costs more
        quality="standard",  # "hd" costs twice more
    )
    image_url = response.data[0].url
    revised_prompt = response.data[0].revised_prompt
    await update.message.reply_photo(image_url, caption=revised_prompt)


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