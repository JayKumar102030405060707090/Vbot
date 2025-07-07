
# Telegram Vote Bot

A powerful Telegram bot that allows users to create automated vote polls for their channels with subscription verification and participant management.

## Features

- 🗳️ **Vote Poll Creation**: Create automated vote polls for Telegram channels
- 👥 **Subscription Verification**: Automatic verification of channel subscriptions
- 📊 **Participant Management**: Track and manage vote participants
- ⏰ **Background Tasks**: Scheduled subscription validation
- 💾 **Hybrid Storage**: MongoDB with JSON fallback for reliability
- 🔧 **Admin Controls**: Statistics and management commands

## Setup Instructions

### 1. Get Telegram API Credentials

1. Go to [my.telegram.org](https://my.telegram.org)
2. Create a new application
3. Note down your `API_ID` and `API_HASH`

### 2. Create a Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Use `/newbot` command to create a new bot
3. Get your `BOT_TOKEN`

### 3. Environment Variables

Set the following environment variables:

```
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
OWNER_USERNAME=@your_username
SUPPORT_CHANNEL=@your_support_channel
UPDATE_CHANNEL=@your_update_channel
MONGO_DB_URI=mongodb://localhost:27017/votebot
DATABASE_NAME=votebot
BOT_USERNAME=your_bot_username
SUBSCRIPTION_CHECK_INTERVAL=5
LOG_CHANNEL_ID=your_log_channel_id
```

### 4. Deploy on Heroku

1. Fork this repository
2. Create a new Heroku app
3. Connect your GitHub repository
4. Set the environment variables in Heroku Config Vars
5. Deploy the app

### 5. Deploy on Replit (Recommended)

1. Import this repository to Replit
2. Set environment variables in Replit Secrets
3. Click the Run button

## Commands

- `/start` - Welcome message and bot information
- `/vote` - Create a vote poll for your channel
- `/help` - Show help message
- `/stats` - Show bot statistics (admin only)

## Usage

1. Add the bot to your channel as an admin
2. Use `/vote` command in private chat with the bot
3. Send your channel username with @
4. Share the participation link with your audience
5. Users will vote and bot will verify their subscriptions

## Architecture

- **Pyrogram**: Telegram Bot API wrapper
- **MongoDB**: Primary database with JSON fallback
- **APScheduler**: Background task scheduling
- **Handler-based**: Modular command handling

## File Structure

```
├── main.py              # Application entry point
├── config.py            # Configuration management
├── handlers/            # Command handlers
│   ├── start.py        # Welcome commands
│   ├── vote_simple.py  # Vote creation
│   ├── verify.py       # Subscription verification
│   └── admin.py        # Admin commands
├── utils/              # Utility modules
│   ├── db.py          # Database operations
│   ├── check.py       # Subscription checking
│   ├── keyboards.py   # Keyboard layouts
│   └── scheduler.py   # Background tasks
```

## Support

For support and updates:
- Support Channel: [@Komal_Music_Support](https://t.me/Komal_Music_Support)
- Update Channel: [@KomalMusicUpdate](https://t.me/KomalMusicUpdate)
- Owner: [@INNOCENT_FUCKER](https://t.me/INNOCENT_FUCKER)

## License

This project is licensed under the MIT License.
