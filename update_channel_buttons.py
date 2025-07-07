#!/usr/bin/env python3
"""
Update channel buttons with new vote counts
"""

import asyncio
from utils.db import Database
from config import Config
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import time

async def update_channel_buttons():
    """Update channel buttons with new vote counts"""
    
    # Initialize database
    db = Database()
    await db.connect()
    
    # Initialize bot client with retry logic
    app = Client(
        "vote_bot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN
    )
    
    try:
        print("Starting channel button updates...")
        
        # Start the bot with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await app.start()
                print("Bot started successfully!")
                break
            except Exception as e:
                print(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    print("Retrying in 5 seconds...")
                    await asyncio.sleep(5)
                else:
                    raise
        
        # Check specific channel
        channel_username = "@chanel1250kkkzza"
        print(f"Updating buttons for channel: {channel_username}")
        
        # Get all participants with channel messages
        participants = await db.db["participants"].find({
            "channel_username": channel_username,
            "channel_message_id": {"$exists": True, "$ne": None}
        }).to_list(length=None)
        
        print(f"Found {len(participants)} participants with channel messages")
        
        for participant in participants:
            unique_post_id = participant.get("unique_post_id")
            message_id = participant.get("channel_message_id")
            current_count = participant.get("post_vote_count", 0)
            
            if unique_post_id and message_id:
                print(f"Updating button for post {unique_post_id}, message {message_id}, count {current_count}")
                
                try:
                    # Create updated button
                    emoji = "⚡"
                    channel_name = channel_username[1:]  # Remove @ prefix
                    updated_button = InlineKeyboardMarkup([
                        [InlineKeyboardButton(f"{emoji} Vote for this participant ({current_count})", 
                                            callback_data=f"channel_vote_{channel_name}_{unique_post_id}")]
                    ])
                    
                    # Update the message
                    await app.edit_message_reply_markup(
                        chat_id=channel_username,
                        message_id=message_id,
                        reply_markup=updated_button
                    )
                    
                    print(f"✓ Updated button for post {unique_post_id} with count {current_count}")
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    print(f"✗ Error updating button for post {unique_post_id}: {e}")
        
        print("Channel button updates completed!")
        
    except Exception as e:
        print(f"Error during button updates: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            await app.stop()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(update_channel_buttons())