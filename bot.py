import discord
from discord.ext import commands, tasks
import asyncio
import asyncpg
import os
import pytz
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
import logging
import random
import string
from typing import Optional, Dict, Any

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Scheduler setup
scheduler = AsyncIOScheduler()

class ELOEngine:
    """Handles ELO calculations and rating updates"""
    
    @staticmethod
    def calculate_expected_score(player_elo: int, opponent_elo: int) -> float:
        """Calculate expected score using ELO formula"""
        return 1 / (1 + 10 ** ((opponent_elo - player_elo) / 400))
    
    @staticmethod
    def calculate_new_elo(current_elo: int, expected_score: float, actual_score: int, k_factor: int) -> int:
        """Calculate new ELO rating"""
        return int(current_elo + k_factor * (actual_score - expected_score))
    
    @staticmethod
    def get_k_factor(total_challenges: int, k_factor_new: int, k_factor_stable: int, stable_threshold: int) -> int:
        """Determine K-factor based on user experience"""
        return k_factor_new if total_challenges < stable_threshold else k_factor_stable

class AccountabilityBot:
    def __init__(self):
        self.db_pool = None
        
    async def init_db(self):
        """Initialize database connection pool"""
        try:
            self.db_pool = await asyncpg.create_pool(
                host=os.getenv('DB_HOST', 'postgres'),
                port=int(os.getenv('DB_PORT', 5432)),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASSWORD'),
                database=os.getenv('DB_NAME', 'accountability'),
                min_size=1,
                max_size=10
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
        
    async def get_guild_config(self, guild_id: int) -> Dict[str, Any]:
        """Get guild configuration with defaults"""
        async with self.db_pool.acquire() as conn:
            config = await conn.fetchrow(
                'SELECT * FROM guild_config WHERE guild_id = $1',
                guild_id
            )
            if not config:
                # Create default config
                await conn.execute(
                    '''INSERT INTO guild_config (guild_id) VALUES ($1) 
                       ON CONFLICT (guild_id) DO NOTHING''',
                    guild_id
                )
                config = await conn.fetchrow(
                    'SELECT * FROM guild_config WHERE guild_id = $1',
                    guild_id
                )
            return dict(config)
    
    async def ensure_user_exists(self, user_id: int, guild_id: int):
        """Ensure user exists in database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                '''INSERT INTO users (user_id, guild_id) VALUES ($1, $2) 
                   ON CONFLICT (user_id, guild_id) DO NOTHING''',
                user_id, guild_id
            )
    
    async def generate_challenge_id(self) -> str:
        """Generate unique challenge ID"""
        while True:
            challenge_id = 'CHL-' + ''.join(random.choices(string.digits, k=3))
            async with self.db_pool.acquire() as conn:
                exists = await conn.fetchval(
                    'SELECT 1 FROM challenges WHERE challenge_id = $1',
                    challenge_id
                )
                if not exists:
                    return challenge_id
    
    async def get_active_sprint(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get current active sprint for guild"""
        async with self.db_pool.acquire() as conn:
            sprint = await conn.fetchrow(
                'SELECT * FROM sprints WHERE guild_id = $1 AND status = $2 ORDER BY start_date DESC LIMIT 1',
                guild_id, 'active'
            )
            return dict(sprint) if sprint else None
    
    async def create_sprint(self, guild_id: int, duration_days: int = 7) -> int:
        """Create new sprint"""
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=duration_days)
        
        async with self.db_pool.acquire() as conn:
            # End current sprint if any
            await conn.execute(
                'UPDATE sprints SET status = $1 WHERE guild_id = $2 AND status = $3',
                'ended', guild_id, 'active'
            )
            
            # Create new sprint
            sprint_id = await conn.fetchval(
                'INSERT INTO sprints (guild_id, start_date, end_date) VALUES ($1, $2, $3) RETURNING id',
                guild_id, start_date, end_date
            )
            return sprint_id

accountability = AccountabilityBot()

