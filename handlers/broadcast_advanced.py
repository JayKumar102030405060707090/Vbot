import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, ChatWriteForbidden, UserIsBlocked, ChatAdminRequired, MessageNotModified
from config import Config
from utils.db import Database
import logging

logger = logging.getLogger(__name__)

# Global broadcasting lock
IS_BROADCASTING = False

class AdvancedBroadcastHandler:
    def __init__(self, app: Client, db: Database):
        self.app = app
        self.db = db
        
    def register(self):
        """Register advanced broadcast handlers"""
        
        @self.app.on_message(filters.command("broadcast") & filters.user(Config.OWNER_ID))
        async def broadcast_command(client: Client, message: Message):
            global IS_BROADCASTING
            
            if IS_BROADCASTING:
                await message.reply_text("❌ **Another broadcast is already in progress. Please wait...**")
                return
            
            # Parse command and flags
            command_text = message.text
            flags = self.parse_flags(command_text)
            
            # Get broadcast message
            broadcast_msg = None
            if message.reply_to_message:
                broadcast_msg = message.reply_to_message
                broadcast_text = "Forwarded Message"
            else:
                # Extract text after command and flags
                text_parts = command_text.split()[1:]  # Remove /broadcast
                # Remove flags from text
                cleaned_text = []
                for part in text_parts:
                    if not part.startswith('-'):
                        cleaned_text.append(part)
                
                if cleaned_text:
                    broadcast_text = ' '.join(cleaned_text)
                else:
                    await message.reply_text("❌ **Please provide a message to broadcast or reply to a message.**")
                    return
            
            # Set broadcasting lock
            IS_BROADCASTING = True
            
            try:
                await self.execute_broadcast(message, broadcast_msg, broadcast_text, flags)
            finally:
                IS_BROADCASTING = False
    
    def parse_flags(self, command_text: str) -> dict:
        """Parse command flags"""
        flags = {
            'pin': False,
            'pinloud': False,
            'nobot': False,
            'user': False
        }
        
        if '-pin' in command_text and '-pinloud' not in command_text:
            flags['pin'] = True
        if '-pinloud' in command_text:
            flags['pinloud'] = True
        if '-nobot' in command_text:
            flags['nobot'] = True
        if '-user' in command_text:
            flags['user'] = True
            
        return flags
    
    async def execute_broadcast(self, original_message: Message, broadcast_msg: Message, broadcast_text: str, flags: dict):
        """Execute the broadcast with given parameters"""
        
        # Get targets based on flags
        if flags['user']:
            # Only users
            served_users = await self.get_served_users()
            served_chats = []
            targets = served_users
            target_type = "users"
        else:
            # Both users and chats
            served_users = await self.get_served_users()
            served_chats = await self.get_served_chats()
            targets = served_users + served_chats
            target_type = "users and chats"
        
        if not targets:
            await original_message.reply_text(f"❌ **No {target_type} found in database.**")
            return
        
        # Send initial status
        status_msg = await original_message.reply_text(
            f"📡 **Broadcasting to {len(targets)} {target_type}...**\n\n"
            f"**Message:** {broadcast_text[:50]}{'...' if len(broadcast_text) > 50 else ''}\n"
            f"**Flags:** {', '.join([k for k, v in flags.items() if v]) or 'None'}"
        )
        
        # Broadcast statistics
        success_count = 0
        failed_count = 0
        pinned_count = 0
        
        # Process each target
        for i, target in enumerate(targets):
            try:
                # Skip bots if nobot flag is set
                if flags['nobot'] and target.get('is_bot', False):
                    continue
                
                chat_id = target.get('chat_id') or target.get('user_id')
                if not chat_id:
                    failed_count += 1
                    continue
                
                # Send message
                sent_message = None
                if broadcast_msg:
                    # Forward the replied message
                    try:
                        sent_message = await self.app.forward_messages(
                            chat_id=chat_id,
                            from_chat_id=broadcast_msg.chat.id,
                            message_ids=broadcast_msg.id
                        )
                    except Exception:
                        # If forward fails, try copying the message
                        if broadcast_msg.text:
                            sent_message = await self.app.send_message(chat_id, broadcast_msg.text)
                        elif broadcast_msg.photo:
                            sent_message = await self.app.send_photo(
                                chat_id, broadcast_msg.photo.file_id, 
                                caption=broadcast_msg.caption
                            )
                        elif broadcast_msg.video:
                            sent_message = await self.app.send_video(
                                chat_id, broadcast_msg.video.file_id,
                                caption=broadcast_msg.caption
                            )
                        elif broadcast_msg.document:
                            sent_message = await self.app.send_document(
                                chat_id, broadcast_msg.document.file_id,
                                caption=broadcast_msg.caption
                            )
                else:
                    # Send text message
                    sent_message = await self.app.send_message(chat_id, broadcast_text)
                
                if sent_message:
                    success_count += 1
                    
                    # Handle pinning if requested
                    if (flags['pin'] or flags['pinloud']) and sent_message:
                        try:
                            await self.app.pin_chat_message(
                                chat_id=chat_id,
                                message_id=sent_message.id if hasattr(sent_message, 'id') else sent_message[0].id,
                                disable_notification=flags['pin']  # True for silent pin
                            )
                            pinned_count += 1
                        except (ChatAdminRequired, Exception) as e:
                            logger.debug(f"Could not pin message in {chat_id}: {e}")
                else:
                    failed_count += 1
                
                # Update status every 20 messages
                if (i + 1) % 20 == 0:
                    try:
                        await status_msg.edit_text(
                            f"📡 **Broadcasting Progress**\n\n"
                            f"**Processed:** {i + 1}/{len(targets)}\n"
                            f"**Success:** {success_count}\n"
                            f"**Failed:** {failed_count}\n"
                            f"**Pinned:** {pinned_count}"
                        )
                    except MessageNotModified:
                        pass
                
                # Flood protection
                await asyncio.sleep(0.1)
                
            except FloodWait as e:
                logger.info(f"FloodWait: sleeping for {e.x} seconds")
                await asyncio.sleep(e.x)
                # Retry the same target
                continue
                
            except (UserIsBlocked, ChatWriteForbidden):
                failed_count += 1
                continue
                
            except Exception as e:
                logger.error(f"Error broadcasting to {chat_id}: {e}")
                failed_count += 1
                continue
        
        # Send final results
        final_text = f"""
✅ **Broadcast Completed!**

📊 **Results:**
**✅ Successful:** {success_count}
**❌ Failed:** {failed_count}
**📌 Pinned:** {pinned_count}
**📊 Total Targets:** {len(targets)}

**Message:** {broadcast_text[:100]}{'...' if len(broadcast_text) > 100 else ''}
**Flags Used:** {', '.join([k for k, v in flags.items() if v]) or 'None'}
"""
        
        try:
            await status_msg.edit_text(final_text)
        except MessageNotModified:
            await original_message.reply_text(final_text)
    
    async def get_served_chats(self):
        """Get all served chats from MongoDB"""
        try:
            chats = await self.db.get_collection("served_chats").find({}).to_list(length=None)
            return chats
        except Exception as e:
            logger.error(f"Error getting served chats: {e}")
            return []
    
    async def get_served_users(self):
        """Get all served users from MongoDB"""
        try:
            users = await self.db.get_collection("served_users").find({}).to_list(length=None)
            return users
        except Exception as e:
            logger.error(f"Error getting served users: {e}")
            return []
    
    async def add_served_chat(self, chat_id: int, chat_title: str = None, chat_type: str = None):
        """Add a chat to served chats collection"""
        try:
            chat_data = {
                "chat_id": chat_id,
                "chat_title": chat_title,
                "chat_type": chat_type,
                "added_date": self.db.get_current_time()
            }
            
            await self.db.get_collection("served_chats").update_one(
                {"chat_id": chat_id},
                {"$set": chat_data},
                upsert=True
            )
            logger.info(f"Added served chat: {chat_id}")
            
        except Exception as e:
            logger.error(f"Error adding served chat: {e}")
    
    async def add_served_user(self, user_id: int, username: str = None, first_name: str = None, is_bot: bool = False):
        """Add a user to served users collection"""
        try:
            user_data = {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "is_bot": is_bot,
                "added_date": self.db.get_current_time()
            }
            
            await self.db.get_collection("served_users").update_one(
                {"user_id": user_id},
                {"$set": user_data},
                upsert=True
            )
            logger.info(f"Added served user: {user_id}")
            
        except Exception as e:
            logger.error(f"Error adding served user: {e}")

# Auto-add middleware to track served chats and users
class ServedTracker:
    def __init__(self, broadcast_handler: AdvancedBroadcastHandler):
        self.broadcast_handler = broadcast_handler
    
    def register_middleware(self, app: Client):
        """Register middleware to track all chats and users"""
        
        @app.on_message(filters.all, group=-1)  # High priority to catch all messages
        async def track_served(client: Client, message: Message):
            try:
                # Track user
                if message.from_user and not message.from_user.is_deleted:
                    await self.broadcast_handler.add_served_user(
                        user_id=message.from_user.id,
                        username=message.from_user.username,
                        first_name=message.from_user.first_name,
                        is_bot=message.from_user.is_bot
                    )
                
                # Track chat (groups, channels)
                if message.chat.type in ["group", "supergroup", "channel"]:
                    await self.broadcast_handler.add_served_chat(
                        chat_id=message.chat.id,
                        chat_title=message.chat.title,
                        chat_type=message.chat.type
                    )
                
            except Exception as e:
                logger.debug(f"Error in served tracker: {e}")