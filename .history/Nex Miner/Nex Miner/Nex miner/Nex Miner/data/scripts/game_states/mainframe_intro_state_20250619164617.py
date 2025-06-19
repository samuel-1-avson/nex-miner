# data/scripts/game_states/mainframe_intro_state.py
import pygame
import json
import random
from ..state import State
from ..text import Font
from .main_menu_state import MainMenuState

class MainframeIntroState(State):
    """
    The state where the player interacts with the Mainframe AI to generate a character.
    Reworked for a more advanced "tech" aesthetic.
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
        
        # --- UI & Fonts ---
        font_path = self.game.get_path('data', 'fonts', 'small_font.png')
        self.font_main = Font(font_path, (140, 245, 250)) # Bright Cyan
        self.font_dim = Font(font_path, (20, 80, 85))   # Dark Cyan for background elements
        self.font_red = Font(font_path, (255, 60, 60))
        self.font_green = Font(font_path, (60, 255, 60))
        self.font_blue = Font(font_path, (60, 60, 255))
        
        # --- Background Effects ---
        self.scanline_surface = pygame.Surface(self.game.DISPLAY_SIZE, pygame.SRCALPHA)
        for y in range(0, self.game.DISPLAY_SIZE[1], 2):
            pygame.draw.line(self.scanline_surface, (0, 10, 15, 80), (0, y), (self.game.DISPLAY_SIZE[0], y), 1)

        self.bg_elements = []
        for _ in range(30): # Generate some random background tech-text
             self.create_bg_element()

        # --- Initial Text & Sound Setup ---
        self.set_typing_text("MAINFRAME OS v2.1 -- CONNECTED.\nAWAITING OPERATIVE PROTOCOLS...")

    def create_bg_element(self):
        text_type = random.choice(['hex', 'coords', 'status'])
        text = ""
        if text_type == 'hex':
            text = f"0x{random.randint(0, 0xFFFFFFFF):08X}"
        elif text_type == 'coords':
            text = f"{random.randint(0, 999)}:{random.randint(0, 999)}:{random.randint(0, 999)}"
        else:
            text = random.choice(["SYNC", "OK", "ACK", "TX", "RX", "IDLE"])
            
        pos = [random.randint(0, self.game.DISPLAY_SIZE[0]), random.randint(0, self.game.DISPLAY_SIZE[1])]
        life = random.randint(120, 300)
        self.bg_elements.append([text, pos, life])


    def set_typing_text(self, text):
        self.text_to_type = text
        self.typed_text = ""
        self.typing_timer = 0

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.stage == "GREETING" and self.is_typing_finished():
                    self.stage = "QUESTION"
                    self.set_typing_text("State your core directive.")
                    if 'upgrade' in self.game.sounds: self.game.sounds['upgrade'].play()

                elif self.stage == "QUESTION" and self.is_typing_finished():
                    if event.key == pygame.K_RETURN and self.input_text:
                        self.stage = "PROCESSING"
                        self.set_typing_text("QUERY RECEIVED. FABRICATING OPERATIVE PROFILE...")
                        if 'upgrade' in self.game.sounds: self.game.sounds['upgrade'].play()
                        self.generate_character()
                    elif event.key == pygame.K_BACKSPACE:
                        self.input_text = self.input_text[:-1]
                        if 'shoot' in self.game.sounds: self.game.sounds['shoot'].play()
                    elif event.unicode.isprintable() and len(self.input_text) < 50:
                        self.input_text += event.unicode
                        if 'shoot' in self.game.sounds: self.game.sounds['shoot'].play()

                elif self.stage == "CONFIRMATION" and self.is_typing_finished():
                    self.game.replace_state(MainMenuState(self.game))
                    if 'upgrade' in self.game.sounds: self.game.sounds['upgrade'].play()

    def is_typing_finished(self):
        return len(self.typed_text) == len(self.text_to_type)

    def generate_character(self):
        if not self.game.ai_agent:
            self.game.ai_agent.response = {"id":"fallback_operative","name":"Drifter","desc":"An operative forged in silence. Resourceful and solitary.","unlock_cost":0,"mods":{"innate_perks":["acrobat"],"starting_item":"cube"}}
            return

        perk_list = list(self.game.perks.keys())
        item_list = list(self.game.item_icons.keys())
        base_chars = {k: v for k, v in self.game.characters.items() if not k.startswith('generated')}
        existing_chars_json = json.dumps(base_chars, indent=2)
        prompt = f"""
