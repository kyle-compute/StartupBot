import discord
from discord.ext import commands

class HelpCog(commands.Cog, name="Help"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='guide')
    async def help_command(self, ctx):
        """Show help and tutorial information"""
        embed = discord.Embed(
            title="MLH ELO Bot - Competitive Accountability",
            description="Transform productivity into a competitive game with peer-reviewed challenges and ELO rankings.",
            color=0x3498db
        )
        
        embed.add_field(
            name="🎯 Getting Started",
            value="""1. Check available categories: `!categories`
2. Issue your first challenge: `!challenge Backend 1200 Build REST API`
3. Complete and submit proof: `!complete CHL-101 https://github.com/user/repo`
4. Peers review with: `!approve CHL-101` or `!reject CHL-101`
5. Climb the leaderboard: `!leaderboard`""",
            inline=False
        )
        
        embed.add_field(
            name="🏆 Core Commands",
            value="""**Challenge Management:**
`!challenge <category> <difficulty> <description>` - Issue new challenge (100-2000 ELO)
`!challenges [status]` - List challenges (active/pending/completed)
`!complete <id> <proof>` - Submit challenge for review
`!approve <id>` / `!reject <id>` - Vote on submissions""",
            inline=False
        )
        
        embed.add_field(
            name="📊 Stats & Leaderboards",
            value="""**View Progress:**
`!leaderboard` or `!lb` - Current sprint rankings
`!leaderboard alltime` - All-time ELO rankings
`!profile [@user]` - View detailed user stats
`!sprint status` - Current sprint information""",
            inline=False
        )
        
        embed.add_field(
            name="🤖 AI Features",
            value="""**Auto-Summarization:**
`!fromhere` - Reply to any message to summarize from that point onward
Generates bullet-point summaries using Gemini AI with key topics, decisions, and action items""",
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Configuration",
            value="""**Categories:**
`!categories` - List available categories
`!category add <name> [description]` - Create custom category
`!category remove <name>` - Remove category (Admin only)

**Admin Commands:**
`!config show` - View server settings
`!sprint start/end` - Manage competition cycles""",
            inline=False
        )
        
        embed.add_field(
            name="🎲 ELO System",
            value="""**Starting ELO:** 1000 points
**Strategy:** Higher difficulty = bigger risk/reward
**Example:** 1000 ELO user vs 1400 difficulty = +45 points if successful
**Peer Review:** Community validates work quality""",
            inline=False
        )
        
        embed.add_field(
            name="🏃 Sprint Cycle",
            value="""**Weekly Competition:**
Monday: Issue challenges
Tue-Sat: Execute work
Weekend: Submit proof & peer review
Sunday: ELO updates & new leaderboard""",
            inline=False
        )
        
        embed.set_footer(text="Ready to start? Try: !categories")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCog(bot)) 