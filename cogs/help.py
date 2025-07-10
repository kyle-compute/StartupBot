import discord
from discord.ext import commands

class HelpCog(commands.Cog, name="Help"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='guide')
    async def help_command(self, ctx):
        """Show a simplified guide to the bot."""
        embed = discord.Embed(
            title="MLH ELO Bot - Quick Start Guide",
            description="Welcome! Let's get you started with your first challenge.",
            color=0x3498db
        )
        
        embed.add_field(
            name="Step 1: Find a Challenge Category",
            value="See what's available to work on.\n`!categories`",
            inline=False
        )

        embed.add_field(
            name="Step 2: Issue Your Challenge",
            value="Pick a category and difficulty (ELO points).\n`!challenge <category> <difficulty> <description>`\n\n**Example:**\n`!challenge Frontend 1100 Create a login form`",
            inline=False
        )

        embed.add_field(
            name="What's Next?",
            value="Once you're done, submit your work with `!complete <challenge-id> <proof>`.\nYour peers will then review it!",
            inline=False
        )

        embed.add_field(
            name="Explore More Commands",
            value="""`!challenges` - See active challenges
`!leaderboard` - Check the rankings
`!profile` - View your stats

For a full list of all commands, use `!help`.""",
            inline=False
        )
        
        embed.set_footer(text="Ready to start? Try: !categories")
        
        await ctx.send(embed=embed)

    @commands.command(name='help')
    async def full_help_command(self, ctx):
        """Show a detailed list of all commands."""
        embed = discord.Embed(
            title="MLH ELO Bot - Command Reference",
            description="Here are all the available commands.",
            color=0x3498db
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
        
        embed.set_footer(text="For a quick start, use !guide")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCog(bot)) 