import os
import threading
import subprocess
import pyaudio
import time
from oci.config import from_file
from oci.ai_speech import AIServiceSpeechClient
from oci.ai_speech.models import (
    SynthesizeSpeechDetails, TtsOracleConfiguration,
    TtsOracleTts2NaturalModelDetails, TtsOracleSpeechSettings
)

class TextToSpeech:
    def __init__(self, compartment_id):
        self.endpoint = "https://speech.aiservice.us-phoenix-1.oci.oraclecloud.com" # Only phoenix region has TTS, for now
        self.compartment_id = os.getenv("COMPARTMENT_ID")
        self.voice_id = os.getenv("VOICE_ID") or "Annabelle"
        self.lock = threading.Lock()
        self.playing = False
        self.speech = None
    
    def set_speech_recognition(self, speech): 
        self.speech = speech
    
    def play(self, text, cooldown=1.0):
        # Skip empty text
        if not text or not text.strip() or not self.compartment_id: 
            return False
        
        # Need to mute mic during audio playback or we get feedback loop
        self.playing = True
        if self.speech:
            self.speech.muted = True
            print("🗣️ Mic muted for speech \n")
  
        # Print a preview of what we're saying
        print(f"🗣️ {text[:50]}...\n" if len(text) > 50 else f"🗣️ {text}\n")
        
        try:
            with self.lock:
                client = AIServiceSpeechClient(from_file(), service_endpoint=self.endpoint)
                
                # Playback speed isn't quite right. Fine with TTS1 but TTS2 is a bit slow, so we'll use SSML to speed it up
                request = SynthesizeSpeechDetails(
                    text=f"<speak><prosody rate='fast'>{text}</prosody></speak>", # Speed up speech rate
                    is_stream_enabled=True,
                    compartment_id=self.compartment_id,
                    configuration=TtsOracleConfiguration(
                        model_family="ORACLE",
                        model_details=TtsOracleTts2NaturalModelDetails(
                            model_name="TTS_2_NATURAL", 
                            voice_id=self.voice_id
                        ),
                        speech_settings=TtsOracleSpeechSettings(
                            text_type="SSML", # SSML, just adjust speech rate
                            sample_rate_in_hz=16000,
                            output_format="PCM",
                            speech_mark_types=[]
                        )
                    )
                )
                
                response = client.synthesize_speech(synthesize_speech_details=request)
                self._play_audio_stream(response)
                
        except Exception as e:
            print(f"⚠️ TTS failed: {e}")
            if self.speech:
                self.speech.muted = False
                print("🗣️ Mic unmuted (after TTS error)")
            return False
        finally:
            self.playing = False
            return True
    
    def _play_audio_stream(self, response):
        ffmpeg = subprocess.Popen(
            ['ffmpeg', '-i', 'pipe:0', '-f', 's16le', '-ar', '16000', '-ac', '1', 'pipe:1'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        
        # Start feeding thread - don't wait for it (even with this the response time is still not where I want it to be)
        threading.Thread(target=self._feed_audio, args=(ffmpeg, response), daemon=True).start()
        
        audio = pyaudio.PyAudio()
        stream = audio.open(format=pyaudio.paInt16, channels=1, rate=16000, output=True)
        
        print("▶️ Playing...\n")
        while chunk := ffmpeg.stdout.read(1024):
            stream.write(chunk)

        stream.stop_stream()
        stream.close()
        audio.terminate()
        print("✓ Done\n")
        
        # Unmute the mic after playback
        if self.speech:
            self.speech.muted = False
            print(f"🗣️ Mic unmuted (after playback)\n")
        
    def _feed_audio(self, ffmpeg, response):
        try:
            for chunk in response.data.iter_content(chunk_size=1024):
                if chunk:
                    ffmpeg.stdin.write(chunk)
                    ffmpeg.stdin.flush()
        except: 
            pass
        finally:
            try: 
                ffmpeg.stdin.close()
            except: 
                pass
