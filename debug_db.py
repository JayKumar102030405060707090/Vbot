import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

async def check_database():
    """Check database entries for debugging"""
    try:
        client = AsyncIOMotorClient(Config.MONGO_DB_URI)
        db = client[Config.DATABASE_NAME]
        
        print("=== PARTICIPANTS COLLECTION ===")
        participants = await db[Config.PARTICIPANTS_COLLECTION].find(
            {"channel_username": "@chanel1250kkkzza"}
        ).sort([("_id", -1)]).limit(10).to_list(length=10)
        
        for i, participant in enumerate(participants, 1):
            print(f"Entry {i}:")
            print(f"  User ID: {participant.get('user_id')}")
            print(f"  Channel: {participant.get('channel_username')}")
            print(f"  Unique Post ID: {participant.get('unique_post_id', 'NOT SET')}")
            print(f"  Post Vote Count: {participant.get('post_vote_count', 'NOT SET')}")
            print(f"  Channel Message ID: {participant.get('channel_message_id', 'NOT SET')}")
            print("---")
            
        print("\n=== USER VOTES COLLECTION ===")
        votes = await db["user_votes"].find(
            {"channel_username": "@chanel1250kkkzza"}
        ).sort([("_id", -1)]).limit(10).to_list(length=10)
        
        for i, vote in enumerate(votes, 1):
            print(f"Vote {i}:")
            print(f"  Voter: {vote.get('voter_id')}")
            print(f"  Participant: {vote.get('participant_user_id')}")
            print(f"  Unique Post ID: {vote.get('unique_post_id')}")
            print(f"  Timestamp: {vote.get('vote_timestamp')}")
            print("---")
            
    except Exception as e:
        print(f"Error checking database: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(check_database())