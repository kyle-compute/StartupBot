import discord
from discord.ext import commands
from utils.db import db_manager

class CategoriesCog(commands.Cog, name="Categories"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='category')
    async def category_command(self, ctx, action: str, *, args: str = None):
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
            
            await db_manager.ensure_user_exists(ctx.author.id, ctx.guild.id)
            
            async with db_manager.db_pool.acquire() as conn:
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
        
        elif action.lower() == 'remove' or action.lower() == 'delete':
            if not ctx.author.guild_permissions.administrator:
                await ctx.send("❌ Administrator permissions required to remove categories")
                return
            
            if not args:
                await ctx.send("Usage: `!category remove <name>`")
                return
            
            category_name = args.strip()
            
            async with db_manager.db_pool.acquire() as conn:
                category = await conn.fetchrow(
                    'SELECT id, name FROM categories WHERE guild_id = $1 AND name = $2',
                    ctx.guild.id, category_name
                )
                
                if not category:
                    await ctx.send(f"❌ Category '{category_name}' not found.")
                    return
                
                active_challenges = await conn.fetchval(
                    'SELECT COUNT(*) FROM challenges WHERE category_id = $1 AND status IN ($2, $3)',
                    category['id'], 'active', 'pending_review'
                )
                
                if active_challenges > 0:
                    await ctx.send(f"❌ Cannot remove category '{category_name}' - it has {active_challenges} active challenges. Complete or reject them first.")
                    return
                
                await conn.execute(
                    'DELETE FROM categories WHERE id = $1',
                    category['id']
                )
                
                await ctx.send(f"✅ Category '{category_name}' removed successfully!")
        
        else:
            await ctx.send("Usage: `!category add <name> [description]` or `!category remove <name>`")

    @commands.command(name='categories')
    async def list_categories(self, ctx):
        """List all available challenge categories"""
        async with db_manager.db_pool.acquire() as conn:
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

async def setup(bot):
    await bot.add_cog(CategoriesCog(bot)) 