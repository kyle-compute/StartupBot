import discord
from discord.ext import commands
from datetime import datetime
from utils.db import db_manager
from utils.elo import ELOEngine
from utils.ui import DifficultyVotingView

class ChallengesCog(commands.Cog, name="Challenges"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='challenge')
    async def issue_challenge(self, ctx, category: str, difficulty: int, *, description: str):
        """Issue a new challenge with difficulty voting"""
        if difficulty < 100 or difficulty > 2000:
            await ctx.send("❌ Difficulty must be between 100 and 2000")
            return
        
        if len(description) > 500:
            await ctx.send("❌ Description must be 500 characters or less")
            return
        
        await db_manager.ensure_user_exists(ctx.author.id, ctx.guild.id)
        
        async with db_manager.db_pool.acquire() as conn:
            category_id = await conn.fetchval(
                'SELECT id FROM categories WHERE guild_id = $1 AND name = $2',
                ctx.guild.id, category
            )
            
            if not category_id:
                await ctx.send(f"❌ Category '{category}' not found. Use `!categories` to see available categories.")
                return
        
        sprint = await db_manager.get_active_sprint(ctx.guild.id)
        if not sprint:
            config = await db_manager.get_guild_config(ctx.guild.id)
            sprint_id = await db_manager.create_sprint(ctx.guild.id, config['sprint_duration_days'])
        else:
            sprint_id = sprint['id']
        
        challenge_id = await db_manager.generate_challenge_id()
        
        async with db_manager.db_pool.acquire() as conn:
            await conn.execute(
                '''INSERT INTO challenges (challenge_id, user_id, guild_id, sprint_id, category_id, title, description, base_difficulty_elo)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8)''',
                challenge_id, ctx.author.id, ctx.guild.id, sprint_id, category_id, description, description, difficulty
            )
            
            await conn.execute(
                'UPDATE users SET total_challenges = total_challenges + 1 WHERE user_id = $1 AND guild_id = $2',
                ctx.author.id, ctx.guild.id
            )
        
        config = await db_manager.get_guild_config(ctx.guild.id)
        voting_channel_id = config.get('difficulty_voting_channel_id')
        
        if voting_channel_id:
            voting_channel = self.bot.get_channel(voting_channel_id)
            if voting_channel:
                embed = discord.Embed(title="⚖️ Difficulty Voting", color=0x9b59b6)
                embed.add_field(name="Challenge ID", value=challenge_id, inline=True)
                embed.add_field(name="Category", value=category, inline=True)
                embed.add_field(name="Base Difficulty", value=f"{difficulty} ELO", inline=True)
                embed.add_field(name="Description", value=description, inline=False)
                embed.add_field(name="Challenger", value=ctx.author.mention, inline=True)
                embed.add_field(name="Voting", value="Use the buttons below to vote on difficulty adjustment:\n-10 ELO | +10 ELO\n\nYou can only vote once!", inline=False)
                
                view = DifficultyVotingView(challenge_id, difficulty)
                voting_message = await voting_channel.send(embed=embed, view=view)
                
                async with db_manager.db_pool.acquire() as conn:
                    await conn.execute(
                        'UPDATE challenges SET difficulty_voting_message_id = $1 WHERE challenge_id = $2',
                        voting_message.id, challenge_id
                    )
        
        embed = discord.Embed(title="🎯 New Challenge Issued!", color=0xe74c3c)
        embed.add_field(name="ID", value=challenge_id, inline=True)
        embed.add_field(name="Category", value=category, inline=True)
        embed.add_field(name="Base Difficulty", value=f"{difficulty} ELO", inline=True)
        embed.add_field(name="Description", value=description, inline=False)
        embed.add_field(name="Challenger", value=ctx.author.mention, inline=True)
        
        if voting_channel_id:
            embed.add_field(name="Status", value="⏳ Pending difficulty voting", inline=False)
        else:
            embed.add_field(name="Status", value="✅ Active (no voting channel configured)", inline=False)
            async with db_manager.db_pool.acquire() as conn:
                await conn.execute(
                    'UPDATE challenges SET status = $1, final_difficulty_elo = $2, difficulty_voting_active = $3 WHERE challenge_id = $4',
                    'active', difficulty, False, challenge_id
                )
        
        await ctx.send(embed=embed)

    @commands.command(name='challenges')
    async def list_challenges(self, ctx, status: str = "active"):
        """List challenges by status"""
        valid_statuses = ['pending_difficulty', 'active', 'pending_review', 'completed', 'failed', 'rejected']
        if status not in valid_statuses:
            await ctx.send(f"❌ Invalid status. Use: {', '.join(valid_statuses)}")
            return
        
        async with db_manager.db_pool.acquire() as conn:
            challenges = await conn.fetch(
                '''SELECT c.challenge_id, c.title, 
                          COALESCE(c.final_difficulty_elo, c.base_difficulty_elo) as difficulty_elo, 
                          c.status, c.created_at, 
                          cat.name as category, u.user_id
                   FROM challenges c
                   JOIN categories cat ON c.category_id = cat.id
                   JOIN users u ON c.user_id = u.user_id AND c.guild_id = u.guild_id
                   WHERE c.guild_id = $1 AND c.status = $2
                   ORDER BY c.created_at DESC
                   LIMIT 10''',
                ctx.guild.id, status
            )
        
        if not challenges:
            await ctx.send(f"No {status} challenges found.")
            return
        
        embed = discord.Embed(title=f"🎯 {status.title().replace('_', ' ')} Challenges", color=0x3498db)
        
        for challenge in challenges:
            user = self.bot.get_user(challenge['user_id'])
            username = user.display_name if user else "Unknown User"
            
            embed.add_field(
                name=f"[{challenge['challenge_id']}] {challenge['title'][:50]}...",
                value=f"**Category:** {challenge['category']} | **Difficulty:** {challenge['difficulty_elo']} | **User:** {username}",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name='complete')
    async def submit_completion(self, ctx, challenge_id: str, *, proof: str):
        """Submit a challenge for review"""
        if not proof.strip():
            await ctx.send("❌ Proof cannot be empty")
            return
        
        if len(proof) > 1000:
            await ctx.send("❌ Proof must be 1000 characters or less")
            return
        
        await db_manager.ensure_user_exists(ctx.author.id, ctx.guild.id)
        
        async with db_manager.db_pool.acquire() as conn:
            challenge = await conn.fetchrow(
                'SELECT * FROM challenges WHERE challenge_id = $1 AND user_id = $2 AND guild_id = $3',
                challenge_id, ctx.author.id, ctx.guild.id
            )
            
            if not challenge:
                await ctx.send(f"❌ Challenge {challenge_id} not found or doesn't belong to you.")
                return
            
            if challenge['status'] not in ['active', 'pending_difficulty']:
                await ctx.send(f"❌ Challenge {challenge_id} is not active (status: {challenge['status']})")
                return
            
            if challenge['status'] == 'pending_difficulty':
                if not challenge['final_difficulty_elo']:
                    await ctx.send(f"❌ Challenge {challenge_id} is still pending difficulty voting. Wait for voting to complete.")
                    return
                else:
                    await conn.execute(
                        'UPDATE challenges SET status = $1 WHERE challenge_id = $2',
                        'active', challenge_id
                    )
            
            await conn.execute(
                '''UPDATE challenges SET status = $1, proof_description = $2, completed_at = $3 
                   WHERE challenge_id = $4''',
                'pending_review', proof, datetime.utcnow(), challenge_id
            )
        
        config = await db_manager.get_guild_config(ctx.guild.id)
        if config.get('review_channel_id'):
            review_channel = self.bot.get_channel(config['review_channel_id'])
            if review_channel:
                embed = discord.Embed(title="📋 Challenge Submitted for Review", color=0xf39c12)
                embed.add_field(name="Challenge ID", value=challenge_id, inline=True)
                embed.add_field(name="User", value=ctx.author.mention, inline=True)
                embed.add_field(name="Proof", value=proof, inline=False)
                embed.add_field(name="Review Commands", value=f"`!approve {challenge_id}` or `!reject {challenge_id}`", inline=False)
                await review_channel.send(embed=embed)
        
        await ctx.send(f"✅ Challenge {challenge_id} submitted for review!")

    @commands.command(name='approve')
    async def approve_challenge(self, ctx, challenge_id: str, *, comment: str = None):
        """Approve a challenge submission"""
        await self.process_review(ctx, challenge_id, 'approve', comment)

    @commands.command(name='reject')
    async def reject_challenge(self, ctx, challenge_id: str, *, reason: str = None):
        """Reject a challenge submission"""
        await self.process_review(ctx, challenge_id, 'reject', reason)

    async def process_review(self, ctx, challenge_id: str, vote_type: str, comment: str = None):
        """Process challenge review vote"""
        await db_manager.ensure_user_exists(ctx.author.id, ctx.guild.id)
        
        async with db_manager.db_pool.acquire() as conn:
            challenge = await conn.fetchrow(
                'SELECT * FROM challenges WHERE challenge_id = $1 AND guild_id = $2',
                challenge_id, ctx.guild.id
            )
            
            if not challenge:
                await ctx.send(f"❌ Challenge {challenge_id} not found.")
                return
            
            if challenge['status'] != 'pending_review':
                await ctx.send(f"❌ Challenge {challenge_id} is not pending review (status: {challenge['status']})")
                return
            
            if challenge['user_id'] == ctx.author.id:
                await ctx.send("❌ You cannot review your own challenge.")
                return
            
            try:
                await conn.execute(
                    'INSERT INTO approvals (challenge_id, voter_id, guild_id, vote_type, comment) VALUES ($1, $2, $3, $4, $5)',
                    challenge['id'], ctx.author.id, ctx.guild.id, vote_type, comment
                )
            except Exception as e:
                if 'unique constraint' in str(e).lower():
                    await ctx.send(f"❌ You have already voted on challenge {challenge_id}.")
                    return
                raise
            
            config = await db_manager.get_guild_config(ctx.guild.id)
            approvals_needed = config['approvals_needed']
            
            votes = await conn.fetch(
                'SELECT vote_type FROM approvals WHERE challenge_id = $1',
                challenge['id']
            )
            
            approve_count = sum(1 for vote in votes if vote['vote_type'] == 'approve')
            reject_count = sum(1 for vote in votes if vote['vote_type'] == 'reject')
            
            if approve_count >= approvals_needed:
                await self.finalize_challenge(challenge, 'completed', conn)
                await ctx.send(f"✅ Challenge {challenge_id} approved and completed!")
            elif reject_count > 0:
                await self.finalize_challenge(challenge, 'rejected', conn)
                await ctx.send(f"❌ Challenge {challenge_id} rejected.")
            else:
                await ctx.send(f"✅ Vote recorded. Need {approvals_needed - approve_count} more approvals.")

    async def finalize_challenge(self, challenge, final_status: str, conn):
        """Finalize a challenge and update ELO"""
        await conn.execute(
            'UPDATE challenges SET status = $1, reviewed_at = $2 WHERE id = $3',
            final_status, datetime.utcnow(), challenge['id']
        )
        
        if final_status == 'completed':
            user = await conn.fetchrow(
                'SELECT * FROM users WHERE user_id = $1 AND guild_id = $2',
                challenge['user_id'], challenge['guild_id']
            )
            
            config = await db_manager.get_guild_config(challenge['guild_id'])
            
            k_factor = ELOEngine.get_k_factor(
                user['total_challenges'],
                config['k_factor_new'],
                config['k_factor_stable'],
                config['stable_user_threshold']
            )
            
            challenge_difficulty = challenge.get('final_difficulty_elo') or challenge.get('base_difficulty_elo')
            
            expected_score = ELOEngine.calculate_expected_score(
                user['current_elo'], challenge_difficulty
            )
            
            new_elo = ELOEngine.calculate_new_elo(
                user['current_elo'], expected_score, 1, k_factor
            )
            
            elo_change = new_elo - user['current_elo']
            
            await conn.execute(
                'UPDATE users SET current_elo = $1, completed_challenges = completed_challenges + 1 WHERE user_id = $2 AND guild_id = $3',
                new_elo, challenge['user_id'], challenge['guild_id']
            )
            
            await conn.execute(
                'INSERT INTO elo_history (user_id, guild_id, challenge_id, elo_before, elo_after, elo_change, reason) VALUES ($1, $2, $3, $4, $5, $6, $7)',
                challenge['user_id'], challenge['guild_id'], challenge['id'],
                user['current_elo'], new_elo, elo_change, 'challenge_completed'
            )

async def setup(bot):
    await bot.add_cog(ChallengesCog(bot)) 