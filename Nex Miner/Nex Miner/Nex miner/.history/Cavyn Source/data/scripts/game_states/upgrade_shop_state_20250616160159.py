# Cavyn Source/data/scripts/game_states/upgrade_shop_state.py

import pygame
from ..state import State
from ..text import Font
from ..gameplay_state import render_panel_9slice # Import the new panel renderer

class UpgradeShopState(State):
    def __init__(self, game):
        super().__init__(game)
        self.selection_index = 0
        self.upgrade_keys = list(self.game.upgrades.keys())

        # Define UI colors and fonts
        self.highlight_color = (255, 230, 90)
        font_path = self.game.get_path('data', 'fonts', 'small_font.png')
        self.highlight_font = Font(font_path, self.highlight_color)
        self.cost_font_can_afford = Font(font_path, (140, 245, 150))
        self.cost_font_cannot_afford = Font(font_path, (200, 80, 80))

        # --- NEW: Mapping upgrades to their icons for visual flair ---
        self.upgrade_icon_map = {
            "jumps": self.game.item_icons.get('jump'),
            "speed": self.game.animation_manager.new('player_run').img,
            "item_luck": self.game.item_icons.get('cube'),
            "coin_magnet": self.game.animation_manager.new('coin_idle').img,
            "combo_shield": self.game.item_icons.get('shield'),
            "focus_mastery": self.game.item_icons.get('hourglass'),
            "starting_item": self.game.item_icons.get('cube'), # Using cube as proxy for now
            "curse_reroll": self.game.animation_manager.new('warp_idle').img,
        }
        self.panel_img = pygame.image.load(self.game.get_path('data', 'images', 'panel_9slice.png')).convert_alpha()


    def enter_state(self):
        self.selection_index = 0

    def handle_events(self, events):
        super().handle_events(events)
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_DOWN, pygame.K_s]:
                    self.selection_index = (self.selection_index + 1) % len(self.upgrade_keys)
                    if 'block_land' in self.game.sounds: self.game.sounds['block_land'].play()
                elif event.key in [pygame.K_UP, pygame.K_w]:
                    self.selection_index = (self.selection_index - 1 + len(self.upgrade_keys)) % len(self.upgrade_keys)
                    if 'block_land' in self.game.sounds: self.game.sounds['block_land'].play()
                elif event.key == pygame.K_RETURN:
                    self.purchase_selected_upgrade()
                elif event.key == pygame.K_ESCAPE:
                    self.game.pop_state()

    def purchase_selected_upgrade(self):
        selected_key = self.upgrade_keys[self.selection_index]
        upgrade_info = self.game.upgrades[selected_key]
        current_level = self.game.save_data['upgrades'].get(selected_key, 0)
        
        # Ensure upgrade key exists in save data
        if selected_key not in self.game.save_data['upgrades']:
            self.game.save_data['upgrades'][selected_key] = 0

        if current_level >= upgrade_info['max_level']:
            return

        cost = int(upgrade_info['base_cost'] * (1.5 ** current_level))

        if self.game.save_data['banked_coins'] >= cost:
            self.game.save_data['banked_coins'] -= cost
            self.game.save_data['upgrades'][selected_key] += 1
            self.game.write_save(self.game.save_data)
            if 'upgrade' in self.game.sounds:
                self.game.sounds['upgrade'].play()

    def render(self, surface):
        surface.fill((22, 19, 40))
        p_rect = pygame.Rect(10, 8, self.game.DISPLAY_SIZE[0] - 20, self.game.DISPLAY_SIZE[1] - 16)
        
        render_panel_9slice(surface, p_rect, self.panel_img, 8)

        title = "UPGRADE SHOP"
        w = self.game.white_font.width(title, 2)
        self.game.black_font.render(title, surface, (self.game.DISPLAY_SIZE[0]//2 - w//2 + 2, p_rect.top + 12), scale=2)
        self.game.white_font.render(title, surface, (self.game.DISPLAY_SIZE[0]//2 - w//2, p_rect.top + 10), scale=2)
        
        bank_txt = f"Bank: {self.game.save_data['banked_coins']}"
        bank_w = self.game.white_font.width(bank_txt)
        bank_pos = (p_rect.right - bank_w - 15, p_rect.top + 12)
        coin_icon = self.game.animation_manager.new('coin_idle').img
        surface.blit(coin_icon, (bank_pos[0] - coin_icon.get_width() - 4, bank_pos[1] - 1))
        self.game.black_font.render(bank_txt, surface, (bank_pos[0] + 1, bank_pos[1] + 1))
        self.game.white_font.render(bank_txt, surface, bank_pos)

        self.render_upgrade_list(surface, p_rect, p_rect.top + 45)
        self.render_details_panel(surface, p_rect, p_rect.top + 45)

        prompt = "Up/Down: Select  -  Enter: Buy  -  Esc: Back"
        w = self.game.white_font.width(prompt)
        pos = (self.game.DISPLAY_SIZE[0]//2 - w//2, p_rect.bottom - 12)
        self.game.black_font.render(prompt, surface, (pos[0] + 1, pos[1] + 1))
        self.game.white_font.render(prompt, surface, pos)
        
    def render_upgrade_list(self, surface, p_rect, start_y):
        list_y = start_y
        for i, key in enumerate(self.upgrade_keys):
            upgrade = self.game.upgrades[key]
            level = self.game.save_data['upgrades'].get(key, 0)
            
            font = self.game.white_font
            x_offset = p_rect.left + 10
            
            if i == self.selection_index:
                font = self.highlight_font
                self.game.white_font.render('>', surface, (x_offset, list_y))

            x_offset += 10
            
            icon = self.upgrade_icon_map.get(key)
            if icon:
                surface.blit(icon, (x_offset, list_y))
                x_offset += icon.get_width() + 4

            font.render(f"{upgrade['name']}", surface, (x_offset, list_y))
            
            lvl_txt = "MAX" if level >= upgrade['max_level'] else f"Lvl {level}"
            font.render(lvl_txt, surface, (p_rect.left + 125, list_y))
            list_y += 14

    def render_details_panel(self, surface, p_rect, start_y):
        det_x, det_y = p_rect.centerx + 10, start_y

        selected_key = self.upgrade_keys[self.selection_index]
        selected_upgrade = self.game.upgrades[selected_key]
        current_level = self.game.save_data['upgrades'].get(selected_key, 0)
        
        details_rect = pygame.Rect(det_x - 5, det_y - 5, p_rect.width / 2 - 10, p_rect.height - (start_y - p_rect.y) - 20)
        pygame.draw.rect(surface, (0, 0, 0, 50), details_rect, border_radius=3)
        pygame.draw.rect(surface, (255, 255, 255, 20), details_rect, 1, border_radius=3)

        self.highlight_font.render(selected_upgrade['name'], surface, (det_x, det_y))
        self.game.white_font.render(selected_upgrade['desc'], surface, (det_x, det_y + 12), line_width=120)

        if current_level < selected_upgrade['max_level']:
            cost = int(selected_upgrade['base_cost'] * (1.5 ** current_level))
            has_enough_coins = self.game.save_data['banked_coins'] >= cost
            
            cost_font = self.cost_font_can_afford if has_enough_coins else self.cost_font_cannot_afford
            
            cost_y = details_rect.bottom - 15
            coin_icon = self.game.animation_manager.new('coin_idle').img
            surface.blit(coin_icon, (det_x, cost_y))
            cost_font.render(f"{cost}", surface, (det_x + coin_icon.get_width() + 4, cost_y+1))

            buy_text = "[Buy]"
            cost_font.render(buy_text, surface, (details_rect.right - cost_font.width(buy_text) - 5, cost_y+1))
        else:
            self.game.white_font.render("Max Level Reached", surface, (det_x, details_rect.bottom - 14))