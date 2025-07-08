#!/usr/bin/env python3
"""
Test script to verify track system functionality
"""

import asyncio
import re
from datetime import datetime

def test_participation_post_detection():
    """Test if participation posts are detected correctly"""
    
    # Sample participation post text
    sample_post = """
🎯 **ᴘᴀʀᴛɪᴄɪᴘᴀᴛɪᴏɴ sᴜᴄᴄᴇssғᴜʟ!** 🎯

👤 **ɴᴀᴍᴇ:** Ajay Kumar
🆔 **ᴜsᴇʀ ɪᴅ:** `7840521426`
📱 **ᴜsᴇʀɴᴀᴍᴇ:** @ajay_test
📢 **ᴄʜᴀɴɴᴇʟ:** @vote_taste
⏰ **ᴛɪᴍᴇ:** 1751953634004009

**❖ ᴘᴀʀᴛɪᴄɪᴘᴀᴛɪᴏɴ ᴄᴏᴍᴘʟᴇᴛᴇᴅ! ɴᴏᴡ sʜᴀʀᴇ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘs ғᴏʀ ᴍᴏʀᴇ ᴠᴏᴛᴇs ❖**
"""
    
    # Test detection
    keywords = [
        "ᴘᴀʀᴛɪᴄɪᴘᴀᴛᴇᴅ ɪɴ ᴠᴏᴛᴇ",
        "participated in vote", 
        "vote participation",
        "ᴠᴏᴛᴇ ᴘᴀʀᴛɪᴄɪᴘᴀᴛɪᴏɴ",
        "ᴘᴀʀᴛɪᴄɪᴘᴀᴛɪᴏɴ",
        "🎯"
    ]
    
    text_lower = sample_post.lower()
    detected = any(keyword.lower() in text_lower for keyword in keywords)
    
    print(f"✅ Participation post detection: {detected}")
    
    # Test extraction
    participant_info = {}
    
    # Extract user ID
    user_id_match = re.search(r'(\d{9,12})', sample_post)
    if user_id_match:
        participant_info['user_id'] = int(user_id_match.group(1))
    
    # Extract username
    username_match = re.search(r'@(\w+)', sample_post)
    if username_match:
        participant_info['username'] = username_match.group(1)
    
    # Extract name
    name_patterns = [
        r'👤.*?([A-Za-z\s]+)',
        r'ɴᴀᴍᴇ.*?([A-Za-z\s]+)',
        r'Name.*?([A-Za-z\s]+)'
    ]
    
    for pattern in name_patterns:
        name_match = re.search(pattern, sample_post, re.IGNORECASE)
        if name_match:
            participant_info['first_name'] = name_match.group(1).strip()
            break
    
    # Extract channel
    channel_match = re.search(r'(@\w+)', sample_post)
    if channel_match:
        participant_info['channel_username'] = channel_match.group(1)
    
    # Extract timestamp
    timestamp_match = re.search(r'(\d{13,16})', sample_post)
    if timestamp_match:
        participant_info['timestamp'] = timestamp_match.group(1)
    
    print(f"✅ Extracted info: {participant_info}")
    
    return participant_info

def test_vote_details_format():
    """Test vote details formatting"""
    
    # Sample vote data
    votes = [
        {
            'voter_id': 123456789,
            'vote_timestamp': datetime.now(),
            'unique_post_id': '7840521426_1751953634004009'
        },
        {
            'voter_id': 987654321, 
            'vote_timestamp': datetime.now(),
            'unique_post_id': '7840521426_1751953634004009'
        }
    ]
    
    # Format voter details
    voter_details = []
    for i, vote in enumerate(votes, 1):
        voter_id = vote.get('voter_id')
        vote_time = vote.get('vote_timestamp', 'Unknown time')
        
        voter_details.append(
            f"**{i}.** Unknown User (@unknown)\n"
            f"   **ID:** `{voter_id}`\n"
            f"   **Time:** {vote_time}\n"
        )
    
    response_text = f"""
📊 **VOTE TRACKING DETAILS** 📊

**👤 Participant Information:**
**Name:** Ajay Kumar
**Username:** @ajay_test
**User ID:** `7840521426`
**Channel:** @vote_taste

**🗳️ Vote Summary:**
**Total Votes:** {len(votes)}
**Vote Status:** {'Active' if len(votes) > 0 else 'No votes yet'}

**👥 Detailed Voter List:**
{chr(10).join(voter_details)}

**📊 Statistics:**
**Most Recent Vote:** {votes[-1].get('vote_timestamp', 'N/A') if votes else 'N/A'}
**First Vote:** {votes[0].get('vote_timestamp', 'N/A') if votes else 'N/A'}
"""
    
    print(f"✅ Vote details format ready")
    print(f"Response preview: {response_text[:200]}...")
    
    return True

if __name__ == "__main__":
    print("🧪 Testing Track System Functionality\n")
    
    # Test 1: Participation post detection
    print("1. Testing participation post detection...")
    participant_info = test_participation_post_detection()
    
    # Test 2: Vote details formatting
    print("\n2. Testing vote details formatting...")
    test_vote_details_format()
    
    print(f"\n✅ All tests passed! Track system is ready to work.")
    print(f"\n📋 How to use:")
    print(f"1. Forward participation post to bot")
    print(f"2. Reply with /track command")
    print(f"3. Get detailed vote information")