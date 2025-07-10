import discord
from discord.ext import commands
from utils.db import db_manager

class LeaderboardCog(commands.Cog, name="Leaderboard"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='leaderboard', aliases=['lb'])
    async def leaderboard(self, ctx, time_period: str = "weekly"):
        """Show leaderboard for weekly or all-time"""
        if time_period.lower() not in ['weekly', 'alltime', 'all-time']:
            await ctx.send("❌ Use `weekly` or `alltime` for time period")
            return
        
        async with db_manager.db_pool.acquire() as conn:
            if time_period.lower() == 'weekly':
                sprint = await db_manager.get_active_sprint(ctx.guild.id)
                if not sprint:
                    await ctx.send("No active sprint found.")
                    return
                
                leaderboard_data = await conn.fetch(
                    '''SELECT u.user_id, u.current_elo, 
                              COALESCE(SUM(eh.elo_change), 0) as weekly_gain,
                              COUNT(c.id) as weekly_challenges,
                              COUNT(CASE WHEN c.status = 'completed' THEN 1 END) as weekly_completed
                       FROM users u
                       LEFT JOIN elo_history eh ON u.user_id = eh.user_id AND u.guild_id = eh.guild_id
                       LEFT JOIN challenges c ON eh.challenge_id = c.id AND c.sprint_id = $1
                       WHERE u.guild_id = $2
                       GROUP BY u.user_id, u.current_elo
                       ORDER BY weekly_gain DESC
                       LIMIT 10''',
                    sprint['id'], ctx.guild.id
                )
                
                embed = discord.Embed(title="🏆 Weekly Sprint Leaderboard", color=0xf1c40f)
                embed.add_field(name="Sprint Period", value=f"{sprint['start_date'].strftime('%Y-%m-%d')} to {sprint['end_date'].strftime('%Y-%m-%d')}", inline=False)
            else:
                leaderboard_data = await conn.fetch(
                    '''SELECT u.user_id, u.current_elo, u.total_challenges, u.completed_challenges
                       FROM users u
                       WHERE u.guild_id = $1
                       ORDER BY u.current_elo DESC
                       LIMIT 10''',
                    ctx.guild.id
                )
                
                embed = discord.Embed(title="🏆 All-Time Leaderboard", color=0xe74c3c)
            
            if not leaderboard_data:
                embed.add_field(name="No Data", value="No users found on leaderboard", inline=False)
            else:
                leaderboard_text = ""
                for i, row in enumerate(leaderboard_data, 1):
                    user = self.bot.get_user(row['user_id'])
                    username = user.display_name if user else "Unknown User"
                    
                    if time_period.lower() == 'weekly':
                        leaderboard_text += f"**{i}.** {username} - {row['current_elo']} ELO (+{row['weekly_gain']}) | {row['weekly_completed']}/{row['weekly_challenges']} completed\n"
                    else:
                        completion_rate = (row['completed_challenges'] / row['total_challenges'] * 100) if row['total_challenges'] > 0 else 0
                        leaderboard_text += f"**{i}.** {username} - {row['current_elo']} ELO | {row['completed_challenges']}/{row['total_challenges']} ({completion_rate:.1f}%)\n"
                
                embed.add_field(name="Rankings", value=leaderboard_text, inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LeaderboardCog(bot)) 