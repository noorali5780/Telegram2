import asyncio
import logging
from typing import List, Dict, Optional
from account_manager import AccountManager
from group_connector import GroupConnector
from message_engine import MessageEngine
from utility import LogManager, ConfigManager, DataExporter, SessionManager, ErrorTracker
import json
import os
from datetime import datetime
import argparse
from pathlib import Path

class TelegramController:
    def __init__(self):
        # Initialize utility modules
        self.log_manager = LogManager()
        self.logger = logging.getLogger(__name__)
        self.config_manager = ConfigManager()
        self.session_manager = SessionManager()
        self.error_tracker = ErrorTracker()
        
        # Initialize core modules
        self.account_manager = AccountManager()
        self.active_sessions: Dict[str, dict] = {}
        
    async def initialize_session(self, session_name: str) -> bool:
        """Initialize a new session with all required components."""
        try:
            client = await self.account_manager.create_client(session_name)
            if client:
                self.active_sessions[session_name] = {
                    'client': client,
                    'group_connector': GroupConnector(client),
                    'message_engine': MessageEngine(client)
                }
                return True
            return False
        except Exception as e:
            self.error_tracker.log_error(
                'SessionInitError',
                str(e),
                {'session_name': session_name}
            )
            return False

    async def process_group(
        self,
        session_name: str,
        group_link: str,
        message_template: str,
        filter_criteria: Optional[Dict] = None
    ):
        """Process a group with the specified session."""
        if session_name not in self.active_sessions:
            self.logger.error(f"Session {session_name} not initialized")
            return
        
        session = self.active_sessions[session_name]
        try:
            # Join the group
            if not await session['group_connector'].join_group(group_link):
                return
            
            # Get group entity
            group_entity = await session['client'].get_entity(group_link)
            
            # Get members
            members = await session['group_connector'].get_group_members(
                group_entity,
                filter_inactive=filter_criteria.get('filter_inactive', False) if filter_criteria else False
            )
            
            if filter_criteria:
                members = await session['group_connector'].filter_members(
                    members,
                    filter_criteria
                )
            
            # Process members
            for member in members:
                message = session['message_engine'].craft_message(
                    message_template,
                    member
                )
                await session['message_engine'].add_to_queue(
                    member['id'],
                    message
                )
            
            # Process message queue
            await session['message_engine'].process_queue()
            
            # Export results
            self._export_results(members, group_link)
            
        except Exception as e:
            self.error_tracker.log_error(
                'GroupProcessError',
                str(e),
                {
                    'session_name': session_name,
                    'group_link': group_link
                }
            )

    def _export_results(self, members: List[Dict], group_link: str):
        """Export processing results to files."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_dir = Path('exports')
        export_dir.mkdir(exist_ok=True)
        
        # Export to CSV
        csv_file = export_dir / f"members_{timestamp}.csv"
        DataExporter.export_to_csv(members, str(csv_file))
        
        # Export to JSON
        json_file = export_dir / f"members_{timestamp}.json"
        DataExporter.export_to_json(members, str(json_file))

    async def close_all_sessions(self):
        """Close all active sessions."""
        for session_name in list(self.active_sessions.keys()):
            await self.account_manager.close_client(session_name)
            del self.active_sessions[session_name]

async def main():
    parser = argparse.ArgumentParser(description='Telegram Group Interaction System')
    parser.add_argument('--config', type=str, default='config.json',
                      help='Path to configuration file')
    parser.add_argument('--session', type=str, required=True,
                      help='Session name to use')
    parser.add_argument('--group', type=str, required=True,
                      help='Telegram group link to process')
    args = parser.parse_args()

    controller = TelegramController()
    
    try:
        # Initialize session
        if await controller.initialize_session(args.session):
            # Load message template
            with open('templates/message.txt', 'r', encoding='utf-8') as f:
                message_template = f.read()
            
            # Process group
            await controller.process_group(
                args.session,
                args.group,
                message_template,
                filter_criteria={
                    'filter_inactive': True,
                    'has_username': True
                }
            )
    finally:
        await controller.close_all_sessions()

if __name__ == "__main__":
    asyncio.run(main())
