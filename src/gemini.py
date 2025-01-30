import asyncio
import os
import base64
import json
import traceback
from typing import Optional, Dict, Any
from websockets.client import WebSocketClientProtocol
from websockets.asyncio.client import connect
from discord import VoiceClient
from src.stream import QueuedStreamingPCMAudio

class GeminiWebSocket:
    def __init__(self, voice: str = 'aoede', persona: str = "You are a helpful assistant") -> None:
        self.ws: Optional[WebSocketClientProtocol] = None
        self.processing: bool = False
        self.lock: asyncio.Lock = asyncio.Lock()
        self.persona: str = persona
        self.config: Dict[str, Any] = {
            'generation_config': {
                "response_modalities": ["AUDIO"],
                'speech_config': {
                    'voice_config': {
                        'prebuilt_voice_config': {'voice_name': voice}
                    }
                }
            }
        }
        
    async def connect(self) -> None:
        api_key: Optional[str] = os.getenv('GEMINI_API_KEY')
        base_url: str = "wss://generativelanguage.googleapis.com"
        endpoint: str = "/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent"
        uri: str = f"{base_url}{endpoint}?key={api_key}"
        
        if not self.ws:
            self.ws = await connect(uri, additional_headers={"Content-Type": "application/json"})
            await self.setup()
            
    async def setup(self) -> None:
        setup_msg: Dict[str, Any] = {
            "setup": {
                "model": f"models/gemini-2.0-flash-exp",
                "generation_config": self.config["generation_config"],
                'system_instruction': {
                    'parts': [{'text': self.persona}], #  "You are a helpful assistant"
                },
                "tools": [{'google_search': {}}],
            }
        }
        if self.ws:
            await self.ws.send(json.dumps(setup_msg))
            raw_response: bytes = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
            setup_response: Dict[str, Any] = json.loads(raw_response.decode("ascii"))
            print(f"Setup response: {json.dumps(setup_response, indent=2)}")
        
    async def process_text(self, text: str, voice_client: VoiceClient) -> None:
        async with self.lock:
            if self.processing:
                print("Already processing, skipping...")
                return
                
            self.processing = True
            audio_queue: asyncio.Queue[Optional[bytes]] = asyncio.Queue()
            
            try:
                msg: Dict[str, Any] = {
                    "client_content": {
                        "turn_complete": True,
                        "turns": [{"role": "user", "parts": [{"text": text}]}],
                    }
                }
                if self.ws:
                    await self.ws.send(json.dumps(msg))
                
                while True:
                    try:
                        raw_response: bytes = await asyncio.wait_for(self.ws.recv(), timeout=5.0) if self.ws else b""
                        response: Dict[str, Any] = json.loads(raw_response.decode("ascii"))
                        
                        if "error" in response:
                            print(f"Error in Gemini response: {response['error']}")
                            break

                        if "serverContent" in response:
                            if "modelTurn" in response["serverContent"]:
                                for part in response["serverContent"]["modelTurn"]["parts"]:
                                    if "inlineData" in part:
                                        b64data = part["inlineData"]["data"]
                                        if not b64data:
                                            continue

                                        audio_bytes = base64.b64decode(b64data)
                                        await audio_queue.put(audio_bytes)

                                        if not voice_client.is_playing():
                                            audio_source = QueuedStreamingPCMAudio(audio_queue)
                                            voice_client.play(audio_source, after=lambda e: print(f"Playback finished: {e}") if e else None)

                                if response["serverContent"].get("turnComplete"):
                                    await audio_queue.put(None)
                                    break
                                    
                    except asyncio.TimeoutError:
                        print("Timeout waiting for response")
                        break
                        
            except Exception as e:
                print(f"Error in process_text: {e}")
                traceback.print_exc()
            finally:
                self.processing = False