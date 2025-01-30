import asyncio
from queue import Queue, Empty
import discord
from typing import Optional

class QueuedStreamingPCMAudio(discord.AudioSource):
    def __init__(self, async_queue: asyncio.Queue[Optional[bytes]]) -> None:
        self.async_queue = async_queue
        self.sync_queue: Queue[Optional[bytes]] = Queue()
        self.buffer: bytearray = bytearray()
        self.pos: int = 0
        self._end_flag: bool = False
        self.interrupted: bool = False
        self.input_frame_size: int = 960  # For 24kHz mono
        self.output_frame_size: int = 3840  # 20ms at 48kHz stereo
        self.silence: bytes = b'\x00' * self.output_frame_size
        self.buffer_task: Optional[asyncio.Task[None]] = None
        self._start_buffer_task()

    def _start_buffer_task(self) -> None:
        async def buffer_filler() -> None:
            try:
                while not self._end_flag:
                    try:
                        chunk = await self.async_queue.get()
                        if chunk is None:
                            self._end_flag = True
                            break
                        self.sync_queue.put(chunk)
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        print(f"Buffer fill error: {e}")
                        break
            finally:
                self.sync_queue.put(None)
                
        self.buffer_task = asyncio.create_task(buffer_filler())

    def read(self) -> bytes:
        try:
            # Fill buffer if needed
            while len(self.buffer) - self.pos < self.input_frame_size:
                try:
                    chunk = self.sync_queue.get_nowait()
                    if chunk is None:
                        if len(self.buffer) - self.pos <= 0:
                            return b''
                        break
                    self.buffer.extend(chunk)
                except Empty:
                    return self.silence

            view = memoryview(self.buffer)
            chunk = view[self.pos:self.pos + self.input_frame_size]
            self.pos += self.input_frame_size

            if self.pos > 48000:  # Buffer cleanup
                self.buffer = self.buffer[self.pos:]
                self.pos = 0

            result = bytearray(self.output_frame_size)
            
            for i in range(0, len(chunk), 2):
                sample = chunk[i:i+2]
                pos = i * 4
                result[pos:pos+2] = sample
                result[pos+2:pos+4] = sample
                result[pos+4:pos+6] = sample
                result[pos+6:pos+8] = sample

            return bytes(result)

        except Exception as e:
            print(f"Read error: {e}")
            return self.silence

    def cleanup(self) -> None:
        print("Cleaning up audio source...")
        self._end_flag = True
        self.interrupted: bool = True
        if self.buffer_task and not self.buffer_task.done():
            self.buffer_task.cancel()
        self.buffer.clear()
        self.pos = 0