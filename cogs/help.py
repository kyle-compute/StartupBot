import discord
from discord.ext import commands

class CustomHelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__(command_attrs={
            'help': 'Show this help message',
            'aliases': ['guide']
        })

    async def send_bot_help(self, mapping):
        """This is the main !help command."""
        embed = discord.Embed(
            title="MLH ELO Bot - Command Reference",
            description="Here are all the available commands. Use `!help <command>` for more info on a specific command.",
            color=0x3498db
        )

        for cog, commands in mapping.items():
            if cog and commands:
                command_signatures = [f"`{self.get_command_signature(c)}`" for c in commands]
                if command_signatures:
                    cog_name = getattr(cog, "qualified_name", "No Category")
                    embed.add_field(name=f"**{cog_name}**", value="\n".join(command_signatures), inline=False)
        
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        """This is the !help <command> command."""
        embed = discord.Embed(
            title=f"Help: `!{command.name}`",
            description=command.help or "No description provided.",
            color=0x3498db
        )
        embed.add_field(name="Usage", value=f"`{self.get_command_signature(command)}`")
        if command.aliases:
            embed.add_field(name="Aliases", value=", ".join(f"`{alias}`" for alias in command.aliases), inline=False)
            
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        """This is the !help <group> command."""
        embed = discord.Embed(
            title=f"Help: `!{group.name}`",
            description=group.help or "No description provided.",
            color=0x3498db
        )
        embed.add_field(name="Usage", value=f"`{self.get_command_signature(group)}`")
        if group.aliases:
            embed.add_field(name="Aliases", value=", ".join(f"`{alias}`" for alias in group.aliases))
        
        subcommand_signatures = [f"`{self.get_command_signature(c)}` - {c.short_doc}" for c in group.commands]
        if subcommand_signatures:
            embed.add_field(name="Subcommands", value="\n".join(subcommand_signatures), inline=False)

        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        """This is the !help <CogName> command."""
        commands = cog.get_commands()
        if not commands:
            await self.get_destination().send(f"No commands found in `{cog.qualified_name}`.")
            return

        embed = discord.Embed(
            title=f"Help: {cog.qualified_name}",
            description=cog.description or f"Commands in the {cog.qualified_name} category.",
            color=0x3498db
        )
        
        command_signatures = [f"`{self.get_command_signature(c)}` - {c.short_doc}" for c in commands]
        embed.add_field(name="Commands", value="\n".join(command_signatures), inline=False)
        
        await self.get_destination().send(embed=embed)

class HelpCog(commands.Cog, name="Help"):
    def __init__(self, bot):
        self._original_help_command = bot.help_command
        bot.help_command = CustomHelpCommand()
        bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self._original_help_command

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
