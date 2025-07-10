import discord
from discord.ext import commands
from utils.db import db_manager

class ProfileCog(commands.Cog, name="Profile"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='profile')
    async def user_profile(self, ctx, user: discord.Member = None):
        """Show user profile and stats"""
        target_user = user or ctx.author
        await db_manager.ensure_user_exists(target_user.id, ctx.guild.id)
        
        async with db_manager.db_pool.acquire() as conn:
            user_data = await conn.fetchrow(
                'SELECT * FROM users WHERE user_id = $1 AND guild_id = $2',
                target_user.id, ctx.guild.id
            )
            
            recent_challenges = await conn.fetch(
                '''SELECT c.challenge_id, c.title, 
                          COALESCE(c.final_difficulty_elo, c.base_difficulty_elo) as difficulty_elo, 
                          c.status, c.created_at,
                          cat.name as category
                   FROM challenges c
                   JOIN categories cat ON c.category_id = cat.id
                   WHERE c.user_id = $1 AND c.guild_id = $2
                   ORDER BY c.created_at DESC
                   LIMIT 5''',
                target_user.id, ctx.guild.id
            )
            
            elo_history = await conn.fetch(
                'SELECT elo_before, elo_after, elo_change, created_at FROM elo_history WHERE user_id = $1 AND guild_id = $2 ORDER BY created_at DESC LIMIT 10',
                target_user.id, ctx.guild.id
            )
        
        embed = discord.Embed(title=f"📊 {target_user.display_name}'s Profile", color=0x9b59b6)
        
        completion_rate = (user_data['completed_challenges'] / user_data['total_challenges'] * 100) if user_data['total_challenges'] > 0 else 0
        embed.add_field(name="Current ELO", value=str(user_data['current_elo']), inline=True)
        embed.add_field(name="Total Challenges", value=str(user_data['total_challenges']), inline=True)
        embed.add_field(name="Completion Rate", value=f"{completion_rate:.1f}%", inline=True)
        
        if recent_challenges:
            challenges_text = ""
            for challenge in recent_challenges:
                status_emoji = {"active": "🟡", "pending_review": "🟠", "completed": "✅", "failed": "❌", "rejected": "🔴"}
                emoji = status_emoji.get(challenge['status'], "❓")
                challenges_text += f"{emoji} [{challenge['challenge_id']}] {challenge['title'][:30]}... ({challenge['difficulty_elo']} ELO)\n"
            
            embed.add_field(name="Recent Challenges", value=challenges_text, inline=False)
        
        if elo_history:
            elo_trend = "📈 ELO History:\n"
            for i, entry in enumerate(elo_history[:5]):
                change_str = f"+{entry['elo_change']}" if entry['elo_change'] > 0 else str(entry['elo_change'])
                elo_trend += f"{entry['elo_before']} → {entry['elo_after']} ({change_str})\n"
            
            embed.add_field(name="ELO Trend", value=elo_trend, inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ProfileCog(bot)) 