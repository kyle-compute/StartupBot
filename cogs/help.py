import discord
from discord.ext import commands

class HelpCog(commands.Cog, name="Help"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='guide')
    async def help_command(self, ctx):
        """Show a simplified guide to the bot."""
        embed = discord.Embed(
            title="ELO Bot Quick Start",
            description="A quick guide to get you started.",
            color=0x3498db
        )
        
        embed.add_field(
            name="1. Issue a Challenge",
            value="Use `!challenge <category> <difficulty> <desc>`.\nFind categories with `!categories`.",
            inline=False
        )

        embed.add_field(
            name="2. Complete & Get Reviewed",
            value="Submit your work with `!complete <id> <proof>`.\nPeers will review it with `!approve` or `!reject`.",
            inline=False
        )

        embed.add_field(
            name="3. Track Your Progress",
            value="See where you stand with `!leaderboard` and `!profile`.",
            inline=False
        )
        
        embed.set_footer(text="For a full list of all commands, use !help")
        
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
            name="🧠 Knowledge Management",
            value="Right-click any message to access these commands:\n**Add Prerequisite** - Link a message to another.\n**View Prerequisites** - Show the chain of prerequisites.",
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


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
