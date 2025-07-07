#!/usr/bin/env python3
"""
Manual vote removal script for testing scheduler functionality
"""

import asyncio
from utils.db import Database
from utils.check import SubscriptionChecker
from config import Config
from pyrogram import Client
import os

async def manual_vote_removal():
    """Manually remove votes from unsubscribed users"""
    
    # Initialize database
    db = Database()
    await db.connect()
    
    # Initialize bot client
    app = Client(
        "vote_bot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN
    )
    
    # Initialize checker
    checker = SubscriptionChecker(app, db)
    
    try:
        print("Starting manual vote removal...")
        
        # Start the bot
        await app.start()
        
        # Check specific channel
        channel_username = "@chanel1250kkkzza"
        print(f"Checking votes for channel: {channel_username}")
        
        # Get all user votes for this channel
        user_votes = await db.db["user_votes"].find({
            "channel_username": channel_username
        }).to_list(length=None)
        
        print(f"Found {len(user_votes)} total votes")
        
        # Group votes by user
        user_vote_map = {}
        for vote in user_votes:
            user_id = vote["voter_id"]
            if user_id not in user_vote_map:
                user_vote_map[user_id] = []
            user_vote_map[user_id].append(vote)
        
        print(f"Votes from {len(user_vote_map)} unique users")
        
        # Check each user's subscription
        for user_id, votes in user_vote_map.items():
            print(f"\nChecking user {user_id} - {len(votes)} votes")
            
            # Check subscription status
            subscription_status = await checker.check_all_subscriptions(
                user_id, [Config.SUPPORT_CHANNEL, Config.UPDATE_CHANNEL, channel_username]
            )
            
            print(f"User {user_id} subscription status: {subscription_status}")
            
            if not subscription_status["all_subscribed"]:
                print(f"User {user_id} is not subscribed - removing votes...")
                
                # Remove each vote
                for vote in votes:
                    unique_post_id = vote.get("unique_post_id")
                    participant_user_id = vote["participant_user_id"]
                    
                    if unique_post_id:
                        # Decrement post vote count
                        result = await db.db["participants"].update_one(
                            {
                                "channel_username": channel_username,
                                "unique_post_id": unique_post_id
                            },
                            {"$inc": {"post_vote_count": -1}}
                        )
                        
                        if result.modified_count > 0:
                            print(f"Decremented vote count for post {unique_post_id}")
                            
                            # Get updated participant data
                            participant_data = await db.db["participants"].find_one({
                                "channel_username": channel_username,
                                "unique_post_id": unique_post_id
                            })
                            
                            if participant_data and participant_data.get("channel_message_id"):
                                new_count = participant_data.get("post_vote_count", 0)
                                print(f"New vote count for post {unique_post_id}: {new_count}")
                                
                                # Update channel button
                                try:
                                    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                                    emoji = "⚡"
                                    channel_name = channel_username[1:]
                                    updated_button = InlineKeyboardMarkup([
                                        [InlineKeyboardButton(f"{emoji} Vote for this participant ({new_count})", 
                                                            callback_data=f"channel_vote_{channel_name}_{unique_post_id}")]
                                    ])
                                    
                                    await app.edit_message_reply_markup(
                                        chat_id=channel_username,
                                        message_id=participant_data["channel_message_id"],
                                        reply_markup=updated_button
                                    )
                                    
                                    print(f"Updated channel button for post {unique_post_id}")
                                    
                                except Exception as e:
                                    print(f"Error updating button: {e}")
                
                # Remove user votes from database
                delete_result = await db.db["user_votes"].delete_many({
                    "voter_id": user_id,
                    "channel_username": channel_username
                })
                
                print(f"Deleted {delete_result.deleted_count} vote records for user {user_id}")
            else:
                print(f"User {user_id} is subscribed - keeping votes")
        
        print("\nManual vote removal completed!")
        
    except Exception as e:
        print(f"Error during manual vote removal: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await app.stop()

if __name__ == "__main__":
    asyncio.run(manual_vote_removal())