@bot.event
async def on_ready():
    logger.info(f'{bot.user} is now online!')
    await accountability.init_db()
    scheduler.start()
    auto_sprint_management.start()
    
    # Initialize default categories for new guilds
    for guild in bot.guilds:
        await init_default_categories(guild.id)

@bot.command(name='category')
async def category_command(ctx, action: str, *, args: str = None):
    """Manage challenge categories"""
    if action.lower() == 'add':
        if not args:
            await ctx.send("Usage: `!category add <name> [description]`")
            return
            
        parts = args.split(' ', 1)
        name = parts[0]
        description = parts[1] if len(parts) > 1 else None
        
        if len(name) > 50:
            await ctx.send("❌ Category name must be 50 characters or less")
            return
        
        await accountability.ensure_user_exists(ctx.author.id, ctx.guild.id)
        
        async with accountability.db_pool.acquire() as conn:
            try:
                await conn.execute(
                    'INSERT INTO categories (guild_id, name, description) VALUES ($1, $2, $3)',
                    ctx.guild.id, name, description
                )
                await ctx.send(f"✅ Category '{name}' created successfully!")
            except Exception as e:
                if 'unique constraint' in str(e).lower():
                    await ctx.send(f"❌ Category '{name}' already exists!")
                else:
                    await ctx.send(f"❌ Error creating category: {str(e)}")
    else:
        await ctx.send("Usage: `!category add <name> [description]`")

@bot.command(name='categories')
async def list_categories(ctx):
    """List all available challenge categories"""
    async with accountability.db_pool.acquire() as conn:
        categories = await conn.fetch(
            'SELECT name, description FROM categories WHERE guild_id = $1 ORDER BY name',
            ctx.guild.id
        )
    
    if not categories:
        await ctx.send("No categories found. Use `!category add <name> [description]` to create one.")
        return
    
    embed = discord.Embed(title="📂 Challenge Categories", color=0x3498db)
    for cat in categories:
        embed.add_field(
            name=cat['name'],
            value=cat['description'] or "No description",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='challenge')
async def issue_challenge(ctx, category: str, difficulty: int, *, description: str):
    """Issue a new challenge"""
    if difficulty < 100 or difficulty > 2000:
        await ctx.send("❌ Difficulty must be between 100 and 2000")
        return
    
    if len(description) > 500:
        await ctx.send("❌ Description must be 500 characters or less")
        return
    
    await accountability.ensure_user_exists(ctx.author.id, ctx.guild.id)
    
    # Check if category exists
    async with accountability.db_pool.acquire() as conn:
        category_id = await conn.fetchval(
            'SELECT id FROM categories WHERE guild_id = $1 AND name = $2',
            ctx.guild.id, category
        )
        
        if not category_id:
            await ctx.send(f"❌ Category '{category}' not found. Use `!categories` to see available categories.")
            return
    
    # Get active sprint
    sprint = await accountability.get_active_sprint(ctx.guild.id)
    if not sprint:
        config = await accountability.get_guild_config(ctx.guild.id)
        sprint_id = await accountability.create_sprint(ctx.guild.id, config['sprint_duration_days'])
    else:
        sprint_id = sprint['id']
    
    # Create challenge
    challenge_id = await accountability.generate_challenge_id()
    
    async with accountability.db_pool.acquire() as conn:
        await conn.execute(
            '''INSERT INTO challenges (challenge_id, user_id, guild_id, sprint_id, category_id, title, description, difficulty_elo)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)''',
            challenge_id, ctx.author.id, ctx.guild.id, sprint_id, category_id, description, description, difficulty
        )
        
        # Update user stats
        await conn.execute(
            'UPDATE users SET total_challenges = total_challenges + 1 WHERE user_id = $1 AND guild_id = $2',
            ctx.author.id, ctx.guild.id
        )
    
    embed = discord.Embed(title="🎯 New Challenge Issued!", color=0xe74c3c)
    embed.add_field(name="ID", value=challenge_id, inline=True)
    embed.add_field(name="Category", value=category, inline=True)
    embed.add_field(name="Difficulty", value=f"{difficulty} ELO", inline=True)
    embed.add_field(name="Description", value=description, inline=False)
    embed.add_field(name="Challenger", value=ctx.author.mention, inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='challenges')
