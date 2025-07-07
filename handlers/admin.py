from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config

class AdminHandler:
    def __init__(self, app: Client, db):
        self.app = app
        self.db = db
        self.owner_id = None  # Will be set dynamically
    
    def register(self):
        """Register admin command handlers"""
        
        @self.app.on_message(filters.command("stats") & filters.private)
        async def stats_command(client: Client, message: Message):
            # Check if user is owner
            if not await self.is_owner(message.from_user.id):
                await message.reply_text("❌ **Access denied!** Only bot owner can use this command.")
                return
            
            await self.send_bot_stats(message)
        
        @self.app.on_message(filters.command("votes") & filters.private)
        async def votes_command(client: Client, message: Message):
            if not await self.is_owner(message.from_user.id):
                await message.reply_text("❌ **Access denied!** Only bot owner can use this command.")
                return
            
            if len(message.command) < 2:
                await message.reply_text("❌ **Usage:** `/votes @channel_username`")
                return
            
            channel_username = message.command[1]
            if not channel_username.startswith("@"):
                channel_username = f"@{channel_username}"
            
            await self.send_channel_votes(message, channel_username)
        
        @self.app.on_message(filters.command("totalvotes") & filters.private)
        async def total_votes_command(client: Client, message: Message):
            if not await self.is_owner(message.from_user.id):
                await message.reply_text("❌ **Access denied!** Only bot owner can use this command.")
                return
            
            if len(message.command) < 2:
                await message.reply_text("❌ **Usage:** `/totalvotes @channel_username`")
                return
            
            channel_username = message.command[1]
            if not channel_username.startswith("@"):
                channel_username = f"@{channel_username}"
            
            await self.send_total_votes(message, channel_username)
        
        @self.app.on_message(filters.command("deletevote") & filters.private)
        async def delete_vote_command(client: Client, message: Message):
            if not await self.is_owner(message.from_user.id):
                await message.reply_text("❌ **Access denied!** Only bot owner can use this command.")
                return
            
            if len(message.command) < 2:
                await message.reply_text("❌ **Usage:** `/deletevote @channel_username`")
                return
            
            channel_username = message.command[1]
            if not channel_username.startswith("@"):
                channel_username = f"@{channel_username}"
            
            await self.delete_vote_poll(message, channel_username)

        @self.app.on_message(filters.command("debug_admin") & filters.private)
        async def debug_admin_command(client: Client, message: Message):
            """Debug admin status for a channel and user"""
            if not await self.is_owner(message.from_user.id):
                await message.reply_text("❌ **Only owner can use this command**")
                return
            
            # Extract parameters from command
            if len(message.command) < 3:
                await message.reply_text("❌ **Usage:** `/debug_admin @channel_username user_id`")
                return
            
            channel_username = message.command[1]
            if not channel_username.startswith('@'):
                channel_username = '@' + channel_username
            
            try:
                user_id = int(message.command[2])
            except ValueError:
                await message.reply_text("❌ **Invalid user ID**")
                return
            
            await self.debug_admin_status(message, channel_username, user_id)
    
    async def is_owner(self, user_id: int) -> bool:
        """Check if user is the bot owner"""
        if self.owner_id is None:
            # Get owner ID from username
            try:
                owner_user = await self.app.get_users(Config.OWNER_USERNAME)
                self.owner_id = owner_user.id
            except:
                return False
        
        return user_id == self.owner_id
    
    async def send_bot_stats(self, message: Message):
        """Send comprehensive bot statistics"""
        try:
            stats = await self.db.get_bot_stats()
            
            stats_text = f"""
📊 **Bot Statistics**

**Vote Polls:**
• Active Polls: {stats['active_votes']}
• Total Polls Created: {stats['total_votes']}

**Participations:**
• Total Participations: {stats['total_participations']}
• Unique Participants: {stats['unique_participants']}

**Users:**
• Total Users: {stats['total_users']}

**Most Active Channel:**
{stats['most_active_channel']}

📅 **Generated:** {await self.db.get_current_timestamp()}
"""
            
            await message.reply_text(stats_text)
            
        except Exception as e:
            await message.reply_text(f"❌ **Error generating stats:** {str(e)}")
    
    async def send_channel_votes(self, message: Message, channel_username: str):
        """Send detailed vote information for a channel"""
        try:
            vote_data = await self.db.get_vote_by_channel(channel_username)
            
            if not vote_data:
                await message.reply_text(f"❌ **No vote poll found for {channel_username}**")
                return
            
            participants = await self.db.get_vote_participants(vote_data["_id"])
            
            participants_text = ""
            for i, participant in enumerate(participants[:20], 1):  # Show first 20
                name = participant.get("first_name", "Unknown")
                username = f"@{participant['username']}" if participant.get("username") else "No username"
                participants_text += f"{i}. {name} ({username})\n"
            
            if len(participants) > 20:
                participants_text += f"\n... and {len(participants) - 20} more participants"
            
            vote_info = f"""
📊 **Vote Details for {channel_username}**

**Vote Info:**
• Created: {vote_data['created_at']}
• Creator ID: {vote_data['creator_id']}
• Total Votes: {len(participants)}
• Status: {"✅ Active" if vote_data.get('active', True) else "❌ Inactive"}

**Recent Participants:**
{participants_text if participants_text else "No participants yet."}
"""
            
            await message.reply_text(vote_info)
            
        except Exception as e:
            await message.reply_text(f"❌ **Error fetching vote data:** {str(e)}")
    
    async def send_total_votes(self, message: Message, channel_username: str):
        """Send total vote count for a channel"""
        try:
            vote_data = await self.db.get_vote_by_channel(channel_username)
            
            if not vote_data:
                await message.reply_text(f"❌ **No vote poll found for {channel_username}**")
                return
            
            total_count = await self.db.get_vote_count(vote_data["_id"])
            
            await message.reply_text(
                f"📊 **Total Votes for {channel_username}**\n\n"
                f"**Vote Count:** {total_count}\n"
                f"**Poll Status:** {'✅ Active' if vote_data.get('active', True) else '❌ Inactive'}"
            )
            
        except Exception as e:
            await message.reply_text(f"❌ **Error fetching vote count:** {str(e)}")
    
    async def delete_vote_poll(self, message: Message, channel_username: str):
        """Delete a vote poll and all its data"""
        try:
            vote_data = await self.db.get_vote_by_channel(channel_username)
            
            if not vote_data:
                await message.reply_text(f"❌ **No vote poll found for {channel_username}**")
                return
            
            # Delete all participations
            deleted_participations = await self.db.delete_vote_participations(vote_data["_id"])
            
            # Delete vote poll
            await self.db.delete_vote(vote_data["_id"])
            
            await message.reply_text(
                f"✅ **Vote poll deleted successfully!**\n\n"
                f"**Channel:** {channel_username}\n"
                f"**Deleted Participations:** {deleted_participations}\n"
                f"**Status:** Poll completely removed"
            )
            
        except Exception as e:
            await message.reply_text(f"❌ **Error deleting vote poll:** {str(e)}")

    async def debug_admin_status(self, message: Message, channel_username: str, user_id: int):
        """Debug admin status for a channel and user"""
        try:
            debug_text = f"🔍 **Admin Status Debug**\n\n"
            debug_text += f"**Channel:** {channel_username}\n"
            debug_text += f"**User ID:** {user_id}\n\n"
            
            # Get channel info
            try:
                chat = await self.app.get_chat(channel_username)
                debug_text += f"✅ **Channel Found:** {chat.title}\n"
                debug_text += f"**Chat ID:** {chat.id}\n\n"
                
                # Check bot admin status
                try:
                    bot_member = await self.app.get_chat_member(chat.id, "me")
                    bot_status_str = str(bot_member.status).split('.')[-1].lower()
                    debug_text += f"🤖 **Bot Status:** {bot_member.status}\n"
                    debug_text += f"🤖 **Bot Status String:** {bot_status_str}\n"
                    debug_text += f"🤖 **Bot is Admin:** {'✅' if bot_status_str in ['administrator', 'creator'] else '❌'}\n\n"
                except Exception as e:
                    debug_text += f"❌ **Bot status check failed:** {e}\n\n"
                
                # Check user admin status
                try:
                    user_member = await self.app.get_chat_member(chat.id, user_id)
                    user_status_str = str(user_member.status).split('.')[-1].lower()
                    debug_text += f"👤 **User Status:** {user_member.status}\n"
                    debug_text += f"👤 **User Status String:** {user_status_str}\n"
                    debug_text += f"👤 **User is Admin:** {'✅' if user_status_str in ['administrator', 'creator'] else '❌'}\n"
                except Exception as e:
                    debug_text += f"❌ **User status check failed:** {e}\n"
                    
            except Exception as e:
                debug_text += f"❌ **Channel access failed:** {e}\n"
            
            await message.reply_text(debug_text)
            
        except Exception as e:
            await message.reply_text(f"❌ **Debug error:** {str(e)}")
            print(f"Debug admin error: {e}")
