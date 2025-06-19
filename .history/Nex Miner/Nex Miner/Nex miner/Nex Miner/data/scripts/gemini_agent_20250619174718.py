--- START OF FILE Nex Miner/Nex Miner/Nex Miner/Nex miner/Nex Miner/data/scripts/gemini_agent.py ---
# data/scripts/gemini_agent.py
import google.generativeai as genai
import os
import json
import threading

class GeminiAgent:
    def __init__(self, api_key):
        # --- FIX: Check for API Key presence and fail gracefully ---
        if not api_key:
            raise ValueError("Gemini API Key not found or provided.")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.response = None
        self.is_thinking = False

    def get_threaded_response(self, prompt, is_directive=False):
        if self.is_thinking:
            return 
        
        self.is_thinking = True
        self.response = None 

        thread = threading.Thread(target=self._get_response, args=(prompt, is_directive))
        thread.start()

    def _get_response(self, prompt, is_directive):
        try:
            api_response = self.model.generate_content(prompt)
            # --- FIX: Directive JSON parsing logic ---
            if is_directive:
                try:
                    # Clean the string from markdown formatting that the AI sometimes adds
                    cleaned_text = api_response.text.strip().replace('```json', '').replace('```', '')
                    directive_data = json.loads(cleaned_text)
                    self.response = directive_data 
                except (json.JSONDecodeError, TypeError):
                    self.response = "The Mainframe's directive is corrupted. Try again."
            else:
                 self.response = api_response.text
        except Exception as e:
            self.response = f"Connection to Mainframe lost... (Error: {e})"
        finally:
            self.is_thinking = False