async def list_challenges(ctx, status: str = "active"):
    """List challenges by status"""
    valid_statuses = ['active', 'pending_review', 'completed', 'failed', 'rejected']
    if status not in valid_statuses:
        await ctx.send(f"❌ Invalid status. Use: {', '.join(valid_statuses)}")
        return
    
    async with accountability.db_pool.acquire() as conn:
        challenges = await conn.fetch(
            '''SELECT c.challenge_id, c.title, c.difficulty_elo, c.status, c.created_at, 
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
        user = bot.get_user(challenge['user_id'])
        username = user.display_name if user else "Unknown User"
        
        embed.add_field(
            name=f"[{challenge['challenge_id']}] {challenge['title'][:50]}...",
            value=f"**Category:** {challenge['category']} | **Difficulty:** {challenge['difficulty_elo']} | **User:** {username}",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='complete')
async def submit_completion(ctx, challenge_id: str, *, proof: str):
    """Submit a challenge for review"""
    if not proof.strip():
        await ctx.send("❌ Proof cannot be empty")
        return
    
    if len(proof) > 1000:
        await ctx.send("❌ Proof must be 1000 characters or less")
        return
    
    await accountability.ensure_user_exists(ctx.author.id, ctx.guild.id)
    
    async with accountability.db_pool.acquire() as conn:
        # Check if challenge exists and belongs to user
        challenge = await conn.fetchrow(
            'SELECT * FROM challenges WHERE challenge_id = $1 AND user_id = $2 AND guild_id = $3',
            challenge_id, ctx.author.id, ctx.guild.id
        )
        
        if not challenge:
            await ctx.send(f"❌ Challenge {challenge_id} not found or doesn't belong to you.")
            return
        
        if challenge['status'] != 'active':
            await ctx.send(f"❌ Challenge {challenge_id} is not active (status: {challenge['status']})")
            return
        
        # Update challenge with proof
        await conn.execute(
            '''UPDATE challenges SET status = $1, proof_description = $2, completed_at = $3 
               WHERE challenge_id = $4''',
            'pending_review', proof, datetime.utcnow(), challenge_id
        )
    
    # Notify review channel if configured
    config = await accountability.get_guild_config(ctx.guild.id)
    if config.get('review_channel_id'):
        review_channel = bot.get_channel(config['review_channel_id'])
        if review_channel:
            embed = discord.Embed(title="📋 Challenge Submitted for Review", color=0xf39c12)
            embed.add_field(name="Challenge ID", value=challenge_id, inline=True)
            embed.add_field(name="User", value=ctx.author.mention, inline=True)
            embed.add_field(name="Proof", value=proof, inline=False)
            embed.add_field(name="Review Commands", value=f"`!approve {challenge_id}` or `!reject {challenge_id}`", inline=False)
            await review_channel.send(embed=embed)
    
    await ctx.send(f"✅ Challenge {challenge_id} submitted for review!")

@bot.command(name='approve')
async def approve_challenge(ctx, challenge_id: str, *, comment: str = None):
    """Approve a challenge submission"""
    await process_review(ctx, challenge_id, 'approve', comment)

@bot.command(name='reject')
async def reject_challenge(ctx, challenge_id: str, *, reason: str = None):
    """Reject a challenge submission"""
    await process_review(ctx, challenge_id, 'reject', reason)

async def process_review(ctx, challenge_id: str, vote_type: str, comment: str = None):
    """Process challenge review vote"""
    await accountability.ensure_user_exists(ctx.author.id, ctx.guild.id)
    
    async with accountability.db_pool.acquire() as conn:
        # Check if challenge exists and is pending review
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
        
        # Record the vote
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
        
        # Check if we have enough votes to finalize
        config = await accountability.get_guild_config(ctx.guild.id)
        approvals_needed = config['approvals_needed']
        
        votes = await conn.fetch(
            'SELECT vote_type FROM approvals WHERE challenge_id = $1',
            challenge['id']
        )
        
        approve_count = sum(1 for vote in votes if vote['vote_type'] == 'approve')
        reject_count = sum(1 for vote in votes if vote['vote_type'] == 'reject')
        
        # Finalize if we have enough approvals or any rejection
        if approve_count >= approvals_needed:
            await finalize_challenge(challenge, 'completed', conn)
            await ctx.send(f"✅ Challenge {challenge_id} approved and completed!")
        elif reject_count > 0:
            await finalize_challenge(challenge, 'rejected', conn)
            await ctx.send(f"❌ Challenge {challenge_id} rejected.")
        else:
            await ctx.send(f"✅ Vote recorded. Need {approvals_needed - approve_count} more approvals.")

async def finalize_challenge(challenge, final_status: str, conn):
    """Finalize a challenge and update ELO"""
    # Update challenge status
    await conn.execute(
        'UPDATE challenges SET status = $1, reviewed_at = $2 WHERE id = $3',
        final_status, datetime.utcnow(), challenge['id']
    )
    
    # Update ELO if completed
    if final_status == 'completed':
        # Get user's current ELO and stats
        user = await conn.fetchrow(
            'SELECT * FROM users WHERE user_id = $1 AND guild_id = $2',
            challenge['user_id'], challenge['guild_id']
        )
        
        config = await accountability.get_guild_config(challenge['guild_id'])
        
        # Calculate ELO change
        k_factor = ELOEngine.get_k_factor(
            user['total_challenges'],
            config['k_factor_new'],
            config['k_factor_stable'],
            config['stable_user_threshold']
        )
        
        expected_score = ELOEngine.calculate_expected_score(
            user['current_elo'], challenge['difficulty_elo']
        )
        
        new_elo = ELOEngine.calculate_new_elo(
            user['current_elo'], expected_score, 1, k_factor
        )
        
        elo_change = new_elo - user['current_elo']
        
        # Update user ELO
        await conn.execute(
            'UPDATE users SET current_elo = $1, completed_challenges = completed_challenges + 1 WHERE user_id = $2 AND guild_id = $3',
            new_elo, challenge['user_id'], challenge['guild_id']
        )
        
        # Record ELO history
        await conn.execute(
            'INSERT INTO elo_history (user_id, guild_id, challenge_id, elo_before, elo_after, elo_change, reason) VALUES ($1, $2, $3, $4, $5, $6, $7)',
            challenge['user_id'], challenge['guild_id'], challenge['id'],
            user['current_elo'], new_elo, elo_change, 'challenge_completed'
        )

@bot.command(name='leaderboard', aliases=['lb'])
async def leaderboard(ctx, time_period: str = "weekly"):
    """Show leaderboard for weekly or all-time"""
    if time_period.lower() not in ['weekly', 'alltime', 'all-time']:
        await ctx.send("❌ Use `weekly` or `alltime` for time period")
        return
    
    async with accountability.db_pool.acquire() as conn:
        if time_period.lower() == 'weekly':
            # Get current sprint leaderboard
            sprint = await accountability.get_active_sprint(ctx.guild.id)
            if not sprint:
                await ctx.send("No active sprint found.")
                return
            
            # Calculate weekly ELO gains
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
            # All-time leaderboard
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
                user = bot.get_user(row['user_id'])
                username = user.display_name if user else "Unknown User"
                
                if time_period.lower() == 'weekly':
                    leaderboard_text += f"**{i}.** {username} - {row['current_elo']} ELO (+{row['weekly_gain']}) | {row['weekly_completed']}/{row['weekly_challenges']} completed\n"
                else:
                    completion_rate = (row['completed_challenges'] / row['total_challenges'] * 100) if row['total_challenges'] > 0 else 0
                    leaderboard_text += f"**{i}.** {username} - {row['current_elo']} ELO | {row['completed_challenges']}/{row['total_challenges']} ({completion_rate:.1f}%)\n"
            
            embed.add_field(name="Rankings", value=leaderboard_text, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='profile')
async def user_profile(ctx, user: discord.Member = None):
    """Show user profile and stats"""
    target_user = user or ctx.author
    await accountability.ensure_user_exists(target_user.id, ctx.guild.id)
    
    async with accountability.db_pool.acquire() as conn:
        # Get user data
        user_data = await conn.fetchrow(
            'SELECT * FROM users WHERE user_id = $1 AND guild_id = $2',
            target_user.id, ctx.guild.id
        )
        
        # Get recent challenges
        recent_challenges = await conn.fetch(
            '''SELECT c.challenge_id, c.title, c.difficulty_elo, c.status, c.created_at,
                      cat.name as category
               FROM challenges c
               JOIN categories cat ON c.category_id = cat.id
               WHERE c.user_id = $1 AND c.guild_id = $2
               ORDER BY c.created_at DESC
               LIMIT 5''',
            target_user.id, ctx.guild.id
        )
        
        # Get ELO history
        elo_history = await conn.fetch(
            'SELECT elo_before, elo_after, elo_change, created_at FROM elo_history WHERE user_id = $1 AND guild_id = $2 ORDER BY created_at DESC LIMIT 10',
            target_user.id, ctx.guild.id
        )
    
    embed = discord.Embed(title=f"📊 {target_user.display_name}'s Profile", color=0x9b59b6)
    
    # Basic stats
    completion_rate = (user_data['completed_challenges'] / user_data['total_challenges'] * 100) if user_data['total_challenges'] > 0 else 0
    embed.add_field(name="Current ELO", value=str(user_data['current_elo']), inline=True)
    embed.add_field(name="Total Challenges", value=str(user_data['total_challenges']), inline=True)
    embed.add_field(name="Completion Rate", value=f"{completion_rate:.1f}%", inline=True)
    
    # Recent challenges
    if recent_challenges:
        challenges_text = ""
        for challenge in recent_challenges:
            status_emoji = {"active": "🟡", "pending_review": "🟠", "completed": "✅", "failed": "❌", "rejected": "🔴"}
            emoji = status_emoji.get(challenge['status'], "❓")
            challenges_text += f"{emoji} [{challenge['challenge_id']}] {challenge['title'][:30]}... ({challenge['difficulty_elo']} ELO)\n"
        
        embed.add_field(name="Recent Challenges", value=challenges_text, inline=False)
    
    # ELO trend
    if elo_history:
        elo_trend = "📈 ELO History:\n"
        for i, entry in enumerate(elo_history[:5]):
            change_str = f"+{entry['elo_change']}" if entry['elo_change'] > 0 else str(entry['elo_change'])
            elo_trend += f"{entry['elo_before']} → {entry['elo_after']} ({change_str})\n"
        
        embed.add_field(name="ELO Trend", value=elo_trend, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='sprint')
async def sprint_management(ctx, action: str = None):
    """Manage sprint cycles (Admin only)"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Administrator permissions required")
        return
    
    if action == "start":
        config = await accountability.get_guild_config(ctx.guild.id)
        sprint_id = await accountability.create_sprint(ctx.guild.id, config['sprint_duration_days'])
        await ctx.send(f"✅ New sprint started! Sprint ID: {sprint_id}")
    
    elif action == "end":
        async with accountability.db_pool.acquire() as conn:
            await conn.execute(
                'UPDATE sprints SET status = $1 WHERE guild_id = $2 AND status = $3',
                'ended', ctx.guild.id, 'active'
            )
        await ctx.send("✅ Current sprint ended!")
    
    elif action == "status":
        sprint = await accountability.get_active_sprint(ctx.guild.id)
        if sprint:
            embed = discord.Embed(title="🏃 Current Sprint Status", color=0x2ecc71)
            embed.add_field(name="Sprint ID", value=sprint['id'], inline=True)
            embed.add_field(name="Started", value=sprint['start_date'].strftime('%Y-%m-%d %H:%M'), inline=True)
            embed.add_field(name="Ends", value=sprint['end_date'].strftime('%Y-%m-%d %H:%M'), inline=True)
            
            days_left = (sprint['end_date'] - datetime.utcnow()).days
            embed.add_field(name="Days Remaining", value=str(days_left), inline=True)
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("No active sprint found.")
    
    else:
        await ctx.send("Usage: `!sprint start|end|status`")

@bot.command(name='config')
async def guild_config(ctx, action: str = None, key: str = None, value: str = None):
    """Configure guild settings (Admin only)"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Administrator permissions required")
        return
    
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
                
            async with accountability.db_pool.acquire() as conn:
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
            channel = bot.get_channel(channel_id)
            if not channel:
                await ctx.send("❌ Channel not found")
                return
                
            async with accountability.db_pool.acquire() as conn:
                await conn.execute(
                    'UPDATE guild_config SET review_channel_id = $1 WHERE guild_id = $2',
                    channel_id, ctx.guild.id
                )
            await ctx.send(f"✅ Set review channel to <#{channel_id}>")
        except ValueError:
            await ctx.send("❌ Invalid channel")
    
    elif action == "show":
        config = await accountability.get_guild_config(ctx.guild.id)
        embed = discord.Embed(title="⚙️ Guild Configuration", color=0x95a5a6)
        
        for key, value in config.items():
            if key not in ['guild_id', 'created_at', 'updated_at']:
                embed.add_field(name=key, value=str(value), inline=True)
        
        await ctx.send(embed=embed)
    
    else:
        await ctx.send("Usage: `!config set <key> <value>` or `!config channel review #channel` or `!config show`")

async def init_default_categories(guild_id: int):
    """Initialize default categories for a guild"""
    default_categories = [
        ('Backend', 'Server-side development, databases, APIs'),
        ('Frontend', 'User interface, web development, mobile apps'),
        ('DevOps', 'Infrastructure, deployment, monitoring'),
        ('Learning', 'Acquiring new skills, studying, research'),
        ('Refactoring', 'Code improvement, optimization, cleanup'),
        ('Testing', 'Writing tests, debugging, quality assurance')
    ]
    
    async with accountability.db_pool.acquire() as conn:
        for name, description in default_categories:
            await conn.execute(
                'INSERT INTO categories (guild_id, name, description) VALUES ($1, $2, $3) ON CONFLICT (guild_id, name) DO NOTHING',
                guild_id, name, description
            )

@tasks.loop(hours=1)
async def auto_sprint_management():
    """Automatically manage sprint cycles"""
    try:
        async with accountability.db_pool.acquire() as conn:
            # Find guilds with auto_start_sprints enabled
            configs = await conn.fetch(
                'SELECT guild_id, sprint_duration_days FROM guild_config WHERE auto_start_sprints = TRUE'
            )
            
            for config in configs:
                guild_id = config['guild_id']
                duration = config['sprint_duration_days']
                
                # Check if current sprint has ended
                current_sprint = await conn.fetchrow(
                    'SELECT * FROM sprints WHERE guild_id = $1 AND status = $2 ORDER BY start_date DESC LIMIT 1',
                    guild_id, 'active'
                )
                
                if current_sprint:
                    if datetime.utcnow() >= current_sprint['end_date']:
                        # End current sprint and start new one
                        await conn.execute(
                            'UPDATE sprints SET status = $1 WHERE id = $2',
                            'ended', current_sprint['id']
                        )
                        
                        # Start new sprint
                        await accountability.create_sprint(guild_id, duration)
                        logger.info(f"Auto-started new sprint for guild {guild_id}")
                else:
                    # No active sprint, create one
                    await accountability.create_sprint(guild_id, duration)
                    logger.info(f"Created initial sprint for guild {guild_id}")
    except Exception as e:
        logger.error(f"Error in auto sprint management: {e}")

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument: {error}")
    else:
        logger.error(f"Unhandled error: {error}")
        await ctx.send("❌ An unexpected error occurred")

@bot.command(name='guide')
async def help_command(ctx):
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
        name="⚙️ Configuration",
        value="""**Categories:**
`!categories` - List available categories
`!category add <name> [description]` - Create custom category

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

@bot.event
async def on_guild_join(guild):
    """Initialize default categories when bot joins a guild"""
    await init_default_categories(guild.id)

if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))