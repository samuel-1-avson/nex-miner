import pygame
import math
import json
from ..state import State
from ..text import Font
from ..gameplay_state import render_panel_9slice

class PlayerHubState(State):
    def __init__(self, game):
        super().__init__(game)
        self.tabs = ["STATS", "COMPENDIUM", "ARTIFACTS", "ORACLE"] # --- MODIFIED ---
        self.current_tab = 0
        self.panel_img = pygame.image.load(self.game.get_path('data', 'images', 'panel_9slice.png')).convert_alpha()
        self.font_title = Font(self.game.get_path('data', 'fonts', 'small_font.png'), (255, 230, 90))
        self.font_locked = Font(self.game.get_path('data', 'fonts', 'small_font.png'), (80, 80, 80))
        self.font_highlight = Font(self.game.get_path('data', 'fonts', 'small_font.png'), (255, 230, 90))
        self.artifact_selection_index = 0
        self.ai_input_text = ""
        self.ai_input_active = True
        self.master_clock = 0

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: self.game.pop_state()
                
                # Handle AI input if on the ORACLE tab
                if self.tabs[self.current_tab] == "ORACLE" and self.ai_input_active:
                    if event.key == pygame.K_RETURN:
                        self.ask_oracle()
                    elif event.key == pygame.K_BACKSPACE:
                        self.ai_input_text = self.ai_input_text[:-1]
                    elif event.unicode.isprintable(): # Accept printable characters
                        self.ai_input_text += event.unicode
                elif event.key == pygame.K_p and self.tabs[self.current_tab] == "ORACLE":
                    self.seek_prophecy()
                
                # Tab switching
                if event.key in [pygame.K_RIGHT, pygame.K_d, pygame.K_TAB]: self.current_tab = (self.current_tab + 1) % len(self.tabs)
                elif event.key in [pygame.K_LEFT, pygame.K_a]: self.current_tab = (self.current_tab - 1 + len(self.tabs)) % len(self.tabs)

                # --- NEW: Artifact Selection Logic ---
                if self.tabs[self.current_tab] == "ARTIFACTS":
                    unlocked_artifacts = [k for k, v in self.game.artifacts.items() if self.is_artifact_unlocked(k)]
                    if unlocked_artifacts:
                        if event.key in [pygame.K_DOWN, pygame.K_s]:
                            self.artifact_selection_index = (self.artifact_selection_index + 1) % len(unlocked_artifacts)
                        elif event.key in [pygame.K_UP, pygame.K_w]:
                            self.artifact_selection_index = (self.artifact_selection_index - 1 + len(unlocked_artifacts)) % len(unlocked_artifacts)
                        elif event.key == pygame.K_RETURN:
                            selected_key = unlocked_artifacts[self.artifact_selection_index]
                            # Unequip if already equipped, otherwise equip it
                            if self.game.save_data['artifacts']['equipped'] == selected_key:
                                self.game.save_data['artifacts']['equipped'] = None
                            else:
                                self.game.save_data['artifacts']['equipped'] = selected_key
                            self.game.write_save(self.game.save_data)
                            if 'upgrade' in self.game.sounds: self.game.sounds['upgrade'].play()

    def update(self):
        self.master_clock += 1
        self.check_artifact_unlocks()
        # If the AI agent is done thinking, make the input active again
        if self.game.ai_agent and not self.game.ai_agent.is_thinking:
            self.ai_input_active = True
            # If the last response was a prophecy, save it.
            if isinstance(self.game.ai_agent.response, dict):
                self.game.save_data['active_prophecy'] = self.game.ai_agent.response
                self.game.write_save(self.game.save_data)
                self.game.ai_agent.response = "A prophecy has been recorded for your next journey..." # User feedback

    def ask_oracle(self):
        if self.game.ai_agent and self.ai_input_text and not self.game.ai_agent.is_thinking:
            self.ai_input_active = False # Deactivate input while waiting
            context = f"You are the Oracle, a wise and slightly mysterious guide in the pixel-art roguelike game 'Cavyn: Recharged'. The player is asking you a question from within the game. Keep your answers concise (2-3 sentences), thematic, and helpful. Here is some data about the player's progress: {self.game.save_data['stats']}. Here is the player's question: "
            full_prompt = context + self.ai_input_text
            self.game.ai_agent.get_threaded_response(full_prompt)
            self.ai_input_text = "" # Clear input after sending

    def seek_prophecy(self):
        if not self.game.ai_agent or self.game.ai_agent.is_thinking or self.game.save_data['active_prophecy']: return
        self.ai_input_active = False
        prophecy_clarity = self.game.save_data['upgrades'].get('prophecy_clarity', 0) > 0
        prompt = f"You are the Oracle in the roguelike game 'Cavyn'. Generate a prophecy for the player's next run. The prophecy must be a valid JSON object with keys 'objective_type', 'value', 'reward_type', 'reward_value', and 'flavor_text'. Objective types can be 'collect_coins', 'destroy_tiles_dash', or 'reach_combo'. Reward types can be 'coins' (value should be 50-200) or 'item' (value can be 'shield', 'bomb', 'warp', etc.). {'Make the reward slightly better than normal because the player has Prophecy Clarity.' if prophecy_clarity else ''} Respond ONLY with the JSON object. Example: {{\"objective_type\": \"reach_combo\", \"value\": 15, \"reward_type\": \"item\", \"reward_value\": \"shield\", \"flavor_text\": \"A cascade of power awaits the swift...\"}}"
        self.game.ai_agent.get_threaded_response(prompt, is_prophecy=True)

    def render(self, surface):
        surface.fill((22, 19, 40))
        p_rect = pygame.Rect(10, 8, self.game.DISPLAY_SIZE[0] - 20, self.game.DISPLAY_SIZE[1] - 16)
        render_panel_9slice(surface, p_rect, self.panel_img, 8)
        
        tab_x = p_rect.left + 5
        for i, tab_name in enumerate(self.tabs):
            w = self.game.white_font.width(tab_name)
            font = self.font_title if i == self.current_tab else self.game.white_font
            font.render(tab_name, surface, (tab_x, p_rect.top + 5))
            tab_x += w + 15
        
        pygame.draw.line(surface, (200, 200, 220, 100), (p_rect.left+5, p_rect.top + 18), (p_rect.right - 5, p_rect.top + 18), 1)

        content_y = p_rect.top + 25
        if self.tabs[self.current_tab] == "STATS": self.render_stats(surface, p_rect.left + 15, content_y)
        elif self.tabs[self.current_tab] == "COMPENDIUM": self.render_compendium(surface, p_rect.left + 15, content_y)
        elif self.tabs[self.current_tab] == "ARTIFACTS": self.render_artifacts(surface, p_rect)
        elif self.tabs[self.current_tab] == "ORACLE": self.render_oracle(surface, p_rect, content_y)
            
        prompt = "Left/Right: Change Tab  -  Esc: Back"
        w = self.game.white_font.width(prompt); pos = (self.game.DISPLAY_SIZE[0]//2 - w//2, p_rect.bottom - 12)
        self.game.black_font.render(prompt, surface, (pos[0] + 1, pos[1] + 1)); self.game.white_font.render(prompt, surface, pos)

    def render_stats(self, surface, x, y):
        stats = self.game.save_data['stats']
        hours = math.floor(stats['play_time'] / 3600)
        minutes = math.floor((stats['play_time'] % 3600) / 60)
        seconds = math.floor(stats['play_time'] % 60)
        play_time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        stats_lines = {
            "Play Time:": play_time_str,
            "Total Coins Collected:": f"{stats['total_coins']}",
            "Runs Started:": f"{stats['runs_started']}",
            "High Score:": f"{self.game.save_data['high_score']}",
        }
        
        y_offset = y
        for label, value in stats_lines.items():
            self.font_title.render(label, surface, (x, y_offset))
            w = self.font_title.width(label)
            self.game.white_font.render(value, surface, (x + w + 5, y_offset))
            y_offset += 14

    def render_oracle(self, surface, p_rect, y):
        # Render the AI's response (or thinking message)
        response_box = pygame.Rect(p_rect.left + 10, y, p_rect.width - 20, 80)
        if not self.game.ai_agent:
            self.game.white_font.render("The Oracle is unavailable. (Check API Key)", surface, (response_box.x, response_box.y), line_width=response_box.width)
        elif self.game.ai_agent.is_thinking:
            msg = "The Oracle is consulting the cosmos..."
            if self.master_clock % 60 < 10: msg = "The Oracle is consulting the cosmos."
            elif self.master_clock % 60 < 20: msg = "The Oracle is consulting the cosmos.."
            self.game.white_font.render(msg, surface, (response_box.x, response_box.y), line_width=response_box.width)
        elif self.game.save_data.get('active_prophecy'):
             prophecy = self.game.save_data['active_prophecy']
             self.game.white_font.render(prophecy['flavor_text'], surface, (response_box.x, response_box.y), line_width=response_box.width)
        elif self.game.ai_agent.response:
            self.game.white_font.render(str(self.game.ai_agent.response), surface, (response_box.x, response_box.y), line_width=response_box.width)
        else:
            self.game.white_font.render("Ask a question, or press [P] to seek a Prophecy for your next run.", surface, (response_box.x, response_box.y), line_width=response_box.width)
        
        prophecy_prompt = "[P] Seek Prophecy"
        w = self.game.white_font.width(prophecy_prompt)
        prophecy_pos = (response_box.right - w - 5, response_box.bottom - 12)
        if not self.game.save_data.get('active_prophecy'):
            font = self.font_highlight if self.master_clock % 80 < 40 else self.game.white_font
            font.render(prophecy_prompt, surface, prophecy_pos)
            
        # Render the text input box
        input_box_y = p_rect.bottom - 25
        input_box = pygame.Rect(p_rect.left + 10, input_box_y, p_rect.width - 20, 12)
        pygame.draw.rect(surface, (0, 0, 1, 150), input_box)
        pygame.draw.rect(surface, (255, 255, 255, 50), input_box, 1)

        # Render input text with a blinking cursor
        render_text = self.ai_input_text
        if self.ai_input_active and self.master_clock % 60 < 30:
            render_text += '|'
        self.game.white_font.render(render_text, surface, (input_box.x + 4, input_box.y + 3))

    def is_artifact_unlocked(self, key):
        return key in self.game.save_data['artifacts']['unlocked']
    
    def check_artifact_unlocks(self):
        for key, artifact in self.game.artifacts.items():
            if not self.is_artifact_unlocked(key):
                req = artifact['unlock_req']
                if req['type'] == 'score' and self.game.save_data['high_score'] >= req['value']:
                    self.game.save_data['artifacts']['unlocked'].append(key)
                elif req['type'] == 'play_time' and self.game.save_data['stats']['play_time'] >= req['value']:
                    self.game.save_data['artifacts']['unlocked'].append(key)
                elif req['type'] == 'total_coins' and self.game.save_data['stats']['total_coins'] >= req['value']:
                    self.game.save_data['artifacts']['unlocked'].append(key)

    def render_artifacts(self, surface, p_rect):
        y = p_rect.top + 25
        unlocked_artifacts = [k for k, v in self.game.artifacts.items() if self.is_artifact_unlocked(k)]
        equipped = self.game.save_data['artifacts']['equipped']
        
        if not unlocked_artifacts:
            self.game.white_font.render("Unlock Artifacts by achieving milestones.", surface, (p_rect.left + 15, y))
            return

        for i, key in enumerate(unlocked_artifacts):
            artifact = self.game.artifacts[key]
            is_equipped = key == equipped
            is_selected = i == self.artifact_selection_index
            
            font = self.font_highlight if is_selected else self.game.white_font
            prefix = "> " if is_selected else ""
            suffix = " [EQUIPPED]" if is_equipped else ""

            font.render(f"{prefix}{artifact['name']}{suffix}", surface, (p_rect.left + 15, y))
            self.game.white_font.render(artifact['desc'], surface, (p_rect.left + 25, y+10), line_width=p_rect.width - 40)
            y += 30
            
    def render_compendium(self, surface, x, y):
        discovered = self.game.save_data['compendium']
        col1_y_offset = y
        self.font_title.render("Perks:", surface, (x, col1_y_offset)); col1_y_offset += 12
        col1_y_offset = self.render_compendium_list(surface, x, col1_y_offset, self.game.perks, discovered['perks'], 100)

        col2_y_offset = y
        col2_x = x + 120
        self.font_title.render("Curses:", surface, (col2_x, col2_y_offset)); col2_y_offset += 12
        col2_y_offset = self.render_compendium_list(surface, col2_x, col2_y_offset, self.game.curses, discovered['curses'], 100)

        col3_y_offset = y
        col3_x = x + 210
        self.font_title.render("Items:", surface, (col3_x, col3_y_offset)); col3_y_offset += 12
        col3_y_offset = self.render_compendium_list(surface, col3_x, col3_y_offset, self.game.item_icons, discovered['items'], 100)
        
    def render_compendium_list(self, surface, x, y, all_defs, discovered_keys, line_width):
        start_y = y
        for key in sorted(all_defs.keys()):
            font = self.game.white_font if key in discovered_keys else self.font_locked
            
            # --- THE FIX IS HERE ---
            # Check if the value is a dictionary (like for perks/curses) or something else (like a Surface for items)
            if isinstance(all_defs[key], dict):
                text = f"- {all_defs[key].get('name', key.replace('_', ' ').title())}" if key in discovered_keys else "- ???"
            else:
                # It's an item, so just format the key
                text = f"- {key.replace('_', ' ').title()}" if key in discovered_keys else "- ???"
            # --- END FIX ---
            
            font.render(text, surface, (x, y))
            y += 10
            if y > 150: # Wrap to next column (crude)
                y = start_y
                x += line_width + 10
        return y