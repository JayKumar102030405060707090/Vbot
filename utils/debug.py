import logging
from pyrogram import Client
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, PeerIdInvalid, ChannelPrivate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DebugHelper:
    def __init__(self, app: Client):
        self.app = app
    
    async def debug_channel_access(self, channel_username: str):
        """Debug channel access and bot permissions"""
        try:
            logger.info(f"=== DEBUGGING CHANNEL: {channel_username} ===")
            
            # Clean channel username
            if channel_username.startswith('@'):
                channel_username = channel_username[1:]
            
            # Try to get channel info
            try:
                chat = await self.app.get_chat(channel_username)
                logger.info(f"✓ Channel found: {chat.title} (ID: {chat.id})")
                logger.info(f"✓ Channel type: {chat.type}")
                logger.info(f"✓ Members count: {getattr(chat, 'members_count', 'Unknown')}")
            except PeerIdInvalid:
                logger.error(f"✗ Channel not found or bot has no access to: {channel_username}")
                return False
            except ChannelPrivate:
                logger.error(f"✗ Channel is private: {channel_username}")
                return False
            except Exception as e:
                logger.error(f"✗ Error accessing channel: {e}")
                return False
            
            # Check bot membership and admin status
            try:
                me = await self.app.get_me()
                bot_member = await self.app.get_chat_member(chat.id, me.id)
                logger.info(f"✓ Bot membership status: {bot_member.status}")
                
                # Convert enum to string for comparison
                status_str = str(bot_member.status).split('.')[-1].lower()
                
                if status_str in ["administrator", "creator"]:
                    logger.info("✓ Bot has admin privileges")
                    if hasattr(bot_member, 'privileges') and bot_member.privileges:
                        logger.info(f"✓ Bot permissions: {bot_member.privileges}")
                    return True
                else:
                    logger.warning(f"✗ Bot is not admin. Status: {bot_member.status}")
                    return False
                    
            except UserNotParticipant:
                logger.error("✗ Bot is not a member of the channel")
                return False
            except ChatAdminRequired:
                logger.error("✗ Bot needs admin access to check membership")
                return False
            except Exception as e:
                logger.error(f"✗ Error checking bot status: {e}")
                return False
                
        except Exception as e:
            logger.error(f"✗ Unexpected error in debug: {e}")
            return False
    
    async def debug_user_subscription(self, user_id: int, channel_username: str):
        """Debug user subscription status"""
        try:
            logger.info(f"=== DEBUGGING USER SUBSCRIPTION ===")
            logger.info(f"User ID: {user_id}")
            logger.info(f"Channel: {channel_username}")
            
            # Clean channel username
            if channel_username.startswith('@'):
                channel_username = channel_username[1:]
            
            try:
                member = await self.app.get_chat_member(channel_username, user_id)
                logger.info(f"✓ User membership status: {member.status}")
                
                valid_statuses = ["member", "administrator", "creator"]
                is_valid = member.status in valid_statuses
                
                if is_valid:
                    logger.info("✓ User has valid subscription")
                else:
                    logger.warning(f"✗ User subscription not valid. Status: {member.status}")
                
                return is_valid
                
            except UserNotParticipant:
                logger.error("✗ User is not a participant in the channel")
                return False
            except ChatAdminRequired:
                logger.error("✗ Bot needs admin access to check user subscription")
                return False
            except Exception as e:
                logger.error(f"✗ Error checking user subscription: {e}")
                return False
                
        except Exception as e:
            logger.error(f"✗ Unexpected error in user subscription debug: {e}")
            return False