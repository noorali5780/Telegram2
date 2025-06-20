import logging
import random
import asyncio
from typing import List, Dict, Optional
from telethon import TelegramClient
from telethon.errors import FloodWaitError
import json
import os
from datetime import datetime

class MessageEngine:
    def __init__(self, client: TelegramClient):
        self.client = client
        self.logger = logging.getLogger(__name__)
        self.min_delay = int(os.getenv('MIN_DELAY', 30))
        self.max_delay = int(os.getenv('MAX_DELAY', 120))
        self.max_retries = int(os.getenv('MAX_RETRIES', 3))
        self.message_queue = []
        
    def load_templates(self, template_file: str) -> List[str]:
        """Load message templates from a JSON file."""
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                templates = json.load(f)
            return templates
        except Exception as e:
            self.logger.error(f"Error loading templates: {str(e)}")
            return []

    def craft_message(self, template: str, user_data: Dict) -> str:
        """Create a personalized message using template and user data."""
        try:
            return template.format(
                first_name=user_data.get('first_name', ''),
                last_name=user_data.get('last_name', ''),
                username=user_data.get('username', ''),
                **user_data
            )
        except KeyError as e:
            self.logger.error(f"Missing template variable: {str(e)}")
            return template
        
    async def add_to_queue(
        self,
        user_id: int,
        message: str,
        priority: int = 1
    ):
        """Add a message to the delivery queue."""
        self.message_queue.append({
            'user_id': user_id,
            'message': message,
            'priority': priority,
            'retries': 0,
            'timestamp': datetime.now().timestamp()
        })
        
    async def process_queue(self):
        """Process the message queue with delays and retries."""
        while self.message_queue:
            # Sort queue by priority and timestamp
            self.message_queue.sort(
                key=lambda x: (-x['priority'], x['timestamp'])
            )
            
            message_data = self.message_queue.pop(0)
            
            try:
                await self.send_message(
                    message_data['user_id'],
                    message_data['message']
                )
                
                # Add random delay between messages
                delay = random.randint(self.min_delay, self.max_delay)
                await asyncio.sleep(delay)
                
            except FloodWaitError as e:
                self.logger.warning(f"Rate limit hit. Waiting {e.seconds} seconds")
                # Put message back in queue
                if message_data['retries'] < self.max_retries:
                    message_data['retries'] += 1
                    self.message_queue.append(message_data)
                await asyncio.sleep(e.seconds)
                
            except Exception as e:
                self.logger.error(f"Error sending message: {str(e)}")
                if message_data['retries'] < self.max_retries:
                    message_data['retries'] += 1
                    self.message_queue.append(message_data)

    async def send_message(
        self,
        user_id: int,
        message: str,
        parse_mode: Optional[str] = None
    ) -> bool:
        """Send a message to a specific user."""
        try:
            await self.client.send_message(
                user_id,
                message,
                parse_mode=parse_mode
            )
            self.logger.info(f"Message sent to user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send message to {user_id}: {str(e)}")
            raise

    def get_queue_status(self) -> Dict:
        """Get current status of the message queue."""
        return {
            'queue_length': len(self.message_queue),
            'high_priority': sum(1 for m in self.message_queue if m['priority'] > 1),
            'retry_messages': sum(1 for m in self.message_queue if m['retries'] > 0)
        }

    async def clear_queue(self):
        """Clear the message queue."""
        self.message_queue = []
        self.logger.info("Message queue cleared")
