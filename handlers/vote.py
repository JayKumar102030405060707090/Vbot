import random
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, PeerIdInvalid
from config import Config
from utils.check import SubscriptionChecker

class VoteHandler:
    def __init__(self, app: Client, db):
        self.app = app
        self.db = db
        self.checker = SubscriptionChecker(app, db)
        self.pending_votes = {}  # Store pending vote creations
    
    def register(self):
        """Register vote command handlers"""
        
        @self.app.on_message(filters.command("vote") & filters.private)
        async def vote_command(client: Client, message: Message):
            user_id = message.from_user.id
            
            # Skip subscription check for now to avoid blocking users
            # Store user state for next message
            self.pending_votes[user_id] = {"step": "waiting_channel"}
            
            await message.reply_text(
                "**❓ ᴇɴᴛᴇʀ ᴄʜᴀɴɴᴇʟ ᴜsᴇʀɴᴀᴍᴇ ᴡɪᴛʜ @**\n\n"
                "**❖ ғɪʀsᴛ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴀs ᴀᴅᴍɪɴ, ᴛʜᴇɴ sᴇɴᴅ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ ᴜsᴇʀɴᴀᴍᴇ ❖**\n\n"
                "**❖ ᴇxᴀᴍᴘʟᴇ:** @KomalMusicUpdate"
            )
        
        @self.app.on_message(filters.private & filters.text)
        async def handle_channel_input(client: Client, message: Message):
            user_id = message.from_user.id
            
            # Check if user is in vote creation process
            if user_id not in self.pending_votes:
                return
            
            if self.pending_votes[user_id]["step"] != "waiting_channel":
                return
            
            channel_username = message.text.strip()
            
            # Validate channel username format
            if not channel_username.startswith("@"):
                await message.reply_text(
                    "❌ **Invalid format!**\n\n"
                    "Please send channel username starting with @ symbol.\n"
                    "**Example:** @YourChannelUsername"
                )
                return
            
            await self.process_vote_creation(message, channel_username, user_id)
    
    async def show_subscription_required(self, message: Message, missing_channels: list):
        """Show subscription requirement message"""
        text = "❌ **You need to subscribe to our channels first:**\n\n"
        
        buttons = []
        for channel in missing_channels:
            if channel == Config.SUPPORT_CHANNEL:
                buttons.append([InlineKeyboardButton("❌ SUPPORT", url=f"https://t.me/{channel[1:]}")])
            elif channel == Config.UPDATE_CHANNEL:
                buttons.append([InlineKeyboardButton("❌ UPDATE", url=f"https://t.me/{channel[1:]}")])
        
        buttons.append([InlineKeyboardButton("✅ I Subscribed", callback_data="verify_channels")])
        
        await message.reply_text(
            text + "**Subscribe to all channels and click the button below.**",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    async def process_vote_creation(self, message: Message, channel_username: str, user_id: int):
        """Process vote creation for the given channel"""
        try:
            # Clean up pending vote
            del self.pending_votes[user_id]
            
            # Check if bot can access the channel
            try:
                chat = await self.app.get_chat(channel_username)
                chat_id = chat.id
                
                # Try to get bot's membership status
                try:
                    bot_member = await self.app.get_chat_member(chat_id, "me")
                    # Only check admin status if we can verify membership - convert enum to string
                    bot_status_str = str(bot_member.status).split('.')[-1].lower()
                    if bot_status_str not in ["administrator", "creator"]:
                        await message.reply_text(
                            f"⚠️ **Warning: I might not be admin in your channel!**\n\n"
                            f"For best results, please make me admin in `{channel_username}`.\n\n"
                            f"Continuing with vote creation..."
                        )
                except:
                    # If membership check fails, assume bot is added and continue
                    print(f"Could not verify membership in {channel_username}, proceeding anyway")
                    
            except PeerIdInvalid:
                await message.reply_text(
                    f"❌ **Channel not found!**\n\n"
                    f"Please make sure:\n"
                    f"1. Channel username `{channel_username}` is correct\n"
                    f"2. Channel is public or I have access to it"
                )
                return
            except Exception as e:
                await message.reply_text(
                    f"❌ **Error accessing channel {channel_username}**\n\n"
                    f"Please check the channel username and try again."
                )
                return
            
            # Allow multiple votes per channel (removed restriction)
            
            # Create vote poll
            await self.create_vote_poll(message, channel_username, chat_id, user_id)
            
        except Exception as e:
            await message.reply_text(
                f"❌ **Error creating vote poll!**\n\n"
                f"Please try again later or contact support: {Config.OWNER_USERNAME}"
            )
            print(f"Vote creation error: {e}")
    
    async def create_vote_poll(self, message: Message, channel_username: str, chat_id: int, creator_id: int):
        """Create and store vote poll"""
        try:
            # Select random emoji
            emoji = random.choice(Config.VOTE_EMOJIS)
            
            # Create participation link
            participation_link = f"https://t.me/{Config.BOT_USERNAME}?start={channel_username[1:]}"
            
            # Create vote message with button
            vote_text = f"""
» **SUCCESSFULLY VOTE-POLL CREATED.**
• **CHAT:** {channel_username}
• **EMOJI:** {emoji}

**Participation Link:** {participation_link}
"""
            
            # Send vote message with initial count button
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{emoji} (0)", callback_data="vote_count")]
            ])
            
            sent_message = await message.reply_text(vote_text, reply_markup=keyboard)
            
            # Store vote data in database
            vote_data = {
                "channel_username": channel_username,
                "channel_id": chat_id,
                "creator_id": creator_id,
                "message_id": sent_message.message_id,
                "emoji": emoji,
                "participation_link": participation_link,
                "created_at": await self.db.get_current_timestamp(),
                "active": True
            }
            
            vote_id = await self.db.create_vote(vote_data)
            
            # Also send a follow-up message with branding
            footer_text = """
**Telegram**
**Vote Bot**
**××** Powered By @Komal_Music_Support
"""
            
            await message.reply_text(footer_text)
            
            print(f"Vote poll created successfully for {channel_username} by user {creator_id}")
            
        except Exception as e:
            await message.reply_text(
                "❌ **Error creating vote poll!**\n\n"
                "Please try again later."
            )
            print(f"Error in create_vote_poll: {e}")
