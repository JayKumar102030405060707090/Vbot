from motor.motor_asyncio import AsyncIOMotorClient
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from bson import ObjectId
from config import Config
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def LOGGER(name):
    return logging.getLogger(name)

class Database:
    def __init__(self):
        self.client = None
        self.db = None
    
    async def connect(self):
        """Connect to MongoDB permanently"""
        try:
            LOGGER(__name__).info("Connecting to your Mongo Database...")
            self.client = AsyncIOMotorClient(Config.MONGO_DB_URI)
            self.db = self.client[Config.DATABASE_NAME]
            
            # Test connection
            await self.client.admin.command('ping')
            LOGGER(__name__).info("Connected to your Mongo Database.")
            print("Connected to MongoDB successfully!")
                
        except Exception as e:
            LOGGER(__name__).error("Failed to connect to your Mongo Database.")
            print(f"MongoDB connection failed: {e}")
            print("Please check your MONGO_DB_URI environment variable")
            exit()
    
    async def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
    
    async def get_current_timestamp(self) -> str:
        """Get current timestamp as string"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Vote operations
    async def create_vote(self, vote_data: Dict) -> str:
        """Create a new vote poll"""
        result = await self.db[Config.VOTES_COLLECTION].insert_one(vote_data)
        return str(result.inserted_id)
    
    async def get_vote_by_channel(self, channel_username: str) -> Optional[Dict]:
        """Get vote poll by channel username"""
        return await self.db[Config.VOTES_COLLECTION].find_one({
            "channel": channel_username,
            "status": "active"
        })
    
    async def get_vote_by_id(self, vote_id: str) -> Optional[Dict]:
        """Get vote poll by ID"""
        return await self.db[Config.VOTES_COLLECTION].find_one({"_id": ObjectId(vote_id)})
    
    async def delete_vote(self, vote_id: str) -> bool:
        """Delete a vote poll"""
        result = await self.db[Config.VOTES_COLLECTION].delete_one({"_id": ObjectId(vote_id)})
        return result.deleted_count > 0
    
    # Participation operations
    async def add_participation(self, participation_data: Dict) -> str:
        """Add a vote participation"""
        result = await self.db[Config.PARTICIPANTS_COLLECTION].insert_one(participation_data)
        return str(result.inserted_id)
    
    async def get_participation(self, vote_id: str, user_id: int) -> Optional[Dict]:
        """Check if user already participated in vote"""
        vote_obj_id = ObjectId(vote_id)
        return await self.db[Config.PARTICIPANTS_COLLECTION].find_one({
            "vote_id": vote_obj_id,
            "user_id": user_id
        })
    
    async def remove_participation(self, vote_id: str, user_id: int) -> bool:
        """Remove user participation"""
        vote_obj_id = ObjectId(vote_id)
        result = await self.db[Config.PARTICIPANTS_COLLECTION].delete_one({
            "vote_id": vote_obj_id,
            "user_id": user_id
        })
        return result.deleted_count > 0
    
    async def get_vote_count(self, vote_id: str) -> int:
        """Get total vote count for a poll"""
        vote_obj_id = ObjectId(vote_id)
        return await self.db[Config.PARTICIPANTS_COLLECTION].count_documents({"vote_id": vote_obj_id})
    
    async def get_vote_participants(self, vote_id: str) -> List[Dict]:
        """Get all participants for a vote"""
        vote_obj_id = ObjectId(vote_id)
        cursor = self.db[Config.PARTICIPANTS_COLLECTION].find({"vote_id": vote_obj_id})
        return await cursor.to_list(length=None)
    
    async def delete_vote_participations(self, vote_id: str) -> int:
        """Delete all participations for a vote"""
        vote_obj_id = ObjectId(vote_id)
        result = await self.db[Config.PARTICIPANTS_COLLECTION].delete_many({"vote_id": vote_obj_id})
        return result.deleted_count
    
    # User operations
    async def store_user(self, user_data: Dict) -> str:
        """Store user information"""
        # Upsert user
        result = await self.db["users"].update_one(
            {"user_id": user_data["user_id"]},
            {"$set": {**user_data, "last_seen": datetime.now()}},
            upsert=True
        )
        return str(result.upserted_id) if result.upserted_id else str(user_data["user_id"])
    
    # Statistics operations
    async def get_bot_stats(self) -> Dict:
        """Get comprehensive bot statistics"""
        # MongoDB aggregation for stats
        active_votes = await self.db[Config.VOTES_COLLECTION].count_documents({"active": True})
        total_votes = await self.db[Config.VOTES_COLLECTION].count_documents({})
        total_participations = await self.db[Config.PARTICIPANTS_COLLECTION].count_documents({})
        
        # Unique participants
        unique_participants_pipeline = [
            {"$group": {"_id": "$user_id"}},
            {"$count": "unique_count"}
        ]
        unique_result = await self.db[Config.PARTICIPANTS_COLLECTION].aggregate(unique_participants_pipeline).to_list(1)
        unique_participants = unique_result[0]["unique_count"] if unique_result else 0
        
        total_users = await self.db["users"].count_documents({})
        
        # Most active channel
        channel_pipeline = [
            {"$group": {"_id": "$channel_username", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 1}
        ]
        channel_result = await self.db[Config.PARTICIPANTS_COLLECTION].aggregate(channel_pipeline).to_list(1)
        most_active_channel = f"{channel_result[0]['_id']} ({channel_result[0]['count']} votes)" if channel_result else "None"
        
        return {
            "active_votes": active_votes,
            "total_votes": total_votes,
            "total_participations": total_participations,
            "unique_participants": unique_participants,
            "total_users": total_users,
            "most_active_channel": most_active_channel
        }
    
    async def get_user_participations(self, user_id: int) -> List[Dict]:
        """Get all participations by a user"""
        cursor = self.db[Config.PARTICIPANTS_COLLECTION].find({"user_id": user_id})
        return await cursor.to_list(length=None)
