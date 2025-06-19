import os
import sys
import random
import math
import json

import pygame
from pygame.locals import *

from .base import State
from data.scripts.entity import Entity
from data.scripts.anim_loader import AnimationManager
from data.scripts.text import Font

class Gameplay(State):
    def __init__(self, game):
        super().__init__(game)
        
        self.TILE_SIZE = 16
        self.WINDOW_TILE_SIZE = (int(self.game.display.get_width() // 16), int(self.game.display.get_height() // 16))
        self.COMBO_DURATION = 180
        self.frozen_game_screen = None
        
        self.load_assets()
        self.reset_game_state()

    def reset_game_state(self):
        """Resets all variables for a new run"""
        self.dead = False
        self.tiles = {}
        self.tile_drops = []
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
        self.time_meter = self.time_meter_max
        self.slowing_time = False
        self.combo_multiplier = 1.0
        self.combo_timer = 0
        self.run_coins_banked = False
        self.upgrade_selection = 0
        self.screen_shake = 0
        self.player_shielded = False
        self.new_high_score = False
        
        self.current_biome_index = 0
        self.perk_selection_active = False
        self.perk_selection_choice = 0
        self.perks_to_offer = []
        self.last_perk_score = 0
        
        self.active_perks.clear()

        self.player = Player(self, (self.game.DISPLAY_SIZE[0] // 2 - 5, -20), (8, 16), 'player')
        self.player.jumps_max += self.save_data['upgrades']['jumps']
        self.player.speed += self.save_data['upgrades']['speed'] * 0.08
        self.player.jumps = self.player.jumps_max

        for i in range(self.WINDOW_TILE_SIZE[0] - 2):
            self.tiles[(i + 1, self.WINDOW_TILE_SIZE[1] - 1)] = {'type': 'tile', 'data': {}}
        self.tiles[(1, self.WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
        self.tiles[(self.WINDOW_TILE_SIZE[0] - 2, self.WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
        self.stack_heights = [self.WINDOW_TILE_SIZE[1] - 1 for i in range(self.WINDOW_TILE_SIZE[0] - 2)]
        self.stack_heights[0] -= 1
        self.stack_heights[-1] -= 1
        
        self.load_biome_bgs(self.BIOMES[0])

    def load_assets(self):
        """Loads all assets and data files once"""
        self.save_data = self.load_save_file()

        self.UPGRADES = {
            'jumps': {'name': 'Extra Jump', 'desc': 'Max jumps +1', 'base_cost': 50, 'max_level': 2},
            'speed': {'name': 'Move Speed', 'desc': 'Run faster', 'base_cost': 40, 'max_level': 5},
            'item_luck': {'name': 'Item Luck', 'desc': 'Better chest loot', 'base_cost': 100, 'max_level': 3},
            'coin_magnet': {'name': 'Coin Magnet', 'desc': 'Coins pull to you', 'base_cost': 150, 'max_level': 4},
        }
        self.upgrade_keys = list(self.UPGRADES.keys())

        self.BIOMES = [
            {'name':'The Depths','score_req':0,'bg_color':(22,19,40),'bg_layers':('data/images/background.png','data/images/background.png'),'available_tiles':['tile','chest','fragile','bounce','spike','greed','magnetic'],'special_spawn_rate':{'magnetic':9}},
            {'name':'Goo-Grotto','score_req':125,'bg_color':(19,40,30),'bg_layers':('data/images/background_cave.png','data/images/background_cave.png'),'available_tiles':['tile','chest','fragile','bounce','spike','greed','sticky'],'special_spawn_rate':{'sticky':8}},
        ]
        
        self.PERKS = {
            'acrobat': {'name': 'Acrobat', 'desc': 'First jump after wall contact is higher.'},
            'overcharge': {'name': 'Overcharge', 'desc': 'Dashing through tiles creates an explosion.'},
            'feather_fall': {'name': 'Feather Fall', 'desc': 'You fall 20% slower.'},
            'technician': {'name': 'Technician', 'desc': 'Projectiles pierce one tile.'},
            'greedy': {'name': 'Greedy', 'desc': 'Chests & Greed Tiles drop double coins.'},
            'glass_cannon': {'name': 'Glass Cannon', 'desc': 'Faster combo, but instant death.'},
        }
        self.active_perks = set()

        self.animation_manager = AnimationManager()
        self.backgrounds = {}
        self.GLOW_CACHE = {}
        self.time_meter_max = 120

        self.tile_img = self.load_img('data/images/tile.png')
        self.placed_tile_img = self.load_img('data/images/placed_tile.png')
        self.chest_img = self.load_img('data/images/chest.png')
        self.ghost_chest_img = self.load_img('data/images/ghost_chest.png')
        self.opened_chest_img = self.load_img('data/images/opened_chest.png')
        self.edge_tile_img = self.load_img('data/images/edge_tile.png')
        self.fragile_tile_img = self.load_img('data/images/fragile_tile.png')
        self.bounce_tile_img = self.load_img('data/images/bounce_tile.png')
        self.spike_tile_img = self.load_img('data/images/spike_tile.png')
        self.magnetic_tile_img = self.load_img('data/images/magnetic_tile.png')
        self.sticky_tile_img = self.load_img('data/images/sticky_tile.png')
        self.coin_icon = self.load_img('data/images/coin_icon.png')
        self.item_slot_img = self.load_img('data/images/item_slot.png')
        self.item_slot_flash_img = self.load_img('data/images/item_slot_flash.png')
        self.border_img = self.load_img('data/images/border.png')
        self.border_img_light = self.border_img.copy()
        self.border_img_light.set_alpha(100)
        self.tile_top_img = self.load_img('data/images/tile_top.png')
        self.greed_tile_img = self.load_img('data/images/greed_tile.png')
        
        self.white_font = Font('data/fonts/small_font.png', (251, 245, 239))
        self.black_font = Font('data/fonts/small_font.png', (0, 0, 1))
        
        self.sounds = {sound.split('/')[-1].split('.')[0] : pygame.mixer.Sound('data/sfx/' + sound) for sound in os.listdir('data/sfx')}
        self.sounds['block_land'].set_volume(0.5);self.sounds['coin'].set_volume(0.6);self.sounds['chest_open'].set_volume(0.8)
        self.sounds['coin_end'] = pygame.mixer.Sound('data/sfx/coin.wav');self.sounds['coin_end'].set_volume(0.35)
        if 'upgrade' in self.sounds: self.sounds['upgrade'].set_volume(0.7)
        if 'explosion' in self.sounds: self.sounds['explosion'].set_volume(0.8)
        if 'combo_end' in self.sounds: self.sounds['combo_end'].set_volume(0.6)
        if 'chest_destroy' in self.sounds: self.sounds['chest_destroy'].set_volume(0.7)
        if 'super_jump' in self.sounds: self.sounds['super_jump'].set_volume(0.7)
        if 'death' in self.sounds: self.sounds['death'].set_volume(0.7)
        if 'collect_item' in self.sounds: self.sounds['collect_item'].set_volume(0.7)
        self.sounds['time_slow_start'] = pygame.mixer.Sound('data/sfx/warp.wav'); self.sounds['time_slow_start'].set_volume(0.4)
        self.sounds['time_slow_end'] = pygame.mixer.Sound('data/sfx/chest_open.wav'); self.sounds['time_slow_end'].set_volume(0.3)
        self.sounds['time_empty'] = pygame.mixer.Sound('data/sfx/death.wav'); self.sounds['time_empty'].set_volume(0.25)
        
        self.item_icons = {'cube': self.load_img('data/images/cube_icon.png'),'warp': self.load_img('data/images/warp_icon.png'),'jump': self.load_img('data/images/jump_icon.png'),'bomb': self.load_img('data/images/bomb_icon.png'),'freeze': self.load_img('data/images/freeze_icon.png'),'shield': self.load_img('data/images/shield_icon.png'),}
        self.shield_aura_img = self.load_img('data/images/shield_aura.png')
        self.shield_aura_img.set_alpha(150)
        
        self.perk_icons = {}
        perk_icon_path = 'data/images/perk_icons/'
        for perk_name in self.PERKS.keys():
            try:
                self.perk_icons[perk_name] = self.load_img(perk_icon_path + perk_name + '.png')
            except pygame.error:
                print(f"Warning: Could not load icon for perk '{perk_name}'.")

        pygame.mixer.music.load('data/music.wav')
        pygame.mixer.music.play(-1)

    # All helper functions are now methods and use `self`.
    # region ############# HELPER FUNCTIONS #############
    def load_img(self, path):
        img = pygame.image.load(path).convert()
        img.set_colorkey((0, 0, 0))
        return img
    
    def load_biome_bgs(self, biome_info):
        try:
            bg_far_path, bg_near_path = biome_info['bg_layers']
            far_surf = pygame.image.load(bg_far_path).convert()
            self.backgrounds['far'] = pygame.transform.scale(far_surf, self.game.DISPLAY_SIZE)
            near_surf = self.load_img(bg_near_path)
            self.backgrounds['near'] = pygame.transform.scale(near_surf, self.game.DISPLAY_SIZE)
        except (pygame.error, FileNotFoundError) as e:
            print(f"Warning: Could not load background for biome {biome_info['name']}. Reason: {e}")
            self.backgrounds['far'] = None; self.backgrounds['near'] = None
    
    def load_save_file(self):
        try:
            with open('save.json', 'r') as f:
                data = json.load(f)
                if 'high_score' not in data: data['high_score'] = 0
                if 'coin_magnet' not in data['upgrades']: data['upgrades']['coin_magnet'] = 0
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            default_save = {"banked_coins": 100, "upgrades": {"jumps": 0, "speed": 0, "item_luck": 0, "coin_magnet": 0}, "high_score": 0}
            self.write_save_file(default_save)
            return default_save
    
    def write_save_file(self, data):
        with open('save.json', 'w') as f:
            json.dump(data, f, indent=4)

    def glow_img(self, size, color):
        if (size, color) not in self.GLOW_CACHE:
            surf = pygame.Surface((size * 2 + 2, size * 2 + 2))
            pygame.draw.circle(surf, color, (surf.get_width() // 2, surf.get_height() // 2), size)
            surf.set_colorkey((0, 0, 0))
            self.GLOW_CACHE[(size, color)] = surf
        return self.GLOW_CACHE[(size, color)]
    
    def recalculate_stack_heights(self):
        new_heights = [self.WINDOW_TILE_SIZE[1] for i in range(self.WINDOW_TILE_SIZE[0] - 2)]
        for tile_x, tile_y in self.tiles:
            if 1 <= tile_x < self.WINDOW_TILE_SIZE[0] - 1:
                col_index = tile_x - 1
                new_heights[col_index] = min(new_heights[col_index], tile_y)
        self.stack_heights = new_heights

    def normalize(self, val, amt):
        if val > amt: val -= amt
        elif val < -amt: val += amt
        else: val = 0
        return val

    def lookup_nearby(self, pos):
        rects = []
        for offset in [(0, 0), (-1, -1), (-1, 0), (-1, 1), (0, 1), (0, -1), (1, -1), (1, 0), (1, 1)]:
            lookup_pos = (pos[0] // self.TILE_SIZE + offset[0], pos[1] // self.TILE_SIZE + offset[1])
            if lookup_pos in self.tiles:
                rects.append(pygame.Rect(lookup_pos[0] * self.TILE_SIZE, lookup_pos[1] * self.TILE_SIZE, self.TILE_SIZE, self.TILE_SIZE))
        return rects
    
    def handle_death(self):
        if self.player_shielded:
            self.player_shielded = False
            if 'explosion' in self.sounds: self.sounds['explosion'].play()
            else: self.sounds['super_jump'].play()
            self.screen_shake = 15
            for i in range(60):
                angle = random.random() * math.pi * 2; speed = random.random() * 2
                self.sparks.append([self.player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.uniform(2, 4), 0.05, (170, 200, 255), True, 0.05])
            return

        if not self.dead:
            self.sounds['death'].play()
            self.screen_shake = 20
            if self.coins > self.save_data['high_score']:
                self.save_data['high_score'] = self.coins
                self.new_high_score = True
                self.write_save_file(self.save_data)
            self.dead = True
            self.run_coins_banked = False
            self.upgrade_selection = 0
            self.player.velocity = [1.3, -6]
            for i in range(380):
                angle = random.random() * math.pi; speed = random.random() * 1.5; physics_on = random.choice([False, True, True])
                self.sparks.append([self.player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.02, (12, 2, 2), physics_on, 0.1 * physics_on])
    # endregion
    
    def update(self, dt):
        if self.perk_selection_active:
            # Game is paused for perk selection, do nothing.
            return
        
        time_scale = dt * 60
        self.master_clock += 1
        # --- Update Biome Logic ---
        if not self.dead:
            next_biome_index = self.current_biome_index
            if self.current_biome_index + 1 < len(self.BIOMES):
                if self.coins >= self.BIOMES[self.current_biome_index + 1]['score_req']:
                    next_biome_index += 1
            if next_biome_index != self.current_biome_index:
                self.current_biome_index = next_biome_index
                self.load_biome_bgs(self.BIOMES[self.current_biome_index])
                self.sounds['warp'].play()
                self.screen_shake = 15
        
        # --- Update Time Scale Logic ---
        # ...
        
        # --- Update Other Timers (Freeze, Combo, Shake) ---
        if self.screen_shake > 0: self.screen_shake -= 0.5 * time_scale
        if self.freeze_timer > 0: self.freeze_timer -= 1 * time_scale
        # ... and so on for all other logic ...
        # (This is where the entire contents of your old main loop would go,
        # but structured cleanly as sequential updates.)
    
    def draw(self, surface):
        surface.blit(self.game_screen_before_ui, (0, 0))
        # Draw all UI elements, etc.
        # This becomes a much cleaner sequence of draw calls.
    
    def handle_event(self, event):
        if self.perk_selection_active:
            if event.type == KEYDOWN:
                if event.key in [K_DOWN, K_s]: self.perk_selection_choice = (self.perk_selection_choice + 1) % len(self.perks_to_offer)
                if event.key in [K_UP, K_w]: self.perk_selection_choice = (self.perk_selection_choice - 1 + len(self.perks_to_offer)) % len(self.perks_to_offer)
                if event.key in [K_RETURN, K_e, K_x]:
                    chosen_perk = self.perks_to_offer[self.perk_selection_choice]
                    self.active_perks.add(chosen_perk)
                    self.perk_selection_active = False
                    if 'upgrade' in self.sounds: self.sounds['upgrade'].play()
                    else: self.sounds['collect_item'].play()
            return
        
        if event.type == KEYDOWN:
            # ... and all other gameplay key handling ...

# Placeholder Classes - these must be defined outside or imported
class Player(Entity): pass
class Item(Entity): pass
class Projectile(Entity): pass