import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

async def fix_database():
    """Fix database entries by cleaning up old entries without unique_post_id"""
    try:
        client = AsyncIOMotorClient(Config.MONGO_DB_URI)
        db = client[Config.DATABASE_NAME]
        
        print("=== CLEANING UP OLD ENTRIES ===")
        
        # Remove entries that don't have unique_post_id
        result = await db[Config.PARTICIPANTS_COLLECTION].delete_many({
            "unique_post_id": {"$exists": False}
        })
        print(f"Deleted {result.deleted_count} old entries without unique_post_id")
        
        # Remove entries that have unique_post_id as None or empty
        result = await db[Config.PARTICIPANTS_COLLECTION].delete_many({
            "$or": [
                {"unique_post_id": None},
                {"unique_post_id": ""}
            ]
        })
        print(f"Deleted {result.deleted_count} entries with empty unique_post_id")
        
        print("=== DATABASE CLEANUP COMPLETE ===")
        
    except Exception as e:
        print(f"Error fixing database: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(fix_database())