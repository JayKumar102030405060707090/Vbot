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
            # Get votes with either active field structure
            cursor = self.db.db[Config.VOTES_COLLECTION].find({
                "$or": [
                    {"active": True},
                    {"status": "active"}
                ]
            })
            votes = await cursor.to_list(length=None)
            
            # Filter out votes with invalid channel usernames
            valid_votes = []
            for vote in votes:
                channel_username = vote.get("channel_username") or vote.get("channel", "")
                if channel_username and len(channel_username) >= 2:
                    valid_votes.append(vote)
                else:
                    print(f"Filtering out vote with invalid channel: '{channel_username}'")
                    
            return valid_votes
        except Exception as e:
            print(f"Error getting active votes: {e}")
            return []
    
    async def check_vote_subscriptions(self, vote_data: dict):
        """Check subscriptions for a specific vote and remove invalid participants"""
        removed_count = 0
        
        try:
            # Get channel username from either field (backward compatibility)
            channel_username = vote_data.get("channel_username") or vote_data.get("channel", "")
            
            # Skip if channel username is empty or invalid
            if not channel_username or len(channel_username) < 2:
                print(f"Skipping vote with invalid channel username: '{channel_username}'")
                return 0
                
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
                                # Remove the vote from user_votes collection
                                await self.db.remove_user_vote(user_id, unique_post_id)
                                
                                # Get live count and update participant record
                                live_count = await self.db.get_post_vote_count(unique_post_id)
                                await self.db.update_post_vote_count(unique_post_id, live_count)
                                
                                print(f"Removed vote for user {user_id} from post {unique_post_id}, new count: {live_count}")
                                
                                # Update channel button
                                try:
                                    await self.update_channel_vote_button_by_post_id(channel_username, unique_post_id)
                                except Exception as button_error:
                                    print(f"Error updating channel button: {button_error}")
                        
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
        """Remove all votes cast by an unsubscribed user and update participant vote counts"""
        try:
            # Find all votes cast by this user in this channel
            user_votes = await self.db.db["user_votes"].find({
                "voter_id": unsubscribed_user_id,
                "channel_username": channel_username
            }).to_list(length=None)
            
            votes_removed = 0
            
            for vote in user_votes:
                unique_post_id = vote.get("unique_post_id")
                
                if unique_post_id:
                    # Remove the vote using database function
                    if await self.db.remove_user_vote(unsubscribed_user_id, unique_post_id):
                        votes_removed += 1
                        
                        # Get live count and update participant record
                        live_count = await self.db.get_post_vote_count(unique_post_id)
                        await self.db.update_post_vote_count(unique_post_id, live_count)
                        
                        print(f"Removed vote from user {unsubscribed_user_id} for post {unique_post_id}, new count: {live_count}")
                        
                        # Update the channel message button with live count
                        await self.update_channel_vote_button_by_post_id(channel_username, unique_post_id)
                else:
                    # Fallback for old votes without unique_post_id
                    participant_user_id = vote.get("participant_user_id")
                    if participant_user_id:
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
            
            print(f"Removed {votes_removed} votes from unsubscribed user {unsubscribed_user_id} in {channel_username}")
            
        except Exception as e:
            print(f"Error removing votes for unsubscribed user {unsubscribed_user_id}: {e}")
    
    async def update_channel_vote_button_by_post_id(self, channel_username: str, unique_post_id: str):
        """Update the vote button in channel message with live count using unique post ID"""
        try:
            # Get participant data using database function
            participant_data = await self.db.get_participant_by_post_id(unique_post_id)
            
            if participant_data and participant_data.get("channel_message_id"):
                # Get live count from user_votes collection
                live_count = await self.db.get_post_vote_count(unique_post_id)
                emoji = "⚡"
                
                # Create updated button
                from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                channel_name = channel_username[1:]  # Remove @ prefix
                updated_button = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"{emoji} Vote for this participant ({live_count})", callback_data=f"channel_vote_{channel_name}_{unique_post_id}")]
                ])
                
                # Update the message
                await self.app.edit_message_reply_markup(
                    chat_id=channel_username,
                    message_id=participant_data["channel_message_id"],
                    reply_markup=updated_button
                )
                
                print(f"Updated channel vote button for post {unique_post_id} with live count {live_count}")
                
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
