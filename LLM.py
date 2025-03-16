import os
import json
import asyncio
from dotenv import load_dotenv
from oci.config import from_file
from oci.generative_ai_inference import GenerativeAiInferenceClient
from oci.generative_ai_inference.models import (
    ChatDetails, OnDemandServingMode, GenericChatRequest,
    UserMessage, TextContent, AssistantMessage
)

load_dotenv()
# This is overkill - we're doing streaming but the voicebot doesn't take advantage of it (yet)
# Streaming could be utilised to improve response time
class Conversation:
    def __init__(self, compartment_id=None):
        self.compartment_id = os.getenv("COMPARTMENT_ID")
        self.model_id = os.getenv("MODEL_ID") or "meta.llama-3.3-70b-instruct"
        self.messages = []
        self.client = GenerativeAiInferenceClient(from_file())
        self.input_queue = asyncio.Queue()
        self.running = False
        self.response_callback = None

        system_prompt = """You're a voice assistant. Be helpful, be conversational, ask lots of question.
        But keep your responses short. Speak in simple and informal language. Ensure you use commas and full stops.
        The text will be converted to audio, so don't use any special characters or markdown"""
        
        self.messages.insert(0, UserMessage(content=[TextContent(text=system_prompt)]))
    
    def set_response_callback(self, callback): 
        self.response_callback = callback
    
    def add_message(self, text, is_user=True):
        if not text or not text.strip(): return
        
        msg = UserMessage() if is_user else AssistantMessage()
        msg.content = [TextContent(text=text)]
        self.messages.append(msg)
    
    def queue_input(self, text):
        if text and text.strip():
            asyncio.run_coroutine_threadsafe(
                self.input_queue.put(text),
                asyncio.get_event_loop()
            )
    
    async def get_response(self, text):
        self.add_message(text, is_user=True)
        
        request = GenericChatRequest(
            messages=self.messages,
            api_format=GenericChatRequest.API_FORMAT_GENERIC,
            num_generations=1, max_tokens=4000,
            temperature=0.7, top_p=0.9,
            is_stream=True
        )
        
        chat = ChatDetails(
            serving_mode=OnDemandServingMode(model_id=self.model_id),
            compartment_id=self.compartment_id,
            chat_request=request
        )
        
        response_text = await self._streaming(chat, request)
                
        if response_text:
            self.add_message(response_text, is_user=False)
            if self.response_callback:
                self.response_callback(response_text)
        else:
            error_msg = "Sorry, my 🧠 stopped working. Try again!"
            self.add_message(error_msg, is_user=False)
            if self.response_callback:
                self.response_callback(error_msg)
            return error_msg
                
        return response_text
    
    async def _streaming(self, chat, request):
        try:
            response = self.client.chat(chat)
            full_text = ""
            
            if hasattr(response.data, 'events'):
                for event in response.data.events():
                    try:
                        data = json.loads(event.data)
                        if 'finishReason' in data: 
                            break
                        
                        if 'message' in data and 'content' in data['message']:
                            for item in data['message']['content']:
                                if isinstance(item, dict) and item.get('type') == 'TEXT':
                                    chunk = item.get('text', '')
                                    print(chunk, end='', flush=True)
                                    full_text += chunk
                    except: 
                        pass # Ignore parsing errors
                    
                print()

                return full_text
        except Exception as e:
            print(f"🧠 LLM error: {e}")
        return None
    
    async def start_processing(self):
        if self.running: 
            return
        
        self.running = True
        print("🧠 LLM ready for chat!\n")
        
        while self.running:
            try:
                text = await self.input_queue.get()
                if text and text.strip():
                    print(f"🧠 Processing: {text}\n")
                    await self.get_response(text)
            except asyncio.CancelledError: 
                break
            except Exception as e:
                print(f"🧠 Error: {e}")
        
        print("🧠 LLM stopped\n")
    
    async def stop(self): 
        self.running = False
