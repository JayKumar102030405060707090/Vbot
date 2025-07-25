import re
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from utils.db import Database
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TrackHandler:
    def __init__(self, app: Client, db: Database):
        self.app = app
        self.db = db
        self.pending_tracks = {}  # Store pending track requests
        
    def register(self):
        """Register track command handlers"""
        
        # Register callbacks first
        self.register_callbacks()
        
        @self.app.on_message(filters.command("track") & filters.private)
        async def track_command(client: Client, message: Message):
            user_id = message.from_user.id
            command_text = message.text.strip()
            
            # Check if user provided a post link or user ID
            if len(command_text.split()) > 1:
                post_identifier = command_text.split(maxsplit=1)[1]
                await self.process_track_by_identifier(message, post_identifier)
            # Check if user replied to a participation post
            elif message.reply_to_message:
                await self.process_track_request(message)
            else:
                await message.reply_text(
                    "📊 **Track Vote Details**\n\n"
                    "**Usage Options:**\n"
                    "**1. `/track user_id`** - Track using participant user ID\n"
                    "**2. `/track post_link`** - Track using post link\n"
                    "**3. Reply to forwarded post with `/track`**\n\n"
                    "**Examples:**\n"
                    "• `/track 7840521426` - Track votes for user ID\n"
                    "• `/track https://t.me/channel/123` - Track using post link\n"
                    "• Forward post → Reply with `/track`"
                )
                return
        
        @self.app.on_message(filters.forwarded & filters.private)
        async def handle_forwarded_post(client: Client, message: Message):
            """Handle forwarded participation posts"""
            try:
                # Check if this looks like a participation post
                if message.text and self.is_participation_post(message.text):
                    # Store this message for potential tracking
                    user_id = message.from_user.id
                    
                    # Send tracking instruction
                    await message.reply_text(
                        "📊 **Participation Post Detected!**\n\n"
                        "**To see vote details, reply to this message with /track**\n\n"
                        "**Example:** Reply `/track` to this forwarded post"
                    )
                    
            except Exception as e:
                logger.error(f"Error handling forwarded post: {e}")
    
    def is_participation_post(self, text: str) -> bool:
        """Check if the text looks like a participation post"""
        keywords = [
            "PARTICIPANT DETAILS",
            "participant details", 
            "USER-ID:",
            "user-id:",
            "USERNAME:",
            "username:",
            "CREATED BY",
            "created by",
            "VOTE BOT",
            "vote bot",
            "ONLY CHANNEL SUBSCRIBERS CAN VOTE",
            "channel subscribers can vote",
            "🎯",
            "◈",
            "▶️"
        ]
        
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)
    
    async def process_track_by_identifier(self, message: Message, identifier: str):
        """Process track request using post link or user ID"""
        try:
            # Check if identifier is a user ID (numeric)
            if identifier.isdigit():
                user_id = int(identifier)
                participant_info = {
                    'user_id': user_id,
                    'username': 'unknown',
                    'first_name': 'Unknown User',
                    'channel_username': '@unknown'
                }
            else:
                # Try to extract user ID from post link or other identifier
                user_id_match = re.search(r'(\d{9,12})', identifier)
                if user_id_match:
                    user_id = int(user_id_match.group(1))
                    participant_info = {
                        'user_id': user_id,
                        'username': 'unknown',
                        'first_name': 'Unknown User',
                        'channel_username': '@unknown'
                    }
                else:
                    await message.reply_text("❌ **Invalid identifier. Please provide a valid user ID or post link.**")
                    return
            
            # Get vote details from database
            vote_details = await self.get_vote_details(participant_info)
            
            if not vote_details or vote_details['total_votes'] == 0:
                await message.reply_text(f"❌ **No votes found for user ID: {participant_info['user_id']}**")
                return
            
            # Send detailed vote information
            await self.send_vote_details(message, participant_info, vote_details)
            
        except Exception as e:
            logger.error(f"Error processing track by identifier: {e}")
            await message.reply_text("❌ **Error processing track request. Please try again.**")
    
    async def process_track_request(self, message: Message):
        """Process track request for participation post"""
        try:
            replied_message = message.reply_to_message
            
            if not replied_message or not replied_message.text:
                await message.reply_text("❌ **Invalid participation post. Please reply to a valid participation message.**")
                return
            
            # Extract participant details from the post
            participant_info = await self.extract_participant_info(replied_message.text)
            
            if not participant_info:
                await message.reply_text("❌ **Could not extract participant information from this post.**")
                return
            
            # Get vote details for this participant
            vote_details = await self.get_vote_details(participant_info)
            
            if not vote_details:
                await message.reply_text("❌ **No vote data found for this participant.**")
                return
            
            # Send detailed vote information
            await self.send_vote_details(message, participant_info, vote_details)
            
        except Exception as e:
            logger.error(f"Error processing track request: {e}")
            await message.reply_text("❌ **Error processing track request. Please try again.**")
    
    async def extract_participant_info(self, post_text: str):
        """Extract participant information from post text"""
        try:
            participant_info = {}
            
            # Extract user ID - looking for USER-ID: pattern
            user_id_patterns = [
                r'USER-ID:\s*(\d+)',
                r'user-id:\s*(\d+)',
                r'USER_ID:\s*(\d+)',
                r'ID:\s*(\d+)',
                r'(\d{9,12})'
            ]
            
            for pattern in user_id_patterns:
                user_id_match = re.search(pattern, post_text, re.IGNORECASE)
                if user_id_match:
                    participant_info['user_id'] = int(user_id_match.group(1))
                    break
            
            # Extract username - looking for USERNAME: pattern and @mentions
            username_patterns = [
                r'USERNAME:\s*#(\w+)',
                r'username:\s*#(\w+)',
                r'USERNAME:\s*@(\w+)',
                r'username:\s*@(\w+)',
                r'@(\w+)',
                r'#(\w+)'
            ]
            
            for pattern in username_patterns:
                username_match = re.search(pattern, post_text, re.IGNORECASE)
                if username_match:
                    participant_info['username'] = username_match.group(1)
                    break
            
            # Extract user display name - looking for USER: pattern
            name_patterns = [
                r'USER:\s*([^◈\n]+)',
                r'user:\s*([^◈\n]+)',
                r'NAME:\s*([^◈\n]+)',
                r'name:\s*([^◈\n]+)'
            ]
            
            for pattern in name_patterns:
                name_match = re.search(pattern, post_text, re.IGNORECASE)
                if name_match:
                    name = name_match.group(1).strip()
                    # Clean special characters
                    name = re.sub(r'[^\w\s]', '', name).strip()
                    if name:
                        participant_info['first_name'] = name
                        break
            
            # Extract timestamp from user ID (assuming format: userid_timestamp)
            if 'user_id' in participant_info:
                # Generate timestamp based on current participation
                import time
                participant_info['timestamp'] = str(int(time.time() * 1000000))
            
            # Set a default channel if not found
            participant_info['channel_username'] = '@vote_taste'  # Default from screenshot
            
            return participant_info if participant_info else None
            
        except Exception as e:
            logger.error(f"Error extracting participant info: {e}")
            return None
    
    async def get_vote_details(self, participant_info):
        """Get detailed vote information for participant"""
        try:
            # Build query based on available information
            query = {}
            
            if 'user_id' in participant_info:
                query['participant_user_id'] = participant_info['user_id']
                
            # Also try searching by user ID in user_votes collection
            votes_collection = self.db.get_collection("user_votes")
            votes = await votes_collection.find(query).to_list(length=None)
            
            # If no votes in user_votes, try the votes collection
            if not votes and 'user_id' in participant_info:
                votes_collection = self.db.get_collection("votes")
                votes = await votes_collection.find(query).to_list(length=None)
            
            # If still no votes, try participants collection to get post info
            if not votes:
                participants_collection = self.db.get_collection("participants")
                participant_data = await participants_collection.find_one(query)
                
                if participant_data and 'unique_post_id' in participant_data:
                    # Search votes by unique_post_id
                    post_query = {'unique_post_id': participant_data['unique_post_id']}
                    votes = await self.db.get_collection("user_votes").find(post_query).to_list(length=None)
                    
                    if not votes:
                        votes = await self.db.get_collection("votes").find(post_query).to_list(length=None)
            
            # Get participant data
            participants_collection = self.db.get_collection("participants")
            participant_data = await participants_collection.find_one(query)
            
            return {
                'votes': votes,
                'participant_data': participant_data,
                'total_votes': len(votes) if votes else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting vote details: {e}")
            return None
    
    async def send_vote_details(self, message: Message, participant_info, vote_details):
        """Send detailed vote information"""
        try:
            votes = vote_details['votes']
            participant_data = vote_details['participant_data']
            total_votes = vote_details['total_votes']
            
            # Build voter details
            voter_details = []
            for i, vote in enumerate(votes, 1):
                voter_id = vote.get('voter_id')
                vote_time = vote.get('vote_timestamp', 'Unknown time')
                
                # Try to get voter info
                try:
                    voter_info = await self.app.get_users(voter_id)
                    voter_name = voter_info.first_name or "Unknown"
                    voter_username = f"@{voter_info.username}" if voter_info.username else "No username"
                except:
                    voter_name = "Unknown User"
                    voter_username = "No username"
                
                voter_details.append(
                    f"**{i}.** {voter_name} ({voter_username})\n"
                    f"   **ID:** `{voter_id}`\n"
                    f"   **Time:** {vote_time}\n"
                )
            
            # Build participant info section
            participant_name = participant_info.get('first_name', 'Unknown')
            participant_username = participant_info.get('username', 'No username')
            participant_id = participant_info.get('user_id', 'Unknown')
            channel_name = participant_info.get('channel_username', 'Unknown channel')
            
            # Create detailed response
            response_text = f"""
📊 **VOTE TRACKING DETAILS** 📊

**👤 Participant Information:**
**Name:** {participant_name}
**Username:** @{participant_username}
**User ID:** `{participant_id}`
**Channel:** {channel_name}

**🗳️ Vote Summary:**
**Total Votes:** {total_votes}
**Vote Status:** {'Active' if total_votes > 0 else 'No votes yet'}

**👥 Detailed Voter List:**
{chr(10).join(voter_details) if voter_details else "No votes found"}

**📊 Statistics:**
**Most Recent Vote:** {votes[-1].get('vote_timestamp', 'N/A') if votes else 'N/A'}
**First Vote:** {votes[0].get('vote_timestamp', 'N/A') if votes else 'N/A'}

**🔍 Track ID:** `{participant_info.get('timestamp', 'Unknown')}`
"""
            
            # Send response with keyboard
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh Data", callback_data=f"refresh_track_{participant_id}")],
                [InlineKeyboardButton("📈 Vote Analytics", callback_data=f"analytics_{participant_id}")],
                [InlineKeyboardButton("❌ Close", callback_data="close_track")]
            ])
            
            await message.reply_text(response_text, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error sending vote details: {e}")
            await message.reply_text("❌ **Error generating vote details. Please try again.**")
    
    def register_callbacks(self):
        """Register callback handlers for track buttons"""
        
        @self.app.on_callback_query(filters.regex(r"^refresh_track_(\d+)"))
        async def refresh_track_data(client: Client, query):
            try:
                user_id = int(query.matches[0].group(1))
                await query.answer("🔄 Refreshing vote data...")
                
                # Get updated vote details
                participant_info = {'user_id': user_id}
                vote_details = await self.get_vote_details(participant_info)
                
                if vote_details:
                    await self.send_vote_details(query.message, participant_info, vote_details)
                else:
                    await query.message.edit_text("❌ **No updated vote data found.**")
                    
            except Exception as e:
                logger.error(f"Error refreshing track data: {e}")
                await query.answer("❌ Error refreshing data", show_alert=True)
        
        @self.app.on_callback_query(filters.regex(r"^analytics_(\d+)"))
        async def show_analytics(client: Client, query):
            try:
                user_id = int(query.matches[0].group(1))
                await query.answer("📈 Loading analytics...")
                
                # Get vote analytics
                analytics_text = await self.generate_vote_analytics(user_id)
                await query.message.edit_text(analytics_text)
                
            except Exception as e:
                logger.error(f"Error showing analytics: {e}")
                await query.answer("❌ Error loading analytics", show_alert=True)
        
        @self.app.on_callback_query(filters.regex("^close_track"))
        async def close_track(client: Client, query):
            try:
                await query.message.delete()
                await query.answer("✅ Tracking closed")
            except Exception as e:
                logger.error(f"Error closing track: {e}")
    
    async def generate_vote_analytics(self, participant_id):
        """Generate vote analytics for participant"""
        try:
            # Get all votes for this participant
            votes_collection = self.db.get_collection("votes")
            votes = await votes_collection.find({"participant_user_id": participant_id}).to_list(length=None)
            
            if not votes:
                return "❌ **No vote data found for analytics.**"
            
            # Analyze vote patterns
            total_votes = len(votes)
            unique_voters = len(set(vote['voter_id'] for vote in votes))
            
            # Time analysis
            vote_times = [vote.get('vote_timestamp') for vote in votes if vote.get('vote_timestamp')]
            
            analytics_text = f"""
📈 **VOTE ANALYTICS**

**📊 Overview:**
**Total Votes:** {total_votes}
**Unique Voters:** {unique_voters}
**Average Votes per Voter:** {total_votes / unique_voters if unique_voters > 0 else 0:.1f}

**⏰ Time Analysis:**
**First Vote:** {min(vote_times) if vote_times else 'N/A'}
**Latest Vote:** {max(vote_times) if vote_times else 'N/A'}

**🔥 Vote Distribution:**
**Peak Activity:** Based on timestamp analysis
**Vote Frequency:** {total_votes / max(1, len(set(str(vt)[:10] for vt in vote_times))) if vote_times else 0:.1f} votes/day

**🎯 Engagement Rate:**
**Vote Momentum:** {'High' if total_votes > 10 else 'Medium' if total_votes > 5 else 'Low'}
"""
            
            return analytics_text
            
        except Exception as e:
            logger.error(f"Error generating analytics: {e}")
            return "❌ **Error generating analytics.**"