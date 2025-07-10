import discord
from discord import app_commands
from discord.ext import commands
from utils.db import db_manager
import re

class PrerequisiteModal(discord.ui.Modal, title="Add Prerequisite"):
    def __init__(self, target_message: discord.Message):
        super().__init__()
        self.target_message = target_message

    prerequisite_link = discord.ui.TextInput(
        label="Prerequisite Message Link or ID",
        style=discord.TextStyle.short,
        placeholder="https://discord.com/channels/... or message ID",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        message_link_regex = re.compile(r"(?:https://discord\.com/channels/(\d+)/(\d+)/)?(\d+)")
        match = message_link_regex.match(self.prerequisite_link.value)

        if not match:
            await interaction.response.send_message("❌ Invalid message link or ID format.", ephemeral=True)
            return

        guild_id, channel_id, message_id = match.groups()
        prereq_message_id = int(message_id)

        try:
            if channel_id:
                prereq_channel_id = int(channel_id)
                prereq_channel = self.target_message.guild.get_channel(prereq_channel_id)
                if not prereq_channel:
                    await interaction.response.send_message("❌ I can't access that channel.", ephemeral=True)
                    return
            else:
                prereq_channel = self.target_message.channel
            
            prereq_message = await prereq_channel.fetch_message(prereq_message_id)

        except (discord.NotFound, discord.Forbidden):
            await interaction.response.send_message("❌ Could not find or access the prerequisite message.", ephemeral=True)
            return

        try:
            async with db_manager.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO prerequisites (guild_id, channel_id, message_id, prerequisite_channel_id, prerequisite_message_id)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    interaction.guild.id,
                    self.target_message.channel.id,
                    self.target_message.id,
                    prereq_message.channel.id,
                    prereq_message.id
                )
            await interaction.response.send_message(f"✅ Prerequisite set: [this message]({self.target_message.jump_url}) now requires [this message]({prereq_message.jump_url}).", ephemeral=True)
        except Exception as e:
            if 'unique constraint' in str(e).lower():
                await interaction.response.send_message("❌ This prerequisite link already exists.", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)


class PrereqCog(commands.Cog, name="Prereq"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.add_prereq_context_menu = app_commands.ContextMenu(
            name="Add Prerequisite",
            callback=self.add_prereq_callback,
        )
        self.view_prereqs_context_menu = app_commands.ContextMenu(
            name="View Prerequisites",
            callback=self.view_prereqs_callback,
        )
        self.bot.tree.add_command(self.add_prereq_context_menu)
        self.bot.tree.add_command(self.view_prereqs_context_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.add_prereq_context_menu.name, type=self.add_prereq_context_menu.type)
        self.bot.tree.remove_command(self.view_prereqs_context_menu.name, type=self.view_prereqs_context_menu.type)

    async def add_prereq_callback(self, interaction: discord.Interaction, message: discord.Message):
        modal = PrerequisiteModal(target_message=message)
        await interaction.response.send_modal(modal)

    async def view_prereqs_callback(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer(ephemeral=True)

        chain = []
        current_message = message
        visited = set()

        while current_message and current_message.id not in visited:
            visited.add(current_message.id)
            chain.append(current_message)
            
            async with db_manager.db_pool.acquire() as conn:
                prereq_record = await conn.fetchrow(
                    "SELECT prerequisite_channel_id, prerequisite_message_id FROM prerequisites WHERE message_id = $1",
                    current_message.id
                )
            
            if not prereq_record:
                break

            prereq_channel_id = prereq_record['prerequisite_channel_id']
            prereq_message_id = prereq_record['prerequisite_message_id']
            
            try:
                channel = interaction.guild.get_channel(prereq_channel_id)
                if not channel: break
                current_message = await channel.fetch_message(prereq_message_id)
            except (discord.NotFound, discord.Forbidden):
                break
        
        if len(chain) <= 1 and not prereq_record:
            await interaction.followup.send("This message has no prerequisites.", ephemeral=True)
            return
        
        embed = discord.Embed(title="Prerequisite Chain", description=f"For message: [link]({message.jump_url})", color=0x3498db)
        
        description = ""
        for i, msg in enumerate(reversed(chain)):
            indent = " " * (i * 2)
            arrow = "↳ " if i > 0 else ""
            description += f"{indent}{arrow}[{msg.channel.name[:15]}: {msg.content[:50]}...]({msg.jump_url})\n"
        
        embed.description = description
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(PrereqCog(bot)) 