import discord
from discord.ext import commands
import os
import logging
from datetime import datetime
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold


logger = logging.getLogger(__name__)

async def get_ai_summary(text: str) -> str:
    """Get AI summary with bullet point constraints using Gemini API"""
    prompt = f"""Please summarize the following conversation into bullet points. Focus on:
- Key topics discussed
- Important decisions made
- Action items or next steps
- Any significant insights or conclusions

Keep each bullet point concise (max 2 lines) and limit to 5-7 main points.

Conversation to summarize:
{text}

Format your response as bullet points starting with •"""
    
    try:
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        response = await model.generate_content_async(
            prompt,
            safety_settings={
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            }
        )
        return response.text.strip()
    except Exception as e:
        raise Exception(f"Gemini API request failed: {str(e)}")

class AICog(commands.Cog, name="AI"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='fromhere')
    async def summarize_from_here(self, ctx):
        """Summarize messages from a replied message onwards"""
        if not os.getenv('GEMINI_API_KEY'):
            await ctx.send("❌ Gemini API key not configured by the bot admin.")
            return

        if not ctx.message.reference:
            await ctx.send("❌ Please reply to a message to use this command")
            return
        
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        except discord.NotFound:
            await ctx.send("❌ Could not find the replied message")
            return
        
        messages = []
        async for message in ctx.channel.history(limit=None, after=replied_message.created_at, oldest_first=True):
            if message.author.bot:
                continue
            messages.append({
                'author': message.author.display_name,
                'content': message.content,
                'timestamp': message.created_at.isoformat()
            })
        
        if not replied_message.author.bot:
            messages.insert(0, {
                'author': replied_message.author.display_name,
                'content': replied_message.content,
                'timestamp': replied_message.created_at.isoformat()
            })
        
        if not messages:
            await ctx.send("❌ No messages found to summarize")
            return
        
        text_to_summarize = "\n".join([f"{msg['author']}: {msg['content']}" for msg in messages])
        
        if len(text_to_summarize) > 10000:
            text_to_summarize = text_to_summarize[:10000] + "..."
        
        try:
            summary = await get_ai_summary(text_to_summarize)
            
            embed = discord.Embed(
                title="📝 Message Summary",
                description=summary,
                color=0x00ff00,
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="Summary Info",
                value=f"Messages analyzed: {len(messages)}\nTime range: {messages[0]['timestamp'][:10]} to {messages[-1]['timestamp'][:10]}",
                inline=False
            )
            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in summarization: {e}")
            await ctx.send("❌ Error occurred while generating summary")

async def setup(bot):
    await bot.add_cog(AICog(bot)) 