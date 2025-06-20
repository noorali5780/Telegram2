import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

class DatabaseManager:
    def __init__(self, db_path: str = "telegram_data.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_db()
        
    def _init_db(self):
        """Initialize database tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create users table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        phone TEXT,
                        is_bot BOOLEAN,
                        is_verified BOOLEAN,
                        last_seen TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create messages table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        group_id INTEGER,
                        message_text TEXT,
                        status TEXT,
                        sent_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id),
                        FOREIGN KEY (group_id) REFERENCES groups (group_id)
                    )
                """)
                
                # Create groups table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS groups (
                        group_id INTEGER PRIMARY KEY,
                        group_name TEXT,
                        group_link TEXT,
                        member_count INTEGER,
                        is_private BOOLEAN,
                        last_scraped TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create group_members table (many-to-many relationship)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS group_members (
                        group_id INTEGER,
                        user_id INTEGER,
                        joined_date TIMESTAMP,
                        role TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (group_id, user_id),
                        FOREIGN KEY (group_id) REFERENCES groups (group_id),
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
                
                # Create errors table for logging
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS errors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        error_type TEXT,
                        error_message TEXT,
                        error_context TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
                self.logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            self.logger.error(f"Database initialization error: {str(e)}")
            raise

    def insert_user(self, user_data: Dict[str, Any]) -> bool:
        """Insert or update user information."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, last_name, phone, is_bot, is_verified, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_data.get('id'),
                    user_data.get('username'),
                    user_data.get('first_name'),
                    user_data.get('last_name'),
                    user_data.get('phone'),
                    user_data.get('bot', False),
                    user_data.get('verified', False),
                    user_data.get('last_seen')
                ))
                conn.commit()
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error inserting user: {str(e)}")
            self.log_error("insert_user", str(e), user_data)
            return False

    def insert_group(self, group_data: Dict[str, Any]) -> bool:
        """Insert or update group information."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO groups 
                    (group_id, group_name, group_link, member_count, is_private, last_scraped)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    group_data.get('id'),
                    group_data.get('name'),
                    group_data.get('link'),
                    group_data.get('member_count'),
                    group_data.get('is_private', False),
                    datetime.now()
                ))
                conn.commit()
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error inserting group: {str(e)}")
            self.log_error("insert_group", str(e), group_data)
            return False

    def add_group_member(self, group_id: int, user_id: int, role: str = 'member') -> bool:
        """Add a user to a group."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO group_members 
                    (group_id, user_id, joined_date, role)
                    VALUES (?, ?, ?, ?)
                """, (group_id, user_id, datetime.now(), role))
                conn.commit()
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error adding group member: {str(e)}")
            self.log_error("add_group_member", str(e), {"group_id": group_id, "user_id": user_id})
            return False

    def log_error(self, error_type: str, error_message: str, error_context: Any) -> None:
        """Log an error to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO errors (error_type, error_message, error_context)
                    VALUES (?, ?, ?)
                """, (error_type, error_message, json.dumps(error_context)))
                conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Error logging error to database: {str(e)}")

    def get_group_members(self, group_id: int) -> List[Dict[str, Any]]:
        """Get all members of a specific group."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT u.*, gm.role, gm.joined_date
                    FROM users u
                    JOIN group_members gm ON u.user_id = gm.user_id
                    WHERE gm.group_id = ?
                """, (group_id,))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"Error getting group members: {str(e)}")
            return []

    def update_group(self, group_id: int, group_name: str, member_count: int) -> bool:
        """Update group information in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO groups 
                    (group_id, group_name, member_count, last_updated)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (group_id, group_name, member_count))
                conn.commit()
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error updating group: {str(e)}")
            return False

    def add_user(self, user_data: Dict[str, Any]) -> bool:
        """Add or update user in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, last_name, last_seen)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    user_data.get('id'),
                    user_data.get('username'),
                    user_data.get('first_name'),
                    user_data.get('last_name')
                ))
                conn.commit()
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error adding user: {str(e)}")
            return False

    def log_message(self, user_id: int, message: str, status: str) -> bool:
        """Log a message in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO messages (user_id, message_text, status, sent_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, message, status))
                conn.commit()
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error logging message: {str(e)}")
            return False

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics for the last 7 days."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT error_type, COUNT(*) as count
                    FROM errors
                    WHERE created_at >= datetime('now', '-7 days')
                    GROUP BY error_type
                """)
                return dict(cursor.fetchall())
        except sqlite3.Error as e:
            self.logger.error(f"Error getting error stats: {str(e)}")
            return {}
