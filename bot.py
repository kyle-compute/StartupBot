import discord
from discord.ext import commands, tasks
import asyncio
import os
from dotenv import load_dotenv
import logging
import google.generativeai as genai

from utils.db import db_manager

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True 
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')


async def init_default_categories(guild_id: int):
    """Initialize default categories for a guild"""
    default_categories = [
        ('Backend', 'Server-side development, databases, APIs'),
        ('Frontend', 'User interface, web development, mobile apps'),
        ('DevOps', 'Infrastructure, deployment, monitoring'),
        ('Learning', 'Acquiring new skills, studying, research'),
        ('Refactoring', 'Code improvement, optimization, cleanup'),
        ('Testing', 'Writing tests, debugging, quality assurance')
    ]
    
    async with db_manager.db_pool.acquire() as conn:
        for name, description in default_categories:
            await conn.execute(
                'INSERT INTO categories (guild_id, name, description) VALUES ($1, $2, $3) ON CONFLICT (guild_id, name) DO NOTHING',
                guild_id, name, description
            )

@bot.event
async def on_ready():
    logger.info(f'{bot.user} is now online!')
    await db_manager.init_db()

    if os.getenv("GEMINI_API_KEY"):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        logger.info("Gemini API configured.")
    else:
        logger.warning("GEMINI_API_KEY not found, AI features will be disabled.")
    
    # Initialize default categories and ensure all members are in the DB
    for guild in bot.guilds:
        await init_default_categories(guild.id)
        for member in guild.members:
            if not member.bot:
                await db_manager.ensure_user_exists(member.id, guild.id)
    logger.info("Finished ensuring all existing members are in the database.")
    
    # Load cogs
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')
            logger.info(f"Loaded cog: {filename}")

    # Sync slash commands
    await bot.tree.sync()
    logger.info("Slash commands synced.")


@bot.event
async def on_guild_join(guild):
    """Initialize default categories when bot joins a guild"""
    await init_default_categories(guild.id)


@bot.event
async def on_member_join(member):
    """Adds a user to the database when they join a guild."""
    if not member.bot:
        await db_manager.ensure_user_exists(member.id, member.guild.id)
        logger.info(f"Added new member '{member.display_name}' to the database.")


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param.name}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You do not have the required permissions to run this command.")
    else:
        logger.error(f"Unhandled error in command {ctx.command}: {error}")
        await ctx.send("❌ An unexpected error occurred. Please check the logs.")


if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))