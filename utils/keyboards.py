from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config

class Keyboards:
    def __init__(self):
        pass
    
    def get_start_keyboard(self) -> InlineKeyboardMarkup:
        """Get start command keyboard"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")],
            [
                InlineKeyboardButton("📢 Support", url=f"https://t.me/{Config.SUPPORT_CHANNEL[1:]}"),
                InlineKeyboardButton("📢 Updates", url=f"https://t.me/{Config.UPDATE_CHANNEL[1:]}")
            ],
            [InlineKeyboardButton("👨‍💻 Owner", url=f"https://t.me/{Config.OWNER_USERNAME[1:]}")]
        ])
    
    def get_help_keyboard(self) -> InlineKeyboardMarkup:
        """Get help command keyboard"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📢 Support", url=f"https://t.me/{Config.SUPPORT_CHANNEL[1:]}"),
                InlineKeyboardButton("📢 Updates", url=f"https://t.me/{Config.UPDATE_CHANNEL[1:]}")
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="start")]
        ])
    
    def get_subscription_keyboard(self, missing_channels: list, callback_data: str = "verify_channels") -> InlineKeyboardMarkup:
        """Get subscription verification keyboard"""
        buttons = []
        
        for channel in missing_channels:
            if channel == Config.SUPPORT_CHANNEL:
                buttons.append([InlineKeyboardButton("❌ SUPPORT", url=f"https://t.me/{channel[1:]}")])
            elif channel == Config.UPDATE_CHANNEL:
                buttons.append([InlineKeyboardButton("❌ UPDATE", url=f"https://t.me/{channel[1:]}")])
            else:
                buttons.append([InlineKeyboardButton(f"❌ {channel}", url=f"https://t.me/{channel[1:]}")])
        
        # Add verification button
        buttons.append([InlineKeyboardButton("✅ I Subscribed", callback_data=callback_data)])
        
        return InlineKeyboardMarkup(buttons)
    
    def get_vote_count_keyboard(self, emoji: str, count: int) -> InlineKeyboardMarkup:
        """Get vote count display keyboard"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{emoji} ({count})", callback_data="vote_count")]
        ])
    
    def get_admin_keyboard(self) -> InlineKeyboardMarkup:
        """Get admin command keyboard"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
                InlineKeyboardButton("🗳️ All Votes", callback_data="admin_votes")
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="start")]
        ])
    
    def get_channel_subscription_keyboard(self, target_channel: str, missing_channels: list) -> InlineKeyboardMarkup:
        """Get keyboard for channel subscription verification"""
        buttons = []
        
        for channel in missing_channels:
            if channel == Config.SUPPORT_CHANNEL:
                buttons.append([InlineKeyboardButton("❌ SUPPORT", url=f"https://t.me/{channel[1:]}")])
            elif channel == Config.UPDATE_CHANNEL:
                buttons.append([InlineKeyboardButton("❌ UPDATE", url=f"https://t.me/{channel[1:]}")])
            else:
                buttons.append([InlineKeyboardButton(f"❌ {channel}", url=f"https://t.me/{channel[1:]}")])
        
        # Remove @ from target channel for callback data
        channel_name = target_channel[1:] if target_channel.startswith("@") else target_channel
        buttons.append([InlineKeyboardButton("✅ I Subscribed", callback_data=f"verify_{channel_name}")])
        
        return InlineKeyboardMarkup(buttons)
    
    def get_vote_management_keyboard(self, channel_username: str) -> InlineKeyboardMarkup:
        """Get vote management keyboard for admins"""
        channel_name = channel_username[1:] if channel_username.startswith("@") else channel_username
        
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👥 Participants", callback_data=f"show_participants_{channel_name}"),
                InlineKeyboardButton("📊 Stats", callback_data=f"vote_stats_{channel_name}")
            ],
            [InlineKeyboardButton("🗑️ Delete Vote", callback_data=f"delete_vote_{channel_name}")]
        ])
    
    def get_confirmation_keyboard(self, action: str, target: str) -> InlineKeyboardMarkup:
        """Get confirmation keyboard for destructive actions"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Yes", callback_data=f"confirm_{action}_{target}"),
                InlineKeyboardButton("❌ No", callback_data="cancel_action")
            ]
        ])
    
    def get_pagination_keyboard(self, current_page: int, total_pages: int, callback_prefix: str) -> InlineKeyboardMarkup:
        """Get pagination keyboard"""
        buttons = []
        
        if total_pages > 1:
            nav_buttons = []
            
            if current_page > 1:
                nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"{callback_prefix}_page_{current_page-1}"))
            
            nav_buttons.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="current_page"))
            
            if current_page < total_pages:
                nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"{callback_prefix}_page_{current_page+1}"))
            
            buttons.append(nav_buttons)
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_menu")])
        
        return InlineKeyboardMarkup(buttons)
