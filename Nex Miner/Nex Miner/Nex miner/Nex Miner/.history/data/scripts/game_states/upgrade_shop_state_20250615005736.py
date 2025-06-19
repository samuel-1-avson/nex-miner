# Cavyn Source/data/scripts/game_states/upgrade_shop_state.py

import pygame
from ..state import State
from ..text import Font

class UpgradeShopState(State):
    """
    A state for displaying and purchasing permanent upgrades.
    """
    def __init__(self, game):
        super().__init__(game)
        self.selection_index = 0
        self.upgrade_keys = list(self.game.upgrades.keys())

        # Define UI colors and fonts here to avoid recreating them every frame
        self.panel_color = (15, 12, 28, 220)
        self.border_color = (200, 200, 220, 230)
        self.highlight_color = (255, 230, 90)

        # CORRECTED: Use self.game.get_path and create all font variations once
        font_path = self.game.get_path('data', 'fonts', 'small_font.png')
        self.highlight_font = Font(font_path, self.highlight_color)
        self.cost_font_can_afford = Font(font_path, (140, 245, 150))
        self.cost_font_cannot_afford = Font(font_path, (200, 80, 80))


    def enter_state(self):
        """Reset the selection when entering the state."""
        self.selection_index = 0

    def handle_events(self, events):
        super().handle_events(events)
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_DOWN, pygame.K_s]:
                    self.selection_index = (self.selection_index + 1) % len(self.upgrade_keys)
                elif event.key in [pygame.K_UP, pygame.K_w]:
                    self.selection_index = (self.selection_index - 1 + len(self.upgrade_keys)) % len(self.upgrade_keys)
                elif event.key == pygame.K_RETURN:
                    self.purchase_selected_upgrade()
                elif event.key == pygame.K_ESCAPE:
                    self.game.pop_state()

    def purchase_selected_upgrade(self):
        """Handles the logic for buying the currently selected upgrade."""
        selected_key = self.upgrade_keys[self.selection_index]
        upgrade_info = self.game.upgrades[selected_key]
        current_level = self.game.save_data['upgrades'][selected_key]
        
        if current_level >= upgrade_info['max_level']:
            return

        cost = int(upgrade_info['base_cost'] * (1.5 ** current_level))

        if self.game.save_data['banked_coins'] >= cost:
            self.game.save_data['banked_coins'] -= cost
            self.game.save_data['upgrades'][selected_key] += 1
            self.game.write_save(self.game.save_data)
            if 'upgrade' in self.game.sounds:
                self.game.sounds['upgrade'].play()
            else:
                self.game.sounds['coin'].play()

    def render(self, surface):
        """Draws the upgrade shop UI."""
        surface.fill((22, 19, 40))

        p_rect = pygame.Rect(10, 8, self.game.DISPLAY_SIZE[0] - 20, self.game.DISPLAY_SIZE[1] - 16)
        p_surf = pygame.Surface(p_rect.size, pygame.SRCALPHA)
        p_surf.fill(self.panel_color)
        surface.blit(p_surf, p_rect.topleft)
        pygame.draw.rect(surface, self.border_color, p_rect, 1, 3)

        title = "UPGRADE SHOP"
        w = self.game.white_font.width(title, 3)
        self.game.black_font.render(title, surface, (self.game.DISPLAY_SIZE[0]//2 - w//2 + 2, p_rect.top + 10), scale=3)
        self.game.white_font.render(title, surface, (self.game.DISPLAY_SIZE[0]//2 - w//2, p_rect.top + 8), scale=3)
        
        y1 = p_rect.top + 30
        pygame.draw.line(surface, self.border_color, (p_rect.left + 10, y1), (p_rect.right - 10, y1), 1)

        bank_txt = f"Bank: {self.game.save_data['banked_coins']}"
        bank_w = self.game.white_font.width(bank_txt)
        bank_pos = (p_rect.right - bank_w - 15, y1 + 5)
        coin_icon = self.game.animation_manager.new('coin_idle').img
        surface.blit(coin_icon, (bank_pos[0] - coin_icon.get_width() - 4, bank_pos[1] - 1))
        self.game.black_font.render(bank_txt, surface, (bank_pos[0] + 1, bank_pos[1] + 1))
        self.game.white_font.render(bank_txt, surface, bank_pos)

        self.render_upgrade_list(surface, p_rect, y1 + 22)
        self.render_details_panel(surface, p_rect, y1 + 22)

        prompt = "Up/Down: Select  -  Enter: Buy  -  Esc: Back"
        w = self.game.white_font.width(prompt)
        pos = (self.game.DISPLAY_SIZE[0]//2 - w//2, p_rect.bottom - 12)
        self.game.black_font.render(prompt, surface, (pos[0] + 1, pos[1] + 1))
        self.game.white_font.render(prompt, surface, pos)
        
    def render_upgrade_list(self, surface, p_rect, start_y):
        list_y = start_y
        for i, key in enumerate(self.upgrade_keys):
            upgrade = self.game.upgrades[key]
            level = self.game.save_data['upgrades'][key]
            
            font = self.highlight_font if i == self.selection_index else self.game.white_font
            
            if i == self.selection_index:
                highlight_rect = pygame.Rect(p_rect.left + 5, list_y - 2, p_rect.width//2 - 5, 12)
                pygame.draw.rect(surface, (40, 30, 60, 150), highlight_rect, 0)

            font.render(f"{upgrade['name']}", surface, (p_rect.left + 10, list_y))
            
            lvl_txt = "MAX" if level >= upgrade['max_level'] else f"Lvl {level}"
            font.render(lvl_txt, surface, (p_rect.left + 80, list_y))
            list_y += 14

    def render_details_panel(self, surface, p_rect, start_y):
        det_x, det_y = p_rect.centerx + 5, start_y

        selected_key = self.upgrade_keys[self.selection_index]
        selected_upgrade = self.game.upgrades[selected_key]
        current_level = self.game.save_data['upgrades'][selected_key]

        self.highlight_font.render(selected_upgrade['name'], surface, (det_x, det_y))
        self.game.white_font.render(selected_upgrade['desc'], surface, (det_x, det_y + 12))

        if current_level < selected_upgrade['max_level']:
            cost = int(selected_upgrade['base_cost'] * (1.5 ** current_level))
            has_enough_coins = self.game.save_data['banked_coins'] >= cost
            
            # REFINED: Select the correct pre-made font object
            cost_font = self.cost_font_can_afford if has_enough_coins else self.cost_font_cannot_afford
            
            cost_y = det_y + 28
            coin_icon = self.game.animation_manager.new('coin_idle').img
            surface.blit(coin_icon, (det_x, cost_y))
            cost_font.render(f"{cost}", surface, (det_x + coin_icon.get_width() + 4, cost_y+1))

            buy_text = "[Buy]"
            cost_font.render(buy_text, surface, (p_rect.right - cost_font.width(buy_text) - 15, cost_y+1))
        else:
            self.game.white_font.render("Max Level Reached", surface, (det_x, det_y + 28))