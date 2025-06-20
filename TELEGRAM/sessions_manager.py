import json
import os
from typing import Dict, Optional
from cryptography.fernet import Fernet
import base64

class SessionsManager:
    def __init__(self, file_path: str = "sessions.json"):
        self.file_path = file_path
        # Generate or load encryption key
        key_file = "session.key"
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                self.key = f.read()
        else:
            self.key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(self.key)
        
        self.cipher_suite = Fernet(self.key)
        
    def save_session(self, session_name: str, session_string: str, phone: str) -> None:
        """Save an encrypted session string"""
        sessions = self.load_all_sessions()
        
        # Encrypt the session string
        encrypted_session = self.cipher_suite.encrypt(session_string.encode())
        encrypted_phone = self.cipher_suite.encrypt(phone.encode())
        
        sessions[session_name] = {
            'session': base64.b64encode(encrypted_session).decode(),
            'phone': base64.b64encode(encrypted_phone).decode()
        }
        
        with open(self.file_path, 'w') as f:
            json.dump(sessions, f)
            
    def load_session(self, session_name: str) -> Optional[Dict[str, str]]:
        """Load and decrypt a session string"""
        sessions = self.load_all_sessions()
        if session_name not in sessions:
            return None
            
        session_data = sessions[session_name]
        try:
            # Decrypt session string
            encrypted_session = base64.b64decode(session_data['session'])
            encrypted_phone = base64.b64decode(session_data['phone'])
            
            session_string = self.cipher_suite.decrypt(encrypted_session).decode()
            phone = self.cipher_suite.decrypt(encrypted_phone).decode()
            
            return {
                'session_string': session_string,
                'phone': phone
            }
        except Exception:
            return None
            
    def load_all_sessions(self) -> Dict[str, Dict[str, str]]:
        """Load all saved sessions"""
        if not os.path.exists(self.file_path):
            return {}
            
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
