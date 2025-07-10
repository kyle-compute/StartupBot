import discord
from discord.ext import commands, tasks
from datetime import datetime
import logging
from utils.db import db_manager

logger = logging.getLogger(__name__)

class SprintsCog(commands.Cog, name="Sprints"):
    def __init__(self, bot):
        self.bot = bot
        self.auto_sprint_management.start()

    def cog_unload(self):
        self.auto_sprint_management.cancel()

    @commands.command(name='sprint')
    @commands.has_permissions(administrator=True)
    async def sprint_management(self, ctx, action: str = None):
        """Manage sprint cycles (Admin only)"""
        if action == "start":
            config = await db_manager.get_guild_config(ctx.guild.id)
            sprint_id = await db_manager.create_sprint(ctx.guild.id, config['sprint_duration_days'])
            await ctx.send(f"✅ New sprint started! Sprint ID: {sprint_id}")
        
        elif action == "end":
            async with db_manager.db_pool.acquire() as conn:
                await conn.execute(
                    'UPDATE sprints SET status = $1 WHERE guild_id = $2 AND status = $3',
                    'ended', ctx.guild.id, 'active'
                )
            await ctx.send("✅ Current sprint ended!")
        
        elif action == "status":
            sprint = await db_manager.get_active_sprint(ctx.guild.id)
            if sprint:
                embed = discord.Embed(title="🏃 Current Sprint Status", color=0x2ecc71)
                embed.add_field(name="Sprint ID", value=sprint['id'], inline=True)
                embed.add_field(name="Started", value=sprint['start_date'].strftime('%Y-%m-%d %H:%M'), inline=True)
                embed.add_field(name="Ends", value=sprint['end_date'].strftime('%Y-%m-%d %H:%M'), inline=True)
                
                days_left = (sprint['end_date'] - datetime.utcnow()).days
                embed.add_field(name="Days Remaining", value=str(days_left), inline=True)
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("No active sprint found.")
        
        else:
            await ctx.send("Usage: `!sprint start|end|status`")

    @tasks.loop(hours=1)
    async def auto_sprint_management(self):
        """Automatically manage sprint cycles"""
        try:
            async with db_manager.db_pool.acquire() as conn:
                configs = await conn.fetch(
                    'SELECT guild_id, sprint_duration_days FROM guild_config WHERE auto_start_sprints = TRUE'
                )
                
                for config in configs:
                    guild_id = config['guild_id']
                    duration = config['sprint_duration_days']
                    
                    current_sprint = await conn.fetchrow(
                        'SELECT * FROM sprints WHERE guild_id = $1 AND status = $2 ORDER BY start_date DESC LIMIT 1',
                        guild_id, 'active'
                    )
                    
                    if current_sprint:
                        if datetime.utcnow() >= current_sprint['end_date']:
                            await conn.execute(
                                'UPDATE sprints SET status = $1 WHERE id = $2',
                                'ended', current_sprint['id']
                            )
                            
                            await db_manager.create_sprint(guild_id, duration)
                            logger.info(f"Auto-started new sprint for guild {guild_id}")
                    else:
                        await db_manager.create_sprint(guild_id, duration)
                        logger.info(f"Created initial sprint for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error in auto sprint management: {e}")

async def setup(bot):
    await bot.add_cog(SprintsCog(bot)) 