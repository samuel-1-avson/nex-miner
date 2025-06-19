
import pygame
from ..state import State
from ..text import Font
from ..ui_utils import render_panel_9slice

class UpgradeShopState(State):
    def __init__(self, game):
        super().__init__(game)
        self.selection_index = 0
        self.upgrade_keys = list(self.game.upgrades.keys())

        # Define UI colors and fonts
        font_path = self.game.get_path('data', 'fonts', 'small_font.png')
        self.highlight_font = Font(font_path, (255, 230, 90))
        self.cost_font_can_afford = Font(font_path, (140, 245, 150))
        self.cost_font_cannot_afford = Font(font_path, (200, 80, 80))
        
        # --- Create a simple solid color surface for missing icons ---
        focus_icon = pygame.Surface((10,10)); focus_icon.fill((190, 40, 50))

        # --- UPDATED: Icon map with new and fallback icons ---
        self.upgrade_icon_map = {
            "jumps": self.game.item_icons.get('jump'),
            "speed": self.game.animation_manager.new('player_run').img,
            "item_luck": self.game.item_icons.get('cube'),
            "coin_magnet": self.game.animation_manager.new('coin_idle').img,
            "combo_shield": self.game.item_icons.get('shield'),
            "focus_mastery": focus_icon,
            "starting_item": self.game.item_icons.get('cube'),
            "curse_reroll": self.game.animation_manager.new('warp_idle').img,
            "prophecy_clarity": self.game.animation_manager.new('turret_idle').img, # Placeholder
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
        
        if selected_key not in self.game.save_data['upgrades']: self.game.save_data['upgrades'][selected_key] = 0
        if current_level >= upgrade_info['max_level']: return

        cost = int(upgrade_info['base_cost'] * (1.5 ** current_level))
        if self.game.save_data['banked_coins'] >= cost:
            self.game.save_data['banked_coins'] -= cost
            self.game.save_data['upgrades'][selected_key] += 1
            self.game.write_save(self.game.save_data)
            if 'upgrade' in self.game.sounds: self.game.sounds['upgrade'].play()

    def render(self, surface):
        surface.fill((22, 19, 40))
        p_rect = pygame.Rect(10, 8, self.game.DISPLAY_SIZE[0] - 20, self.game.DISPLAY_SIZE[1] - 16)
        pygame.draw.rect(surface, (200, 200, 220), p_rect, 1, 3)

        title = "SYSTEM UPGRADES"
        w = self.game.white_font.width(title)
        self.game.black_font.render(title, surface, (self.game.DISPLAY_SIZE[0]//2 - w//2 + 1, p_rect.top + 7), 1)
        self.game.white_font.render(title, surface, (self.game.DISPLAY_SIZE[0]//2 - w//2, p_rect.top + 6), 1)
        
        bank_txt = f"Credits: {self.game.save_data['banked_coins']}"
        bank_w = self.game.white_font.width(bank_txt)
        bank_pos = (p_rect.right - bank_w - 5, p_rect.top + 6)
        coin_icon = self.game.animation_manager.new('coin_idle').img
        surface.blit(coin_icon, (bank_pos[0] - coin_icon.get_width() - 4, bank_pos[1] - 1))
        self.game.white_font.render(bank_txt, surface, bank_pos)

        self.render_upgrade_list(surface, p_rect, p_rect.top + 25)
        self.render_details_panel(surface, p_rect)

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
            x_offset = p_rect.left + 15
            
            if i == self.selection_index:
                font = self.highlight_font
                self.game.white_font.render('>', surface, (x_offset - 8, list_y))

            icon = self.upgrade_icon_map.get(key)
            if icon:
                icon_y = list_y + (self.game.white_font.line_height - icon.get_height()) // 2
                surface.blit(icon, (x_offset, icon_y))
                x_offset += icon.get_width() + 4

            font.render(f"{upgrade['name']}", surface, (x_offset, list_y))
            
            max_lvl_font = self.highlight_font if level >= upgrade['max_level'] else self.game.white_font
            lvl_txt = "MAX" if level >= upgrade['max_level'] else f"Lvl {level}"
            max_lvl_font.render(lvl_txt, surface, (p_rect.left + 150, list_y))
            list_y += 11

    def render_details_panel(self, surface, p_rect):
        det_x, det_y = p_rect.left + 180, p_rect.top + 25
        det_w, det_h = 115, 115

        render_panel_9slice(surface, pygame.Rect(det_x, det_y, det_w, det_h), self.panel_img, 4)

        selected_key = self.upgrade_keys[self.selection_index]
        selected_upgrade = self.game.upgrades[selected_key]
        current_level = self.game.save_data['upgrades'].get(selected_key, 0)
        
        self.highlight_font.render(selected_upgrade['name'], surface, (det_x + 5, det_y + 5))
        self.game.white_font.render(selected_upgrade['desc'], surface, (det_x + 5, det_y + 17), line_width=det_w - 10)

        if current_level < selected_upgrade['max_level']:
            cost = int(selected_upgrade['base_cost'] * (1.5 ** current_level))
            has_enough = self.game.save_data['banked_coins'] >= cost
            
            cost_font = self.cost_font_can_afford if has_enough else self.cost_font_cannot_afford
            cost_y = det_y + det_h - 14
            
            coin_icon = self.game.animation_manager.new('coin_idle').img
            surface.blit(coin_icon, (det_x + 5, cost_y))
            cost_font.render(f"{cost}", surface, (det_x + 5 + coin_icon.get_width() + 4, cost_y+1))

            buy_text = "[Buy]"
            cost_font.render(buy_text, surface, (det_x + det_w - cost_font.width(buy_text) - 5, cost_y+1))
        else:
            self.game.white_font.render("Max Level Reached", surface, (det_x + 5, det_y + det_h - 14))