from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import PeerIdInvalid, UserNotParticipant, ChannelPrivate, ChatAdminRequired
from config import Config
from utils.check import SubscriptionChecker
import random
from datetime import datetime

class SimpleVoteHandler:
    def __init__(self, app: Client, db):
        self.app = app
        self.db = db
        self.checker = SubscriptionChecker(app, db)
        self.pending_channels = {}  # Store pending channel inputs
    
    def register(self):
        """Register simple vote handlers"""
        
        # Main vote command
        @self.app.on_message(filters.command("vote") & filters.private)
        async def vote_command(client: Client, message: Message):
            user_id = message.from_user.id
            
            # Store user state for channel input
            self.pending_channels[user_id] = True
            
            await message.reply_text(
                "**Send your channel username (e.g., @KomalMusicUpdate)**"
            )
        
        # Handle channel username input
        @self.app.on_message(filters.text & filters.private & ~filters.command(["start", "help"]))
        async def handle_channel_input(client: Client, message: Message):
            user_id = message.from_user.id
            
            # Check if user is in channel input mode
            if user_id not in self.pending_channels:
                return
            
            channel_username = message.text.strip()
            
            # Validate channel format
            if not channel_username.startswith('@'):
                await message.reply_text(
                    "❌ **Invalid Format**\n\n"
                    "Please send channel username with @ symbol\n"
                    "Example: @KomalMusicUpdate"
                )
                return
            
            # Process vote creation
            await self.create_vote_session(message, channel_username, user_id)
            
            # Clean up pending state
            del self.pending_channels[user_id]
        
        # Handle vote button clicks
        @self.app.on_callback_query(filters.regex(r"^vote_btn_"))
        async def handle_vote_button(client: Client, query: CallbackQuery):
            channel_username = query.data.split("_")[2]
            await self.process_vote_click(query, f"@{channel_username}")
    
    async def create_vote_session(self, message: Message, channel_username: str, user_id: int):
        """Create vote session with all validations"""
        
        try:
            # Step 1: Check if bot is in the channel
            try:
                chat = await self.app.get_chat(channel_username)
                chat_id = chat.id
            except PeerIdInvalid:
                await message.reply_text("❌ **Please add me in your channel.**")
                return
            except Exception:
                await message.reply_text("❌ **Channel not found or not accessible.**")
                return
            
            # Step 2: Check if bot is admin using improved method
            from utils.check import SubscriptionChecker
            checker = SubscriptionChecker(self.app, self.db)
            
            is_admin = await checker.is_bot_admin(channel_username)
            if not is_admin:
                await message.reply_text("❌ **Please make me admin in your channel.**")
                return
            
            # Step 3: Check if user is admin/owner of the channel
            print(f"DEBUG: Checking admin status for user {user_id} in channel {channel_username}")
            
            try:
                # Get user's membership status in the channel
                user_member = await self.app.get_chat_member(chat_id, user_id)
                status_str = str(user_member.status).split('.')[-1].lower()
                is_channel_admin = status_str in ["administrator", "creator", "owner"]
                
                print(f"DEBUG: User status in channel: {user_member.status} -> {status_str}")
                print(f"DEBUG: Is channel admin/owner: {is_channel_admin}")
                
                if not is_channel_admin:
                    await message.reply_text(
                        f"❌ **You must be an admin or owner of {channel_username} to create vote polls.**\n\n"
                        f"Your current status: {status_str.replace('_', ' ').title()}"
                    )
                    return
                    
            except UserNotParticipant:
                print(f"DEBUG: User {user_id} not member of {channel_username}")
                await message.reply_text(
                    f"❌ **You must be a member and admin/owner of {channel_username} to create vote polls.**"
                )
                return
            except Exception as e:
                print(f"DEBUG: User admin check error: {e}")
                await message.reply_text(
                    f"❌ **Could not verify your admin status in {channel_username}.**\n"
                    f"Please ensure you are an admin/owner of the channel."
                )
                return
            
            # Step 4: Check if vote session already exists
            existing_vote = await self.db.get_vote_by_channel(channel_username)
            if existing_vote:
                await message.reply_text(
                    f"⚠️ **Vote poll already exists for {channel_username}**\n\n"
                    f"**Participation Link:**\n"
                    f"https://t.me/{Config.BOT_USERNAME}?start={channel_username[1:]}"
                )
                return
            
            # Step 5: Create database entry
            vote_data = {
                "channel": channel_username,
                "channel_username": channel_username,  # Add both for compatibility
                "chat_id": chat_id,
                "created_by": user_id,
                "created_at": datetime.now().isoformat(),
                "status": "active",
                "active": True,  # Add both status fields for compatibility
                "participants": [],
                "votes": [],
                "vote_count": 0
            }
            
            vote_id = await self.db.create_vote(vote_data)
            
            # Convert vote_id string back to ObjectId for database operations
            from bson import ObjectId
            vote_object_id = ObjectId(vote_id)
            
            # Step 6: Get actual bot username and create participation link
            me = await self.app.get_me()
            bot_username = me.username
            participation_link = f"https://t.me/{bot_username}?start={channel_username[1:]}"
            
            # Step 7: Create vote post in the channel
            vote_emoji = random.choice(Config.VOTE_EMOJIS)
            vote_message = (
                f"{vote_emoji} **Vote Poll Created!**\n\n"
                f"Click the button below to participate in the vote!\n\n"
                f"**Note:** Only channel subscribers can participate."
            )
            
            # Create inline keyboard for vote button
            vote_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    f"{vote_emoji} Participate in Vote", 
                    url=participation_link
                )]
            ])
            
            try:
                # Send post to channel
                channel_message = await self.app.send_message(
                    chat_id,
                    vote_message,
                    reply_markup=vote_keyboard
                )
                
                # Update the vote data with message info for future updates
                await self.db.db[Config.VOTES_COLLECTION].update_one(
                    {"_id": vote_object_id},
                    {"$set": {
                        "message_id": channel_message.message_id,
                        "emoji": vote_emoji
                    }}
                )
                
                print(f"Vote post sent to channel {channel_username} (Message ID: {channel_message.message_id})")
            except Exception as e:
                print(f"Failed to send post to channel: {e}")
                # Continue anyway - don't block vote creation
            
            # Step 8: Send success message to user
            await message.reply_text(
                f"✅ **Successfully created vote-poll for:** {channel_username}\n\n"
                f"📩 **Participation Link:**\n"
                f"{participation_link}\n\n"
                f"📝 **Only channel subscribers can participate and vote.**\n\n"
                f"🎯 **Vote post has been automatically sent to your channel!**"
            )
            
        except Exception as e:
            await message.reply_text(f"❌ **Error creating vote session:** {str(e)}")
    
    async def process_participation(self, user_id: int, channel_username: str, user_data: dict):
        """Process user participation in vote"""
        
        try:
            # Get vote session
            vote_session = await self.db.get_vote_by_channel(channel_username)
            if not vote_session:
                return {
                    'success': False,
                    'message': "❌ **Vote session not found.**"
                }
            
            # Check if user is subscribed to the channel
            is_subscribed = await self.checker.check_subscription(user_id, channel_username)
            if not is_subscribed:
                return {
                    'success': False,
                    'message': f"❌ **Please subscribe to {channel_username} to participate.**"
                }
            
            # Check if user already participated
            if user_id in vote_session.get('participants', []):
                return {
                    'success': False,
                    'message': "✅ **You have already participated in this vote.**"
                }
            
            # Add user to participants
            if 'participants' not in vote_session:
                vote_session['participants'] = []
            vote_session['participants'].append(user_id)
            
            # Update database
            await self.db.add_participation({
                'vote_id': vote_session.get('vote_id', vote_session.get('_id')),
                'user_id': user_id,
                'channel': channel_username,
                'participated_at': datetime.now().isoformat()
            })
            
            # Send participation message to channel
            await self.send_participation_message(vote_session, user_data)
            
            return {
                'success': True,
                'message': "✅ **Successfully participated! Your message has been sent to the channel.**"
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"❌ **Error processing participation:** {str(e)}"
            }
    
    async def send_participation_message(self, vote_session: dict, user_data: dict):
        """Send participation message to channel with vote button"""
        
        try:
            chat_id = vote_session['chat_id']
            channel_username = vote_session['channel']
            current_votes = len(vote_session.get('votes', []))
            
            # Create participation message
            participant_message = f"""
🖼️ **[⚡] PARTICIPANT DETAILS [⚡]**

► **USER:** {user_data.get('first_name', 'Unknown')} {user_data.get('last_name', '')}
► **USER-ID:** {user_data['id']}
► **USERNAME:** @{user_data.get('username', 'None')}

**NOTE: ONLY CHANNEL SUBSCRIBERS CAN VOTE.**
"""
            
            # Create vote button
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    f"⚡ Vote ({current_votes})", 
                    callback_data=f"vote_btn_{channel_username[1:]}"
                )]
            ])
            
            # Send message to channel
            await self.app.send_message(
                chat_id=chat_id,
                text=participant_message,
                reply_markup=keyboard
            )
            
        except Exception as e:
            print(f"Error sending participation message: {e}")
    
    async def process_vote_click(self, query: CallbackQuery, channel_username: str):
        """Process vote button click"""
        
        user_id = query.from_user.id
        
        try:
            # Get vote session
            vote_session = await self.db.get_vote_by_channel(channel_username)
            if not vote_session:
                await query.answer("❌ Vote session not found.", show_alert=True)
                return
            
            # Check if vote session is active
            if vote_session.get('status') != 'active':
                await query.answer("❌ This vote session is no longer active.", show_alert=True)
                return
            
            # Check if user is subscribed
            is_subscribed = await self.checker.check_subscription(user_id, channel_username)
            if not is_subscribed:
                await query.answer(
                    f"❌ Please subscribe to {channel_username} to vote.", 
                    show_alert=True
                )
                return
            
            # Check if user already voted
            votes_list = vote_session.get('votes', [])
            if user_id in votes_list:
                await query.answer("✅ You have already voted!", show_alert=True)
                return
            
            # Add vote
            votes_list.append(user_id)
            new_vote_count = len(votes_list)
            
            # Update database
            vote_session['votes'] = votes_list
            vote_session['vote_count'] = new_vote_count
            
            # Update button with new count
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    f"⚡ Vote ({new_vote_count})", 
                    callback_data=f"vote_btn_{channel_username[1:]}"
                )]
            ])
            
            # Update message
            await query.edit_message_reply_markup(reply_markup=keyboard)
            await query.answer("✅ Vote counted successfully!", show_alert=False)
            
            # Save vote to database
            await self.db.add_participation({
                'vote_id': vote_session.get('vote_id', vote_session.get('_id')),
                'user_id': user_id,
                'channel': channel_username,
                'action': 'vote',
                'voted_at': datetime.now().isoformat()
            })
            
        except Exception as e:
            await query.answer("❌ Error processing vote.", show_alert=True)
            print(f"Vote processing error: {e}")
    
    async def cleanup_unsubscribed_votes(self):
        """Auto cleanup - remove votes from unsubscribed users"""
        
        try:
            # Get all active vote sessions
            # This would be implemented based on your database structure
            pass
        except Exception as e:
            print(f"Cleanup error: {e}")