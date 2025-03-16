import asyncio
import pyaudio
import time
from oci.config import from_file
from oci_ai_speech_realtime import RealtimeSpeechClient, RealtimeSpeechClientListener
from oci.ai_speech.models import RealtimeParameters

SAMPLE_RATE = 16000
FORMAT = pyaudio.paInt16
CHANNELS = 1
FRAMES_PER_BUFFER = 1536

class Listener(RealtimeSpeechClientListener):
    def __init__(self, service):
        self.service = service
    
    def on_result(self, result):
        transcription = result["transcriptions"][0]["transcription"]
        is_final = result["transcriptions"][0]["isFinal"]
        
        # Only care about final results with actual text (streaming could be utilised to improve response time)
        # Save streaming feature for future update
        # Skip if muted - avoid speaker playing into mic!
        if is_final and transcription.strip() and not self.service.is_muted():
            print(f"🎤 {transcription}")
            asyncio.create_task(self.service.output_queue.put(transcription))
    
    def on_connect(self):
        print("🎤 Connected to speech API!\n")
        return super().on_connect()
    
    def on_error(self, error_message):
        print(f"🎤  Speech error: {error_message}")
        return super().on_error(error_message)
    
    # Required but not used
    def on_ack_message(self, msg): return super().on_ack_message(msg)
    def on_connect_message(self, msg): return super().on_connect_message(msg)
    def on_network_event(self, msg): return super().on_network_event(msg)

class SpeechRecognition:
    def __init__(self, compartment_id, region):
        self.compartment_id = compartment_id
        self.region = region
        self.audio_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()
        self.client = None
        self.muted = False
        self.unmute_time = 0
        self.shutdown = None
        self.listener = Listener(self)
    
    def mute(self, seconds=1.5):
        print(f"🎤 Mic muted for {seconds}s")
        self.muted = True
    
    def unmute(self): 
        self.muted = False
        print("🎤 Mic unmuted")
    
    def is_muted(self):
        return self.muted
    
    # Shortcuts for connecting to other components
    def set_output_queue(self, queue): self.output_queue = queue
    def set_shutdown_event(self, event): self.shutdown = event
    
    async def start(self):
        # Setup basic speech recognition params
        params = RealtimeParameters()
        params.language_code = "en-US"
        params.model_domain = params.MODEL_DOMAIN_GENERIC
        params.final_silence_threshold_in_ms = 2000
        params.encoding = f"audio/raw;rate={SAMPLE_RATE}"
        
        # Connect to Oracle API
        endpoint = f"wss://realtime.aiservice.{self.region}.oci.oraclecloud.com"
        self.client = RealtimeSpeechClient(
            config=from_file(),
            realtime_speech_parameters=params,
            listener=self.listener,
            service_endpoint=endpoint,
            compartment_id=self.compartment_id,
        )
        
        # Start sending audio in the background
        asyncio.create_task(self._send_audio())
        
        try:
            await self.client.connect()
            print("🎤 Speech recognition running!")
            
            # Just loop until shutdown
            while not (self.shutdown and self.shutdown.is_set()):
                await asyncio.sleep(1)
        except Exception as e:
            print(f"🎤 Error: {e}")
        finally:
            if self.client: 
                self.client.close()
    
    async def _send_audio(self):
        while self.client and not self.client.close_flag:
            if self.shutdown and self.shutdown.is_set(): 
                break
                
            try:
                if not self.is_muted():
                    data = await asyncio.wait_for(self.audio_queue.get(), timeout=0.1)
                    await self.client.send_data(data)
                else: 
                    while not self.audio_queue.empty():
                        try: 
                            self.audio_queue.get_nowait()
                        except: 
                            break
                    await asyncio.sleep(0.1)
            except: 
                await asyncio.sleep(0.01)
    
    async def stop(self):
        if self.client: 
            self.client.close()