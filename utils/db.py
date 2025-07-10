import asyncpg
import os
import logging
from datetime import datetime, timedelta
import random
import string
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class DatabaseManager:
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

db_manager = DatabaseManager() 