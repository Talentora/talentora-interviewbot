import asyncio
from typing import Any, Callable, Optional
from .base_processor import BaseProcessor
from pipecat.frames.frames import Frame

class IdleFrameProcessor(BaseProcessor):
    def __init__(self, callback: Callable, timeout: float = 5.0):
        self.callback = callback
        self.timeout = timeout
        self.last_frame_time = None
        self.idle_check_task = None
        self._running = True

    async def on_frame(self, frame: Frame) -> Frame:
        """Process incoming frame and reset idle timer."""
        self.last_frame_time = asyncio.get_event_loop().time()
        if self.idle_check_task is None:
            self.idle_check_task = asyncio.create_task(self._check_idle())
        return frame

    async def _check_idle(self):
        """Monitor for idle timeout and trigger callback."""
        while self._running:
            await asyncio.sleep(1)  # Check every second
            if self.last_frame_time is None:
                continue
                
            current_time = asyncio.get_event_loop().time()
            if current_time - self.last_frame_time >= self.timeout:
                await self.callback(self)
                self.last_frame_time = current_time  # Reset timer

    async def cleanup(self):
        """Clean up the idle check task."""
        self._running = False
        if self.idle_check_task:
            self.idle_check_task.cancel()
            try:
                await self.idle_check_task
            except asyncio.CancelledError:
                pass
