import asyncio
import logging
from telethon import TelegramClient
from database_manager import DatabaseManager
from group_connector import GroupConnector
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_env_variables() -> tuple[int, str]:
    """Get and validate environment variables."""
    load_dotenv()
    
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    
    if not api_id:
        raise ValueError("API_ID must be set in .env file")
    if not api_hash:
        raise ValueError("API_HASH must be set in .env file")
        
    try:
        return int(api_id), api_hash
    except ValueError:
        raise ValueError("API_ID must be a valid integer")

async def test_group_operations(client: TelegramClient, db: DatabaseManager):
    try:
        # Initialize GroupConnector
        connector = GroupConnector(client)
        
        # Test group joining
        test_group = "your_test_group_link"  # Replace with actual test group
        logger.info(f"Attempting to join group: {test_group}")
        
        success = await connector.join_group(test_group)
        if not success:
            logger.error("Failed to join group")
            return
            
        # Get group entity
        entity = await connector.check_group_entity(test_group)
        if not entity:
            logger.error("Failed to get group entity")
            return
            
        # Test member fetching
        logger.info("Fetching group members...")
        members = await connector.get_group_members(
            entity,
            filter_inactive=True,
            min_activity_date=int((datetime.now() - timedelta(days=30)).timestamp())
        )
        
        logger.info(f"Found {len(members)} active members")
        
        # Test database operations
        for member in members:
            if db.insert_user(member):
                logger.info(f"Successfully stored user {member.get('username', member.get('id'))}")
            else:
                logger.error(f"Failed to store user {member.get('username', member.get('id'))}")
                
        # Test group info storage
        group_info = {
            'id': entity.id,
            'name': getattr(entity, 'title', None),
            'link': test_group,
            'member_count': len(members),
            'is_private': getattr(entity, 'username', None) is None
        }
        
        if db.insert_group(group_info):
            logger.info("Successfully stored group information")
        else:
            logger.error("Failed to store group information")
            
        # Add group memberships
        for member in members:
            if db.add_group_member(entity.id, member['id']):
                logger.info(f"Added member {member.get('username', member['id'])} to group")
            else:
                logger.error(f"Failed to add member {member.get('username', member['id'])} to group")
                
        # Verify stored data
        stored_members = db.get_group_members(entity.id)
        logger.info(f"Retrieved {len(stored_members)} members from database")
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")

async def main():
    try:
        # Get and validate API credentials
        api_id, api_hash = get_env_variables()
        
        # Initialize database
        db = DatabaseManager()
        
        # Initialize Telegram client
        client = TelegramClient('anon', api_id, api_hash)
        
        try:
            # Start the client (not awaitable)
            client.start()
            
            # Run the test operations
            await test_group_operations(client, db)
        finally:
            client.disconnect()
    except Exception as e:
        logger.error(f"Main execution failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
