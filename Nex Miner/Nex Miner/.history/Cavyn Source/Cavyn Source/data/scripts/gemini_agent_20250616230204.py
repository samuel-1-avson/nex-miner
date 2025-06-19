# data/scripts/gemini_agent.py
import google.generativeai as genai
import os
import json
import threading

class GeminiAgent:
    def __init__(self, api_key):
        # Configure the API key
        genai.configure(api_key=api_key)
        # --- MODIFIED: Use the recommended 'gemini-1.5-flash' model
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.response = None
        self.is_thinking = False

    def get_threaded_response(self, prompt, is_prophecy=False):
        # Starts the API call in a new thread
        if self.is_thinking:
            return # Don't start a new request if one is in progress
        
        self.is_thinking = True
        self.response = None # Clear old response

        thread = threading.Thread(target=self._get_response, args=(prompt, is_prophecy))
        thread.start()

    def _get_response(self, prompt, is_prophecy):
        # This is the function the thread will run
        try:
            api_response = self.model.generate_content(prompt)
            # --- NEW: Prophecy JSON parsing logic ---
            if is_prophecy:
                try:
                    # The model might return the JSON string within markdown backticks
                    cleaned_text = api_response.text.strip().replace('```json', '').replace('```', '')
                    prophecy_data = json.loads(cleaned_text)
                    # This response is handled differently, it's saved directly
                    # to game.save_data['active_prophecy'] in PlayerHubState
                    self.response = prophecy_data 
                except (json.JSONDecodeError, TypeError):
                    self.response = "The Oracle's vision is clouded. Try again."
            else:
                 self.response = api_response.text
            # ---
        except Exception as e:
            self.response = f"The cosmos are silent... (Error: {e})"
        finally:
            self.is_thinking = False