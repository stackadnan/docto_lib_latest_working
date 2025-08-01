# Security Guidelines

## Environment Variables

This project uses environment variables to securely store sensitive configuration:

### Required Variables

1. **BOT_TOKEN**: Your Telegram bot token (get from @BotFather)
2. **PROXY_SERVER**: Proxy server URL (format: `http://host:port`)
3. **PROXY_USERNAME**: Proxy username
4. **PROXY_PASSWORD**: Proxy password

Note: The same proxy configuration is used by both `scraper.py` and `play_wright.py`. The scraper builds the full proxy URL internally from these components.

### Setup Instructions

1. Copy `.env.example` to `.env`
2. Fill in your actual credentials in `.env`
3. Never commit `.env` to version control (it's in `.gitignore`)

### File Structure

- `.env` - Contains your actual credentials (DO NOT SHARE)
- `.env.example` - Template file with placeholder values (safe to share)

## Important Security Notes

⚠️ **NEVER** commit actual credentials to version control
⚠️ **ALWAYS** use environment variables for sensitive data
⚠️ Keep your `.env` file secure and backed up separately
⚠️ Rotate credentials regularly for security
