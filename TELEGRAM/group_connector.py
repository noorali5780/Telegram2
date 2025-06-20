import logging
from typing import List, Dict, Optional, Union
from telethon import TelegramClient
from telethon.tl.functions.channels import GetParticipantsRequest, JoinChannelRequest
from telethon.tl.types import ChannelParticipantsSearch, User, Channel, Chat
from telethon.errors import (
    FloodWaitError, 
    ChannelPrivateError, 
    UserAlreadyParticipantError,
    ChatAdminRequiredError
)
import asyncio
from datetime import datetime

class GroupConnector:
    def __init__(self, client: TelegramClient):
        self.client = client
        self.logger = logging.getLogger(__name__)
        
    async def join_group(self, group_link: str) -> bool:
        """Join a Telegram group using its invite link."""
        try:
            entity = await self.client.get_entity(group_link)
            if not isinstance(entity, (Channel, Chat)):
                self.logger.error(f"Invalid group type for {group_link}")
                return False
                
            await self.client(JoinChannelRequest(entity))
            self.logger.info(f"Successfully joined group: {group_link}")
            return True
            
        except UserAlreadyParticipantError:
            self.logger.info(f"Already a member of group: {group_link}")
            return True
        except ChannelPrivateError:
            self.logger.error(f"Cannot join private group: {group_link}")
            return False
        except FloodWaitError as e:
            self.logger.error(f"Rate limit hit. Wait {e.seconds} seconds before retrying")
            return False
        except Exception as e:
            self.logger.error(f"Failed to join group {group_link}: {str(e)}")
            return False

    async def get_group_members(
        self, 
        group_entity: Union[Channel, Chat], 
        filter_inactive: bool = False,
        min_activity_date: Optional[int] = None
    ) -> List[Dict]:
        """
        Fetch group members with optional filtering.
        Returns a list of member information dictionaries.
        """
        members = []
        offset = 0
        limit = 200
        
        while True:
            try:
                participants = await self.client(GetParticipantsRequest(
                    channel=group_entity,
                    filter=ChannelParticipantsSearch(''),
                    offset=offset,
                    limit=limit,
                    hash=0
                ))
                
                if not participants.users:
                    break
                    
                for user in participants.users:
                    if not isinstance(user, User):
                        continue
                        
                    member_info = {
                        'id': user.id,
                        'username': user.username,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'phone': user.phone,
                        'bot': user.bot,
                        'last_seen': getattr(user.status, 'was_online', None),
                        'verified': user.verified,
                        'retrieved_at': datetime.now().isoformat()
                    }
                    
                    if filter_inactive and min_activity_date:
                        if not user.status or not getattr(user.status, 'was_online', None) or \
                           user.status.was_online < min_activity_date:
                            continue
                            
                    members.append(member_info)
                
                offset += len(participants.users)
                
                # Avoid rate limiting
                await asyncio.sleep(1)
                
            except FloodWaitError as e:
                self.logger.warning(f"Rate limit hit. Waiting {e.seconds} seconds...")
                await asyncio.sleep(e.seconds)
            except ChatAdminRequiredError:
                self.logger.error("Admin privileges required to fetch members")
                break
            except Exception as e:
                self.logger.error(f"Error fetching members: {str(e)}")
                break
                
        return members

    async def check_group_entity(self, group_link: str) -> Optional[Union[Channel, Chat]]:
        """Validate and return a group entity."""
        try:
            entity = await self.client.get_entity(group_link)
            if not isinstance(entity, (Channel, Chat)):
                self.logger.error(f"Invalid group type for {group_link}")
                return None
            return entity
        except Exception as e:
            self.logger.error(f"Failed to get entity for {group_link}: {str(e)}")
            return None
