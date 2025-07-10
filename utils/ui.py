import discord
from utils.db import db_manager

class DifficultyVotingView(discord.ui.View):
    def __init__(self, challenge_id: str, base_difficulty: int):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.challenge_id = challenge_id
        self.base_difficulty = base_difficulty
    
    @discord.ui.button(label='-10 ELO', style=discord.ButtonStyle.red, emoji='⬇️')
    async def vote_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_vote(interaction, -10)
    
    @discord.ui.button(label='+10 ELO', style=discord.ButtonStyle.green, emoji='⬆️')
    async def vote_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_vote(interaction, 10)
    
    @discord.ui.button(label='Finalize Voting', style=discord.ButtonStyle.primary, emoji='✅')
    async def finalize_voting(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Only administrators can finalize voting", ephemeral=True)
            return
        
        await self.finish_voting(interaction)
    
    async def process_vote(self, interaction: discord.Interaction, adjustment: int):
        async with db_manager.db_pool.acquire() as conn:
            # Check if user already voted
            existing_vote = await conn.fetchrow(
                'SELECT * FROM difficulty_votes WHERE challenge_id = (SELECT id FROM challenges WHERE challenge_id = $1) AND voter_id = $2',
                self.challenge_id, interaction.user.id
            )
            
            if existing_vote:
                await interaction.response.send_message("❌ You have already voted on this challenge's difficulty!", ephemeral=True)
                return
            
            # Get challenge database ID
            challenge_db_id = await conn.fetchval(
                'SELECT id FROM challenges WHERE challenge_id = $1',
                self.challenge_id
            )
            
            if not challenge_db_id:
                await interaction.response.send_message("❌ Challenge not found", ephemeral=True)
                return
            
            # Record vote
            await conn.execute(
                'INSERT INTO difficulty_votes (challenge_id, voter_id, guild_id, vote_adjustment) VALUES ($1, $2, $3, $4)',
                challenge_db_id, interaction.user.id, interaction.guild.id, adjustment
            )
            
            # Get current vote tally
            votes = await conn.fetch(
                'SELECT vote_adjustment FROM difficulty_votes WHERE challenge_id = $1',
                challenge_db_id
            )
            
            total_adjustment = sum(vote['vote_adjustment'] for vote in votes)
            final_difficulty = max(100, min(2000, self.base_difficulty + total_adjustment))
            vote_count = len(votes)
            
            # Update embed with current voting status
            embed = discord.Embed(title="⚖️ Difficulty Voting", color=0x9b59b6)
            embed.add_field(name="Challenge ID", value=self.challenge_id, inline=True)
            embed.add_field(name="Base Difficulty", value=f"{self.base_difficulty} ELO", inline=True)
            embed.add_field(name="Current Adjustment", value=f"{total_adjustment:+d} ELO", inline=True)
            embed.add_field(name="Projected Final", value=f"{final_difficulty} ELO", inline=True)
            embed.add_field(name="Total Votes", value=str(vote_count), inline=True)
            embed.add_field(name="Status", value="🗳️ Voting in progress", inline=True)
            
            await interaction.response.edit_message(embed=embed, view=self)
    
    async def finish_voting(self, interaction: discord.Interaction):
        async with db_manager.db_pool.acquire() as conn:
            # Get challenge database ID
            challenge_db_id = await conn.fetchval(
                'SELECT id FROM challenges WHERE challenge_id = $1',
                self.challenge_id
            )
            
            # Calculate final difficulty
            votes = await conn.fetch(
                'SELECT vote_adjustment FROM difficulty_votes WHERE challenge_id = $1',
                challenge_db_id
            )
            
            total_adjustment = sum(vote['vote_adjustment'] for vote in votes) if votes else 0
            final_difficulty = max(100, min(2000, self.base_difficulty + total_adjustment))
            
            # Update challenge status
            await conn.execute(
                'UPDATE challenges SET status = $1, final_difficulty_elo = $2, difficulty_voting_active = $3 WHERE challenge_id = $4',
                'active', final_difficulty, False, self.challenge_id
            )
            
            # Update embed to show finalized result
            embed = discord.Embed(title="✅ Difficulty Voting Finalized", color=0x27ae60)
            embed.add_field(name="Challenge ID", value=self.challenge_id, inline=True)
            embed.add_field(name="Base Difficulty", value=f"{self.base_difficulty} ELO", inline=True)
            embed.add_field(name="Final Adjustment", value=f"{total_adjustment:+d} ELO", inline=True)
            embed.add_field(name="Final Difficulty", value=f"{final_difficulty} ELO", inline=True)
            embed.add_field(name="Total Votes", value=str(len(votes)), inline=True)
            embed.add_field(name="Status", value="🎯 Challenge now active!", inline=True)
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            await interaction.response.edit_message(embed=embed, view=self) 