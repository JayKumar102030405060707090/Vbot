from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, 
    CallbackQuery, InputMediaPhoto
)
from pyrogram.errors import (
    PeerIdInvalid, UserNotParticipant, ChannelPrivate, 
    ChatAdminRequired, MessageNotModified
)
from config import Config
from utils.check import SubscriptionChecker
from utils.keyboards import Keyboards
import random
import asyncio
from datetime import datetime, timedelta
import re

class AdvancedVoteHandler:
    def __init__(self, app: Client, db):
        self.app = app
        self.db = db
        self.checker = SubscriptionChecker(app, db)
        self.keyboards = Keyboards()
        
        # Session management
        self.vote_sessions = {}  # Interactive vote creation sessions
        self.pending_votes = {}  # Quick vote creation storage
        
        # Vote configuration templates
        self.vote_templates = {
            'giveaway': {
                'title': '🎁 GIVEAWAY ALERT',
                'description': 'Participate in our amazing giveaway!',
                'emoji': '🎁',
                'color': '🟢'
            },
            'poll': {
                'title': '📊 COMMUNITY POLL',
                'description': 'Vote and make your voice heard!',
                'emoji': '📊',
                'color': '🔵'
            },
            'contest': {
                'title': '🏆 CONTEST ENTRY',
                'description': 'Join the contest and win prizes!',
                'emoji': '🏆',
                'color': '🟡'
            },
            'event': {
                'title': '🎪 EVENT PARTICIPATION',
                'description': 'Be part of our special event!',
                'emoji': '🎪',
                'color': '🟣'
            }
        }
        
        # Advanced vote analytics
        self.vote_analytics = {}
    
    def register(self):
        """Register all vote-related handlers"""
        
        # Main vote command with interactive menu
        @self.app.on_message(filters.command("vote") & filters.private)
        async def vote_command(client: Client, message: Message):
            user_id = message.from_user.id
            await self.show_vote_creation_menu(message, user_id)
        
        # Quick vote creation
        @self.app.on_message(filters.command("quickvote") & filters.private)
        async def quick_vote_command(client: Client, message: Message):
            user_id = message.from_user.id
            await self.start_quick_vote_creation(message, user_id)
        
        # Advanced vote with custom options
        @self.app.on_message(filters.command("advancedvote") & filters.private)
        async def advanced_vote_command(client: Client, message: Message):
            user_id = message.from_user.id
            await self.start_advanced_vote_creation(message, user_id)
        
        # Vote template selection
        @self.app.on_callback_query(filters.regex(r"^vote_template_"))
        async def handle_template_selection(client: Client, query: CallbackQuery):
            template_type = query.data.split("_")[2]
            await self.handle_vote_template_selection(query, template_type)
        
        # Vote type selection callbacks
        @self.app.on_callback_query(filters.regex(r"^vote_type_"))
        async def handle_vote_type(client: Client, query: CallbackQuery):
            vote_type = query.data.split("_")[2]
            await self.handle_vote_type_selection(query, vote_type)
        
        # Channel input handler for vote sessions
        @self.app.on_message(filters.text & filters.private & ~filters.command(["start", "help", "vote", "quickvote", "advancedvote"]))
        async def handle_vote_session_input(client: Client, message: Message):
            user_id = message.from_user.id
            if user_id in self.vote_sessions:
                await self.process_vote_session_input(message)
        
        # Vote management callbacks
        @self.app.on_callback_query(filters.regex(r"^vote_manage_"))
        async def handle_vote_management(client: Client, query: CallbackQuery):
            action = query.data.split("_")[2]
            await self.handle_vote_management(query, action)
        
        # Vote analytics callbacks
        @self.app.on_callback_query(filters.regex(r"^vote_analytics_"))
        async def handle_vote_analytics(client: Client, query: CallbackQuery):
            action = query.data.split("_")[2]
            await self.handle_vote_analytics(query, action)
        
        # Back to menu callback
        @self.app.on_callback_query(filters.regex(r"^vote_type_menu$"))
        async def back_to_menu(client: Client, query: CallbackQuery):
            await self.show_vote_creation_menu(query.message, query.from_user.id)
        
        # Help callback
        @self.app.on_callback_query(filters.regex(r"^vote_help$"))
        async def vote_help(client: Client, query: CallbackQuery):
            await self.show_vote_help(query)
    
    async def show_vote_creation_menu(self, message: Message, user_id: int):
        """Show advanced vote creation menu"""
        menu_text = f"""
🎯 **ADVANCED VOTE CREATOR**

**Choose Your Vote Creation Method:**

🚀 **Quick Vote** - Fast & Simple
   └ Create vote poll in 30 seconds

⚡ **Template Vote** - Pre-designed
   └ Use professional templates

🔧 **Advanced Vote** - Full Control
   └ Custom settings & features

📊 **Analytics** - Track Performance
   └ View vote statistics

**Bot Owner:** {Config.OWNER_USERNAME}
**Support:** {Config.SUPPORT_CHANNEL}
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🚀 Quick Vote", callback_data="vote_type_quick"),
                InlineKeyboardButton("⚡ Templates", callback_data="vote_type_template")
            ],
            [
                InlineKeyboardButton("🔧 Advanced", callback_data="vote_type_advanced"),
                InlineKeyboardButton("📊 Analytics", callback_data="vote_type_analytics")
            ],
            [
                InlineKeyboardButton("📋 My Votes", callback_data="vote_manage_list"),
                InlineKeyboardButton("❓ Help", callback_data="vote_help")
            ],
            [
                InlineKeyboardButton("🔙 Back to Main", callback_data="start")
            ]
        ])
        
        await message.reply_text(menu_text, reply_markup=keyboard)
    
    async def handle_vote_type_selection(self, query: CallbackQuery, vote_type: str):
        """Handle vote type selection"""
        user_id = query.from_user.id
        
        if vote_type == "quick":
            await self.start_quick_vote_creation(query.message, user_id, edit=True)
        elif vote_type == "template":
            await self.show_template_selection(query)
        elif vote_type == "advanced":
            await self.start_advanced_vote_creation(query.message, user_id, edit=True)
        elif vote_type == "analytics":
            await self.show_vote_analytics(query)
    
    async def start_quick_vote_creation(self, message: Message, user_id: int, edit: bool = False):
        """Start quick vote creation process"""
        self.vote_sessions[user_id] = {
            'type': 'quick',
            'step': 'channel',
            'data': {},
            'created_at': datetime.now()
        }
        
        text = f"""
