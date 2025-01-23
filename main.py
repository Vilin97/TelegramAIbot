# main.py
import os
import logging
from discord.ext import commands
import ai
import database as db
import dnd
import utils

############### GLOBALS ##################
DEFAULTS = {"history": 50, "model": "gpt-4o", "language": "English"}
BOT_PREFIX = "!"
BOT_USERNAME = "VasChatGPTBot"
##########################################

# Set up logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING)

# Initialize bot
intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)


# Post init setup
@bot.event
async def on_ready():
    pool = await db.init_db()
    bot.defaults = DEFAULTS
    bot.db_pool = pool
    print(f"Logged in as {bot.user.name}")

############## COMMANDS ##################


@bot.command(name="help")
async def show_help(ctx):
    """Show available commands and their descriptions"""
    await utils.show_help(ctx)


@bot.command(name="reset")
async def reset_history(ctx):
    """Reset the conversation history"""
    await db.reset_history(ctx)


@bot.command(name="delete")
async def delete_message(ctx):
    """Delete a message from the bot's brain"""
    if ctx.message.reference:
        ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        await db.delete_message(ctx, ref_msg)
        await ref_msg.delete()
        await ctx.message.delete()
    else:
        await ctx.reply("Reply to a message you wish to delete.")


@bot.command(name="imagine")
async def imagine(ctx, *, prompt=None):
    """Generate an image from a prompt"""
    if prompt:
        await ai.imagine(ctx, prompt)
    else:
        await ctx.reply("Please provide a prompt for the image.")


@bot.command(name="settings")
async def settings(ctx, *, key_value=None):
    """View or update settings"""
    if not key_value:
        model = await db.get_setting(ctx, "model")
        history = await db.get_setting(ctx, "history")
        language = await db.get_setting(ctx, "language")
        conversation_history = await db.conversation_history(ctx)
        history_length = len(conversation_history)
        await ctx.reply(
            f"language = {language}, model = {model}, history = {history} "
            f"({history_length} messages total)."
        )
    else:
        await db.update_settings(ctx, key_value)


@bot.command(name="roll")
async def roll(ctx, dice: str):
    """Roll dice (e.g. !roll 2d6)"""
    await ctx.reply(dnd.roll(dice))


@bot.command(name="respond")
async def respond(ctx, *, prompt=None):
    """Respond to user messages"""
    if not prompt:
        await ctx.reply("Please provide a message.")
        return
    prompt = utils.prepend_username(ctx.author, prompt)
    await db.save_message(ctx, ctx.message, "user", prompt)
    content, tokens = await ai.generate_response(ctx, prompt)
    reply = await ctx.reply(content + f"\n({tokens} tokens)")
    await db.save_message(ctx, reply, "assistant", content)


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if bot.user.mentioned_in(message):
        ctx = await bot.get_context(message)
        await respond(ctx, prompt=utils.message_text(message, bot))
    else:
        await bot.process_commands(message)

# Run the bot
if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))

