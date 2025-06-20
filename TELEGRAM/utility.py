import logging
import json
import csv
from typing import Dict, Any, List, Optional
import coloredlogs
from datetime import datetime
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

class LogManager:
    def __init__(self, log_file: str = "telegram_bot.log"):
        self.log_file = log_file
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup logging configuration with both file and console output."""
        try:
            # Create logs directory if it doesn't exist
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            # Basic logging format
            log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            
            # Get the root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(logging.INFO)
            
            # Remove any existing handlers
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            
            # Create and configure file handler (with rotation)
            file_handler = RotatingFileHandler(
                log_dir / self.log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(logging.Formatter(log_format))
            root_logger.addHandler(file_handler)
            
            # Create and configure console handler with colors
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(log_format))
            root_logger.addHandler(console_handler)
            
            # Set up colored logs for console
            coloredlogs.install(
                level='INFO',
                fmt=log_format,
                logger=root_logger
            )
            
        except Exception as e:
            print(f"Failed to setup logging: {str(e)}")
            raise

class ConfigManager:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
            
    def save_config(self):
        """Save current configuration to file."""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)
            
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)
        
    def set(self, key: str, value: Any):
        """Set configuration value."""
        self.config[key] = value
        self.save_config()

class DataExporter:
    @staticmethod
    def export_to_csv(data: List[Dict], filename: str):
        """Export data to CSV file."""
        if not data:
            return
            
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            
    @staticmethod
    def export_to_json(data: Any, filename: str):
        """Export data to JSON file."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

class SessionManager:
    def __init__(self, session_dir: str = "sessions"):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(exist_ok=True)
        
    def save_session(self, session_name: str, session_string: str) -> None:
        """Save session string to file."""
        with open(self.session_dir / f"{session_name}.session", 'w') as f:
            f.write(session_string)
            
    def load_session(self, session_name: str) -> Optional[str]:
        """Load session string from file."""
        try:
            with open(self.session_dir / f"{session_name}.session", 'r') as f:
                return f.read()
        except FileNotFoundError:
            return None
            
    def list_sessions(self) -> List[str]:
        """List all saved sessions."""
        return [f.stem for f in self.session_dir.glob("*.session")]
        
    def delete_session(self, session_name: str) -> None:
        """Delete a session file."""
        session_file = self.session_dir / f"{session_name}.session"
        if session_file.exists():
            session_file.unlink()

class ErrorTracker:
    def __init__(self, error_log: str = "error_log.json"):
        self.error_log = Path(error_log)
        self.errors: List[Dict[str, Any]] = self._load_errors()
        
    def _load_errors(self) -> List[Dict[str, Any]]:
        """Load existing error log."""
        try:
            with open(self.error_log, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
            
    def log_error(self, error_type: str, error_message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log an error with timestamp and context."""
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': error_type,
            'message': error_message,
            'context': context or {}
        }
        self.errors.append(error_entry)
        self._save_errors()
        
    def _save_errors(self) -> None:
        """Save errors to file."""
        with open(self.error_log, 'w') as f:
            json.dump(self.errors, f, indent=4)
            
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recent errors."""
        return sorted(
            self.errors,
            key=lambda x: x['timestamp'],
            reverse=True
        )[:limit]
        
    def clear_errors(self) -> None:
        """Clear error log."""
        self.errors = []
        self._save_errors()