🚀 **QUICK VOTE CREATOR**

**Step 1/2:** Enter Channel Username

📝 **Instructions:**
• Send your channel username with @
• Example: @KomalMusicUpdate
• Make sure I'm admin in your channel

⚠️ **Requirements:**
• Bot must be admin in channel
• Channel must be accessible
• Valid channel username format

Type your channel username below:
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="vote_type_menu")]
        ])
        
        if edit:
            await message.edit_text(text, reply_markup=keyboard)
        else:
            await message.reply_text(text, reply_markup=keyboard)
    
    async def show_template_selection(self, query: CallbackQuery):
        """Show vote template selection"""
        text = f"""
⚡ **VOTE TEMPLATES**

Choose from professional templates:

🎁 **Giveaway** - For prizes & rewards
📊 **Poll** - For community voting  
🏆 **Contest** - For competitions
🎪 **Event** - For special events

Each template includes:
• Professional design
• Optimized text
• Attractive emoji
• Engagement features
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎁 Giveaway", callback_data="vote_template_giveaway"),
                InlineKeyboardButton("📊 Poll", callback_data="vote_template_poll")
            ],
            [
                InlineKeyboardButton("🏆 Contest", callback_data="vote_template_contest"),
                InlineKeyboardButton("🎪 Event", callback_data="vote_template_event")
            ],
            [
                InlineKeyboardButton("🔙 Back to Menu", callback_data="vote_type_menu")
            ]
        ])
        
        await query.edit_message_text(text, reply_markup=keyboard)
    
    async def handle_vote_template_selection(self, query: CallbackQuery, template_type: str):
        """Handle template selection and start creation"""
        user_id = query.from_user.id
        template = self.vote_templates.get(template_type, self.vote_templates['poll'])
        
        self.vote_sessions[user_id] = {
            'type': 'template',
            'template': template_type,
            'step': 'channel',
            'data': template.copy(),
            'created_at': datetime.now()
        }
        
        text = f"""
{template['emoji']} **{template['title']} CREATOR**

**Template:** {template_type.title()}
**Description:** {template['description']}

**Step 1/3:** Enter Channel Username

📝 Send your channel username with @
Example: @KomalMusicUpdate

