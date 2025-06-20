import os
import logging
import asyncio
from typing import Dict, Optional, List, Any, Union, Tuple, Callable, Awaitable
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    PhoneCodeInvalidError, 
    PhoneCodeExpiredError, 
    SessionPasswordNeededError,
    FloodWaitError,
    PhoneNumberInvalidError,
    PhoneCodeEmptyError,
    PhoneCodeHashEmptyError
)
import python_socks
from dotenv import load_dotenv
from sessions_manager import SessionsManager

class AccountManager:
    def __init__(self):
        load_dotenv()
        self.clients: Dict[str, TelegramClient] = {}
        self.logger = logging.getLogger(__name__)
        self.sessions_manager = SessionsManager()
        
        # Convert API_ID to int and ensure it exists
        api_id_str = os.getenv('API_ID')
        if not api_id_str:
            raise ValueError("API_ID must be set in .env file")
        self.api_id = int(api_id_str)
        
        # Ensure api_hash exists
        api_hash = os.getenv('API_HASH')
        if not api_hash:
            raise ValueError("API_HASH must be set in .env file")
        self.api_hash = api_hash
        
        self.use_proxy = os.getenv('USE_PROXY', 'false').lower() == 'true'

    async def create_client(
        self, 
        session_name: str, 
        phone: Optional[str] = None,
        code_callback: Optional[Callable[[str], Awaitable[str]]] = None,
        password_callback: Optional[Callable[[], Awaitable[str]]] = None,
        proxy: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[TelegramClient], Optional[str]]:
        """Create a new Telegram client with enhanced authentication handling."""
        proxy_config: Optional[Dict[str, Any]] = None
        
        if self.use_proxy and proxy:
            proxy_config = {
                'proxy_type': getattr(python_socks, 'SOCKS5', 2),
                'addr': proxy.get('host', ''),
                'port': proxy.get('port', 0),
                'username': proxy.get('username', ''),
                'password': proxy.get('password', '')
            }

        # Try to load existing session
        session_data = self.sessions_manager.load_session(session_name)
        if session_data:
            # Create client with saved session string
            client = TelegramClient(
                StringSession(session_data['session_string']),
                self.api_id,
                self.api_hash,
                proxy=proxy_config
            )
            
            try:
                await client.connect()
                if await client.is_user_authorized():
                    self.clients[session_name] = client
                    self.logger.info(f"Client {session_name} restored from saved session")
                    return client, None
                else:
                    await client.disconnect()
            except Exception as e:
                self.logger.warning(f"Failed to restore session {session_name}: {str(e)}")

        # If no valid saved session, create new one
        client = TelegramClient(
            StringSession(),
            self.api_id,
            self.api_hash,
            proxy=proxy_config
        )
        
        try:
            await client.connect()
            
            if not await client.is_user_authorized():
                if not phone:
                    if not code_callback:
                        raise ValueError("Phone number and code callback are required for authentication")
                    return None, "Phone number is required"
                
                try:
                    # Send authentication code
                    code_sent = await client.send_code_request(phone)
                    if not code_sent:
                        return None, "Failed to send verification code"
                except PhoneNumberInvalidError:
                    await client.disconnect()
                    return None, "The phone number is invalid"
                except FloodWaitError as e:
                    await client.disconnect()
                    return None, f"Too many attempts. Please wait {e.seconds} seconds"
                
                max_attempts = 3
                for attempt in range(max_attempts):
                    try:
                        if not code_callback:
                            raise ValueError("Code callback is required for authentication")
                        
                        code = await code_callback(session_name)
                        if not code:
                            await client.disconnect()
                            return None, "No verification code provided"
                            
                        signed_in = await client.sign_in(phone, code)
                        if not signed_in:
                            continue
                            
                        # Save session after successful sign in
                        session_str = client.session.save()
                        self.sessions_manager.save_session(session_name, session_str, phone)
                        break
                        
                    except PhoneCodeInvalidError:
                        if attempt == max_attempts - 1:
                            await client.disconnect()
                            return None, "Invalid code provided too many times"
                        continue
                    except PhoneCodeExpiredError:
                        await client.disconnect()
                        return None, "Verification code has expired"
                    except SessionPasswordNeededError:
                        if not password_callback:
                            await client.disconnect()
                            return None, "Two-factor authentication is enabled but no password callback provided"
                        
                        try:
                            password = await password_callback()
                            signed_in = await client.sign_in(password=password)
                            if not signed_in:
                                await client.disconnect()
                                return None, "Failed to sign in with 2FA password"
                                
                            # Save session after successful 2FA
                            session_str = client.session.save()
                            self.sessions_manager.save_session(session_name, session_str, phone)
                        except Exception as e:
                            await client.disconnect()
                            return None, f"Failed to complete 2FA: {str(e)}"
                            
                    except Exception as e:
                        await client.disconnect()
                        return None, f"Authentication error: {str(e)}"
            
            self.clients[session_name] = client
            self.logger.info(f"Client {session_name} successfully created and authenticated")
            return client, None
            
        except Exception as e:
            self.logger.error(f"Failed to create client {session_name}: {str(e)}")
            await client.disconnect()
            return None, str(e)

    async def get_client(self, session_name: str) -> Optional[TelegramClient]:
        """Get an existing client."""
        return self.clients.get(session_name)

    async def close_client(self, session_name: str) -> None:
        """Close a specific client connection."""
        if session_name in self.clients:
            client = self.clients[session_name]
            if client:
                await client.disconnect()
            del self.clients[session_name]
            self.logger.info(f"Client {session_name} disconnected")

    async def close_all(self) -> None:
        """Close all client connections."""
        for session_name in list(self.clients.keys()):
            await self.close_client(session_name)

    def get_active_clients(self) -> List[str]:
        """Get list of active client session names."""
        return list(self.clients.keys())

    async def check_client_health(self, session_name: str) -> bool:
        """Check if a client is connected and authorized."""
        client = self.clients.get(session_name)
        if not client:
            return False
        
        try:
            is_connected = client.is_connected()
            is_authorized = await client.is_user_authorized()
            return is_connected and is_authorized
        except Exception:
            return False

    async def rotate_session(self, current_session: str, new_session: str) -> Optional[TelegramClient]:
        """Rotate from one session to another."""
        await self.close_client(current_session)
        client, _ = await self.create_client(new_session)
        return client