You are the Mainframe, a powerful and creative AI in the sci-fi roguelike game 'Nex Miner'.
Your task is to generate a new, unique operative (a playable character) based on the player's response to the question: "State your core directive."
The player's response is: "{self.input_text}"
Analyze the player's response for themes (e.g., greed, speed, exploration, destruction, caution, intelligence) and create a character that reflects it.
You must generate a response in a single, valid JSON format. Do NOT include any other text, explanations, or markdown formatting like ```json.
The JSON object must have the following structure:
{{
  "id": "generated_operative",
  "name": "A creative, thematic name for the character",
  "desc": "A short, thematic description (1-2 sentences)",
  "unlock_cost": 0,
  "mods": {{ "innate_perks": ["perk1", "perk2"], "starting_item": "item_name" }}
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
                if 'coin' in self.game.sounds and self.master_clock % 2 == 0: self.game.sounds['coin'].play()

        for i, element in sorted(enumerate(self.bg_elements), reverse=True):
            element[2] -= 1
            if element[2] <= 0:
                self.bg_elements.pop(i)
                self.create_bg_element()

        if self.stage == "PROCESSING" and not self.game.ai_agent.is_thinking:
            if isinstance(self.game.ai_agent.response, dict):
                new_char_data = self.game.ai_agent.response
                new_char_data['id'] = 'generated_operative'
                new_char_data['unlock_cost'] = 0
                if 'mods' not in new_char_data: new_char_data['mods'] = {}
                
                self.game.save_data['generated_character'] = new_char_data
                if 'generated_operative' not in self.game.save_data['characters']['unlocked']: self.game.save_data['characters']['unlocked'].append('generated_operative')
                self.game.save_data['characters']['selected'] = 'generated_operative'
                self.game.write_save(self.game.save_data)
                self.game.load_dynamic_character()
                self.set_typing_text(f"PROFILE FABRICATED: [{new_char_data.get('name', '???').upper()}].\n{new_char_data.get('desc', '...')}\n\nPRESS ANY KEY TO INITIALIZE.")
            else:
                self.set_typing_text("MAINFRAME CONNECTION INTERRUPTED.\nASSIGNING STANDBY OPERATIVE PROFILE: [Drifter].\n\nPRESS ANY KEY TO INITIALIZE.")
                fallback_char = {"id":"generated_operative","name":"Drifter","desc":"An operative forged in silence. Resourceful and solitary.","unlock_cost":0,"mods":{"innate_perks":["acrobat"],"starting_item":"cube"}}
                self.game.save_data['generated_character'] = fallback_char
                if 'generated_operative' not in self.game.save_data['characters']['unlocked']: self.game.save_data['characters']['unlocked'].append('generated_operative')
                self.game.save_data['characters']['selected'] = 'generated_operative'
                self.game.write_save(self.game.save_data)
                self.game.load_dynamic_character()
            
            self.stage = "CONFIRMATION"

    def render_glitchy_text(self, surface, text, pos, font, scale=1):
        x, y = pos
        # Render chromatic aberration effect by drawing offset text in R, G, B
        glitch_offset = int(self.master_clock/2) % 4 - 2
        self.font_red.render(text, surface, (x + glitch_offset, y), scale=scale)
        self.font_green.render(text, surface, (x, y + glitch_offset), scale=scale)
        self.font_blue.render(text, surface, (x - glitch_offset, y), scale=scale)
        # Render the main text on top
        font.render(text, surface, (x, y), scale=scale)

    def render(self, surface):
        surface.fill((2, 4, 16)) # Deep Navy Blue
        
        # Render dynamic background
        self.render_background_effects(surface)
        
        # Main dialogue rendering
        self.render_dialogue(surface)

        # Bottom prompt
        self.render_footer_prompt(surface)
        
        # Scanline overlay
        surface.blit(self.scanline_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    def render_background_effects(self, surface):
        # Grid
        grid_color = (10, 30, 45, 100)
        for x in range(0, self.game.DISPLAY_SIZE[0], 16):
            pygame.draw.line(surface, grid_color, (x, 0), (x, self.game.DISPLAY_SIZE[1]))
        for y in range(0, self.game.DISPLAY_SIZE[1], 16):
            pygame.draw.line(surface, grid_color, (0, y), (self.game.DISPLAY_SIZE[0], y))
        
        # Random background text
        for text, pos, life in self.bg_elements:
            alpha = min(255, life) * 0.4
            self.font_dim.color = (self.font_dim.color[0], self.font_dim.color[1], self.font_dim.color[2], alpha)
            self.font_dim.render(text, surface, pos)
        
        # Flickering Corner Brackets
        if self.master_clock % 20 > 5:
            corner_size = 8
            self.font_dim.render('[', surface, (4,2))
            self.font_dim.render(']', surface, (surface.get_width()-10, 2))
            self.font_dim.render('[', surface, (4, surface.get_height()-12))
            self.font_dim.render(']', surface, (surface.get_width()-10, surface.get_height()-12))
            

    def render_dialogue(self, surface):
        text_pos = [20, 40]
        # Custom render for words with glitch effects
        words = self.typed_text.split(' ')
        line_width_limit = 280
        space_width = self.font_main.width(' ')
        current_line_width = 0

        for word in words:
            # Handle newline chars
            if '\n' in word:
                parts = word.split('\n')
                for i, part in enumerate(parts):
                    self.render_word(surface, part, text_pos)
                    text_pos[0] += self.font_main.width(part) + space_width
                    if i < len(parts) - 1:
                        text_pos[0] = 20
                        text_pos[1] += self.font_main.line_height + 5
                        current_line_width = 0
                continue
            
            word_width = self.font_main.width(word)
            if current_line_width + word_width > line_width_limit:
                text_pos[0] = 20
                text_pos[1] += self.font_main.line_height + 5
                current_line_width = 0
            
            self.render_word(surface, word, text_pos)
            text_pos[0] += word_width + space_width
            current_line_width += word_width + space_width
            

        # Render input box if in QUESTION stage
        if self.stage == "QUESTION" and self.is_typing_finished():
            input_pos_y = text_pos[1] + 20
            input_prompt = "INPUT_QUERY:> "
            self.font_main.render(input_prompt, surface, (20, input_pos_y))
            
            # Text being typed by user
            cursor_char = '█' if (self.master_clock // 15) % 2 == 0 else '_'
            render_text = self.input_text + cursor_char
            self.font_main.render(render_text, surface, (20 + self.font_main.width(input_prompt), input_pos_y))

        if self.stage == "PROCESSING":
            y_offset = surface.get_height()//2
            processing_status = [
                "//: PARSING SEMANTICS...",
                "//: CROSS-REFERENCING PERK MATRIX...",
                "//: SIMULATING COMBAT VIABILITY...",
                "//: CALIBRATING MODULE AFFINITY...",
                "//: FABRICATING PROFILE..."
            ][(self.master_clock // 60) % 5]
            w = self.font_main.width(processing_status)
            self.font_main.render(processing_status, surface, (surface.get_width()//2-w//2, y_offset))
            
            bar_w = (self.master_clock % 300 / 300) * 150
            bar_rect = pygame.Rect(surface.get_width()//2 - 75, y_offset+15, bar_w, 5)
            pygame.draw.rect(surface, self.font_main.color, bar_rect)
            pygame.draw.rect(surface, (255,255,255,100), bar_rect, 1)

    def render_word(self, surface, word, pos):
        # If the word is a special "glitchy" word, use the custom renderer
        if word in ["MAINFRAME", "FABRICATING", "PROFILE"]:
            self.render_glitchy_text(surface, word, pos, self.font_main)
        else:
            self.font_main.render(word, surface, pos)
            
    def render_footer_prompt(self, surface):
        if self.is_typing_finished():
            prompt = ""
            if self.stage == "GREETING": prompt = "EXECUTE (Enter)"
            elif self.stage == "QUESTION": prompt = "SUBMIT QUERY (Enter)"
            elif self.stage == "CONFIRMATION": prompt = "INITIALIZE (Enter)"

            if prompt:
                w = self.font_main.width(prompt)
                self.font_main.render(prompt, surface, (surface.get_width()//2 - w//2, surface.get_height() - 20))