import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PermanentDatabase:
    def __init__(self):
        self.mongo_uri = os.getenv("MONGO_DB_URI") or Config.MONGO_DB_URI
        self.client = None
        self.db = None
        
    async def connect(self):
        """Connect to MongoDB database"""
        try:
            self.client = AsyncIOMotorClient(self.mongo_uri)
            self.db = self.client.permanent_storage
            logger.info("Connected to MongoDB permanent storage successfully!")
            await self.create_indexes()
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            raise
    
    async def create_indexes(self):
        """Create indexes for better performance"""
        try:
            # Create indexes for users collection
            await self.db.permanent_users.create_index("user_id", unique=True)
            await self.db.permanent_users.create_index("last_seen")
            await self.db.permanent_users.create_index("is_active")
            
            # Create indexes for channels collection
            await self.db.permanent_channels.create_index("channel_username", unique=True)
            await self.db.permanent_channels.create_index("added_by_user_id")
            await self.db.permanent_channels.create_index("last_vote_created")
            
            # Create indexes for broadcast logs
            await self.db.broadcast_logs.create_index("broadcast_id", unique=True)
            await self.db.broadcast_logs.create_index("sent_at")
            
            logger.info("MongoDB indexes created successfully!")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            raise
    
    async def save_user(self, user_data):
        """Save user permanently to MongoDB"""
        try:
            existing_user = await self.db.permanent_users.find_one({"user_id": user_data['user_id']})
            
            if existing_user:
                # Update existing user
                await self.db.permanent_users.update_one(
                    {"user_id": user_data['user_id']},
                    {
                        "$set": {
                            "username": user_data.get('username'),
                            "first_name": user_data.get('first_name'),
                            "last_name": user_data.get('last_name'),
                            "last_seen": datetime.now(),
                            "is_active": True
                        },
                        "$inc": {"total_commands": 1}
                    }
                )
                logger.info(f"Updated existing user: {user_data['user_id']}")
            else:
                # Insert new user
                new_user = {
                    "user_id": user_data['user_id'],
                    "username": user_data.get('username'),
                    "first_name": user_data.get('first_name'),
                    "last_name": user_data.get('last_name'),
                    "is_bot": user_data.get('is_bot', False),
                    "language_code": user_data.get('language_code'),
                    "is_premium": user_data.get('is_premium', False),
                    "first_seen": datetime.now(),
                    "last_seen": datetime.now(),
                    "total_commands": 1,
                    "is_active": True
                }
                await self.db.permanent_users.insert_one(new_user)
                logger.info(f"Saved new user: {user_data['user_id']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving user: {e}")
            return False
    
    async def save_channel(self, channel_data):
        """Save channel permanently to MongoDB"""
        try:
            existing_channel = await self.db.permanent_channels.find_one({"channel_username": channel_data['channel_username']})
            
            if existing_channel:
                # Update existing channel
                await self.db.permanent_channels.update_one(
                    {"channel_username": channel_data['channel_username']},
                    {
                        "$set": {
                            "channel_id": channel_data.get('channel_id'),
                            "channel_title": channel_data.get('channel_title'),
                            "last_vote_created": datetime.now(),
                            "is_active": True
                        },
                        "$inc": {"total_votes_created": 1}
                    }
                )
                logger.info(f"Updated existing channel: {channel_data['channel_username']}")
            else:
                # Insert new channel
                new_channel = {
                    "channel_username": channel_data['channel_username'],
                    "channel_id": channel_data.get('channel_id'),
                    "channel_title": channel_data.get('channel_title'),
                    "added_by_user_id": channel_data.get('added_by_user_id'),
                    "added_date": datetime.now(),
                    "last_vote_created": datetime.now(),
                    "total_votes_created": 1,
                    "is_active": True,
                    "member_count": 0
                }
                await self.db.permanent_channels.insert_one(new_channel)
                logger.info(f"Saved new channel: {channel_data['channel_username']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving channel: {e}")
            return False
    
    async def get_all_users(self):
        """Get all active users for broadcasting"""
        try:
            users = await self.db.permanent_users.find(
                {"is_active": True}
            ).sort("last_seen", -1).to_list(length=None)
            return users
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []
    
    async def get_all_channels(self):
        """Get all active channels for broadcasting"""
        try:
            channels = await self.db.permanent_channels.find(
                {"is_active": True}
            ).sort("last_vote_created", -1).to_list(length=None)
            return channels
        except Exception as e:
            logger.error(f"Error getting channels: {e}")
            return []
    
    async def get_user_count(self):
        """Get total active user count"""
        try:
            count = await self.db.permanent_users.count_documents({"is_active": True})
            return count
        except Exception as e:
            logger.error(f"Error getting user count: {e}")
            return 0
    
    async def get_channel_count(self):
        """Get total active channel count"""
        try:
            count = await self.db.permanent_channels.count_documents({"is_active": True})
            return count
        except Exception as e:
            logger.error(f"Error getting channel count: {e}")
            return 0
    
    async def log_broadcast(self, broadcast_data):
        """Log broadcast activity"""
        try:
            broadcast_log = {
                "broadcast_id": broadcast_data['broadcast_id'],
                "message_text": broadcast_data['message_text'],
                "sent_by_user_id": broadcast_data['sent_by_user_id'],
                "total_users": broadcast_data['total_users'],
                "successful_sends": broadcast_data['successful_sends'],
                "failed_sends": broadcast_data['failed_sends'],
                "broadcast_type": broadcast_data.get('broadcast_type', 'user'),
                "sent_at": datetime.now()
            }
            await self.db.broadcast_logs.insert_one(broadcast_log)
            return True
        except Exception as e:
            logger.error(f"Error logging broadcast: {e}")
            return False
    
    async def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

# Global database instance
permanent_db = PermanentDatabase()