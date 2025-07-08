import asyncio
import uuid
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserIsBlocked, ChatWriteForbidden, FloodWait
from config import Config
from database import permanent_db
import logging

logger = logging.getLogger(__name__)

class BroadcastHandler:
    def __init__(self, app: Client, db):
        self.app = app
        self.db = db
        self.permanent_db = permanent_db
        self.pending_broadcasts = {}
        
    def register(self):
        """Register broadcast command handlers"""
        
        @self.app.on_message(filters.command("broadcast") & filters.private)
        async def broadcast_command(client: Client, message: Message):
            user_id = message.from_user.id
            
            # Check if user is owner
            if user_id != Config.OWNER_ID:
                await message.reply_text("❌ **Only bot owner can use this command!**")
                return
            
            # Show broadcast menu
            await self.show_broadcast_menu(message)
        
        @self.app.on_message(filters.command("broadcast_users") & filters.private)
        async def broadcast_users_command(client: Client, message: Message):
            user_id = message.from_user.id
            
            # Check if user is owner
            if user_id != Config.OWNER_ID:
                await message.reply_text("❌ **Only bot owner can use this command!**")
                return
            
            # Start user broadcast
            await self.start_user_broadcast(message)
        
        @self.app.on_message(filters.command("broadcast_channels") & filters.private)
        async def broadcast_channels_command(client: Client, message: Message):
            user_id = message.from_user.id
            
            # Check if user is owner
            if user_id != Config.OWNER_ID:
                await message.reply_text("❌ **Only bot owner can use this command!**")
                return
            
            # Start channel broadcast
            await self.start_channel_broadcast(message)
        
        @self.app.on_message(filters.command("stats") & filters.private)
        async def stats_command(client: Client, message: Message):
            user_id = message.from_user.id
            
            # Check if user is owner
            if user_id != Config.OWNER_ID:
                await message.reply_text("❌ **Only bot owner can use this command!**")
                return
            
            # Show database statistics
            await self.show_database_stats(message)
        
        @self.app.on_message(filters.text & filters.private)
        async def handle_broadcast_message(client: Client, message: Message):
            user_id = message.from_user.id
            
            # Check if user has pending broadcast
            if user_id in self.pending_broadcasts:
                broadcast_type = self.pending_broadcasts[user_id]
                
                if broadcast_type == "user":
                    await self.process_user_broadcast(message)
                elif broadcast_type == "channel":
                    await self.process_channel_broadcast(message)
                
                # Remove pending broadcast
                del self.pending_broadcasts[user_id]
    
    async def show_broadcast_menu(self, message: Message):
        """Show broadcast menu with statistics"""
        try:
            # Get statistics
            user_count = await self.permanent_db.get_user_count()
            channel_count = await self.permanent_db.get_channel_count()
            
            menu_text = f"""
**❖ ʙʀᴏᴀᴅᴄᴀsᴛ ᴍᴇɴᴜ ❖**

**📊 Database Statistics:**
**👥 Total Users:** {user_count}
**📢 Total Channels:** {channel_count}

**📡 Broadcast Options:**
**• /broadcast_users** - Broadcast to all users
**• /broadcast_channels** - Broadcast to all channels  
**• /stats** - Show detailed statistics

**⚠️ Note:** Only bot owner can use broadcast commands.
"""
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("👥 Broadcast Users", callback_data="broadcast_users")],
                [InlineKeyboardButton("📢 Broadcast Channels", callback_data="broadcast_channels")],
                [InlineKeyboardButton("📊 Statistics", callback_data="show_stats")]
            ])
            
            await message.reply_text(menu_text, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error showing broadcast menu: {e}")
            await message.reply_text("❌ **Error loading broadcast menu!**")
    
    async def start_user_broadcast(self, message: Message):
        """Start user broadcast process"""
        try:
            user_count = await self.permanent_db.get_user_count()
            
            if user_count == 0:
                await message.reply_text("❌ **No users found in database!**")
                return
            
            # Set pending broadcast
            self.pending_broadcasts[message.from_user.id] = "user"
            
            await message.reply_text(
                f"**📡 User Broadcast Mode Active**\n\n"
                f"**Total Users:** {user_count}\n\n"
                f"**Send your message to broadcast to all users:**\n"
                f"(Text, Photo, Video, Document supported)"
            )
            
        except Exception as e:
            logger.error(f"Error starting user broadcast: {e}")
            await message.reply_text("❌ **Error starting user broadcast!**")
    
    async def start_channel_broadcast(self, message: Message):
        """Start channel broadcast process"""
        try:
            channel_count = await self.permanent_db.get_channel_count()
            
            if channel_count == 0:
                await message.reply_text("❌ **No channels found in database!**")
                return
            
            # Set pending broadcast
            self.pending_broadcasts[message.from_user.id] = "channel"
            
            await message.reply_text(
                f"**📡 Channel Broadcast Mode Active**\n\n"
                f"**Total Channels:** {channel_count}\n\n"
                f"**Send your message to broadcast to all channels:**\n"
                f"(Text, Photo, Video, Document supported)"
            )
            
        except Exception as e:
            logger.error(f"Error starting channel broadcast: {e}")
            await message.reply_text("❌ **Error starting channel broadcast!**")
    
    async def process_user_broadcast(self, message: Message):
        """Process user broadcast"""
        try:
            # Get all users
            users = await self.permanent_db.get_all_users()
            
            if not users:
                await message.reply_text("❌ **No users found for broadcast!**")
                return
            
            # Generate broadcast ID
            broadcast_id = str(uuid.uuid4())
            
            # Send confirmation
            confirm_text = f"""
**📡 User Broadcast Confirmation**

**Message:** {message.text[:100]}...
**Total Users:** {len(users)}

**Proceeding with broadcast...**
"""
            
            await message.reply_text(confirm_text)
            
            # Start broadcast
            successful = 0
            failed = 0
            
            for user in users:
                try:
                    await self.app.send_message(
                        chat_id=user['user_id'],
                        text=message.text
                    )
                    successful += 1
                    
                    # Small delay to avoid flood limits
                    await asyncio.sleep(0.1)
                    
                except (UserIsBlocked, ChatWriteForbidden):
                    failed += 1
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    failed += 1
                except Exception as e:
                    logger.error(f"Error sending to user {user['user_id']}: {e}")
                    failed += 1
            
            # Log broadcast
            broadcast_data = {
                "broadcast_id": broadcast_id,
                "message_text": message.text,
                "sent_by_user_id": message.from_user.id,
                "total_users": len(users),
                "successful_sends": successful,
                "failed_sends": failed,
                "broadcast_type": "user"
            }
            
            await self.permanent_db.log_broadcast(broadcast_data)
            
            # Send completion message
            completion_text = f"""
**✅ User Broadcast Completed!**

**📊 Results:**
**✅ Successful:** {successful}
**❌ Failed:** {failed}
**📊 Total:** {len(users)}

**Broadcast ID:** `{broadcast_id}`
"""
            
            await message.reply_text(completion_text)
            
        except Exception as e:
            logger.error(f"Error processing user broadcast: {e}")
            await message.reply_text("❌ **Error processing user broadcast!**")
    
    async def process_channel_broadcast(self, message: Message):
        """Process channel broadcast"""
        try:
            # Get all channels
            channels = await self.permanent_db.get_all_channels()
            
            if not channels:
                await message.reply_text("❌ **No channels found for broadcast!**")
                return
            
            # Generate broadcast ID
            broadcast_id = str(uuid.uuid4())
            
            # Send confirmation
            confirm_text = f"""
**📡 Channel Broadcast Confirmation**

**Message:** {message.text[:100]}...
**Total Channels:** {len(channels)}

**Proceeding with broadcast...**
"""
            
            await message.reply_text(confirm_text)
            
            # Start broadcast
            successful = 0
            failed = 0
            
            for channel in channels:
                try:
                    await self.app.send_message(
                        chat_id=channel['channel_username'],
                        text=message.text
                    )
                    successful += 1
                    
                    # Small delay to avoid flood limits
                    await asyncio.sleep(0.1)
                    
                except (ChatWriteForbidden, Exception) as e:
                    logger.error(f"Error sending to channel {channel['channel_username']}: {e}")
                    failed += 1
            
            # Log broadcast
            broadcast_data = {
                "broadcast_id": broadcast_id,
                "message_text": message.text,
                "sent_by_user_id": message.from_user.id,
                "total_users": len(channels),
                "successful_sends": successful,
                "failed_sends": failed,
                "broadcast_type": "channel"
            }
            
            await self.permanent_db.log_broadcast(broadcast_data)
            
            # Send completion message
            completion_text = f"""
**✅ Channel Broadcast Completed!**

**📊 Results:**
**✅ Successful:** {successful}
**❌ Failed:** {failed}
**📊 Total:** {len(channels)}

**Broadcast ID:** `{broadcast_id}`
"""
            
            await message.reply_text(completion_text)
            
        except Exception as e:
            logger.error(f"Error processing channel broadcast: {e}")
            await message.reply_text("❌ **Error processing channel broadcast!**")
    
    async def show_database_stats(self, message: Message):
        """Show detailed database statistics"""
        try:
            # Get counts
            user_count = await self.permanent_db.get_user_count()
            channel_count = await self.permanent_db.get_channel_count()
            
            # Get recent users
            users = await self.permanent_db.get_all_users()
            recent_users = users[:5] if users else []
            
            # Get recent channels
            channels = await self.permanent_db.get_all_channels()
            recent_channels = channels[:5] if channels else []
            
            stats_text = f"""
**📊 Database Statistics**

**👥 Users:** {user_count}
**📢 Channels:** {channel_count}

**🔥 Recent Users:**
"""
            
            for user in recent_users:
                username = user.get('username', 'No username')
                first_name = user.get('first_name', 'No name')
                stats_text += f"**• @{username}** ({first_name})\n"
            
            stats_text += f"\n**📢 Recent Channels:**\n"
            
            for channel in recent_channels:
                channel_name = channel.get('channel_username', 'Unknown')
                channel_title = channel.get('channel_title', 'No title')
                stats_text += f"**• {channel_name}** ({channel_title})\n"
            
            await message.reply_text(stats_text)
            
        except Exception as e:
            logger.error(f"Error showing database stats: {e}")
            await message.reply_text("❌ **Error loading database statistics!**")