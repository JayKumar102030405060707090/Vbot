import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from pyrogram import Client
from config import Config
from utils.check import SubscriptionChecker

class VoteScheduler:
    def __init__(self, app: Client, db):
        self.app = app
        self.db = db
        self.scheduler = AsyncIOScheduler()
        self.checker = SubscriptionChecker(app, db)
        self.is_running = False
    
    async def start(self):
        """Start the scheduler"""
        if not self.is_running:
            # Add subscription check job
            self.scheduler.add_job(
                self.check_subscriptions,
                IntervalTrigger(minutes=Config.SUBSCRIPTION_CHECK_INTERVAL),
                id='subscription_check',
                replace_existing=True
            )
            
            # Add cleanup job (runs daily)
            self.scheduler.add_job(
                self.cleanup_old_data,
                IntervalTrigger(hours=24),
                id='daily_cleanup',
                replace_existing=True
            )
            
            # Start scheduler
            self.scheduler.start()
            self.is_running = True
            print(f"Scheduler started! Checking subscriptions every {Config.SUBSCRIPTION_CHECK_INTERVAL} minutes.")
    
    async def stop(self):
        """Stop the scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            print("Scheduler stopped.")
    
    async def check_subscriptions(self):
        """Check all participants' subscriptions and remove invalid ones"""
        try:
            print("Starting subscription check...")
            
            # Get all active votes
            votes = await self.get_active_votes()
            
            total_removed = 0
            for vote in votes:
                removed_count = await self.check_vote_subscriptions(vote)
                total_removed += removed_count
            
            if total_removed > 0:
                print(f"Subscription check completed. Removed {total_removed} invalid participations.")
            else:
                print("Subscription check completed. No invalid participations found.")
                
        except Exception as e:
            print(f"Error in subscription check: {e}")
    
    async def get_active_votes(self):
        """Get all active vote polls"""
        try:
            cursor = self.db.db[Config.VOTES_COLLECTION].find({"active": True})
            return await cursor.to_list(length=None)
        except Exception as e:
            print(f"Error getting active votes: {e}")
            return []
    
    async def check_vote_subscriptions(self, vote_data: dict):
        """Check subscriptions for a specific vote and remove invalid participants"""
        removed_count = 0
        
        try:
            channel_username = vote_data["channel_username"]
            print(f"Checking subscriptions for channel: {channel_username}")
            
            # Get all user votes for this channel (not participants)
            user_votes = await self.db.db["user_votes"].find({
                "channel_username": channel_username
            }).to_list(length=None)
            
            # Group votes by user
            user_vote_map = {}
            for vote in user_votes:
                user_id = vote["voter_id"]
                if user_id not in user_vote_map:
                    user_vote_map[user_id] = []
                user_vote_map[user_id].append(vote)
            
            print(f"Found votes from {len(user_vote_map)} unique users")
            
            # Check each user's subscription
            for user_id, votes in user_vote_map.items():
                try:
                    # Check if user is still subscribed to all required channels
                    subscription_status = await self.checker.check_all_subscriptions(
                        user_id, [Config.SUPPORT_CHANNEL, Config.UPDATE_CHANNEL, channel_username]
                    )
                    
                    if not subscription_status["all_subscribed"]:
                        print(f"User {user_id} is not subscribed - removing {len(votes)} votes")
                        
                        # Remove each vote and update counts
                        for vote in votes:
                            unique_post_id = vote.get("unique_post_id")
                            
                            if unique_post_id:
                                # Decrement post vote count
                                result = await self.db.db["participants"].update_one(
                                    {
                                        "channel_username": channel_username,
                                        "unique_post_id": unique_post_id
                                    },
                                    {"$inc": {"post_vote_count": -1}}
                                )
                                
                                if result.modified_count > 0:
                                    print(f"Decremented vote count for post {unique_post_id}")
                                    
                                    # Update channel button
                                    await self.update_channel_vote_button_by_post_id(channel_username, unique_post_id)
                        
                        # Remove all votes from this user
                        delete_result = await self.db.db["user_votes"].delete_many({
                            "voter_id": user_id,
                            "channel_username": channel_username
                        })
                        
                        removed_count += delete_result.deleted_count
                        print(f"Removed {delete_result.deleted_count} votes from user {user_id}")
                        
                except Exception as e:
                    print(f"Error checking user {user_id}: {e}")
                    continue
            
        except Exception as e:
            print(f"Error checking subscriptions for vote {vote_data.get('channel_username', 'unknown')}: {e}")
        
        return removed_count
    
    async def remove_user_votes(self, unsubscribed_user_id: int, channel_username: str):
        """Remove all votes cast by an unsubscribed user and decrement participant vote counts"""
        try:
            # Find all votes cast by this user in this channel
            user_votes = await self.db.db["user_votes"].find({
                "voter_id": unsubscribed_user_id,
                "channel_username": channel_username
            }).to_list(length=None)
            
            votes_removed = 0
            
            for vote in user_votes:
                participant_user_id = vote["participant_user_id"]
                unique_post_id = vote.get("unique_post_id")
                
                if unique_post_id:
                    # Decrement the vote count for this specific post
                    result = await self.db.db[Config.PARTICIPANTS_COLLECTION].update_one(
                        {
                            "channel_username": channel_username,
                            "unique_post_id": unique_post_id
                        },
                        {"$inc": {"post_vote_count": -1}}
                    )
                    
                    if result.modified_count > 0:
                        votes_removed += 1
                        print(f"Removed vote from user {unsubscribed_user_id} for post {unique_post_id}")
                        
                        # Update the channel message button with new vote count
                        await self.update_channel_vote_button_by_post_id(channel_username, unique_post_id)
                else:
                    # Fallback for old votes without unique_post_id
                    result = await self.db.db[Config.PARTICIPANTS_COLLECTION].update_one(
                        {
                            "channel_username": channel_username,
                            "user_id": participant_user_id
                        },
                        {"$inc": {"vote_count": -1}}
                    )
                    
                    if result.modified_count > 0:
                        votes_removed += 1
                        print(f"Removed vote from user {unsubscribed_user_id} for participant {participant_user_id} (legacy)")
                        
                        # Update the channel message button with new vote count
                        await self.update_channel_vote_button(channel_username, participant_user_id)
            
            # Remove all vote records for this user in this channel
            delete_result = await self.db.db["user_votes"].delete_many({
                "voter_id": unsubscribed_user_id,
                "channel_username": channel_username
            })
            
            print(f"Removed {votes_removed} votes from unsubscribed user {unsubscribed_user_id} in {channel_username}")
            print(f"Deleted {delete_result.deleted_count} vote records from database")
            
        except Exception as e:
            print(f"Error removing votes for unsubscribed user {unsubscribed_user_id}: {e}")
    
    async def update_channel_vote_button_by_post_id(self, channel_username: str, unique_post_id: str):
        """Update the vote button in channel message with new count using unique post ID"""
        try:
            # Get updated participant data by unique_post_id
            participant_data = await self.db.db[Config.PARTICIPANTS_COLLECTION].find_one({
                "channel_username": channel_username,
                "unique_post_id": unique_post_id
            })
            
            if participant_data and participant_data.get("channel_message_id"):
                new_count = participant_data.get("post_vote_count", 0)
                emoji = "⚡"
                
                # Create updated button
                from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                channel_name = channel_username[1:]  # Remove @ prefix
                updated_button = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"{emoji} Vote for this participant ({new_count})", callback_data=f"channel_vote_{channel_name}_{unique_post_id}")]
                ])
                
                # Update the message
                await self.app.edit_message_reply_markup(
                    chat_id=channel_username,
                    message_id=participant_data["channel_message_id"],
                    reply_markup=updated_button
                )
                
                print(f"Updated channel vote button for post {unique_post_id} with count {new_count}")
                
        except Exception as e:
            print(f"Error updating channel vote button by post ID: {e}")
    
    async def update_channel_vote_button(self, channel_username: str, participant_user_id: int):
        """Update the vote button in channel message with new count"""
        try:
            # Get updated participant data
            participant_data = await self.db.db[Config.PARTICIPANTS_COLLECTION].find_one({
                "channel_username": channel_username,
                "user_id": participant_user_id
            })
            
            if participant_data and participant_data.get("channel_message_id"):
                new_count = participant_data.get("vote_count", 0)
                emoji = "⚡"
                
                # Create updated button
                from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                channel_name = channel_username[1:]  # Remove @ prefix
                updated_button = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"{emoji} Vote for this participant ({new_count})", 
                                        callback_data=f"channel_vote_{channel_name}_{participant_user_id}")]
                ])
                
                # Update the channel message
                await self.app.edit_message_reply_markup(
                    chat_id=channel_username,
                    message_id=participant_data["channel_message_id"],
                    reply_markup=updated_button
                )
                
                print(f"Updated channel vote button for participant {participant_user_id} with new count: {new_count}")
        except Exception as e:
            print(f"Error updating channel vote button for participant {participant_user_id}: {e}")
    
    async def update_vote_count_button(self, vote_data: dict):
        """Update vote count button after removing participants"""
        try:
            new_count = await self.db.get_vote_count(vote_data["_id"])
            
            # Create updated keyboard
            from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{vote_data['emoji']} ({new_count})", callback_data="vote_count")]
            ])
            
            # Update message
            await self.app.edit_message_reply_markup(
                chat_id=vote_data["creator_id"],
                message_id=vote_data["message_id"],
                reply_markup=keyboard
            )
            
        except Exception as e:
            print(f"Error updating vote count button: {e}")
    
    async def log_participant_removal(self, user_id: int, channel_username: str):
        """Log participant removal to log channel"""
        try:
            log_text = f"""
⚠️ **Participant Removed**

🆔 **User ID:** {user_id}
📢 **Channel:** {channel_username}
❌ **Reason:** Unsubscribed from required channels
⏰ **Time:** {await self.db.get_current_timestamp()}
"""
            
            await self.app.send_message(Config.LOG_CHANNEL_ID, log_text)
            
        except Exception as e:
            print(f"Error logging participant removal: {e}")
    
    async def cleanup_old_data(self):
        """Clean up old data (run daily)"""
        try:
            print("Starting daily cleanup...")
            
            # This can be customized based on requirements
            # For now, we'll just log the cleanup
            stats = await self.db.get_bot_stats()
            
            cleanup_log = f"""
🧹 **Daily Cleanup Report**

📊 **Current Stats:**
• Active Polls: {stats['active_votes']}
• Total Participations: {stats['total_participations']}
• Total Users: {stats['total_users']}

⏰ **Time:** {await self.db.get_current_timestamp()}
"""
            
            if Config.LOG_CHANNEL_ID:
                await self.app.send_message(Config.LOG_CHANNEL_ID, cleanup_log)
            
            print("Daily cleanup completed.")
            
        except Exception as e:
            print(f"Error in daily cleanup: {e}")
    
    async def force_subscription_check(self):
        """Force an immediate subscription check (can be called manually)"""
        await self.check_subscriptions()
    
    async def get_scheduler_status(self):
        """Get current scheduler status"""
        return {
            "is_running": self.is_running,
            "jobs": len(self.scheduler.get_jobs()) if self.is_running else 0,
            "next_subscription_check": self.scheduler.get_job('subscription_check').next_run_time if self.is_running else None,
            "next_cleanup": self.scheduler.get_job('daily_cleanup').next_run_time if self.is_running else None
        }
