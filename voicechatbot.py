import asyncio
import threading
import pyaudio
from dotenv import load_dotenv
import os

from STT import SpeechRecognition, SAMPLE_RATE, FORMAT, CHANNELS, FRAMES_PER_BUFFER
from TTS import TextToSpeech
from LLM import Conversation

load_dotenv()
COMPARTMENT_ID = os.getenv("COMPARTMENT_ID")
REGION = os.getenv("REGION") or "us-phoenix-1"
shutdown = threading.Event()

class VoiceChatbot:
    def __init__(self):
        self.speech = SpeechRecognition(COMPARTMENT_ID, REGION)
        self.tts = TextToSpeech(COMPARTMENT_ID)
        self.conversation = Conversation(COMPARTMENT_ID)
        self.audio = None
        self.stream = None

        self.speech.set_shutdown_event(shutdown)
        self.speech.set_output_queue(asyncio.Queue())
        self.tts.set_speech_recognition(self.speech)
        self.conversation.set_response_callback(lambda text: self.tts.play(text))
    
    async def run(self):
        print("🤖 Starting voice chatbot...\n")
        
        try:
            # Setup audio input
            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                format=FORMAT, channels=CHANNELS, rate=SAMPLE_RATE,
                input=True, frames_per_buffer=FRAMES_PER_BUFFER,
                stream_callback=lambda in_data, *args: 
                    self._audio_callback(in_data) or (None, pyaudio.paContinue)
            )
            self.stream.start_stream()
            
            asyncio.create_task(self.conversation.start_processing())
            asyncio.create_task(self._forward_transcripts())
            
            self.tts.play("Say something!") # Say hello
            
            await self.speech.start() # Run speech recognition (blocks until shutdown)
            
        except Exception as e:
            print(f"🤖 Error: {e}")
        finally:
            if self.stream: 
                self.stream.stop_stream()
                self.stream.close()
            if self.audio: 
                self.audio.terminate()
    
    def _audio_callback(self, in_data):
        if not self.speech.is_muted(): # Skip if we're speaking to avoid feedback
            self.speech.audio_queue.put_nowait(in_data)
    
    async def _forward_transcripts(self):
        while not shutdown.is_set():
            try:
                transcript = await self.speech.output_queue.get()
                self.conversation.queue_input(transcript)
            except:
                await asyncio.sleep(0.1)

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 WEEKEND VOICE CHATBOT 🤖")
    print("=" * 50)
    
    try:
        asyncio.run(VoiceChatbot().run())
    except KeyboardInterrupt:
        print("🤖 Shutting down...")
        shutdown.set()
    except Exception as e:
        print(f"🤖 Fatal error: {e}")
