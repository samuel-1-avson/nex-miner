import pygame
import math
import json
from ..state import State
from ..text import Font
from ..gameplay_state import render_panel_9slice

class PlayerHubState(State):
    def __init__(self, game):
        super().__init__(game)
        self.tabs = ["STATS", "COMPENDIUM", "ARTIFACTS", "ORACLE"]
        self.current_tab = 0
        self.panel_img = pygame.image.load(self.game.get_path('data', 'images', 'panel_9slice.png')).convert_alpha()
        self.font_title = Font(self.game.get_path('data', 'fonts', 'small_font.png'), (255, 230, 90))
        self.font_locked = Font(self.game.get_path('data', 'fonts', 'small_font.png'), (80, 80, 80))
        self.font_highlight = Font(self.game.get_path('data', 'fonts', 'small_font.png'), (255, 230, 90))
        self.artifact_selection_index = 0
        self.ai_input_text = ""
        self.ai_input_active = True
        self.master_clock = 0

        # Compendium navigation
        self.compendium_selection_index = 0
        self.combined_compendium = []
        # Create a unified list for easier navigation
        for key in sorted(self.game.perks.keys()): self.combined_compendium.append(('perk', key))
        for key in sorted(self.game.curses.keys()): self.combined_compendium.append(('curse', key))
        for key in sorted(self.game.item_icons.keys()): self.combined_compendium.append(('item', key))


    def enter_state(self):
        super().enter_state()
        # Clear notifications for the starting tab
        self.clear_current_tab_notification()

    def clear_current_tab_notification(self):
        """Helper to clear notifications for the tab we are on."""
        tab_name = self.tabs[self.current_tab]
        if tab_name == "ARTIFACTS":
            self.game.clear_notification('artifacts')
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: self.game.pop_state()
                
                is_on_oracle = self.tabs[self.current_tab] == "ORACLE"
                is_on_artifacts = self.tabs[self.current_tab] == "ARTIFACTS"
                is_on_compendium = self.tabs[self.current_tab] == "COMPENDIUM"

                # Tab switching
                if event.key in [pygame.K_RIGHT, pygame.K_d, pygame.K_TAB]:
                    self.current_tab = (self.current_tab + 1) % len(self.tabs)
                    self.clear_current_tab_notification()
                elif event.key in [pygame.K_LEFT, pygame.K_a]:
                    self.current_tab = (self.current_tab - 1 + len(self.tabs)) % len(self.tabs)
                    self.clear_current_tab_notification()

                # Handle AI input if on the ORACLE tab
                if is_on_oracle and self.ai_input_active:
                    if event.key == pygame.K_RETURN: self.ask_oracle()
                    elif event.key == pygame.K_BACKSPACE: self.ai_input_text = self.ai_input_text[:-1]
                    elif event.unicode.isprintable(): self.ai_input_text += event.unicode
                elif is_on_oracle and event.key == pygame.K_p: self.seek_prophecy()
                
                # Artifact Selection Logic
                if is_on_artifacts:
                    unlocked_artifacts = [k for k, v in self.game.artifacts.items() if self.is_artifact_unlocked(k)]
                    if unlocked_artifacts:
                        if event.key in [pygame.K_DOWN, pygame.K_s]: self.artifact_selection_index = (self.artifact_selection_index + 1) % len(unlocked_artifacts)
                        elif event.key in [pygame.K_UP, pygame.K_w]: self.artifact_selection_index = (self.artifact_selection_index - 1 + len(unlocked_artifacts)) % len(unlocked_artifacts)
                        elif event.key == pygame.K_RETURN:
                            selected_key = unlocked_artifacts[self.artifact_selection_index]
                            if self.game.save_data['artifacts']['equipped'] == selected_key: self.game.save_data['artifacts']['equipped'] = None
                            else: self.game.save_data['artifacts']['equipped'] = selected_key
                            self.game.write_save(self.game.save_data); self.game.sounds['artifact_equip'].play()

                # Compendium Navigation
                if is_on_compendium:
                    if event.key in [pygame.K_DOWN, pygame.K_s]: self.compendium_selection_index = min(self.compendium_selection_index + 1, len(self.combined_compendium) - 1)
                    elif event.key in [pygame.K_UP, pygame.K_w]: self.compendium_selection_index = max(0, self.compendium_selection_index - 1)

    def update(self):
        self.master_clock += 1
        self.check_artifact_unlocks()
        if self.game.ai_agent and not self.game.ai_agent.is_thinking:
            self.ai_input_active = True
            if isinstance(self.game.ai_agent.response, dict):
                self.game.save_data['active_prophecy'] = self.game.ai_agent.response
                self.game.write_save(self.game.save_data)
                self.game.ai_agent.response = "A prophecy has been recorded for your next journey..."

    def ask_oracle(self):
        if self.game.ai_agent and self.ai_input_text and not self.game.ai_agent.is_thinking:
            self.ai_input_active = False
            context = f"You are the Oracle, a wise and slightly mysterious guide in the pixel-art roguelike game 'Cavyn: Recharged'. The player is asking you a question from within the game. Keep your answers concise (2-3 sentences), thematic, and helpful. Here is some data about the player's progress: {self.game.save_data['stats']}. Here is the player's question: "
            full_prompt = context + self.ai_input_text
            self.game.ai_agent.get_threaded_response(full_prompt)
            self.ai_input_text = ""

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
            
            # Render notification on tab
            if tab_name == "ARTIFACTS" and 'artifacts' in self.game.unlock_notifications:
                self.highlight_font.render('!', surface, (tab_x + w + 2, p_rect.top + 5))
                
            tab_x += w + 15
        
        pygame.draw.line(surface, (200, 200, 220, 100), (p_rect.left+5, p_rect.top + 18), (p_rect.right - 5, p_rect.top + 18), 1)

        content_y = p_rect.top + 25
        if self.tabs[self.current_tab] == "STATS": self.render_stats(surface, p_rect, content_y)
        elif self.tabs[self.current_tab] == "COMPENDIUM": self.render_compendium(surface, p_rect, content_y)
        elif self.tabs[self.current_tab] == "ARTIFACTS": self.render_artifacts(surface, p_rect)
        elif self.tabs[self.current_tab] == "ORACLE": self.render_oracle(surface, p_rect, content_y)
            
        prompt = "Up/Down: Select - Left/Right: Change Tab - Esc: Back"
        w = self.game.white_font.width(prompt); pos = (self.game.DISPLAY_SIZE[0]//2 - w//2, p_rect.bottom - 12)
        self.game.black_font.render(prompt, surface, (pos[0] + 1, pos[1] + 1)); self.game.white_font.render(prompt, surface, pos)

    def render_stats(self, surface, p_rect, y):
        x = p_rect.left + 15
        stats = self.game.save_data['stats']
        hours, rem = divmod(stats['play_time'], 3600)
        minutes, seconds = divmod(rem, 60)
        play_time_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        stats_lines = {
            "Play Time:": play_time_str, "Total Coins Collected:": f"{stats['total_coins']}",
            "Runs Started:": f"{stats['runs_started']}", "High Score:": f"{self.game.save_data['high_score']}",
        }
        for label, value in stats_lines.items():
            self.font_title.render(label, surface, (x, y)); w = self.font_title.width(label)
            self.game.white_font.render(value, surface, (x + w + 5, y)); y += 14

    def render_oracle(self, surface, p_rect, y):
        response_box = pygame.Rect(p_rect.left + 10, y, p_rect.width - 20, 80)
        if not self.game.ai_agent: self.game.white_font.render("The Oracle is unavailable. (Check API Key)", surface, response_box.topleft, response_box.width)
        elif self.game.ai_agent.is_thinking:
            msg = "The Oracle is consulting the cosmos" + "." * (int(self.master_clock/20) % 4)
            self.game.white_font.render(msg, surface, response_box.topleft, response_box.width)
        elif self.game.save_data.get('active_prophecy'): self.game.white_font.render(self.game.save_data['active_prophecy']['flavor_text'], surface, response_box.topleft, response_box.width)
        elif self.game.ai_agent.response: self.game.white_font.render(str(self.game.ai_agent.response), surface, response_box.topleft, response_box.width)
        else: self.game.white_font.render("Ask a question. Try 'What is the best way to earn coins?' or 'Tell me about the Ninja character.'", surface, response_box.topleft, response_box.width)

        if self.game.save_data.get('active_prophecy'): prophecy_prompt = "[PROPHECY RECORDED]"
        elif self.game.save_data['upgrades'].get('prophecy_clarity', 0) > 0: prophecy_prompt = "[P] Seek Clarified Prophecy"
        else: prophecy_prompt = "[P] Seek Prophecy"
        w = self.game.white_font.width(prophecy_prompt); prophecy_pos = (response_box.right - w, response_box.bottom)
        if not self.game.save_data.get('active_prophecy'): (self.font_highlight if self.master_clock % 80 < 40 else self.game.white_font).render(prophecy_prompt, surface, prophecy_pos)
        else: self.font_locked.render(prophecy_prompt, surface, prophecy_pos)
            
        input_box = pygame.Rect(p_rect.left + 10, p_rect.bottom - 25, p_rect.width - 20, 12)
        pygame.draw.rect(surface, (0, 0, 1, 150), input_box); pygame.draw.rect(surface, (255, 255, 255, 50), input_box, 1)
        render_text = self.ai_input_text + ('|' if self.ai_input_active and self.master_clock % 60 < 30 else '')
        self.game.white_font.render(render_text, surface, (input_box.x + 4, input_box.y + 3))

    def is_artifact_unlocked(self, key): return key in self.game.save_data['artifacts']['unlocked']
    def check_artifact_unlocks(self):
        for key, artifact in self.game.artifacts.items():
            if self.is_artifact_unlocked(key): continue
            req = artifact['unlock_req']
            unlocked = False
            if req['type'] == 'score' and self.game.save_data['high_score'] >= req['value']: unlocked = True
            elif req['type'] == 'play_time' and self.game.save_data['stats']['play_time'] >= req['value']: unlocked = True
            elif req['type'] == 'total_coins' and self.game.save_data['stats']['total_coins'] >= req['value']: unlocked = True
            if unlocked: self.game.save_data['artifacts']['unlocked'].append(key); self.game.notify_unlock('artifacts')

    def render_artifacts(self, surface, p_rect):
        y = p_rect.top + 25
        unlocked_artifacts = [k for k in self.game.artifacts if self.is_artifact_unlocked(k)]
        if not unlocked_artifacts:
            self.game.white_font.render("Unlock Artifacts by achieving milestones.", surface, (p_rect.left + 15, y)); return

        for i, key in enumerate(unlocked_artifacts):
            artifact, is_equipped = self.game.artifacts[key], key == self.game.save_data['artifacts']['equipped']
            font = self.font_highlight if i == self.artifact_selection_index else self.game.white_font
            prefix = "> " if i == self.artifact_selection_index else ""; suffix = " [EQUIPPED]" if is_equipped else ""
            font.render(f"{prefix}{artifact['name']}{suffix}", surface, (p_rect.left + 15, y))
            self.game.white_font.render(artifact['desc'], surface, (p_rect.left + 25, y+10), p_rect.width - 40)
            y += 30
            
    def render_compendium(self, surface, p_rect, y):
        discovered = self.game.save_data['compendium']
        col_width = (p_rect.width - 20) // 3
        
        # Draw the lists
        item_counter = 0
        x = p_rect.left + 15
        for category, full_dict, icon_dict, cat_title in [
            ('perk', self.game.perks, self.game.perk_icons, "Perks:"),
            ('curse', self.game.curses, {}, "Curses:"),
            ('item', self.game.item_icons, self.game.item_icons, "Items:")
        ]:
            y_offset = y
            self.font_title.render(cat_title, surface, (x, y_offset)); y_offset += 12
            for key in sorted(full_dict.keys()):
                is_selected = self.compendium_selection_index == item_counter
                is_discovered = key in discovered.get(category + 's', [])
                font = self.font_locked if not is_discovered else self.font_highlight if is_selected else self.game.white_font
                
                if is_discovered:
                    name = full_dict[key].get('name') if isinstance(full_dict[key], dict) else key.replace('_', ' ').title()
                    text = f"- {name}"
                else: text = "- ???"
                font.render(text, surface, (x, y_offset))
                y_offset += 10
                item_counter += 1
            x += col_width

        # Draw the details panel
        if self.combined_compendium:
            details_x, details_y = p_rect.centerx, p_rect.bottom - 50
            category, key = self.combined_compendium[self.compendium_selection_index]
            is_discovered = key in discovered.get(category + 's', [])
            if is_discovered:
                name, desc, icon = "???", "Undiscovered.", None
                if category == 'perk': name, desc, icon = self.game.perks[key]['name'], self.game.perks[key]['desc'], self.game.perk_icons.get(key)
                elif category == 'curse': name, desc = self.game.curses[key]['name'], self.game.curses[key]['desc']
                elif category == 'item': name, desc, icon = key.replace('_', ' ').title(), "", self.game.item_icons.get(key)

                if icon: surface.blit(icon, (details_x, details_y))
                self.font_highlight.render(name.upper(), surface, (details_x + 15, details_y))
                self.game.white_font.render(desc, surface, (details_x + 15, details_y + 10), line_width=p_rect.width - (details_x - p_rect.x) - 20)