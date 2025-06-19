# Cavyn Source/data/scripts/states/gameplay.py

import os
import sys
import random
import math
import json
import pygame
from pygame.locals import *

# Import other project files with relative paths
from ..entity import Entity
from ..anim_loader import AnimationManager
from ..text import Font
from .state_base import State

class GameplayState(State):
    def __init__(self, game):
        super().__init__(game)
        
        # --- Constants and Definitions ---
        self.TILE_SIZE = 16
        self.WINDOW_TILE_SIZE = (int(self.game.display.get_width() // self.TILE_SIZE), int(self.game.display.get_height() // self.TILE_SIZE))
        self.SAVE_FILE = 'save.json'
        
        self.UPGRADES = {
            'jumps': {'name': 'Extra Jump', 'desc': 'Max jumps +1', 'base_cost': 50, 'max_level': 2},
            'speed': {'name': 'Move Speed', 'desc': 'Run faster', 'base_cost': 40, 'max_level': 5},
            'item_luck': {'name': 'Item Luck', 'desc': 'Better chest loot', 'base_cost': 100, 'max_level': 3},
            'coin_magnet': {'name': 'Coin Magnet', 'desc': 'Coins pull to you', 'base_cost': 150, 'max_level': 4},
        }
        self.upgrade_keys = list(self.UPGRADES.keys())

        self.BIOMES = [
            {'name': 'The Depths', 'score_req': 0, 'bg_color': (22, 19, 40), 'bg_layers': ('data/images/background.png', 'data/images/background.png'), 'available_tiles': ['tile', 'chest', 'fragile', 'bounce', 'spike', 'greed', 'magnetic', 'motherlode', 'unstable'], 'special_spawn_rate': {'magnetic': 9}},
            {'name': 'Goo-Grotto', 'score_req': 125, 'bg_color': (19, 40, 30), 'bg_layers': ('data/images/background_cave.png', 'data/images/background_cave.png'), 'available_tiles': ['tile', 'chest', 'fragile', 'bounce', 'spike', 'greed', 'sticky', 'motherlode', 'unstable'], 'special_spawn_rate': {'sticky': 8}},
        ]
        
        self.PERKS = {
            'acrobat': {'name': 'Acrobat', 'desc': 'First jump after wall contact is higher.'}, 'overcharge': {'name': 'Overcharge', 'desc': 'Dashing through tiles creates an explosion.'},
            'feather_fall': {'name': 'Feather Fall', 'desc': 'You fall 20% slower.'}, 'technician': {'name': 'Technician', 'desc': 'Projectiles pierce one tile.'},
            'greedy': {'name': 'Greedy', 'desc': 'Chests & Greed Tiles drop double coins.'}, 'glass_cannon': {'name': 'Glass Cannon', 'desc': 'Faster combo, but instant death.'},
        }
        
        self.GLOW_CACHE = {}

        # --- Asset Loading ---
        self.animation_manager = AnimationManager()
        self.load_assets()
        
        # --- Save Data ---
        self.save_data = self.load_save()
        
        # Game surface for rendering world elements
        self.game_surface = pygame.Surface(self.game.DISPLAY_SIZE)
        
    def enter_state(self):
        super().enter_state()
        self.reset_run()
        
    def reset_run(self):
        self.Player_cls = self.create_player_class()
        self.Item_cls = self.create_item_class()
        self.Projectile_cls = self.create_projectile_class()
        
        self.player = self.Player_cls(self.animation_manager, (self.game.DISPLAY_SIZE[0] // 2 - 5, -20), (8, 16), 'player')
        self.player.jumps_max = 2 + self.save_data['upgrades']['jumps']
        self.player.speed = 1.4 + self.save_data['upgrades']['speed'] * 0.08
        self.player.jumps = self.player.jumps_max
        
        self.dead = False
        self.tiles = {}
        self.tile_drops = []
        self.tile_drop_rects = []
        self.sparks = []
        self.projectiles = []
        self.items = []
        
        self.freeze_timer = 0
        self.game_timer = 0
        self.height = 0
        self.target_height = 0
        self.coins = 0
        self.end_coin_count = 0
        self.current_item = None
        self.master_clock = 0
        self.last_place = 0
        self.item_used = False
        
        self.time_meter = 120
        self.time_meter_max = 120
        self.time_scale = 1.0
        self.slowing_time = False
        
        self.combo_multiplier = 1.0
        self.combo_timer = 0
        self.COMBO_DURATION = 180
        
        self.run_coins_banked = False
        self.upgrade_selection = 0
        self.screen_shake = 0
        self.player_shielded = False
        
        self.current_biome_index = 0
        self.perk_selection_active = False
        self.perk_selection_choice = 0
        self.perks_to_offer = []
        self.last_perk_score = 0
        self.new_high_score = False
        self.active_perks = set()
        
        for i in range(self.WINDOW_TILE_SIZE[0] - 2):
            self.tiles[(i + 1, self.WINDOW_TILE_SIZE[1] - 1)] = {'type': 'tile', 'data': {}}
        self.tiles[(1, self.WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
        self.tiles[(self.WINDOW_TILE_SIZE[0] - 2, self.WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
        self.stack_heights = [self.WINDOW_TILE_SIZE[1] - 1 for i in range(self.WINDOW_TILE_SIZE[0] - 2)]
        self.stack_heights[0] -= 1; self.stack_heights[-1] -= 1
        
        self.load_biome_bgs(self.BIOMES[0])
        pygame.mixer.music.load('data/music.wav')
        pygame.mixer.music.play(-1)

    def update(self, dt, events):
        time_scale = dt * 60

        for event in events:
            self.handle_input(event)
        
        self.game_surface_cache = self.game.display.copy()

        if self.perk_selection_active:
            return

        self.update_gameplay(time_scale)

    def render(self, surface):
        surface.blit(self.game_surface, (0, 0))
        
        if self.perk_selection_active:
            surface.blit(self.game_surface_cache, (0, 0))
            self.render_perk_selection(surface)
        elif self.dead:
            self.render_game_over(surface)
        else:
            self.render_hud(surface)
            
    def update_gameplay(self, time_scale):
        if not self.dead:
            next_biome_index = self.current_biome_index
            if self.current_biome_index + 1 < len(self.BIOMES):
                if self.coins >= self.BIOMES[self.current_biome_index + 1]['score_req']:
                    next_biome_index += 1
            if next_biome_index != self.current_biome_index:
                self.current_biome_index = next_biome_index
                self.load_biome_bgs(self.BIOMES[self.current_biome_index])
                self.sounds['warp'].play(); self.screen_shake = 15

        self.master_clock += 1
        self.time_scale = 1.0
        if not self.dead:
            is_slowing_now = (pygame.key.get_pressed()[K_LSHIFT] and self.time_meter > 0) or self.player.is_charging_dash
            if is_slowing_now and not self.slowing_time: self.sounds['time_slow_start'].play()
            elif not is_slowing_now and self.slowing_time: self.sounds['time_slow_end'].play()
            self.slowing_time = is_slowing_now
            if self.slowing_time:
                self.time_scale = 0.4
                if self.player.is_charging_dash:
                    self.player.focus_meter = max(0, self.player.focus_meter - 1.5 * time_scale)
                    if self.player.focus_meter <= 0: self.player.is_charging_dash = False
                elif pygame.key.get_pressed()[K_LSHIFT]:
                    self.time_meter = max(0, self.time_meter - 0.75 * time_scale)
                    if self.time_meter <= 0: self.sounds['time_empty'].play()
            else:
                self.time_meter = min(self.time_meter_max, self.time_meter + 0.2 * time_scale)
        else:
            self.slowing_time = False; self.time_scale = 1.0

        if self.screen_shake > 0: self.screen_shake -= 0.5 * time_scale

        if self.combo_timer > 0:
            depletion_rate = 1 if 'glass_cannon' not in self.active_perks else 2
            self.combo_timer -= depletion_rate * time_scale
            if self.combo_timer <= 0 and self.combo_multiplier > 1.0:
                self.combo_timer = 0; self.combo_multiplier = 1.0; 
                if 'combo_end' in self.sounds: self.sounds['combo_end'].play()

        if self.master_clock > 180:
            self.game_timer += self.time_scale
            if self.game_timer > 10 + 25 * (20000 - min(20000, self.master_clock)) / 20000:
                self.game_timer = 0; self.spawn_tile()
        
        self.render_game_world(self.game_surface) # Draw the world onto the buffer

        self.update_tile_drops(time_scale)
        self.update_placed_tiles(time_scale)
        self.update_items(time_scale)
        self.update_projectiles(time_scale)
        self.update_world_scroll()
        
        edge_rects = [pygame.Rect(0, self.player.pos[1] - 300, self.TILE_SIZE, 600), pygame.Rect(self.TILE_SIZE * (self.WINDOW_TILE_SIZE[0] - 1), self.player.pos[1] - 300, self.TILE_SIZE, 600)]
        tile_rects = [pygame.Rect(self.TILE_SIZE * pos[0], self.TILE_SIZE * pos[1], self.TILE_SIZE, self.TILE_SIZE) for pos in self.tiles]
        
        if not self.dead:
            collisions = self.player.update(self.tile_drop_rects + edge_rects + tile_rects, self.time_scale)
            self.handle_player_collisions(collisions)
        else:
            self.player.opacity = 80; self.player.update([], time_scale); self.player.rotation -= 16 * time_scale

        self.update_sparks(time_scale)
        if self.freeze_timer > 0: self.freeze_timer -= 1 * time_scale

        if not self.dead and not self.perk_selection_active:
            score_interval = 75
            if self.coins > 0 and self.coins // score_interval > self.last_perk_score // score_interval:
                self.last_perk_score = self.coins
                available_perks = [p for p in self.PERKS.keys() if p not in self.active_perks]
                if available_perks:
                    self.perk_selection_active = True
                    self.perks_to_offer = random.sample(available_perks, k=min(3, len(available_perks)))
                    self.perk_selection_choice = 0; self.sounds['warp'].play()

    def render_game_world(self, surface):
        current_biome = self.BIOMES[self.current_biome_index]
        surface.fill(current_biome['bg_color'])
        
        if self.backgrounds.get('far'):
            scroll_y = (self.height * 0.2) % self.game.DISPLAY_SIZE[1]
            surface.blit(self.backgrounds['far'], (0, scroll_y)); surface.blit(self.backgrounds['far'], (0, scroll_y - self.game.DISPLAY_SIZE[1]))
        if self.backgrounds.get('near'):
            scroll_y = (self.height * 0.4) % self.game.DISPLAY_SIZE[1]
            surface.blit(self.backgrounds['near'], (0, scroll_y)); surface.blit(self.backgrounds['near'], (0, scroll_y - self.game.DISPLAY_SIZE[1]))

        for tile in self.tile_drops:
            if tile[2] == 'greed': img = self.greed_tile_img
            elif tile[2] == 'motherlode': img = self.motherlode_tile_img
            elif tile[2] == 'unstable': img = self.unstable_tile_img
            else: img = self.tile_img
            surface.blit(img, (tile[0], tile[1] + self.height))
            if tile[2] == 'chest':
                surface.blit(self.ghost_chest_img, (tile[0], tile[1] + self.height - self.TILE_SIZE))

        self.render_placed_tiles(surface)
        self.render_items(surface)
        self.render_projectiles(surface)

        if self.player_shielded and not self.dead: self.render_shield_aura(surface)
        self.player.render(surface, (0, -int(self.height)))
        self.render_sparks(surface)
        
        if self.freeze_timer > 0:
            freeze_overlay = pygame.Surface(self.game.DISPLAY_SIZE, pygame.SRCALPHA)
            alpha = 60 + math.sin(self.master_clock / 5) * 10
            freeze_overlay.fill((170, 200, 255, alpha)); surface.blit(freeze_overlay, (0, 0))

        surface.blit(self.border_img_light, (0, -math.sin(self.master_clock / 30) * 4 - 7))
        surface.blit(self.border_img, (0, -math.sin(self.master_clock / 40) * 7 - 14))
        surface.blit(pygame.transform.flip(self.border_img_light, False, True), (0, self.game.DISPLAY_SIZE[1] + math.sin(self.master_clock / 40) * 3 + 9 - self.border_img.get_height()))
        surface.blit(pygame.transform.flip(self.border_img, False, True), (0, self.game.DISPLAY_SIZE[1] + math.sin(self.master_clock / 30) * 3 + 16 - self.border_img.get_height()))
        
    def render_hud(self, surface):
        hud_panel = pygame.Surface((self.game.DISPLAY_SIZE[0], 28)); hud_panel.set_alpha(100); hud_panel.fill((0, 0, 1))
        surface.blit(hud_panel, (0, 0))

        surface.blit(self.coin_icon, (4, 4))
        self.black_font.render(str(self.coins), surface, (17, 6)); self.white_font.render(str(self.coins), surface, (16, 5))

        time_bar_pos_x = 4; time_bar_pos_y = 17; time_bar_w = 40; time_bar_h = 6
        pygame.draw.rect(surface, (0, 0, 1), [time_bar_pos_x, time_bar_pos_y, time_bar_w, time_bar_h])
        bar_fill_width = (self.time_meter / self.time_meter_max) * (time_bar_w - 2)
        bar_color = (80, 150, 255)
        if self.slowing_time and not self.player.is_charging_dash and self.master_clock % 10 < 5: bar_color = (255, 255, 100)
        pygame.draw.rect(surface, bar_color, [time_bar_pos_x + 1, time_bar_pos_y + 1, bar_fill_width, time_bar_h - 2])
        
        if self.combo_multiplier > 1.0:
            combo_text = f"x{self.combo_multiplier:.1f}"; scale = 2
            text_width = self.white_font.width(combo_text, scale=scale)
            pos_x = self.game.DISPLAY_SIZE[0] // 2 - text_width // 2; pos_y = 4
            combo_color = (255, 150, 40) if self.master_clock % 20 <= 10 else (255, 255, 255)
            combo_font = Font('data/fonts/small_font.png', combo_color)
            self.black_font.render(combo_text, surface, (pos_x + 1, pos_y + 1), scale=scale)
            combo_font.render(combo_text, surface, (pos_x, pos_y), scale=scale)
            bar_width = (self.combo_timer / self.COMBO_DURATION) * 60; bar_x = self.game.DISPLAY_SIZE[0] // 2 - 30; bar_y = 20
            pygame.draw.rect(surface, (0, 0, 1), [bar_x + 1, bar_y + 1, 60, 4]); pygame.draw.rect(surface, (251, 245, 239), [bar_x, bar_y, bar_width, 4])
            
        surface.blit(self.item_slot_img, (self.game.DISPLAY_SIZE[0] - 20, 4))
        if self.current_item:
            if (self.master_clock % 50 < 12) or (abs(self.master_clock % 50 - 20) < 3):
                surface.blit(self.item_slot_flash_img, (self.game.DISPLAY_SIZE[0] - 20, 4))
            surface.blit(self.item_icons[self.current_item], (self.game.DISPLAY_SIZE[0] - 15, 9))

        focus_bar_x = self.game.DISPLAY_SIZE[0] - 25; focus_bar_y = 8; focus_bar_w = 8; focus_bar_h = 16
        pygame.draw.rect(surface, (0, 0, 1), [focus_bar_x, focus_bar_y, focus_bar_w, focus_bar_h])
        bar_color = (255, 150, 40)
        if self.player.is_charging_dash and self.master_clock % 10 < 5: bar_color = (255, 255, 255)
        elif self.player.focus_meter < self.player.FOCUS_DASH_COST: bar_color = (100, 60, 20)
        fill_ratio = self.player.focus_meter / self.player.FOCUS_METER_MAX; current_fill_h = int(focus_bar_h * fill_ratio)
        fill_y = (focus_bar_y + focus_bar_h) - current_fill_h
        pygame.draw.rect(surface, bar_color, [focus_bar_x + 1, fill_y, focus_bar_w - 2, current_fill_h])

        perk_x_offset = 5; perk_y_pos = self.game.DISPLAY_SIZE[1] - 12
        for perk_key in sorted(list(self.active_perks)):
            if perk_key in self.perk_icons:
                icon = self.perk_icons[perk_key]
                icon_bg = pygame.Surface((icon.get_width() + 2, icon.get_height() + 2), pygame.SRCALPHA); icon_bg.fill((0,0,1,150))
                surface.blit(icon_bg, (perk_x_offset - 1, perk_y_pos - 1)); surface.blit(icon, (perk_x_offset, perk_y_pos))
                perk_x_offset += icon.get_width() + 4
                
    def render_game_over(self, surface):
        PANEL_COLOR = (15, 12, 28, 220); BORDER_COLOR = (200, 200, 220, 230); TITLE_COLOR = (255, 255, 255); HIGHLIGHT_COLOR = (255, 230, 90)
        AFFORD_COLOR = (140, 245, 150); CANT_AFFORD_COLOR = (120, 120, 130); NEW_BEST_COLOR = (100, 255, 120)
        highlight_font = Font('data/fonts/small_font.png', HIGHLIGHT_COLOR); cant_afford_font = Font('data/fonts/small_font.png', CANT_AFFORD_COLOR)
        afford_font = Font('data/fonts/small_font.png', AFFORD_COLOR); new_best_font = Font('data/fonts/small_font.png', NEW_BEST_COLOR)
        title_font = Font('data/fonts/small_font.png', TITLE_COLOR)

        panel_rect = pygame.Rect(10, 8, self.game.DISPLAY_SIZE[0] - 20, self.game.DISPLAY_SIZE[1] - 16)
        panel_surf = pygame.Surface(panel_rect.size, pygame.SRCALPHA); panel_surf.fill(PANEL_COLOR)
        surface.blit(panel_surf, panel_rect.topleft)
        pygame.draw.rect(surface, BORDER_COLOR, panel_rect, 1, border_radius=3)
        
        title_text = "GAME OVER"; text_w = self.white_font.width(title_text, scale=3)
        self.black_font.render(title_text, surface, (self.game.DISPLAY_SIZE[0]//2 - text_w//2 + 2, panel_rect.top + 8 + 2), scale=3)
        title_font.render(title_text, surface, (self.game.DISPLAY_SIZE[0]//2 - text_w//2, panel_rect.top + 8), scale=3)
        
        line_y1 = panel_rect.top + 30
        pygame.draw.line(surface, BORDER_COLOR, (panel_rect.left + 10, line_y1), (panel_rect.right - 10, line_y1), 1)

        score_text = f"SCORE: {self.coins}"; hs_text = f"HIGH SCORE: {self.save_data['high_score']}"
        score_w = self.white_font.width(score_text, scale=2); hs_w = self.white_font.width(hs_text, scale=2)
        
        self.black_font.render(score_text, surface, (self.game.DISPLAY_SIZE[0]/2 - score_w/2 + 1, line_y1 + 7 + 1), scale=2)
        self.white_font.render(score_text, surface, (self.game.DISPLAY_SIZE[0]/2 - score_w/2, line_y1 + 7), scale=2)
        
        hs_font = highlight_font if self.new_high_score and self.master_clock % 40 < 20 else self.white_font
        self.black_font.render(hs_text, surface, (self.game.DISPLAY_SIZE[0]/2 - hs_w/2 + 1, line_y1 + 22 + 1), scale=2)
        hs_font.render(hs_text, surface, (self.game.DISPLAY_SIZE[0]/2 - hs_w/2, line_y1 + 22), scale=2)
        
        if self.new_high_score and self.master_clock % 30 < 20: new_best_font.render("NEW!", surface, (self.game.DISPLAY_SIZE[0]/2 + hs_w/2 + 5, line_y1 + 22), scale=2)

        line_y2 = line_y1 + 42
        pygame.draw.line(surface, BORDER_COLOR, (panel_rect.left + 10, line_y2), (panel_rect.right - 10, line_y2), 1)
        
        if self.end_coin_count != self.coins and self.master_clock % 3 == 0:
            self.sounds['coin_end'].play(); self.end_coin_count = min(self.end_coin_count + 1, self.coins)
        elif not self.run_coins_banked:
            self.save_data['banked_coins'] += self.end_coin_count; self.write_save(self.save_data); self.run_coins_banked = True

        if self.run_coins_banked:
            upgrade_title_pos = (panel_rect.left + 15, line_y2 + 7)
            self.black_font.render("Upgrades", surface, (upgrade_title_pos[0]+1, upgrade_title_pos[1]+1), scale=2); self.white_font.render("Upgrades", surface, upgrade_title_pos, scale=2)
            bank_text = f"Bank: {self.save_data['banked_coins']}"; bank_w = self.white_font.width(bank_text)
            bank_pos = (panel_rect.right - bank_w - 15, line_y2 + 9)
            surface.blit(self.coin_icon, (bank_pos[0] - self.coin_icon.get_width() - 3, bank_pos[1] - 1))
            self.black_font.render(bank_text, surface, (bank_pos[0]+1, bank_pos[1]+1)); self.white_font.render(bank_text, surface, bank_pos)

            list_y = line_y2 + 28
            for i, key in enumerate(self.upgrade_keys):
                upgrade = self.UPGRADES[key]; level = self.save_data['upgrades'][key]
                name_text = f"{upgrade['name']}"; level_text = "MAX" if level >= upgrade['max_level'] else f"Lvl {level}"
                font = highlight_font if i == self.upgrade_selection else self.white_font
                pygame.draw.rect(surface, (40, 30, 60, 150), [panel_rect.left + 5, list_y-2, panel_rect.width//2-10, 11], 0)
                font.render(name_text, surface, (panel_rect.left + 10, list_y)); font.render(level_text, surface, (panel_rect.left + 80, list_y))
                list_y += 13
            
            sel_key = self.upgrade_keys[self.upgrade_selection]; sel_upgrade = self.UPGRADES[sel_key]; sel_level = self.save_data['upgrades'][sel_key]
            cost = int(sel_upgrade['base_cost'] * (1.5 ** sel_level)); can_afford = self.save_data['banked_coins'] >= cost
            highlight_font.render(sel_upgrade['name'], surface, (panel_rect.centerx + 5, line_y2 + 28))
            self.white_font.render(sel_upgrade['desc'], surface, (panel_rect.centerx + 5, line_y2 + 40))
            if sel_level < sel_upgrade['max_level']:
                cost_font = afford_font if can_afford else cant_afford_font
                cost_pos_y = line_y2 + 54; buy_text = "[Buy]"
                surface.blit(self.coin_icon, (panel_rect.centerx + 5, cost_pos_y))
                cost_font.render(str(cost), surface, (panel_rect.centerx + 5 + self.coin_icon.get_width() + 4, cost_pos_y))
                cost_font.render(buy_text, surface, (panel_rect.right - cost_font.width(buy_text) - 15, cost_pos_y))
            else:
                 self.white_font.render("Max Level Reached", surface, (panel_rect.centerx + 5, line_y2 + 54))
        else:
            banking_text = "Banking coins..."
            text_w = self.white_font.width(banking_text)
            self.black_font.render(banking_text, surface, (self.game.DISPLAY_SIZE[0]//2 - text_w//2 + 1, line_y2 + 25 + 1)); self.white_font.render(banking_text, surface, (self.game.DISPLAY_SIZE[0]//2 - text_w//2, line_y2 + 25))

        prompt_text = "Up/Down: Select  -  Enter: Buy  -  R: Restart"; prompt_w = self.white_font.width(prompt_text)
        self.black_font.render(prompt_text, surface, (self.game.DISPLAY_SIZE[0]//2 - prompt_w//2 + 1, panel_rect.bottom - 12 + 1))
        self.white_font.render(prompt_text, surface, (self.game.DISPLAY_SIZE[0]//2 - prompt_w//2, panel_rect.bottom - 12))

    def render_perk_selection(self, surface):
        overlay = pygame.Surface(self.game.DISPLAY_SIZE, pygame.SRCALPHA); overlay.fill((10, 5, 20, 200))
        surface.blit(overlay, (0, 0))
        title_text = "CHOOSE A PERK"; text_w = self.white_font.width(title_text, scale=2); title_pos = (self.game.DISPLAY_SIZE[0]//2 - text_w//2, 20)
        self.black_font.render(title_text, surface, (title_pos[0]+1, title_pos[1]+1), scale=2); self.white_font.render(title_text, surface, title_pos, scale=2)
        panel_y_start = 50; panel_h = 35; panel_margin = 5
        for i, perk_key in enumerate(self.perks_to_offer):
            panel_rect = pygame.Rect(40, panel_y_start + i * (panel_h + panel_margin), self.game.DISPLAY_SIZE[0] - 80, panel_h)
            if i == self.perk_selection_choice: pygame.draw.rect(surface, (255, 230, 90), panel_rect, 1)
            else: pygame.draw.rect(surface, (150, 150, 180), panel_rect, 1)
            perk_name = self.PERKS[perk_key]['name'].upper(); perk_desc = self.PERKS[perk_key]['desc']
            self.white_font.render(perk_name, surface, (panel_rect.x + 8, panel_rect.y + 7))
            self.black_font.render(perk_desc, surface, (panel_rect.x + 9, panel_rect.y + 19)); self.white_font.render(perk_desc, surface, (panel_rect.x + 8, panel_rect.y + 18))
    
    # ... and many, many more methods for update and render logic would go here.
    # The key is that they are now neatly organized inside this one class.

    def create_player_class(self):
        gs_ref = self # A reference to the GameplayState for the inner class to use
        class Player(Entity):
            def __init__(self, *args):
                super().__init__(*args)
                self.velocity = [0, 0]; self.right = False; self.left = False; self.speed = 1.4
                self.jumps = 2; self.jumps_max = 2; self.jumping = False; self.jump_rot = 0
                self.air_time = 0; self.coyote_timer = 0; self.jump_buffer_timer = 0; self.dash_timer = 0
                self.DASH_SPEED = 8; self.DASH_DURATION = 8; self.focus_meter = 100
                self.FOCUS_METER_MAX = 100; self.is_charging_dash = False; self.FOCUS_DASH_COST = 50
                self.FOCUS_RECHARGE_RATE = 0.4; self.wall_contact_timer = 0

            def attempt_jump(self):
                jump_velocity = -6.5 if 'acrobat' in gs_ref.active_perks and self.wall_contact_timer > 0 else -5
                if 'acrobat' in gs_ref.active_perks: self.wall_contact_timer = 0
                if self.jumps > 0 or self.coyote_timer > 0:
                    self.velocity[1] = jump_velocity if self.jumps == self.jumps_max or self.coyote_timer > 0 else -4
                    if self.jumps < self.jumps_max and self.coyote_timer <= 0:
                        for i in range(24):
                            direction = 1 if i % 2 else -1; physics_on = random.choice([False, False, True])
                            gs_ref.sparks.append([[self.center[0] + random.uniform(-7, 7), self.center[1]], [direction * random.uniform(0.05, 0.1) + random.uniform(-2, 2) * physics_on, random.uniform(0.05, 0.1) + random.uniform(0, 2) * physics_on], random.uniform(3, 6), 0.04 - 0.02 * physics_on, (6, 4, 1), physics_on, 0.05 * physics_on])
                    if self.coyote_timer <= 0: self.jumps -= 1
                    self.coyote_timer = 0; self.jumping = True; self.jump_rot = 0
            
            def update(self, tiles, time_scale=1.0):
                super().update(1/60, time_scale); self.air_time += 1
                if self.coyote_timer > 0: self.coyote_timer -= 1
                if self.jump_buffer_timer > 0: self.jump_buffer_timer -= 1
                if self.dash_timer > 0: self.dash_timer -= 1
                if not self.is_charging_dash: self.focus_meter = min(self.FOCUS_METER_MAX, self.focus_meter + self.FOCUS_RECHARGE_RATE)
                
                if self.dash_timer > 0:
                    direction = 1 if self.flip[0] else -1; self.velocity[0] = direction * self.DASH_SPEED
                    gs_ref.sparks.append([[self.center[0] - direction * 6, self.center[1] + random.uniform(-3, 3)], [-direction * random.uniform(1, 2), random.uniform(-0.5, 0.5)], random.uniform(2, 5), 0.15, (200, 220, 255), False, 0])
                else:
                    target_velocity_x = self.speed if self.right else -self.speed if self.left else 0
                    self.velocity[0] += (target_velocity_x - self.velocity[0]) * 0.3
                    if abs(self.velocity[0]) < 0.1: self.velocity[0] = 0
                
                if self.dash_timer > 0: self.velocity[1] = 0
                else:
                    gravity = 0.24 if 'feather_fall' in gs_ref.active_perks else 0.3
                    self.velocity[1] = min(self.velocity[1] + gravity, 4)
                
                if not gs_ref.dead and self.dash_timer <= 0:
                    if self.velocity[0] > 0.1: self.flip[0] = True
                    if self.velocity[0] < -0.1: self.flip[0] = False
                
                if self.jumping:
                    self.jump_rot += 16
                    if self.jump_rot >= 360: self.jump_rot = 0; self.jumping = False
                    self.rotation = -self.jump_rot if self.flip[0] else self.jump_rot; self.scale[1] = 0.7
                else: self.scale[1] = 1
                
                if self.is_charging_dash: self.set_action('idle')
                elif self.dash_timer > 0 or self.air_time > 3: self.set_action('jump')
                elif abs(self.velocity[0]) > 0.1: self.set_action('run')
                else: self.set_action('idle')
                
                was_on_ground = self.air_time <= 1
                collisions = self.move(list(map(lambda x: x * time_scale, self.velocity)), tiles, 1) # Move expects unscaled motion
                if collisions['left'] or collisions['right']: self.wall_contact_timer = 15
                if self.wall_contact_timer > 0: self.wall_contact_timer -= 1
                
                if collisions['bottom']:
                    self.velocity[1] = 0; self.air_time = 0; self.jumps = self.jumps_max
                    self.jumping = False; self.rotation = 0
                    if self.jump_buffer_timer > 0:
                        self.jump_buffer_timer = 0; gs_ref.sounds['jump'].play(); self.attempt_jump()
                elif was_on_ground: self.coyote_timer = 6
                return collisions
        return Player

    def create_item_class(self):
        gs_ref = self
        class Item(Entity):
            def __init__(self, *args, velocity=[0, 0]): super().__init__(*args); self.velocity = velocity; self.time = 0
            def update(self, tiles, time_scale=1.0):
                self.time += time_scale; self.velocity[1] = min(self.velocity[1] + 0.2, 3)
                self.velocity[0] = gs_ref.normalize(self.velocity[0], 0.05); self.move(self.velocity, tiles, time_scale)
        return Item

    def create_projectile_class(self):
        gs_ref = self
        class Projectile(Entity):
            def __init__(self, *args, velocity=[0, 0]):
                super().__init__(*args); self.velocity = velocity
                self.health = 2 if 'technician' in gs_ref.active_perks else 1
            def update(self, time_scale=1.0):
                super().update(1/60, time_scale); self.pos[0] += self.velocity[0] * time_scale; self.pos[1] += self.velocity[1] * time_scale
        return Projectile