Make sure I'm admin in your channel!
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Templates", callback_data="vote_type_template")]
        ])
        
        await query.edit_message_text(text, reply_markup=keyboard)
    
    async def start_advanced_vote_creation(self, message: Message, user_id: int, edit: bool = False):
        """Start advanced vote creation with full customization"""
        self.vote_sessions[user_id] = {
            'type': 'advanced',
            'step': 'channel',
            'data': {
                'custom_title': None,
                'custom_description': None,
                'custom_emoji': None,
                'expiry_time': None,
                'max_participants': None,
                'require_screenshot': False,
                'auto_winner_selection': False
            },
            'created_at': datetime.now()
        }
        
        text = f"""
🔧 **ADVANCED VOTE CREATOR**

**Full Customization Available:**
• Custom title & description
• Custom emoji & colors
• Participant limits
• Auto-expiry settings
• Winner selection features
• Screenshot requirements

**Step 1/6:** Enter Channel Username

📝 Send your channel username with @
Example: @KomalMusicUpdate
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="vote_type_menu")]
        ])
        
        if edit:
            await message.edit_text(text, reply_markup=keyboard)
        else:
            await message.reply_text(text, reply_markup=keyboard)
    
    async def process_vote_session_input(self, message: Message):
        """Process input during vote creation session"""
        user_id = message.from_user.id
        session = self.vote_sessions[user_id]
        text = message.text.strip()
        
        if session['step'] == 'channel':
            await self.process_channel_input(message, session, text)
        elif session['step'] == 'custom_title':
            await self.process_custom_title(message, session, text)
        elif session['step'] == 'custom_description':
            await self.process_custom_description(message, session, text)
        # Add more steps as needed
    
    async def process_channel_input(self, message: Message, session: dict, channel_username: str):
        """Process channel username input"""
        user_id = message.from_user.id
        
        # Validate channel format
        if not channel_username.startswith('@'):
            await message.reply_text(
                "❌ **Invalid Format**\n\n"
                "Please send channel username with @ symbol\n"
                "Example: @KomalMusicUpdate"
            )
            return
        
        # Validate channel access and bot permissions
        validation_result = await self.validate_channel_access(channel_username, user_id)
        
        if not validation_result['success']:
            await message.reply_text(validation_result['message'])
            return
        
        # Store channel and proceed to next step
        session['data']['channel'] = channel_username
        session['data']['chat_id'] = validation_result['chat_id']
        
        if session['type'] == 'quick':
            await self.finalize_quick_vote(message, session)
        elif session['type'] == 'template':
            await self.finalize_template_vote(message, session)
        elif session['type'] == 'advanced':
            await self.proceed_to_advanced_customization(message, session)
    
    async def validate_channel_access(self, channel_username: str, user_id: int) -> dict:
        """Comprehensive channel validation"""
        try:
            # Get channel info
            chat = await self.app.get_chat(channel_username)
            chat_id = chat.id
            
            # Check if bot is member and has admin rights
            try:
                bot_member = await self.app.get_chat_member(chat_id, "me")
                # Convert enum to string for comparison
                bot_status_str = str(bot_member.status).split('.')[-1].lower()
                if bot_status_str not in ["administrator", "creator"]:
                    return {
                        'success': False,
                        'message': f"❌ **Not Admin in Channel**\n\n"
                                 f"I need admin permissions in `{channel_username}`\n\n"
                                 f"**Required Permissions:**\n"
                                 f"• Post messages\n"
                                 f"• Edit messages\n"
                                 f"• Delete messages\n\n"
                                 f"Please make me admin and try again."
                    }
            except UserNotParticipant:
                return {
                    'success': False,
                    'message': f"❌ **Not Added to Channel**\n\n"
                             f"Please add me to `{channel_username}` as admin first.\n\n"
                             f"**Steps:**\n"
                             f"1. Go to {channel_username}\n"
                             f"2. Add me as admin\n"
                             f"3. Give required permissions\n"
                             f"4. Try again"
                }
            except ChatAdminRequired:
                # If we can't check membership, assume it's fine but warn
                pass
            
            # Check if vote already exists
            existing_vote = await self.db.get_vote_by_channel(channel_username)
            if existing_vote:
                return {
                    'success': False,
                    'message': f"⚠️ **Vote Already Exists**\n\n"
                             f"Channel `{channel_username}` already has an active vote poll.\n\n"
                             f"**Options:**\n"
                             f"• Delete existing vote first\n"
                             f"• Use different channel\n"
                             f"• Contact admin for help"
                }
            
            return {
                'success': True,
                'chat_id': chat_id,
                'message': '✅ Channel validation successful'
            }
            
        except PeerIdInvalid:
            return {
                'success': False,
                'message': f"❌ **Channel Not Found**\n\n"
                         f"Channel `{channel_username}` doesn't exist or is private.\n\n"
                         f"**Check:**\n"
                         f"• Username spelling\n"
                         f"• Channel is public\n"
                         f"• I have access to it"
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"❌ **Error Accessing Channel**\n\n"
                         f"Could not access `{channel_username}`\n"
                         f"Error: {str(e)}\n\n"
                         f"Please check channel settings and try again."
            }
    
    async def finalize_quick_vote(self, message: Message, session: dict):
        """Finalize quick vote creation"""
        user_id = message.from_user.id
        channel_username = session['data']['channel']
        chat_id = session['data']['chat_id']
        
        # Create vote with default quick settings
        vote_data = await self.create_advanced_vote_poll(
            channel_username=channel_username,
            chat_id=chat_id,
            creator_id=user_id,
            vote_type='quick',
            custom_data=session['data']
        )
        
        if vote_data['success']:
            await message.reply_text(
                f"✅ **Quick Vote Created Successfully!**\n\n"
                f"**Channel:** {channel_username}\n"
                f"**Vote ID:** `{vote_data['vote_id']}`\n"
                f"**Participation Link:** {vote_data['participation_link']}\n\n"
                f"🎯 **Share this link with your audience:**\n"
                f"`{vote_data['participation_link']}`"
            )
        else:
            await message.reply_text(vote_data['message'])
        
        # Clean up session
        del self.vote_sessions[user_id]
    
    async def finalize_template_vote(self, message: Message, session: dict):
        """Finalize template-based vote creation"""
        user_id = message.from_user.id
        channel_username = session['data']['channel']
        chat_id = session['data']['chat_id']
        template_type = session['template']
        
        # Create vote with template settings
        vote_data = await self.create_advanced_vote_poll(
            channel_username=channel_username,
            chat_id=chat_id,
            creator_id=user_id,
            vote_type='template',
            template_type=template_type,
            custom_data=session['data']
        )
        
        if vote_data['success']:
            template = self.vote_templates[template_type]
            await message.reply_text(
                f"{template['emoji']} **{template['title']} Created Successfully!**\n\n"
                f"**Channel:** {channel_username}\n"
                f"**Template:** {template_type.title()}\n"
                f"**Vote ID:** `{vote_data['vote_id']}`\n\n"
                f"🎯 **Participation Link:**\n"
                f"`{vote_data['participation_link']}`\n\n"
                f"💡 **Pro Tip:** Share this link across social media for maximum engagement!"
            )
        else:
            await message.reply_text(vote_data['message'])
        
        # Clean up session
        del self.vote_sessions[user_id]
    
    async def create_advanced_vote_poll(self, channel_username: str, chat_id: int, creator_id: int, 
                                      vote_type: str, template_type: str = None, custom_data: dict = None) -> dict:
        """Create advanced vote poll with comprehensive features"""
        try:
            # Generate unique vote ID
            vote_id = f"vote_{creator_id}_{int(datetime.now().timestamp())}"
            
            # Determine vote configuration based on type
            if vote_type == 'template' and template_type:
                template = self.vote_templates[template_type]
                vote_title = template['title']
                vote_emoji = template['emoji']
                vote_description = template['description']
            else:
                vote_title = "🎯 VOTE POLL"
                vote_emoji = random.choice(Config.VOTE_EMOJIS)
                vote_description = "Participate and win amazing prizes!"
            
            # Create comprehensive vote message
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            vote_message = f"""
{vote_emoji} **{vote_title}**

