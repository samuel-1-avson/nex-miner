# Cavyn Source/data/scripts/game_states/upgrade_shop_state.py
import pygame
import math
from ..state import State
from ..text import Font
from ..ui_utils import render_panel_9slice

class UpgradeShopState(State):
    def __init__(self, game):
        super().__init__(game)
        self.selection_index = 0
        self.upgrade_keys = list(self.game.upgrades.keys())
        self.master_clock = 0
        
        # --- UI Fonts ---
        font_path = self.game.get_path('data', 'fonts', 'small_font.png')
        self.font_main = Font(font_path, (140, 245, 250))
        self.font_highlight = Font(font_path, (255, 230, 90))
        self.font_title = Font(font_path, (255, 255, 255))
        self.font_cost_can_afford = Font(font_path, (60, 255, 60))
        self.font_cost_cannot_afford = Font(font_path, (255, 60, 60))

    def handle_events(self, events):
        super().handle_events(events)
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_DOWN, pygame.K_s]:
                    self.selection_index = (self.selection_index + 1) % len(self.upgrade_keys)
                    if 'shoot' in self.game.sounds: self.game.sounds['shoot'].play()
                elif event.key in [pygame.K_UP, pygame.K_w]:
                    self.selection_index = (self.selection_index - 1 + len(self.upgrade_keys)) % len(self.upgrade_keys)
                    if 'shoot' in self.game.sounds: self.game.sounds['shoot'].play()
                elif event.key == pygame.K_RETURN:
                    self.purchase_selected_upgrade()
                elif event.key == pygame.K_ESCAPE:
                    self.game.pop_state()

    def purchase_selected_upgrade(self):
        selected_key = self.upgrade_keys[self.selection_index]
        upgrade_info = self.game.upgrades[selected_key]
        current_level = self.game.save_data['upgrades'].get(selected_key, 0)
        
        if current_level >= upgrade_info['max_level']: return

        cost = int(upgrade_info['base_cost'] * (1.5 ** current_level))
        if self.game.save_data['banked_coins'] >= cost:
            self.game.save_data['banked_coins'] -= cost
            self.game.save_data['upgrades'][selected_key] += 1
            self.game.write_save(self.game.save_data)
            if 'upgrade' in self.game.sounds: self.game.sounds['upgrade'].play()
        else:
            if 'combo_end' in self.game.sounds: self.game.sounds['combo_end'].play()
            
    def update(self):
        self.master_clock += 1

    def render(self, surface):
        surface.fill((2, 4, 16))
        
        # --- Header ---
        self.font_title.render("[ SYSTEM UPGRADES ]", surface, (surface.get_width()//2 - self.font_title.width("[ SYSTEM UPGRADES ]")//2, 12))
        
        credits_text = f"CREDITS: {self.game.save_data['banked_coins']}"
        self.font_main.render(credits_text, surface, (surface.get_width() - self.font_main.width(credits_text) - 15, 12))
        
        pygame.draw.line(surface, self.font_main.color, (15, 25), (surface.get_width()-15, 25), 1)
        
        # --- Upgrade List ---
        self.render_upgrade_list(surface, 20, 35)
        
        # --- Details Panel ---
        pygame.draw.line(surface, self.font_main.color, (170, 30), (170, surface.get_height() - 30), 1)
        self.render_details_panel(surface)

        # --- Footer ---
        prompt = "SELECT [↑/↓]  -  PURCHASE [ENTER]  -  BACK [ESC]"
        w = self.font_main.width(prompt)
        self.font_main.render(prompt, surface, (surface.get_width()//2 - w//2, surface.get_height() - 15))
        
    def render_upgrade_list(self, surface, x_base, y_base):
        y_pos = y_base
        for i, key in enumerate(self.upgrade_keys):
            upgrade = self.game.upgrades[key]
            level = self.game.save_data['upgrades'].get(key, 0)
            
            font = self.font_main
            selector = ""
            if i == self.selection_index:
                font = self.font_highlight
                selector = "> "

            font.render(f"{selector}{upgrade['name']}", surface, (x_base, y_pos))
            
            lvl_txt = f"LVL: {level}/{upgrade['max_level']}"
            if level >= upgrade['max_level']: lvl_txt = "LVL: MAX"
            
            w = font.width(lvl_txt)
            font.render(lvl_txt, surface, (x_base + 140 - w, y_pos))
            
            y_pos += 12

    def render_details_panel(self, surface):
        x_base, y_base = 180, 40
        selected_key = self.upgrade_keys[self.selection_index]
        upgrade = self.game.upgrades[selected_key]
        current_level = self.game.save_data['upgrades'].get(selected_key, 0)
        
        self.font_title.render(f"//: {upgrade['name']}", surface, (x_base, y_base), scale=2)
        y_pos = y_base + 20
        self.font_main.render(upgrade['desc'], surface, (x_base, y_pos), line_width=surface.get_width() - x_base - 15)
        
        y_pos += 45
        
        if current_level < upgrade['max_level']:
            cost = int(upgrade['base_cost'] * (1.5 ** current_level))
            can_afford = self.game.save_data['banked_coins'] >= cost
            cost_font = self.font_cost_can_afford if can_afford else self.font_cost_cannot_afford
            
            self.font_main.render("Next Level:", surface, (x_base, y_pos))
            cost_font.render(f"Cost: {cost} Credits", surface, (x_base, y_pos + 12))
        else:
            self.font_green.render("Maximum level reached.", surface, (x_base, y_pos))