"""
Audio Handler Module for Gurtoy Telegram Bot
Handles voice message download, transcription, and cleanup.
"""
import os
import asyncio
import logging
import base64
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import aiofiles
import google.generativeai as genai

# Configure logging
logger = logging.getLogger(__name__)

class AudioHandler:
    """Handles voice message processing using Gemini Flash models."""
    
    # Directory for temporary audio storage
    TEMP_AUDIO_DIR = Path(__file__).parent / "temp_audio"
    
    # Maximum audio file age before cleanup (in minutes)
    MAX_AUDIO_AGE_MINUTES = 60
    
    # Maximum audio duration to process (in seconds)
    MAX_AUDIO_DURATION = 300  # 5 minutes
    
    def __init__(
        self,
        telegram_bot_token: str,
        gemini_api_key: str,
        voice_model_name: Optional[str] = None,
    ):
        """
        Initialize AudioHandler.
        
        Args:
            telegram_bot_token: Telegram bot token for file downloads
            gemini_api_key: Gemini API key for transcription
            voice_model_name: Optional override for the Gemini model used for voice transcription
        """
        self.telegram_bot_token = telegram_bot_token
        self.telegram_api_url = f"https://api.telegram.org/bot{telegram_bot_token}"
        
        # Configure Gemini
        genai.configure(api_key=gemini_api_key)
        
        # Voice transcription model configuration
        self.voice_model_name = (
            voice_model_name
            or os.getenv("VOICE_MODEL_NAME")
            or os.getenv("VOICE_MODEL")
            or "gemini-2.5-flash"
        )
        self.voice_model_temperature = float(
            os.getenv("VOICE_MODEL_TEMPERATURE", "0.2")
        )
        self.voice_model_top_p = float(os.getenv("VOICE_MODEL_TOP_P", "0.8"))
        self.voice_model_top_k = int(os.getenv("VOICE_MODEL_TOP_K", "40"))
        self.voice_post_process_strategy = (
            os.getenv("VOICE_TRANSCRIPTION_POST_PROCESS", "strip")
            .strip()
            .lower()
        )
        
        # Ensure temp directory exists
        self.TEMP_AUDIO_DIR.mkdir(exist_ok=True)
        
        logger.info(
            "🎤 AudioHandler initialized | Model: %s | Temp: %.2f | top_p: %.2f | top_k: %d",
            self.voice_model_name,
            self.voice_model_temperature,
            self.voice_model_top_p,
            self.voice_model_top_k,
        )
    
    async def download_voice_message(
        self, 
        file_id: str, 
        telegram_id: int,
        duration: int = 0
    ) -> Optional[str]:
        """
        Download voice message from Telegram.
        
        Args:
            file_id: Telegram file ID
            telegram_id: User's Telegram ID (for unique filename)
            duration: Voice message duration in seconds
            
        Returns:
            Path to downloaded audio file or None if failed
        """
        try:
            # Check duration limit
            if duration > self.MAX_AUDIO_DURATION:
                logger.warning(
                    f"Voice message too long: {duration}s (max: {self.MAX_AUDIO_DURATION}s)"
                )
                return None
            
            # Step 1: Get file info from Telegram
            logger.info(f"📥 Downloading voice message (file_id: {file_id})")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.telegram_api_url}/getFile",
                    params={"file_id": file_id}
                )
                response.raise_for_status()
                result = response.json()
                
                if not result.get("ok"):
                    logger.error(f"Failed to get file info: {result}")
                    return None
                
                file_path = result["result"]["file_path"]
                file_size = result["result"]["file_size"]
                
                logger.info(f"File info: {file_path} ({file_size} bytes, {duration}s)")
            
            # Step 2: Download file
            file_url = f"https://api.telegram.org/file/bot{self.telegram_bot_token}/{file_path}"
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(file_url)
                response.raise_for_status()
                audio_data = response.content
            
            # Step 3: Save to temp directory with unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{telegram_id}_{timestamp}.ogg"
            audio_path = self.TEMP_AUDIO_DIR / filename
            
            async with aiofiles.open(audio_path, 'wb') as f:
                await f.write(audio_data)
            
            logger.info(f"✅ Voice file saved: {audio_path} ({len(audio_data)} bytes)")
            return str(audio_path)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading voice file: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error downloading voice file: {e}", exc_info=True)
            return None
    
    async def transcribe_audio(self, audio_path: str) -> Optional[Dict[str, Any]]:
        """
        Transcribe audio using Gemini 2.5 Flash with base64 encoding.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with transcription results:
            {
                "transcription": "transcribed text",
                "language": "detected language",
                "confidence": "high/medium/low",
                "file_size_kb": 123.45,
                "processing_time": 2.5
            }
        """
        start_time = datetime.now()
        
        try:
            # Get file size
            file_size_kb = os.path.getsize(audio_path) / 1024
            logger.info(f"🎧 Processing audio: {file_size_kb:.2f} KB")
            
            # Read and encode audio file as base64
            logger.info("📤 Encoding audio file...")
            async with aiofiles.open(audio_path, 'rb') as f:
                audio_data = await f.read()
            
            audio_base64 = base64.standard_b64encode(audio_data).decode('utf-8')
            logger.info(f"✅ Audio encoded: {len(audio_base64) // 1024} KB (base64)")
            
            # Determine MIME type based on file extension
            file_ext = Path(audio_path).suffix.lower()
            mime_types = {
                '.ogg': 'audio/ogg',
                '.mp3': 'audio/mpeg',
                '.wav': 'audio/wav',
                '.m4a': 'audio/mp4',
                '.webm': 'audio/webm'
            }
            mime_type = mime_types.get(file_ext, 'audio/ogg')
            logger.info(f"📝 Detected MIME type: {mime_type}")
            
            # Create Gemini model (configurable)
            model = genai.GenerativeModel(
                model_name=self.voice_model_name,
                generation_config={
                    "temperature": self.voice_model_temperature,
                    "top_p": self.voice_model_top_p,
                    "top_k": self.voice_model_top_k,
                    "max_output_tokens": int(
                        os.getenv("VOICE_MODEL_MAX_OUTPUT_TOKENS", "2048")
                    ),
                },
            )
            
            # Create intelligent prompt for transcription
            prompt = """You are an expert audio transcription assistant for a fashion store chatbot.

**Your Task:**
1. Transcribe this voice message EXACTLY as spoken
2. Detect the language (English, Hindi, or Hinglish mix)
3. Preserve natural speaking style and emotions
4. If the audio is unclear, transcribe what you can understand

**Important Guidelines:**
- Transcribe ONLY what is said, don't add explanations
- Keep Hindi words in Devanagari if spoken in Hindi
- For Hinglish, use Roman script for Hindi words (e.g., "mujhe", "chahiye")
- Preserve question marks, exclamations, and emotions
- If multiple speakers, separate with line breaks

**Output Format:**
Just provide the transcribed text, nothing else.

Now transcribe this voice message:"""
            
            # Generate transcription using base64-encoded audio
            logger.info(
                "🤖 Sending to Gemini for transcription... | Model: %s",
                self.voice_model_name,
            )
            response = await asyncio.to_thread(
                model.generate_content,
                [
                    prompt,
                    {
                        "mime_type": mime_type,
                        "data": audio_base64
                    }
                ]
            )
            
            transcription = response.text.strip()
            
            # Apply optional post-processing if configured
            transcription = self._post_process_transcription(transcription)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Estimate confidence based on transcription length and quality
            confidence = self._estimate_confidence(transcription, file_size_kb)
            
            # Detect language
            language = self._detect_language(transcription)
            
            logger.info(f"✅ Transcription successful ({processing_time:.2f}s)")
            logger.info(f"📝 Text: {transcription[:100]}...")
            logger.info(f"🌐 Language: {language}, Confidence: {confidence}")
            
            return {
                "transcription": transcription,
                "language": language,
                "confidence": confidence,
                "file_size_kb": file_size_kb,
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}", exc_info=True)
            return None
    
    def _post_process_transcription(self, transcription: str) -> str:
        """Apply optional post-processing strategies to the transcription."""
        strategy = self.voice_post_process_strategy
        logger.debug("🧹 Post-processing transcription | strategy=%s", strategy)

        try:
            if strategy == "none":
                return transcription
            if strategy == "strip":
                return transcription.strip()
            if strategy == "smart-strip":
                return self._smart_strip_transcription(transcription)
            if strategy == "normalize":
                return self._normalize_transcription(transcription)
        except Exception as error:
            logger.warning(
                "⚠️ Post-processing failed (strategy=%s): %s",
                strategy,
                error,
            )
            return transcription

        return transcription

    def _smart_strip_transcription(self, transcription: str) -> str:
        """Trim repeated leading/trailing tokens added by the model."""
        cleaned = transcription.strip()
        cleaned = cleaned.lstrip('"\'“”').rstrip('"\'“”')  # Remove leading/trailing quotes
        cleaned = "\n".join(line.strip() for line in cleaned.splitlines())
        lines = [line for line in cleaned.splitlines() if line.strip()]
        return "\n".join(lines)

    def _normalize_transcription(self, transcription: str) -> str:
        """Normalize transcription text for consistent spacing (casing preserved)."""
        cleaned = self._smart_strip_transcription(transcription)
        return " ".join(cleaned.split())

    def _estimate_confidence(self, transcription: str, file_size_kb: float) -> str:
        """Estimate transcription confidence based on heuristics with additional metrics."""
        words = transcription.split()
        word_count = len(words)
        character_count = len(transcription)
        avg_word_length = (character_count / word_count) if word_count else 0
        unique_words = len(set(words)) if words else 0
        lexical_diversity = (unique_words / word_count) if word_count else 0
    
        logger.debug(
            "🔎 Confidence heuristics | words=%d | chars=%d | avg_len=%.2f | diversity=%.2f | size=%.2fKB",
            word_count,
            character_count,
            avg_word_length,
            lexical_diversity,
            file_size_kb,
        )
    
        if word_count == 0:
            return "low"
        if word_count < 3 and file_size_kb > 10:
            return "low"
        if word_count < 5 and file_size_kb > 20:
            return "medium"
        if avg_word_length < 2.3 and word_count > 3:
            return "medium"
        if lexical_diversity < 0.4 and word_count > 8:
            return "medium"
        return "high"
    
    def _detect_language(self, text: str) -> str:
        """
        Detect language from transcribed text.
        
        Args:
            text: Transcribed text
            
        Returns:
            "English", "Hindi", "Hinglish", or "Unknown"
        """
        # Simple heuristic-based language detection
        hindi_words = ['मुझे', 'चाहिए', 'क्या', 'है', 'के', 'लिए', 'और']
        hinglish_words = ['mujhe', 'chahiye', 'kya', 'hai', 'ke', 'liye', 'aur', 'bhi']
        
        text_lower = text.lower()
        
        # Check for Hindi script
        has_hindi_script = any(char in text for word in hindi_words for char in word)
        
        # Check for Hinglish words
        has_hinglish = any(word in text_lower for word in hinglish_words)
        
        # Check for English words
        english_words = ['the', 'is', 'are', 'for', 'and', 'want', 'need', 'please']
        has_english = any(word in text_lower for word in english_words)
        
        if has_hindi_script:
            return "Hindi"
        elif has_hinglish and has_english:
            return "Hinglish"
        elif has_hinglish:
            return "Hinglish"
        elif has_english:
            return "English"
        else:
            return "Unknown"
    
    async def cleanup_audio_file(self, audio_path: str) -> bool:
        """
        Delete temporary audio file.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            True if deleted successfully
        """
        try:
            if os.path.exists(audio_path):
                await asyncio.to_thread(os.remove, audio_path)
                logger.info(f"🗑️ Cleaned up audio file: {audio_path}")
                return True
            else:
                logger.warning(f"Audio file not found for cleanup: {audio_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error cleaning up audio file: {e}")
            return False
    
    async def cleanup_old_audio_files(self) -> int:
        """
        Cleanup audio files older than MAX_AUDIO_AGE_MINUTES.
        
        Returns:
            Number of files deleted
        """
        try:
            deleted_count = 0
            current_time = datetime.now()
            max_age = timedelta(minutes=self.MAX_AUDIO_AGE_MINUTES)
            
            for audio_file in self.TEMP_AUDIO_DIR.glob("*.ogg"):
                try:
                    # Get file modification time
                    file_mtime = datetime.fromtimestamp(audio_file.stat().st_mtime)
                    file_age = current_time - file_mtime
                    
                    if file_age > max_age:
                        await asyncio.to_thread(audio_file.unlink)
                        deleted_count += 1
                        logger.info(f"🗑️ Deleted old audio file: {audio_file.name} (age: {file_age})")
                        
                except Exception as e:
                    logger.error(f"Error deleting old audio file {audio_file}: {e}")
            
            if deleted_count > 0:
                logger.info(f"🧹 Cleanup complete: {deleted_count} old audio files deleted")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during audio cleanup: {e}")
            return 0
    
    async def process_voice_message(
        self,
        file_id: str,
        telegram_id: int,
        duration: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Complete voice message processing pipeline.
        
        Args:
            file_id: Telegram file ID
            telegram_id: User's Telegram ID
            duration: Voice message duration in seconds
            
        Returns:
            Dictionary with transcription results or None if failed
        """
        audio_path = None
        
        try:
            # Step 1: Download
            audio_path = await self.download_voice_message(file_id, telegram_id, duration)
            if not audio_path:
                return None
            
            # Step 2: Transcribe
            result = await self.transcribe_audio(audio_path)
            
            return result
            
        finally:
            # Step 3: Always cleanup (even if transcription fails)
            if audio_path:
                await self.cleanup_audio_file(audio_path)


# Singleton instance (will be initialized in gurtoy_bot_polling.py)
audio_handler: Optional[AudioHandler] = None


def initialize_audio_handler(
    telegram_bot_token: str,
    gemini_api_key: str,
    voice_model_name: Optional[str] = None,
) -> AudioHandler:
    """Initialize the global audio handler instance."""
    global audio_handler
    audio_handler = AudioHandler(
        telegram_bot_token=telegram_bot_token,
        gemini_api_key=gemini_api_key,
        voice_model_name=voice_model_name,
    )
    return audio_handler


def get_audio_handler() -> Optional[AudioHandler]:
    """
    Get the global audio handler instance.
    
    Returns:
        AudioHandler instance or None if not initialized
    """
    return audio_handler