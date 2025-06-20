# Telegram Group Interaction System

A modular, scalable system for managing Telegram group interactions using Telethon.

## Features

- Multiple account management
- Efficient group member collection
- Customizable message templates
- Time-distributed messaging
- Smart filtering options
- Detailed logging and error tracking
- Data export capabilities
- Session persistence
- Proxy support

## Setup

1. Install requirements:
```bash
pip install -r requirements.txt
```

2. Configure your settings:
   - Copy `.env.example` to `.env` and fill in your Telegram API credentials
   - Modify `config.json` with your preferred settings
   - Create custom message templates in the `templates` directory

## Usage

Basic usage:
```bash
python controller.py --session session_name --group group_link
```

### Configuration

1. Telegram API Credentials:
   - Get your API credentials from https://my.telegram.org
   - Add them to your `.env` file

2. Message Templates:
   - Create templates in the `templates` directory
   - Use variables like {first_name}, {username}, etc.

3. Filtering Options:
   - Configure filters in `config.json`
   - Options include activity filtering, username requirements, etc.

### Directory Structure

```
├── account_manager.py    # Handles Telegram accounts
├── group_connector.py    # Manages group interactions
├── message_engine.py     # Handles message delivery
├── utility.py           # Utility functions
├── controller.py        # Main controller
├── config.json         # Configuration
├── templates/          # Message templates
├── sessions/          # Session storage
├── logs/              # Log files
└── exports/           # Exported data
```

## Safety Features

- Randomized delays between messages
- Account rotation capability
- Rate limiting protection
- Error handling and logging
- Session persistence

## Error Handling

The system includes comprehensive error tracking:
- Logs are stored in the `logs` directory
- Detailed error tracking with context
- Export capabilities for troubleshooting

## Data Export

Results are automatically exported in both CSV and JSON formats to the `exports` directory.

## Best Practices

1. Start with small batches to test settings
2. Monitor logs for any rate limiting or errors
3. Use multiple sessions for large groups
4. Regularly check account health
5. Keep message templates personalized but professional

## License

MIT License - see LICENSE file for details.
