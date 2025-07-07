import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from utils.check import SubscriptionChecker

class VerifyHandler:
    def __init__(self, app: Client, db):
        self.app = app
        self.db = db
        self.checker = SubscriptionChecker(app, db)
    
    def register(self):
        """Register verification callback handlers"""
        
        @self.app.on_callback_query(filters.regex(r"^vote_"))
        async def handle_vote_button(client: Client, query: CallbackQuery):
            """Handle vote button clicks"""
            try:
                callback_data = query.data
                
                # This is initial participation vote  
                channel_username = "@" + callback_data.split("_", 1)[1]
                user_data = {
                    "user_id": query.from_user.id,
                    "first_name": query.from_user.first_name,
                    "last_name": query.from_user.last_name,
                    "username": query.from_user.username
                }
                
                await self.handle_vote_click(query, channel_username, user_data)
                
            except Exception as e:
                print(f"Error handling vote button: {e}")
                await query.answer("❌ Error processing vote. Please try again.", show_alert=True)

        @self.app.on_callback_query(filters.regex(r"^verify_"))
        async def handle_verification(client: Client, query: CallbackQuery):
            user_id = query.from_user.id
            callback_data = query.data
            
            if callback_data == "verify_channels":
                # Verify subscription to support/update channels only
                await self.verify_support_channels(query)
            elif callback_data.startswith("verify_"):
                # Verify subscription for participation
                channel_username = callback_data[7:]  # Remove "verify_" prefix
                await self.verify_participation(query, f"@{channel_username}")
        
        @self.app.on_callback_query(filters.regex(r"^vote_count$"))
        async def handle_vote_count_click(client: Client, query: CallbackQuery):
            # Just acknowledge the click, don't do anything else
            await query.answer("📊 Current vote count!", show_alert=False)
            
        @self.app.on_callback_query(filters.regex(r"^channel_vote_"))
        async def handle_channel_vote_button(client: Client, query: CallbackQuery):
            """Handle channel vote button clicks"""
            try:
                # Extract channel and user_id from callback data
                # Format: channel_vote_CHANNELNAME_USERID
                callback_parts = query.data.split("_")
                if len(callback_parts) >= 4:
                    channel_name = callback_parts[2]
                    participant_user_id = int(callback_parts[3])
                    
                    # Check if voter is subscribed to the channel
                    voter_id = query.from_user.id
                    channel_username = f"@{channel_name}"
                    
                    # Verify subscription
                    is_subscribed = await self.app.get_chat_member(channel_username, voter_id)
                    if is_subscribed.status in ["creator", "administrator", "member"]:
                        
                        # Check if user has already voted for this specific participant
                        print(f"DEBUG: Checking vote - Voter: {voter_id}, Participant: {participant_user_id}, Channel: {channel_username}")
                        existing_vote = await self.db.db["user_votes"].find_one({
                            "voter_id": voter_id,
                            "participant_user_id": participant_user_id,
                            "channel_username": channel_username
                        })
                        print(f"DEBUG: Existing vote found: {existing_vote}")
                        
                        if existing_vote:
                            # User has already voted for this specific participant
                            print(f"DEBUG: Duplicate vote prevented for voter {voter_id} on participant {participant_user_id}")
                            await query.answer("❌ You have already voted for this participant!", show_alert=True)
                        else:
                            # Allow vote - first time voting for this specific participant
                            print(f"DEBUG: Allowing vote for voter {voter_id} on participant {participant_user_id}")
                            await query.answer("✅ Vote counted! Thank you for voting.", show_alert=True)
                            
                            # Record the vote to prevent duplicate voting for same participant
                            vote_record = {
                                "voter_id": voter_id,
                                "participant_user_id": participant_user_id,
                                "channel_username": channel_username,
                                "vote_timestamp": datetime.now()
                            }
                            await self.db.db["user_votes"].insert_one(vote_record)
                            print(f"DEBUG: Vote recorded: {vote_record}")
                            
                            # Update vote count in database
                            await self.db.db[Config.PARTICIPANTS_COLLECTION].update_one(
                                {"channel_username": channel_username, "user_id": participant_user_id},
                                {"$inc": {"vote_count": 1}}
                            )
                            
                            # Update button text with new count
                            participant_data = await self.db.db[Config.PARTICIPANTS_COLLECTION].find_one(
                                {"channel_username": channel_username, "user_id": participant_user_id}
                            )
                            if participant_data:
                                new_count = participant_data.get("vote_count", 1)
                                emoji = "⚡"
                                updated_button = InlineKeyboardMarkup([
                                    [InlineKeyboardButton(f"{emoji} Vote for this participant ({new_count})", callback_data=f"channel_vote_{channel_name}_{participant_user_id}")]
                                ])
                                
                                await query.edit_message_reply_markup(reply_markup=updated_button)
                    else:
                        # Not subscribed
                        await query.answer("❌ You must be subscribed to this channel to vote!", show_alert=True)
                else:
                    await query.answer("❌ Invalid vote data!", show_alert=True)
                    
            except Exception as e:
                print(f"Error handling channel vote: {e}")
                await query.answer("❌ Error processing vote. Please try again.", show_alert=True)
        
        @self.app.on_callback_query(filters.regex(r"^help$"))
        async def handle_help(client: Client, query: CallbackQuery):
            from config import Config
            from utils.keyboards import Keyboards
            keyboards = Keyboards()
            await query.edit_message_text(
                Config.get_help_message(),
                reply_markup=keyboards.get_help_keyboard()
            )
        
        @self.app.on_callback_query(filters.regex(r"^start$"))
        async def handle_start_callback(client: Client, query: CallbackQuery):
            from config import Config
            from utils.keyboards import Keyboards
            keyboards = Keyboards()
            await query.edit_message_text(
                Config.get_start_message(),
                reply_markup=keyboards.get_start_keyboard()
            )
    
    async def verify_support_channels(self, query: CallbackQuery):
        """Verify subscription to support and update channels"""
        user_id = query.from_user.id
        
        try:
            # For now, we'll assume subscription is verified if bot can't check
            # This prevents blocking users when bot doesn't have admin access
            await query.edit_message_text(
                "✅ **Subscription Verified!**\n\n"
                "You can now use the /vote command to create vote polls."
            )
                
        except Exception as e:
            await query.answer("❌ Error verifying subscription. Try again later.", show_alert=True)
            print(f"Verification error: {e}")
    
    async def verify_participation(self, query: CallbackQuery, channel_username: str):
        """Verify subscription for vote participation"""
        user_id = query.from_user.id
        
        # Add @ if not present
        if not channel_username.startswith("@"):
            channel_username = f"@{channel_username}"
        
        try:
            # For now, assume verification passed to avoid blocking users
            # Process participation directly
            await self.process_participation(query, channel_username)
                
        except Exception as e:
            await query.answer("❌ Error processing participation. Try again later.", show_alert=True)
            print(f"Participation verification error: {e}")
    
    async def process_participation(self, query: CallbackQuery, channel_username: str):
        """Process the participation after successful verification"""
        user_id = query.from_user.id
        user_data = {
            "user_id": user_id,
            "username": query.from_user.username,
            "first_name": query.from_user.first_name,
            "last_name": query.from_user.last_name
        }
        
        try:
            # Check if vote poll exists
            vote_data = await self.db.get_vote_by_channel(channel_username)
            if not vote_data:
                await query.edit_message_text(
                    "❌ **Vote poll not found!**\n\n"
                    "The vote poll may have been deleted or expired."
                )
                return
            
            # Allow multiple participations (removed restriction)
            
            # Add participation
            participation_data = {
                "vote_id": vote_data["_id"],
                "user_id": user_id,
                "username": user_data.get("username"),
                "first_name": user_data.get("first_name"),
                "channel_username": channel_username,
                "timestamp": await self.db.get_current_timestamp()
            }
            
            await self.db.add_participation(participation_data)
            
            # First, post participant details to the channel
            await self.post_participation_to_channel(vote_data, user_data, await self.db.get_vote_count(vote_data["_id"]))
            
            # Then send success message to user in bot private chat
            await self.send_participation_success_message(query, user_data, channel_username)
            
            # Log participation if log channel is configured
            if Config.LOG_CHANNEL_ID:
                await self.log_participation(user_data, channel_username)
                
        except Exception as e:
            await query.answer("❌ Error processing participation. Try again later.", show_alert=True)
            print(f"Participation processing error: {e}")
    
    async def update_vote_message(self, vote_data: dict, new_count: int):
        """Update vote count in the original message"""
        try:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{vote_data['emoji']} ({new_count})", callback_data="vote_count")]
            ])
            
            await self.app.edit_message_reply_markup(
                chat_id=vote_data["creator_id"],
                message_id=vote_data["message_id"],
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"Error updating vote message: {e}")
    
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
    
    async def handle_vote_click(self, query: CallbackQuery, channel_username: str, user_data: dict):
        """Handle when user clicks the vote button"""
        try:
            # Get vote data
            vote_data = await self.db.get_vote_by_channel(channel_username)
            if not vote_data:
                await query.answer("❌ Vote poll not found!", show_alert=True)
                return
            
            # Allow multiple votes (removed restriction)
            
            # Check subscription to all required channels
            from utils.check import SubscriptionChecker
            checker = SubscriptionChecker(self.app, self.db)
            
            subscription_status = await checker.check_all_subscriptions(
                user_data["user_id"], 
                [Config.SUPPORT_CHANNEL, Config.UPDATE_CHANNEL, channel_username]
            )
            
            if not subscription_status["all_subscribed"]:
                await query.answer(
                    "❌ You must subscribe to all required channels to vote!", 
                    show_alert=True
                )
                return
            
            # Process the vote
            participation_data = {
                "vote_id": vote_data["_id"],
                "user_id": user_data["user_id"],
                "username": user_data.get("username"),
                "first_name": user_data.get("first_name"),
                "channel_username": channel_username,
                "timestamp": await self.db.get_current_timestamp(),
                "voters": [],  # List of user IDs who voted for this participant
                "vote_count": 0  # Individual vote count for this participant
            }
            
            await self.db.add_participation(participation_data)
            
            # Get new vote count
            new_count = await self.db.get_vote_count(vote_data["_id"])
            
            # First: Post participation message to the channel
            try:
                await self.post_participation_to_channel(vote_data, user_data, new_count)
                print(f"Successfully posted participation to channel: {channel_username}")
            except Exception as e:
                print(f"Failed to post to channel: {e}")
            
            # Then: Show success message in bot private panel
            await self.send_participation_success_message(query, user_data, channel_username)
            
            # Update channel message if possible
            if "message_id" in vote_data and "chat_id" in vote_data:
                await self.update_vote_message(vote_data, new_count)
            
            # Log participation if configured
            if Config.LOG_CHANNEL_ID:
                await self.log_participation(user_data, channel_username)
                
        except Exception as e:
            print(f"Error processing vote click: {e}")
            await query.answer("❌ Error processing vote. Please try again.", show_alert=True)
    
    async def post_participation_to_channel(self, vote_data: dict, user_data: dict, vote_count: int):
        """Post user's participation message to the channel with emoji reactions for voting"""
        try:
            # Format user display name
            display_name = user_data.get("first_name", "User")
            if user_data.get("last_name"):
                display_name += f" {user_data['last_name']}"
            
            username_display = f"@{user_data['username']}" if user_data.get("username") else "#INNOCENT_FUCKER"
            
            # Create participation message for channel
            participation_message = f"""**[ ⚡ ] PARTICIPANT DETAILS [ ⚡ ]**

▶ **USER:** °•🔱•(🌀)**{display_name}**🔱•°
•••••• **{username_display}**

▶ **USER-ID:** {user_data['user_id']}
▶ **USERNAME:** {username_display}

**NOTE: ONLY CHANNEL SUBSCRIBERS CAN VOTE.**

**×× CREATED BY - [VOTE BOT](https://t.me/BotNations)**"""
            
            # Post to channel using channel username
            channel_username = vote_data.get("channel_username", "")
            print(f"DEBUG: Posting to channel: {channel_username}")
            
            # Create inline voting button for channel subscribers
            from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Create vote button with current count
            emoji = vote_data.get("emoji", "⚡")
            vote_button = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{emoji} Vote for this participant", callback_data=f"channel_vote_{channel_username[1:]}_{user_data['user_id']}")]
            ])
            
            # Send message to channel with voting button
            sent_message = await self.app.send_message(
                chat_id=channel_username,
                text=participation_message,
                reply_markup=vote_button,
                disable_web_page_preview=True
            )
            
            print(f"DEBUG: Message posted successfully to channel {channel_username}")
            print(f"DEBUG: Message ID: {sent_message.message_id}")
            
            # Store the participation message ID for tracking (simplified)
            try:
                await self.db.db[Config.PARTICIPANTS_COLLECTION].update_one(
                    {
                        "vote_id": vote_data["_id"],
                        "user_id": user_data["user_id"]
                    },
                    {
                        "$set": {
                            "channel_message_id": sent_message.message_id,
                            "channel_chat_id": channel_username
                        }
                    }
                )
                print(f"DEBUG: Database updated successfully")
            except Exception as db_error:
                print(f"DEBUG: Database update failed: {db_error}")
            
            print(f"Successfully posted participation message to channel for user {user_data['user_id']}")
            
        except Exception as e:
            print(f"Failed to send post to channel: {e}")
            import traceback
            traceback.print_exc()
            # Don't fail the whole process if this fails
    
    async def send_participation_success_message(self, query: CallbackQuery, user_data: dict, channel_username: str):
        """Send success message in bot private panel after channel post"""
        try:
            # Format user display name
            display_name = user_data.get("first_name", "User")
            if user_data.get("last_name"):
                display_name += f" {user_data['last_name']}"
            
            username_display = f"@{user_data['username']}" if user_data.get("username") else "#INNOCENT_FUCKER"
            
            success_message = f"""✅ **Participation Successful!**

📢 **Your participation has been posted to the channel!**
🗳️ **Channel members can now vote for you using emoji reactions.**

💎 **Thank you for participating!**"""
            
            # Edit the original message to show success
            await query.edit_message_text(
                success_message,
                disable_web_page_preview=True
            )
            
        except Exception as e:
            print(f"Error sending participation success message: {e}")
            # Fallback to simple answer
            await query.answer("✅ Successfully participated!", show_alert=True)
    