{vote_description}

🎁 **How to Participate:**
1️⃣ Join our channels (required)
2️⃣ Click the vote button below
3️⃣ Get counted automatically
4️⃣ Winners announced soon!

📊 **Current Participants:** 0
🕒 **Created:** {current_time}
👑 **By:** {Config.OWNER_USERNAME}

**Required Channels:**
• {Config.UPDATE_CHANNEL}
• {Config.SUPPORT_CHANNEL}
"""
            
            # Create advanced keyboard with vote button
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    f"{vote_emoji} Participate (0)", 
                    url=f"https://t.me/{Config.BOT_USERNAME}?start=vote_{channel_username[1:]}"
                )]
            ])
            
            # Send vote message to channel
            sent_message = await self.app.send_message(
                chat_id=chat_id,
                text=vote_message,
                reply_markup=keyboard
            )
            
            # Store comprehensive vote data
            vote_data = {
                'vote_id': vote_id,
                'channel_username': channel_username,
                'chat_id': chat_id,
                'message_id': sent_message.message_id,
                'creator_id': creator_id,
                'vote_type': vote_type,
                'template_type': template_type,
                'title': vote_title,
                'description': vote_description,
                'emoji': vote_emoji,
                'created_at': current_time,
                'participant_count': 0,
                'is_active': True,
                'custom_settings': custom_data or {},
                'analytics': {
                    'total_clicks': 0,
                    'unique_participants': 0,
                    'conversion_rate': 0.0,
                    'engagement_score': 0.0
                }
            }
            
            # Save to database
            await self.db.create_vote(vote_data)
            
            # Generate participation link
            participation_link = f"https://t.me/{Config.BOT_USERNAME}?start=vote_{channel_username[1:]}"
            
            return {
                'success': True,
                'vote_id': vote_id,
                'participation_link': participation_link,
                'message': 'Vote created successfully!'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"❌ **Error Creating Vote**\n\n{str(e)}"
            }
    
    async def show_vote_analytics(self, query: CallbackQuery):
        """Show comprehensive vote analytics"""
        user_id = query.from_user.id
        
        # Get user's votes
        user_votes = await self.get_user_votes(user_id)
        
        if not user_votes:
            await query.edit_message_text(
                "📊 **Vote Analytics**\n\n"
                "No votes found. Create your first vote to see analytics!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 Create Vote", callback_data="vote_type_quick")],
                    [InlineKeyboardButton("🔙 Back", callback_data="vote_type_menu")]
                ])
            )
            return
        
        # Generate analytics summary
        total_votes = len(user_votes)
        total_participants = sum(vote.get('participant_count', 0) for vote in user_votes)
        active_votes = len([v for v in user_votes if v.get('is_active', True)])
        
        analytics_text = f"""
