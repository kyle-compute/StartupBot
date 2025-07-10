import discord
from discord.ext import commands
from utils.db import db_manager

class ConfigCog(commands.Cog, name="Config"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='config')
    @commands.has_permissions(administrator=True)
    async def guild_config(self, ctx, action: str = None, key: str = None, value: str = None):
        """Configure guild settings (Admin only)"""
        if action == "set" and key and value:
            valid_keys = ['k_factor_new', 'k_factor_stable', 'approvals_needed', 'sprint_duration_days', 'stable_user_threshold']
            
            if key not in valid_keys:
                await ctx.send(f"❌ Invalid key. Valid keys: {', '.join(valid_keys)}")
                return
            
            try:
                int_value = int(value)
                if int_value <= 0:
                    await ctx.send("❌ Value must be positive")
                    return
                    
                async with db_manager.db_pool.acquire() as conn:
                    await conn.execute(
                        f'UPDATE guild_config SET {key} = $1 WHERE guild_id = $2',
                        int_value, ctx.guild.id
                    )
                await ctx.send(f"✅ Set {key} = {int_value}")
            except ValueError:
                await ctx.send("❌ Value must be an integer")
        
        elif action == "channel" and key == "review" and value:
            try:
                channel_id = int(value.strip('<#>'))
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    await ctx.send("❌ Channel not found")
                    return
                    
                async with db_manager.db_pool.acquire() as conn:
                    await conn.execute(
                        'UPDATE guild_config SET review_channel_id = $1 WHERE guild_id = $2',
                        channel_id, ctx.guild.id
                    )
                await ctx.send(f"✅ Set review channel to <#{channel_id}>")
            except ValueError:
                await ctx.send("❌ Invalid channel")
        
        elif action == "channel" and key == "voting" and value:
            try:
                channel_id = int(value.strip('<#>'))
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    await ctx.send("❌ Channel not found")
                    return
                    
                async with db_manager.db_pool.acquire() as conn:
                    await conn.execute(
                        'UPDATE guild_config SET difficulty_voting_channel_id = $1 WHERE guild_id = $2',
                        channel_id, ctx.guild.id
                    )
                await ctx.send(f"✅ Set difficulty voting channel to <#{channel_id}>")
            except ValueError:
                await ctx.send("❌ Invalid channel")
        
        elif action == "show":
            config = await db_manager.get_guild_config(ctx.guild.id)
            embed = discord.Embed(title="⚙️ Guild Configuration", color=0x95a5a6)
            
            for key, value in config.items():
                if key not in ['guild_id', 'created_at', 'updated_at']:
                    embed.add_field(name=key, value=str(value), inline=True)
            
            await ctx.send(embed=embed)
        
        else:
            await ctx.send("Usage: `!config set <key> <value>` or `!config channel review #channel` or `!config channel voting #channel` or `!config show`")

async def setup(bot):
    await bot.add_cog(ConfigCog(bot)) 