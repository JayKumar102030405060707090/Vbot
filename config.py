import os
from typing import List

class Config:
    # Bot configuration
    API_ID = int(os.getenv("API_ID", "12345678"))
    API_HASH = os.getenv("API_HASH", "abcdef1234567890abcdef1234567890")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    
    # Owner and channels
    OWNER_USERNAME = os.getenv("OWNER_USERNAME", "@INNOCENT_FUCKER")
    SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "@Komal_Music_Support")
    UPDATE_CHANNEL = os.getenv("UPDATE_CHANNEL", "@KomalMusicUpdate")
    
    # Optional log channel
    LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0")) if os.getenv("LOG_CHANNEL_ID") else None
    
    # Database configuration
    MONGO_DB_URI = os.getenv("MONGO_DB_URI", "mongodb://localhost:27017/votebot")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "votebot")
    
    # Collections
    VOTES_COLLECTION = "votes"
    PARTICIPANTS_COLLECTION = "participants"
    CHANNELS_COLLECTION = "channels"
    
    # Bot settings
    BOT_USERNAME = os.getenv("BOT_USERNAME", "VOTES_RO_BOT")
    
    # Subscription check interval (in minutes)
    SUBSCRIPTION_CHECK_INTERVAL = int(os.getenv("SUBSCRIPTION_CHECK_INTERVAL", "5"))
    
    # Random emojis for vote polls
    VOTE_EMOJIS = ["⚡", "🔥", "💎", "🎯", "🚀", "⭐", "💫", "🌟", "✨", "🎭"]
    
    # Messages
    START_MESSAGE = """
🤖 **Welcome to Vote Bot!**

» To create auto vote creator for your channel, use /vote command.
‣ Vote-Poll - Giveaway

If you need any help, then DM to my owner ( {owner} ).

**Available Commands:**
• /vote - Create a vote poll for your channel
• /help - Show this help message
• /stats - Show bot statistics (Admin only)
"""
    
    HELP_MESSAGE = """
🔰 **Vote Bot Help**

**How to use:**
1. Add me to your channel as admin
2. Use /vote command
3. Send your channel username with @
4. Share the participation link with your audience

**Commands:**
• /vote - Create vote poll
• /help - Show help
• /stats - Bot statistics (Admin only)

**Need Support?** Contact: {owner}
"""
    
    @classmethod
    def get_start_message(cls):
        return cls.START_MESSAGE.format(owner=cls.OWNER_USERNAME)
    
    @classmethod
    def get_help_message(cls):
        return cls.HELP_MESSAGE.format(owner=cls.OWNER_USERNAME)
