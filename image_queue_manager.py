"""
Image Queue Manager for Gurtoy Telegram Bot
Manages pending images waiting for follow-up text messages.
"""
import asyncio
import logging
import time
from typing import Optional, Dict, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PendingImageData:
    """Stores image data while waiting for follow-up text or more images."""
    user_id: int
    chat_id: int
    image_paths: List[str]  # Can store multiple images
    file_ids: List[str]  # Telegram file IDs
    captions: List[Optional[str]]  # Captions for each image
    timestamp: float
    timeout_task: Optional[asyncio.Task] = None
    processing_started: bool = False  # Flag to indicate if processing has begun

    def add_image(self, image_path: str, file_id: str, caption: Optional[str] = None):
        """Add another image to the pending collection."""
        self.image_paths.append(image_path)
        self.file_ids.append(file_id)
        self.captions.append(caption)
        self.timestamp = time.time()  # Update timestamp


class ImageQueueManager:
    """Manages queue of pending images waiting for follow-up messages."""
    
    # Configuration
    IMAGE_WAIT_TIMEOUT = 7.5  # seconds to wait for follow-up text
    MAX_IMAGES_PER_USER = 6   # maximum images to collect per user
    MAX_QUEUE_SIZE = 100      # maximum total pending users
    
    def __init__(self):
        """Initialize the queue manager."""
        self.pending_images: Dict[int, PendingImageData] = {}
        logger.info("📋 ImageQueueManager initialized")
    
    def add_image(
        self,
        user_id: int,
        chat_id: int,
        image_path: str,
        file_id: str,
        caption: Optional[str] = None
    ) -> bool:
        """
        Add an image to the pending queue.

        If user already has pending images, add to their collection.
        If this is a new user, create a new pending entry.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            image_path: Path to downloaded image
            file_id: Telegram file ID
            caption: Optional caption from the image message

        Returns:
            True if added successfully, False if queue is full or limit reached
        """
        try:
            # Check if user already has pending images
            if user_id in self.pending_images:
                pending = self.pending_images[user_id]

                # Check if user has reached max images limit
                if len(pending.image_paths) >= self.MAX_IMAGES_PER_USER:
                    logger.warning(
                        f"User {user_id} reached max images limit ({self.MAX_IMAGES_PER_USER})"
                    )
                    return False

                # Cancel existing timeout task only if we're extending the collection
                # Don't cancel if the task is already processing (to avoid interrupting analysis)
                if (pending.timeout_task and not pending.timeout_task.done()
                    and not pending.processing_started):
                    try:
                        # Try to cancel, but don't log as this is normal when adding more images
                        pending.timeout_task.cancel()
                        logger.info(f"⏰ Cancelled previous timeout for user {user_id}")
                    except:
                        pass  # Task might already be cancelled or completed

                # Add image to existing collection with its caption
                pending.add_image(image_path, file_id, caption)

                logger.info(
                    f"📸 Added image {len(pending.image_paths)}/{self.MAX_IMAGES_PER_USER} "
                    f"for user {user_id}"
                )

                return True

            else:
                # Check queue size limit
                if len(self.pending_images) >= self.MAX_QUEUE_SIZE:
                    logger.warning(f"Queue full ({self.MAX_QUEUE_SIZE}), cannot add new user")
                    return False

                # Create new pending entry
                pending = PendingImageData(
                    user_id=user_id,
                    chat_id=chat_id,
                    image_paths=[image_path],
                    file_ids=[file_id],
                    captions=[caption],
                    timestamp=time.time()
                )

                self.pending_images[user_id] = pending
                logger.info(f"📸 New pending image for user {user_id}")

                return True

        except Exception as e:
            logger.error(f"Error adding image to queue: {e}", exc_info=True)
            return False
    
    def set_timeout_task(self, user_id: int, task: asyncio.Task):
        """
        Set the timeout task for a pending image.
        
        Args:
            user_id: Telegram user ID
            task: Asyncio task that handles timeout
        """
        if user_id in self.pending_images:
            self.pending_images[user_id].timeout_task = task
    
    def get_pending(self, user_id: int) -> Optional[PendingImageData]:
        """
        Get pending image data for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            PendingImageData or None if not found
        """
        return self.pending_images.get(user_id)
    
    def remove_pending(self, user_id: int) -> Optional[PendingImageData]:
        """
        Remove and return pending image data for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            PendingImageData or None if not found
        """
        if user_id in self.pending_images:
            pending = self.pending_images[user_id]

            # Cancel timeout task if exists and it's not the current task
            # (to avoid cancelling ourselves during processing)
            if (pending.timeout_task and not pending.timeout_task.done()
                and pending.timeout_task != asyncio.current_task()):
                pending.timeout_task.cancel()

            del self.pending_images[user_id]
            logger.info(f"🗑️ Removed pending images for user {user_id}")
            return pending
        
        return None
    
    def has_pending(self, user_id: int) -> bool:
        """
        Check if user has pending images.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if user has pending images
        """
        return user_id in self.pending_images
    
    def get_queue_size(self) -> int:
        """Get current queue size."""
        return len(self.pending_images)
    
    def get_user_image_count(self, user_id: int) -> int:
        """
        Get number of pending images for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Number of pending images (0 if none)
        """
        if user_id in self.pending_images:
            return len(self.pending_images[user_id].image_paths)
        return 0
    
    async def cleanup_stale_entries(self, max_age_seconds: float = 60.0) -> int:
        """
        Clean up stale entries that are too old.
        
        Args:
            max_age_seconds: Maximum age in seconds
            
        Returns:
            Number of entries cleaned up
        """
        try:
            current_time = time.time()
            stale_users = []
            
            for user_id, pending in self.pending_images.items():
                age = current_time - pending.timestamp
                if age > max_age_seconds:
                    stale_users.append(user_id)
            
            # Remove stale entries
            for user_id in stale_users:
                self.remove_pending(user_id)
            
            if stale_users:
                logger.info(f"🧹 Cleaned up {len(stale_users)} stale queue entries")
            
            return len(stale_users)
            
        except Exception as e:
            logger.error(f"Error cleaning up stale entries: {e}")
            return 0


# Global instance
_queue_manager_instance: Optional[ImageQueueManager] = None


def get_queue_manager() -> ImageQueueManager:
    """
    Get or create the global ImageQueueManager instance.
    
    Returns:
        ImageQueueManager instance
    """
    global _queue_manager_instance
    if _queue_manager_instance is None:
        _queue_manager_instance = ImageQueueManager()
    return _queue_manager_instance