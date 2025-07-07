#!/usr/bin/env python3
"""
Debug vote removal without starting bot client
"""

import asyncio
from utils.db import Database
from config import Config

async def debug_vote_removal():
    """Debug vote removal by checking database directly"""
    
    # Initialize database
    db = Database()
    await db.connect()
    
    try:
        print("=== DEBUGGING VOTE REMOVAL ===")
        
        # Check specific channel
        channel_username = "@chanel1250kkkzza"
        print(f"Checking votes for channel: {channel_username}")
        
        # Get all user votes for this channel
        user_votes = await db.db["user_votes"].find({
            "channel_username": channel_username
        }).to_list(length=None)
        
        print(f"Found {len(user_votes)} total votes:")
        
        # Group votes by user
        user_vote_map = {}
        for vote in user_votes:
            user_id = vote["voter_id"]
            if user_id not in user_vote_map:
                user_vote_map[user_id] = []
            user_vote_map[user_id].append(vote)
        
        for user_id, votes in user_vote_map.items():
            print(f"\nUser {user_id}:")
            for vote in votes:
                print(f"  - Post: {vote.get('unique_post_id')}")
                print(f"    Participant: {vote.get('participant_user_id')}")
                print(f"    Timestamp: {vote.get('vote_timestamp')}")
        
        # Check participants in channel
        print(f"\n=== PARTICIPANTS IN {channel_username} ===")
        participants = await db.db["participants"].find({
            "channel_username": channel_username
        }).to_list(length=None)
        
        print(f"Found {len(participants)} participants:")
        for participant in participants:
            print(f"  - User: {participant.get('user_id')}")
            print(f"    Post ID: {participant.get('unique_post_id')}")
            print(f"    Vote Count: {participant.get('post_vote_count', 0)}")
            print(f"    Message ID: {participant.get('channel_message_id')}")
            print()
        
        # Manual vote removal simulation
        print("=== MANUAL VOTE REMOVAL SIMULATION ===")
        
        # Let's assume user 7168729089 unsubscribed
        unsubscribed_user_id = 7168729089
        print(f"Simulating removal for user {unsubscribed_user_id}")
        
        # Get their votes
        user_votes_to_remove = await db.db["user_votes"].find({
            "voter_id": unsubscribed_user_id,
            "channel_username": channel_username
        }).to_list(length=None)
        
        print(f"Found {len(user_votes_to_remove)} votes to remove")
        
        for vote in user_votes_to_remove:
            unique_post_id = vote.get("unique_post_id")
            print(f"Processing vote for post: {unique_post_id}")
            
            if unique_post_id:
                # Check current count
                participant_data = await db.db["participants"].find_one({
                    "channel_username": channel_username,
                    "unique_post_id": unique_post_id
                })
                
                if participant_data:
                    current_count = participant_data.get("post_vote_count", 0)
                    print(f"  Current count: {current_count}")
                    
                    # Simulate decrement
                    new_count = max(0, current_count - 1)
                    print(f"  New count would be: {new_count}")
                    
                    # Actually perform the update
                    result = await db.db["participants"].update_one(
                        {
                            "channel_username": channel_username,
                            "unique_post_id": unique_post_id
                        },
                        {"$set": {"post_vote_count": new_count}}
                    )
                    
                    if result.modified_count > 0:
                        print(f"  ✓ Updated count to {new_count}")
                    else:
                        print(f"  ✗ Failed to update count")
        
        # Remove the votes
        delete_result = await db.db["user_votes"].delete_many({
            "voter_id": unsubscribed_user_id,
            "channel_username": channel_username
        })
        
        print(f"Deleted {delete_result.deleted_count} vote records")
        
        print("\n=== FINAL STATE ===")
        # Check final state
        final_participants = await db.db["participants"].find({
            "channel_username": channel_username
        }).to_list(length=None)
        
        for participant in final_participants:
            print(f"  - User: {participant.get('user_id')}")
            print(f"    Post ID: {participant.get('unique_post_id')}")
            print(f"    Final Vote Count: {participant.get('post_vote_count', 0)}")
            print()
        
        print("Vote removal simulation completed!")
        
    except Exception as e:
        print(f"Error during debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_vote_removal())