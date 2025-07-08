import os
from typing import List

class Config:
    # Bot configuration
    API_ID = int(os.getenv("API_ID", "12380656"))
    API_HASH = os.getenv("API_HASH", "d927c13beaaf5110f25c505b7c071273")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "7745907443:AAE5yUnznFdtHnvf3ZCaS4vwbLVIIC-hnDY")
    
    # Owner and channels
    OWNER_USERNAME = os.getenv("OWNER_USERNAME", "@INNOCENT_FUCKER")
    OWNER_ID = int(os.getenv("OWNER_ID", "7840521426"))  # Replace with actual owner ID
    SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "@Komal_Music_Support")
    UPDATE_CHANNEL = os.getenv("UPDATE_CHANNEL", "@KomalMusicUpdate")
    
    # Optional log channel
    LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-1002387668895")) if os.getenv("LOG_CHANNEL_ID") else None
    
    # Database configuration
    MONGO_DB_URI = os.getenv("MONGO_DB_URI", "mongodb+srv://jaydipmore74:xCpTm5OPAfRKYnif@cluster0.5jo18.mongodb.net/?retryWrites=true&w=majority")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "Nottyvotebot")
    
    # Collections
    VOTES_COLLECTION = "votes"
    PARTICIPANTS_COLLECTION = "participants"
    CHANNELS_COLLECTION = "channels"
    
    # Bot settings
    BOT_USERNAME = os.getenv("BOT_USERNAME", "My_Vote_Robot")
    
    # Subscription check interval (in minutes)
    SUBSCRIPTION_CHECK_INTERVAL = int(os.getenv("SUBSCRIPTION_CHECK_INTERVAL", "5"))
    
    # Random emojis for vote polls
    VOTE_EMOJIS = ["⚡", "🔥", "💎", "🎯", "🚀", "⭐", "💫", "🌟", "✨", "🎭"]
    
    # Messages
    START_MESSAGE = """
**❖ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴠᴏᴛᴇ ʙᴏᴛ!**

**» ᴛᴏ ᴄʀᴇᴀᴛᴇ ᴀᴜᴛᴏ ᴠᴏᴛᴇ ᴄʀᴇᴀᴛᴏʀ ғᴏʀ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟ, ᴜsᴇ /vote ᴄᴏᴍᴍᴀɴᴅ.**
**‣ ᴠᴏᴛᴇ-ᴘᴏʟʟ - ɢɪᴠᴇᴀᴡᴀʏ**

**❖ ɪғ ʏᴏᴜ ɴᴇᴇᴅ ᴀɴʏ ʜᴇʟᴘ, ᴛʜᴇɴ ᴅᴍ ᴛᴏ ᴍʏ ᴏᴡɴᴇʀ ( {owner} ) ❖**

**❖ ᴀᴠᴀɪʟᴀʙʟᴇ ᴄᴏᴍᴍᴀɴᴅs:**
**• /vote - ᴄʀᴇᴀᴛᴇ ᴀ ᴠᴏᴛᴇ ᴘᴏʟʟ ғᴏʀ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟ**
**• /help - sʜᴏᴡ ᴛʜɪs ʜᴇʟᴘ ᴍᴇssᴀɢᴇ**
**• /stats - sʜᴏᴡ ʙᴏᴛ sᴛᴀᴛɪsᴛɪᴄs (ᴀᴅᴍɪɴ ᴏɴʟʏ)**
"""
    
    HELP_MESSAGE = """
**❖ ᴠᴏᴛᴇ ʙᴏᴛ ʜᴇʟᴘ ❖**

**❖ ʜᴏᴡ ᴛᴏ ᴜsᴇ:**
**1. ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴀs ᴀᴅᴍɪɴ**
**2. ᴜsᴇ /vote ᴄᴏᴍᴍᴀɴᴅ**
**3. sᴇɴᴅ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴜsᴇʀɴᴀᴍᴇ ᴡɪᴛʜ @**
**4. sʜᴀʀᴇ ᴛʜᴇ ᴘᴀʀᴛɪᴄɪᴘᴀᴛɪᴏɴ ʟɪɴᴋ ᴡɪᴛʜ ʏᴏᴜʀ ᴀᴜᴅɪᴇɴᴄᴇ**

**❖ ᴄᴏᴍᴍᴀɴᴅs:**
**• /vote - ᴄʀᴇᴀᴛᴇ ᴠᴏᴛᴇ ᴘᴏʟʟ**
**• /help - sʜᴏᴡ ʜᴇʟᴘ**
**• /stats - ʙᴏᴛ sᴛᴀᴛɪsᴛɪᴄs (ᴀᴅᴍɪɴ ᴏɴʟʏ)**

**❖ ɴᴇᴇᴅ sᴜᴘᴘᴏʀᴛ?** ᴄᴏɴᴛᴀᴄᴛ: {owner}
"""
    
    @classmethod
    def get_start_message(cls):
        return cls.START_MESSAGE.format(owner=cls.OWNER_USERNAME)
    
    @classmethod
    def get_help_message(cls):
        return cls.HELP_MESSAGE.format(owner=cls.OWNER_USERNAME)
