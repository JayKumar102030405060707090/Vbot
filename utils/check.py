from pyrogram import Client
from pyrogram.errors import UserNotParticipant, PeerIdInvalid, ChannelPrivate
from typing import List, Dict

class SubscriptionChecker:
    def __init__(self, app: Client, db):
        self.app = app
        self.db = db
    
    async def check_subscription(self, user_id: int, channel_username: str) -> bool:
        """Check if user is subscribed to a specific channel"""
        try:
            # Get chat information
            chat = await self.app.get_chat(channel_username)
            
            # Check user membership
            member = await self.app.get_chat_member(chat.id, user_id)
            
            # Valid subscription statuses - convert enum to string
            status_str = str(member.status).split('.')[-1].lower()
            valid_statuses = ["member", "administrator", "creator", "owner"]
            
            return status_str in valid_statuses
            
        except UserNotParticipant:
            return False
        except (PeerIdInvalid, ChannelPrivate):
            # Channel not accessible or doesn't exist
            return False
        except Exception as e:
            # If we get CHAT_ADMIN_REQUIRED, we'll assume user is subscribed
            # This happens when bot is not admin in the channel
            if "CHAT_ADMIN_REQUIRED" in str(e):
                print(f"Warning: Cannot verify subscription for {channel_username} - bot needs admin access")
                return True  # Assume subscribed to avoid blocking users
            print(f"Subscription check error for {channel_username}: {e}")
            return False
    
    async def check_all_subscriptions(self, user_id: int, channels: List[str]) -> Dict:
        """Check subscription to multiple channels"""
        subscription_results = {}
        missing_channels = []
        
        for channel in channels:
            is_subscribed = await self.check_subscription(user_id, channel)
            subscription_results[channel] = is_subscribed
            
            if not is_subscribed:
                missing_channels.append(channel)
        
        return {
            "all_subscribed": len(missing_channels) == 0,
            "subscription_results": subscription_results,
            "missing_channels": missing_channels
        }
    
    async def check_bot_admin_status(self, chat_id: int) -> Dict:
        """Check if bot is admin in the given chat"""
        try:
            # Get bot's own user ID first
            me = await self.app.get_me()
            bot_member = await self.app.get_chat_member(chat_id, me.id)
            
            is_admin = bot_member.status in ["administrator", "creator"]
            
            return {
                "is_member": True,
                "is_admin": is_admin,
                "status": bot_member.status,
                "permissions": bot_member.privileges if hasattr(bot_member, 'privileges') else None
            }
            
        except UserNotParticipant:
            return {
                "is_member": False,
                "is_admin": False,
                "status": "not_member",
                "permissions": None
            }
        except Exception as e:
            print(f"Bot admin check error: {e}")
            return {
                "is_member": False,
                "is_admin": False,
                "status": "error",
                "permissions": None,
                "error": str(e)
            }
    
    async def is_bot_admin(self, channel_username: str) -> bool:
        """Simple admin check function as per user's requirement"""
        try:
            # Clean channel username
            if channel_username.startswith('@'):
                channel_username = channel_username[1:]
            
            # Get chat by username
            chat = await self.app.get_chat(channel_username)
            
            # Get bot's own user ID
            me = await self.app.get_me()
            
            # Check bot's membership status
            bot_member = await self.app.get_chat_member(chat.id, me.id)
            
            # Return True if bot is admin or creator - convert enum to string
            status_str = str(bot_member.status).split('.')[-1].lower()
            return status_str in ["administrator", "creator", "owner"]
            
        except Exception as e:
            print(f"Admin check error for {channel_username}: {e}")
            return False
    
    async def check_user_admin_status(self, chat_id: int, user_id: int) -> Dict:
        """Check if user is admin in the given chat"""
        try:
            user_member = await self.app.get_chat_member(chat_id, user_id)
            
            # Convert enum to string for comparison
            status_str = str(user_member.status).split('.')[-1].lower()
            is_admin = status_str in ["administrator", "creator", "owner"]
            
            return {
                "is_member": True,
                "is_admin": is_admin,
                "status": user_member.status,
                "permissions": user_member.privileges if hasattr(user_member, 'privileges') else None
            }
            
        except UserNotParticipant:
            return {
                "is_member": False,
                "is_admin": False,
                "status": "not_member",
                "permissions": None
            }
        except Exception as e:
            print(f"User admin check error: {e}")
            return {
                "is_member": False,
                "is_admin": False,
                "status": "error",
                "permissions": None,
                "error": str(e)
            }
    
    async def get_channel_member_count(self, channel_username: str) -> int:
        """Get member count of a channel"""
        try:
            chat = await self.app.get_chat(channel_username)
            return chat.members_count if hasattr(chat, 'members_count') else 0
        except Exception as e:
            print(f"Error getting member count for {channel_username}: {e}")
            return 0
    
    async def validate_channel_access(self, channel_username: str) -> Dict:
        """Validate bot's access to a channel"""
        try:
            # Try to get chat info
            chat = await self.app.get_chat(channel_username)
            
            # Check bot status
            bot_status = await self.check_bot_admin_status(chat.id)
            
            return {
                "accessible": True,
                "chat_id": chat.id,
                "chat_title": chat.title,
                "chat_type": str(chat.type),
                "bot_status": bot_status,
                "member_count": getattr(chat, 'members_count', 0)
            }
            
        except PeerIdInvalid:
            return {
                "accessible": False,
                "error": "Channel not found or bot doesn't have access",
                "error_type": "peer_invalid"
            }
        except ChannelPrivate:
            return {
                "accessible": False,
                "error": "Channel is private and bot is not a member",
                "error_type": "channel_private"
            }
        except Exception as e:
            return {
                "accessible": False,
                "error": str(e),
                "error_type": "unknown"
            }
