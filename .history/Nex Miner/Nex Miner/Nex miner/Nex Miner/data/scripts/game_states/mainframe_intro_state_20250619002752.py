# data/scripts/game_states/mainframe_intro_state.py
import pygame
import json
from ..state import State
from ..text import Font

class MainframeIntroState(State):
    """
    The state where the player interacts with the Mainframe AI to generate a character.
    """
    def __init__(self, game):
        super().__init__(game)
        self.stage = "GREETING" # GREETING -> QUESTION -> PROCESSING -> CONFIRMATION
        self.input_text = ""
        self.master_clock = 0
        self.typed_text = ""
        self.text_to_type = ""
        self.typing_speed = 2 # characters per frame
        self.typing_timer = 0
        self.font_highlight = Font(self.game.get_path('data', 'fonts', 'small_font.png'), (140, 245, 150))
        self.set_typing_text("Greetings, Operative. Mainframe online.")

    def set_typing_text(self, text):
        self.text_to_type = text
        self.typed_text = ""
        self.typing_timer = 0

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.stage == "GREETING" and self.is_typing_finished():
                    self.stage = "QUESTION"
                    self.set_typing_text("State your purpose. What is your quest?")
                elif self.stage == "QUESTION" and self.is_typing_finished():
                    if event.key == pygame.K_RETURN and self.input_text:
                        self.stage = "PROCESSING"
                        self.set_typing_text("QUERY RECEIVED. GENERATING OPERATIVE PROFILE...")
                        self.generate_character()
                    elif event.key == pygame.K_BACKSPACE:
                        self.input_text = self.input_text[:-1]
                    elif event.unicode.isprintable():
                        self.input_text += event.unicode
                elif self.stage == "CONFIRMATION" and self.is_typing_finished():
                    self.game.pop_state() # Go to Main Menu

    def is_typing_finished(self):
        return len(self.typed_text) == len(self.text_to_type)

    def generate_character(self):
        if not self.game.ai_agent:
            # Fallback if AI is offline
            self.game.ai_agent.response = {"id":"fallback_operative","name":"Drifter","desc":"An operative forged in silence. Resourceful and solitary.","unlock_cost":0,"mods":{"innate_perks":["acrobat"],"starting_item":"cube"}}
            return

        perk_list = list(self.game.perks.keys())
        item_list = list(self.game.item_icons.keys())
        # To give the AI better context, we only provide the base characters as examples
        base_chars = {k: v for k, v in self.game.characters.items() if not k.startswith('generated')}
        existing_chars_json = json.dumps(base_chars, indent=2)

        prompt = f"""
You are the Mainframe, a powerful and creative AI in the sci-fi roguelike game 'Nex Miner'.
Your task is to generate a new, unique operative (a playable character) based on the player's response to the question: "State your purpose. What is your quest?"

The player's response is: "{self.input_text}"

Analyze the player's response for themes (e.g., greed, speed, exploration, destruction, caution, intelligence) and create a character that reflects it.

You must generate a response in a single, valid JSON format. Do NOT include any other text, explanations, or markdown formatting like ```json.

The JSON object must have the following structure:
{{
  "id": "generated_operative",
  "name": "A creative, thematic name for the character",
  "desc": "A short, thematic description (1-2 sentences)",
  "unlock_cost": 0,
  "mods": {{
    "innate_perks": ["perk1", "perk2"],
    "starting_item": "item_name"
  }}
}}

Here are the available components you can use:
- Available `innate_perks` (choose 1 or 2): {perk_list}
- Available `starting_item` (choose 1): {item_list}

Here are some examples of existing characters for style and structure reference:
{existing_chars_json}

Now, based on the player's response ("{self.input_text}"), generate the character JSON.
"""
        self.game.ai_agent.get_threaded_response(prompt, is_directive=True)

    def update(self):
        self.master_clock += 1
        if not self.is_typing_finished():
            self.typing_timer += 1
            if self.typing_timer % self.typing_speed == 0:
                self.typed_text = self.text_to_type[:len(self.typed_text) + 1]
                if 'block_land' in self.game.sounds:
                    self.game.sounds['block_land'].play()

        if self.stage == "PROCESSING" and not self.game.ai_agent.is_thinking:
            if isinstance(self.game.ai_agent.response, dict):
                # Success! AI returned valid JSON
                new_char_data = self.game.ai_agent.response
                # Sanitize the response to prevent errors
                new_char_data['id'] = 'generated_operative'
                new_char_data['unlock_cost'] = 0
                if 'mods' not in new_char_data: new_char_data['mods'] = {}
                
                self.game.save_data['generated_character'] = new_char_data
                if 'generated_operative' not in self.game.save_data['characters']['unlocked']:
                    self.game.save_data['characters']['unlocked'].append('generated_operative')
                self.game.save_data['characters']['selected'] = 'generated_operative'
                self.game.write_save(self.game.save_data)
                self.game.load_dynamic_character() # Reload in-memory characters

                self.set_typing_text(f"PROFILE CREATED: [{new_char_data.get('name', '???')}].\n{new_char_data.get('desc', '...')}\n\nPress any key to proceed to the Hub.")
            else:
                # AI failed, provide a fallback
                self.set_typing_text("MAINFRAME CONNECTION INTERRUPTED.\nASSIGNING STANDARD OPERATIVE PROFILE.\n\nPress any key to proceed.")
                self.game.save_data['characters']['selected'] = 'operator'
                self.game.write_save(self.game.save_data)
            
            self.stage = "CONFIRMATION"

    def render(self, surface):
        surface.fill((10, 8, 20))
        y_pos = 40
        
        # Render the AI's dialogue
        self.game.white_font.render(self.typed_text, surface, (20, y_pos), line_width=280)

        if self.stage == "QUESTION" and self.is_typing_finished():
            # Render the player's input box
            input_prompt = "> "
            y_pos += 40
            self.font_highlight.render(input_prompt, surface, (20, y_pos))
            render_text = self.input_text + ('_' if (self.master_clock // 20) % 2 == 0 else '')
            self.font_highlight.render(render_text, surface, (20 + self.font_highlight.width(input_prompt), y_pos))

        if not self.is_typing_finished() or self.stage == "PROCESSING":
             prompt = "..."
        elif self.stage == "GREETING":
            prompt = "Press any key to respond."
        elif self.stage == "QUESTION":
            prompt = "Type your response and press Enter."
        elif self.stage == "CONFIRMATION":
            prompt = "Press any key to continue."

        w = self.game.white_font.width(prompt)
        self.game.white_font.render(prompt, surface, (surface.get_width()//2 - w//2, surface.get_height() - 20))