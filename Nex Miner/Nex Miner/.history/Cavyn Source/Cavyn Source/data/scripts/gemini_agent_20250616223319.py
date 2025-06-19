# data/scripts/gemini_agent.py
import google.generativeai as genai
import os
import threading

class GeminiAgent:
    def __init__(self, api_key):
        # Configure the API key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
        self.response = None
        self.is_thinking = False

    def get_threaded_response(self, prompt):
        # Starts the API call in a new thread
        if self.is_thinking:
            return # Don't start a new request if one is in progress
        
        self.is_thinking = True
        self.response = None # Clear old response
        
        thread = threading.Thread(target=self._get_response, args=(prompt,))
        thread.start()

    def _get_response(self, prompt):
        # This is the function the thread will run
        try:
            api_response = self.model.generate_content(prompt)
            self.response = api_response.text
        except Exception as e:
            self.response = f"The cosmos are silent... (Error: {e})"
        finally:
            self.is_thinking = False

# In your Game class (Cavyn.py)
# from data.scripts.gemini_agent import GeminiAgent

class Game:
    def __init__(self):
        # ... your existing init code ...
        self.ai_agent = GeminiAgent(api_key="AIzaSyBsRGlo1wmmvBIfEzwII-zs2d6xxvopIpM") # Store your key securely