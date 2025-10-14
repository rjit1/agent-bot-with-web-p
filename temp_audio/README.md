# Temporary Audio Storage

This directory stores voice messages temporarily during processing.

**Privacy & Security:**
- Audio files are automatically deleted after transcription
- Maximum retention: 5 seconds (during processing)
- Periodic cleanup removes orphaned files older than 1 hour
- No permanent audio storage

**Format:**
- Telegram voice messages: OGG with Opus codec
- File naming: `{telegram_id}_{timestamp}.ogg`

**Do not commit audio files to version control!**