import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import Config
from utils.check import SubscriptionChecker
from utils.keyboards import Keyboards
from database import permanent_db

class StartHandler:
    def __init__(self, app: Client, db):
        self.app = app
        self.db = db
        self.permanent_db = permanent_db
        self.checker = SubscriptionChecker(app, db)
        self.keyboards = Keyboards()
    
    def register(self):
        """Register start command handlers"""
        
        @self.app.on_message(filters.command("start") & filters.private)
        async def start_command(client: Client, message: Message):
            user_id = message.from_user.id
            user_data = {
                "user_id": user_id,
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
                "is_bot": message.from_user.is_bot,
                "language_code": message.from_user.language_code,
                "is_premium": message.from_user.is_premium
            }
            
            # Save user permanently to database
            await self.permanent_db.save_user(user_data)
            
            # Check if it's a participation start (has parameter)
            if len(message.command) > 1:
                channel_username = message.command[1]
                await self.handle_participation(message, channel_username, user_data)
            else:
                await self.handle_start(message, user_data)
        
        @self.app.on_message(filters.command("help") & filters.private)
        async def help_command(client: Client, message: Message):
            await message.reply_text(
                Config.get_help_message(),
                reply_markup=self.keyboards.get_help_keyboard()
            )
    
    async def handle_start(self, message: Message, user_data: dict):
        """Handle regular start command"""
        # Store user in database
        await self.db.store_user(user_data)
        
        await message.reply_text(
            Config.get_start_message(),
            reply_markup=self.keyboards.get_start_keyboard()
        )
    
    async def handle_participation(self, message: Message, channel_username: str, user_data: dict):
        """Handle participation via deep link"""
        user_id = user_data["user_id"]
        
        # Ensure channel username starts with @
        if not channel_username.startswith("@"):
            channel_username = f"@{channel_username}"
        
        try:
            # Check if vote poll exists for this channel
            vote_data = await self.db.get_vote_by_channel(channel_username)
            if not vote_data:
                await message.reply_text(
                    "❌ **Vote poll not found for this channel!**\n\n"
                    "The vote poll may have been deleted or expired."
                )
                return
            
            # Check subscription to required channels
            subscription_status = await self.checker.check_all_subscriptions(
                user_id, [Config.SUPPORT_CHANNEL, Config.UPDATE_CHANNEL, channel_username]
            )
            
            if not subscription_status["all_subscribed"]:
                await self.show_subscription_prompt(
                    message, subscription_status["missing_channels"], channel_username
                )
                return
            
            # Show voting interface regardless of participation status
            await self.show_voting_interface(message, user_data, channel_username, vote_data)
            
            # Log to channel if configured
            if Config.LOG_CHANNEL_ID:
                await self.log_participation(user_data, channel_username)
                
        except Exception as e:
            await message.reply_text(
                "❌ **Error processing your participation!**\n\n"
                f"Please try again later or contact support: {Config.OWNER_USERNAME}"
            )
            print(f"Participation error: {e}")
    
    async def show_subscription_prompt(self, message: Message, missing_channels: list, target_channel: str):
        """Show subscription prompt with buttons"""
        text = "❌ **You need to subscribe to the following channels to participate:**\n\n"
        
        buttons = []
        for channel in missing_channels:
            if channel == Config.SUPPORT_CHANNEL:
                buttons.append([InlineKeyboardButton("❌ SUPPORT", url=f"https://t.me/{channel[1:]}")])
            elif channel == Config.UPDATE_CHANNEL:
                buttons.append([InlineKeyboardButton("❌ UPDATE", url=f"https://t.me/{channel[1:]}")])
            else:
                buttons.append([InlineKeyboardButton(f"❌ {channel}", url=f"https://t.me/{channel[1:]}")])
        
        # Add verification button
        buttons.append([InlineKeyboardButton("✅ I Subscribed", callback_data=f"verify_{target_channel[1:]}")])
        
        await message.reply_text(
            text + "**Please subscribe to all channels and click 'I Subscribed' button.**",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    async def send_participation_success(self, message: Message, user_data: dict, channel_username: str):
        """Send participation success message"""
        display_name = user_data.get("first_name", "User")
        if user_data.get("last_name"):
            display_name += f" {user_data['last_name']}"
        
        username_display = f"@{user_data['username']}" if user_data.get("username") else "No Username"
        
        success_text = f"""
✅ **Successfully Participated!**

⚡ **Participant Details:**
• **USER:** {display_name}
• **USER-ID:** {user_data['user_id']}
• **USERNAME:** {username_display}

**NOTE:** Only channel subscribers can vote.

** Created by - VOTE BOT**
🌟 @Komal_Music_Support
"""
        
        await message.reply_text(success_text)
    
    async def show_voting_interface(self, message: Message, user_data: dict, channel_username: str, vote_data: dict):
        """Show voting interface like in the reference image"""
        try:
            # Get current vote count
            current_count = await self.db.get_vote_count(vote_data["_id"])
            
            # Allow multiple participations (removed restriction)
            
            # Format user display name
            display_name = user_data.get("first_name", "User")
            if user_data.get("last_name"):
                display_name += f" {user_data['last_name']}"
            
            username_display = f"@{user_data['username']}" if user_data.get("username") else "#INNOCENT_FUCKER"
            
            # Create simple success message instead of participant details
            success_message = f"""✅ **Ready to Vote!**

🎯 **Channel:** {channel_username}
👥 **Current Participants:** {current_count}

📢 **Click below to participate in the vote!**"""
            
            # Create vote button
            emoji = vote_data.get("emoji", "⚡")
            button_text = f"{emoji} Participate in Vote"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(button_text, callback_data=f"vote_{channel_username[1:]}")]
            ])
            
            # Send the voting interface without participant details
            await message.reply_text(
                success_message,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
            
        except Exception as e:
            print(f"Error showing voting interface: {e}")
            await message.reply_text("❌ Error loading voting interface. Please try again.")
    
    async def update_vote_message(self, vote_data: dict, new_count: int):
        """Update the vote count in the channel message"""
        try:
            # Use a default emoji if not available in vote_data
            emoji = vote_data.get("emoji", "⚡")
            
            # Create updated message text
            updated_message = (
                f"{emoji} **Vote Poll - Live Count: {new_count}**\n\n"
                f"Click the button below to participate in the vote!\n\n"
                f"**Note:** Only channel subscribers can participate."
            )
            
            # Get participation link for the button
            channel_username = vote_data.get("channel", vote_data.get("channel_username", ""))
            me = await self.app.get_me()
            participation_link = f"https://t.me/{me.username}?start={channel_username[1:]}"
            
            # Create updated keyboard
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    f"{emoji} Participate in Vote ({new_count})", 
                    url=participation_link
                )]
            ])
            
            # Update the channel message
            await self.app.edit_message_text(
                chat_id=vote_data["chat_id"],
                message_id=vote_data["message_id"],
                text=updated_message,
                reply_markup=keyboard
            )
            print(f"Updated channel message with new count: {new_count}")
            
        except Exception as e:
            print(f"Error updating vote message: {e}")
            # Don't let this error stop the participation process
    
    async def log_participation(self, user_data: dict, channel_username: str):
        """Log participation to log channel"""
        try:
            log_text = f"""
📊 **New Vote Participation**

👤 **User:** {user_data.get('first_name', 'Unknown')}
🆔 **ID:** {user_data['user_id']}
📢 **Channel:** {channel_username}
⏰ **Time:** {await self.db.get_current_timestamp()}
"""
            
            await self.app.send_message(Config.LOG_CHANNEL_ID, log_text)
        except Exception as e:
            print(f"Error logging participation: {e}")
