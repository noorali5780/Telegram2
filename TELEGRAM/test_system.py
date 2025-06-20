import asyncio
import logging
from datetime import datetime
from account_manager import AccountManager
from group_connector import GroupConnector
from message_engine import MessageEngine
from utility import LogManager, ConfigManager
from database_manager import DatabaseManager
from telethon.tl.types import User
from typing import Dict, Any, Optional
from telethon import TelegramClient

async def main():
    # Initialize logging and database
    log_manager = LogManager()
    logger = logging.getLogger(__name__)
    db_manager = DatabaseManager()
    logger.info("Starting Telegram interaction test")

    try:
        # Initialize account manager and create a client
        account_manager = AccountManager()
        client_result = await account_manager.create_client("test_session")
        
        if not client_result or not client_result[0]:
            error_msg = client_result[1] if client_result else "Failed to create client"
            logger.error(error_msg)
            return

        client = client_result[0]
        logger.info("Successfully created Telegram client")

        # Initialize group connector and message engine
        group_connector = GroupConnector(client)
        message_engine = MessageEngine(client)

        # Test group connection (replace with actual group link)
        group_link = input("Enter Telegram group link to test: ")
        success = await group_connector.join_group(group_link)

        if success:
            logger.info(f"Successfully joined group: {group_link}")

            # Get group entity
            group_entity = await client.get_entity(group_link)

            try:
                # Get members and store in database
                members = await group_connector.get_group_members(group_entity)
                logger.info(f"Found {len(members)} members")

                # Store group info in database
                group_id = getattr(group_entity, 'id', None)
                if group_id:
                    db_manager.update_group(
                        group_id=group_id,
                        group_name=getattr(group_entity, 'title', 'Unknown'),
                        member_count=len(members)
                    )

                # Store member info in database
                for member in members:
                    db_manager.add_user(member)

                # Test message sending to yourself (safe testing)
                me = await client.get_me()
                if isinstance(me, User):
                    user_id = me.id
                else:
                    user_id = getattr(me, 'user_id', None)
                
                if user_id:
                    test_message = "This is a test message from the Telegram interaction system."
                    # Log message to database before sending
                    db_manager.log_message(user_id, test_message, "queued")
                    
                    await message_engine.add_to_queue(
                        user_id,
                        test_message,
                        priority=1
                    )

                    # Process the queue
                    await message_engine.process_queue()
                    logger.info("Test message sent successfully")
                    
                    # Update message status in database
                    db_manager.log_message(user_id, test_message, "sent")
                else:
                    error_msg = "Could not determine user ID"
                    logger.error(error_msg)
                    db_manager.log_error(
                        error_type="UserIDError",
                        error_message=error_msg,
                        error_context={"action": "get_user_id"}
                    )

            except Exception as process_error:
                error_context = {
                    'timestamp': datetime.now().isoformat(),
                    'group_link': group_link,
                    'action': 'process_members'
                }
                logger.error(f"Error processing group: {str(process_error)}")
                db_manager.log_error(
                    error_type=type(process_error).__name__,
                    error_message=str(process_error),
                    error_context=error_context
                )
        else:
            error_msg = f"Failed to join group: {group_link}"
            logger.error(error_msg)
            db_manager.log_error(
                error_type="GroupJoinError",
                error_message=error_msg,
                error_context={"group_link": group_link}
            )

    except Exception as e:
        error_context = {
            'timestamp': datetime.now().isoformat(),
            'error_location': 'main',
            'last_action': 'Unknown'
        }
        
        logger.error(f"Test failed: {str(e)}")
        try:
            db_manager.log_error(
                error_type=type(e).__name__,
                error_message=str(e),
                error_context=error_context
            )
        except Exception as db_error:
            logger.critical(f"Failed to log error to database: {str(db_error)}")
            
    finally:
        try:
            # Clean up
            if 'account_manager' in locals():
                await account_manager.close_all()
            logger.info("Test completed")
            
            # Log error statistics
            error_stats = db_manager.get_error_stats()
            if error_stats:
                logger.info(f"Error statistics for the last 7 days: {error_stats}")
                
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {str(cleanup_error)}")

if __name__ == "__main__":
    asyncio.run(main())
