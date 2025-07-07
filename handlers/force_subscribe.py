from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.errors import ChatAdminRequired, UserNotParticipant, ChatWriteForbidden
from config import Config

# Must join channel
MUST_JOIN = "KOMALMUSICUPDATE"

class ForceSubscribeHandler:
    def __init__(self, app: Client, db):
        self.app = app
        self.db = db

    def register(self):
        """Register force subscribe handler"""
        
        @self.app.on_message(filters.incoming & filters.private, group=-1)
        async def must_join_channel(app: Client, msg: Message):
            if not MUST_JOIN:
                return
            try:
                try:
                    await app.get_chat_member(MUST_JOIN, msg.from_user.id)
                except UserNotParticipant:
                    if MUST_JOIN.isalpha():
                        link = "https://t.me/" + MUST_JOIN
                    else:
                        chat_info = await app.get_chat(MUST_JOIN)
                        link = chat_info.invite_link
                    try:
                        await msg.reply_photo(
                            photo="https://graph.org/file/46412deeaab8e8b8c0b06-3bc9b2e0ae531f7b9c.jpg", 
                            caption=f"๏ ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴊᴏɪɴ ᴛʜᴇ [๏ sᴜᴘᴘᴏʀᴛ ๏]({link}) ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴄʜᴇᴀᴋ ᴍʏ ғᴇᴀᴛᴜʀᴇs.\n\nᴀғᴛᴇʀ ᴊᴏɪɴ ᴛʜᴇ [๏ ᴄʜᴀɴɴᴇʟ ๏]({link}) ᴄᴏᴍᴇ ʙᴀᴄᴋ ᴛᴏ ᴛʜᴇ ʙᴏᴛ ᴀɴᴅ ᴛʏᴘᴇ /start ᴀɢᴀɪɴ !! ",
                            reply_markup=InlineKeyboardMarkup(
                                [
                                    [
                                        InlineKeyboardButton("• ᴊᴏɪɴ •", url=link),
                                        InlineKeyboardButton("• ᴊᴏɪɴ •", url="https://t.me/BestFriendsChattingZone"),
                                    ]
                                ]
                            )
                        )
                        await msg.stop_propagation()
                    except ChatWriteForbidden:
                        pass
            except ChatAdminRequired:
                print(f"๏ ᴘʀᴏᴍᴏᴛᴇ ᴍᴇ ᴀs ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴇ ᴍᴜsᴛ_ᴊᴏɪɴ ᴄʜᴀᴛ ๏: {MUST_JOIN} !")

    async def check_subscription(self, user_id: int, channel: str) -> bool:
        """Check if user is subscribed to a channel"""
        try:
            await self.app.get_chat_member(channel, user_id)
            return True
        except UserNotParticipant:
            return False
        except Exception:
            return False

    async def send_subscription_prompt(self, msg: Message, missing_channels: list, target_channel: str):
        """Send subscription prompt to user"""
        # This method is kept for compatibility but the main logic is now in the decorator above
        pass