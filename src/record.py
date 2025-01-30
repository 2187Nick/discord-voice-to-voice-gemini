import asyncio
import traceback
import discord
import speech_recognition as sr
from typing import Optional
from src.gemini import GeminiWebSocket 
from discord.ext import voice_recv, commands

recognizer: sr.Recognizer = sr.Recognizer()

def convert_audio_to_text_using_google_speech(audio: sr.AudioData) -> str:
    print("Converting audio to text...")
    try:
        command_text: str = recognizer.recognize_google(audio)
        return command_text.lower()
    except sr.UnknownValueError:
        print("Speech recognition could not understand the audio")
        return "could_not_understand"
    except sr.RequestError as e:
        print(f"Could not request results from speech recognition service; {e}")
        return "service_error" 
    except Exception as e:
        print(f"Error in speech recognition: {e}")
        return "error" 

class AudioProcessor(voice_recv.AudioSink):
    def __init__(self, 
                 user: discord.User, 
                 channel: discord.TextChannel, 
                 bot: commands.Bot, 
                 gemini_ws: GeminiWebSocket) -> None:
        super().__init__()
        self.buffer: bytes = b""
        self.target_user: discord.User = user
        self.recording_active: bool = False
        self.channel: discord.TextChannel = channel
        self.bot: commands.Bot = bot
        self.gemini_ws: GeminiWebSocket = gemini_ws
        
    def wants_opus(self) -> bool:
        return False

    def write(self, user: Optional[discord.User], data: voice_recv.VoiceData) -> None:
        """Accumulate audio data only when recording is active."""
        if self.recording_active and data.pcm:
            if user == self.target_user:
                self.buffer += data.pcm

    @voice_recv.AudioSink.listener()
    def on_voice_member_speaking_start(self, member: discord.Member) -> None:
        print(f"User {member} started speaking.")

        if member == self.target_user:
            #print("Recording active.")
            # Stop any currently playing audio
            if self.voice_client and self.voice_client.is_playing():
                #print("Stopping current audio playback")
                self.voice_client.stop_playing()

            self.recording_active = True
    
    @voice_recv.AudioSink.listener()
    def on_voice_member_speaking_stop(self, member: discord.Member) -> None:
        print(f"User {member.name} stopped speaking.")
        if member == self.target_user:
            
            self.recording_active = False

            if self.buffer:

                try:
                    print("Audio capture stopped")
                    sample_rate = 48000  # Discord's sample rate
                    sample_width = 4      # 16-bit audio  Should this be 2

                    audio_data = sr.AudioData(self.buffer, sample_rate, sample_width)
                    #print("Audio capture done. Now convert it to text...")

                    wav_data = audio_data.get_wav_data()

                    # Check if audio is empty or just silence
                    if not wav_data or not wav_data.strip():
                        print("No words captured - audio appears to be silence")
                        self.buffer = b""
                        return
                    
                    # Check for minimum audio length (e.g., less than 0.3 seconds is likely too short for a word)
                    audio_length = len(self.buffer) / (sample_rate * sample_width)
                    if audio_length < 0.3:  # 300ms minimum
                        print("Audio too short - likely not a complete word")
                        self.buffer = b""
                        return
                    
                    self.buffer = b""

                    # Process the audio
                    if audio_data.get_wav_data().strip():
                        #print("Audio data is not empty")
                        result = convert_audio_to_text_using_google_speech(audio_data)
                        if result in ["could_not_understand", "service_error", "error"]:
                            # Handle the error based on the specific return value
                            if result == "could_not_understand":
                                future = asyncio.run_coroutine_threadsafe(
                                    self.channel.send("I couldn't understand you."),
                                    self.bot.loop
                                )
                            elif result == "service_error":
                                future = asyncio.run_coroutine_threadsafe(
                                    self.channel.send("I'm having trouble connecting to the speech service. Please try again in a moment."),
                                    self.bot.loop
                                )
                            else:
                                future = asyncio.run_coroutine_threadsafe(
                                    self.channel.send("Something went wrong. I'm ready to listen again."),
                                    self.bot.loop
                                )
                          
                            try:
                                # Will return as soon as message is sent, or raise TimeoutError after 5 seconds
                                future.result(timeout=5)  # This is non-blocking if future completes quickly
                            except Exception as e:
                                print(f"Error sending message: {e}")
                            
                            return
                        
                        print(f"Text: {result}")

                        # We use self.bot.loop to schedule the coroutine on Discord's event loop
                        asyncio.run_coroutine_threadsafe(self.gemini_ws.process_text(result, self.voice_client), self.bot.loop)

                except Exception as e:
                    print(f"Error processing audio: {e}")
                    traceback.print_exc()
            
    
    def cleanup(self) -> None:
        print("AudioSink cleanup complete.")