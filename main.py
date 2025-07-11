import asyncio
import logging
from pyrogram import Client
from pyrogram.errors import FloodWait
from config import Config
from utils.db import Database
from utils.scheduler import VoteScheduler
from handlers import start, vote, verify, admin, broadcast
from database import permanent_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VoteBot:
    def __init__(self):
        self.app = Client(
            name=":memory:",  # No session file, use memory only
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            sleep_threshold=60
        )
        self.db = Database()
        self.permanent_db = permanent_db
        self.scheduler = VoteScheduler(self.app, self.db)
        
    async def start_bot(self):
        """Start the bot and initialize services"""
        try:
            # Start bot client with flood wait handling
            logger.info("Starting bot client...")
            await self.app.start()
            logger.info("Bot started successfully!")
            
            # Initialize database
            await self.db.connect()
            logger.info("Database connected!")
            
            # Initialize permanent database
            await self.permanent_db.connect()
            logger.info("Permanent database connected!")
            
            # Start scheduler for subscription checks
            await self.scheduler.start()
            logger.info("Scheduler started!")
            
            # Register handlers
            self.register_handlers()
            
            # Keep the bot running
            print("Bot is running... Press Ctrl+C to stop.")
            while True:
                await asyncio.sleep(1)
                
        except FloodWait as e:
            logger.error(f"FloodWait error: Need to wait {e.value} seconds")
            logger.info(f"Waiting for {e.value} seconds before retrying...")
            await asyncio.sleep(e.value)
            await self.start_bot()  # Retry after waiting
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            await self.cleanup()
            raise
    
    def register_handlers(self):
        """Register all message and callback handlers"""
        # Import handlers
        from handlers.start import StartHandler
        from handlers.vote_simple import SimpleVoteHandler
        from handlers.verify import VerifyHandler
        from handlers.admin import AdminHandler
        from handlers.force_subscribe import ForceSubscribeHandler
        
        # Initialize handlers with dependencies
        start_handler = StartHandler(self.app, self.db)
        vote_handler = SimpleVoteHandler(self.app, self.db)
        verify_handler = VerifyHandler(self.app, self.db)
        admin_handler = AdminHandler(self.app, self.db)
        force_subscribe_handler = ForceSubscribeHandler(self.app, self.db)
        from handlers.broadcast_advanced import AdvancedBroadcastHandler, ServedTracker
        from handlers.track import TrackHandler
        broadcast_handler = AdvancedBroadcastHandler(self.app, self.db)
        served_tracker = ServedTracker(broadcast_handler)
        track_handler = TrackHandler(self.app, self.db)
        
        # Register handlers (force subscribe first to catch all messages)
        force_subscribe_handler.register()
        start_handler.register()
        vote_handler.register()
        verify_handler.register()
        admin_handler.register()
        broadcast_handler.register()
        track_handler.register()
        served_tracker.register_middleware(self.app)
        
        logger.info("All handlers registered successfully!")
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            await self.scheduler.stop()
            await self.db.close()
            await self.app.stop()
            logger.info("Bot stopped and resources cleaned up!")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

async def main():
    bot = VoteBot()
    await bot.start_bot()

if __name__ == "__main__":
    asyncio.run(main())