📊 **YOUR VOTE ANALYTICS**

📈 **Overview:**
• Total Votes Created: {total_votes}
• Active Votes: {active_votes}
• Total Participants: {total_participants}
• Average per Vote: {total_participants/total_votes if total_votes > 0 else 0:.1f}

🎯 **Top Performing Votes:**
"""
        
        # Show top 3 votes by participant count
        sorted_votes = sorted(user_votes, key=lambda x: x.get('participant_count', 0), reverse=True)[:3]
        for i, vote in enumerate(sorted_votes, 1):
            analytics_text += f"\n{i}. {vote.get('channel_username', 'Unknown')} - {vote.get('participant_count', 0)} participants"
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📋 Detailed Stats", callback_data="vote_analytics_detailed"),
                InlineKeyboardButton("📊 Export Data", callback_data="vote_analytics_export")
            ],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="vote_type_menu")]
        ])
        
        await query.edit_message_text(analytics_text, reply_markup=keyboard)
    
    async def get_user_votes(self, user_id: int) -> list:
        """Get all votes created by a user"""
        try:
            # Get user's vote statistics from database
            stats = await self.db.get_bot_stats()
            # Return empty for now - would implement proper user vote filtering
            return []
        except:
            return []
    
    async def handle_vote_management(self, query: CallbackQuery, action: str):
        """Handle vote management actions"""
        if action == "list":
            await self.show_user_votes_list(query)
        elif action == "delete":
            await self.show_vote_deletion_menu(query)
        elif action == "stats":
            await self.show_detailed_vote_stats(query)
    
    async def handle_vote_analytics(self, query: CallbackQuery, action: str):
        """Handle vote analytics actions"""
        if action == "detailed":
            await self.show_detailed_analytics(query)
        elif action == "export":
            await self.export_vote_data(query)
    
    async def show_user_votes_list(self, query: CallbackQuery):
        """Show list of user's votes"""
        await query.edit_message_text(
            "📋 **Your Vote Polls**\n\n"
            "No active votes found.\n"
            "Create your first vote to see it here!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Create Vote", callback_data="vote_type_quick")],
                [InlineKeyboardButton("🔙 Back", callback_data="vote_type_menu")]
            ])
        )
    
    async def show_vote_deletion_menu(self, query: CallbackQuery):
        """Show vote deletion options"""
        await query.edit_message_text(
            "🗑️ **Delete Vote Polls**\n\n"
            "Select a vote to delete:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="vote_type_menu")]
            ])
        )
    
    async def show_detailed_vote_stats(self, query: CallbackQuery):
        """Show detailed vote statistics"""
        await query.edit_message_text(
            "📊 **Detailed Vote Statistics**\n\n"
            "Coming soon - comprehensive analytics dashboard!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="vote_type_menu")]
            ])
        )
    
    async def show_detailed_analytics(self, query: CallbackQuery):
        """Show detailed analytics dashboard"""
        await query.edit_message_text(
            "📈 **Advanced Analytics**\n\n"
            "Detailed analytics features coming soon!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="vote_analytics")]
            ])
        )
    
    async def export_vote_data(self, query: CallbackQuery):
        """Export vote data for user"""
        await query.answer("📊 Export feature coming soon!", show_alert=True)
    
    async def show_vote_help(self, query: CallbackQuery):
        """Show comprehensive vote help"""
        help_text = f"""
❓ **Vote Bot Help**

**Available Commands:**
• `/vote` - Main vote creation menu
• `/quickvote` - Fast vote creation
• `/advancedvote` - Full customization

**Vote Types:**
🚀 **Quick Vote** - Simple, fast creation
⚡ **Template Vote** - Pre-designed formats
🔧 **Advanced Vote** - Full customization

**Features:**
• Professional templates
• Real-time analytics
• Participant tracking
• Auto-verification
• Multi-channel support

**Requirements:**
• Bot must be admin in your channel
• Users must join required channels
• Valid channel username format

**Support:** {Config.SUPPORT_CHANNEL}
**Updates:** {Config.UPDATE_CHANNEL}
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Create Vote", callback_data="vote_type_quick")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="vote_type_menu")]
        ])
        
        await query.edit_message_text(help_text, reply_markup=keyboard)
    
    async def process_custom_title(self, message: Message, session: dict, title: str):
        """Process custom title input for advanced votes"""
        session['data']['custom_title'] = title
        session['step'] = 'custom_description'
        
        await message.reply_text(
            f"✅ **Title Set:** {title}\n\n"
            "🔧 **Step 2/6:** Enter Custom Description\n\n"
            "Send a description for your vote poll:"
        )
    
    async def process_custom_description(self, message: Message, session: dict, description: str):
        """Process custom description input for advanced votes"""
        session['data']['custom_description'] = description
        session['step'] = 'finalize'
        
        await message.reply_text(
            f"✅ **Description Set:** {description}\n\n"
            "🎯 **Creating Advanced Vote...**"
        )
        
        # Finalize advanced vote creation
        await self.finalize_advanced_vote(message, session)
    
    async def proceed_to_advanced_customization(self, message: Message, session: dict):
        """Continue with advanced vote customization"""
        session['step'] = 'custom_title'
        
        await message.reply_text(
            "🔧 **Advanced Customization**\n\n"
            "**Step 2/6:** Enter Custom Title\n\n"
            "Send a custom title for your vote poll:"
        )
    
    async def finalize_advanced_vote(self, message: Message, session: dict):
        """Finalize advanced vote creation"""
        user_id = message.from_user.id
        channel_username = session['data']['channel']
        chat_id = session['data']['chat_id']
        
        # Create vote with advanced settings
        vote_data = await self.create_advanced_vote_poll(
            channel_username=channel_username,
            chat_id=chat_id,
            creator_id=user_id,
            vote_type='advanced',
            custom_data=session['data']
        )
        
        if vote_data['success']:
            await message.reply_text(
                f"🔧 **Advanced Vote Created Successfully!**\n\n"
                f"**Channel:** {channel_username}\n"
                f"**Vote ID:** `{vote_data['vote_id']}`\n"
                f"**Features:** Custom title, description & settings\n\n"
                f"🎯 **Participation Link:**\n"
                f"`{vote_data['participation_link']}`"
            )
        else:
            await message.reply_text(vote_data['message'])
        
        # Clean up session
        del self.vote_sessions[user_id]