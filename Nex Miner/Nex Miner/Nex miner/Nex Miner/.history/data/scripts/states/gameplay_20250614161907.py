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
        
    def enter_state(self):
        super().enter_state()
        self.reset_run()
        
    def reset_run(self):
        # HELPER CLASSES that need access to the game state
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
        # We now use the dt passed from the game loop to manage time_scale
        time_scale_multiplier = dt * 60
        
        for event in events:
            self.handle_input(event)
        
        self.game_surface_cache = self.game.display.copy()

        if self.perk_selection_active:
            # We are in perk selection, so no game logic update, just handle input (done above)
            return

        self.update_gameplay(time_scale_multiplier)

    def render(self, surface):
        if self.perk_selection_active:
            surface.blit(self.game_surface_cache, (0, 0))
            self.render_perk_selection(surface)
        else:
            self.render_gameplay(surface)
            if not self.dead:
                self.render_hud(surface)
            else:
                self.render_game_over(surface)
                
    # --- MAJOR LOGIC SUB-FUNCTIONS ---
    
    def update_gameplay(self, time_scale):
        # Biome transition logic
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
        
        # Time Scale Management
        self.time_scale = 1.0
        if not self.dead:
            is_slowing_now = (pygame.key.get_pressed()[K_LSHIFT] and self.time_meter > 0) or self.player.is_charging_dash
            if is_slowing_now and not self.slowing_time: self.sounds['time_slow_start'].play()
            elif not is_slowing_now and self.slowing_time: self.sounds['time_slow_end'].play()
            self.slowing_time = is_slowing_now
            if self.slowing_time:
                self.time_scale = 0.4
                if self.player.is_charging_dash:
                    self.player.focus_meter = max(0, self.player.focus_meter - 1.5)
                    if self.player.focus_meter <= 0: self.player.is_charging_dash = False
                elif pygame.key.get_pressed()[K_LSHIFT]:
                    self.time_meter = max(0, self.time_meter - 0.75)
                    if self.time_meter <= 0: self.sounds['time_empty'].play()
            else:
                self.time_meter = min(self.time_meter_max, self.time_meter + 0.2)
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
            self.game_timer += time_scale
            if self.game_timer > 10 + 25 * (20000 - min(20000, self.master_clock)) / 20000:
                self.game_timer = 0
                self.spawn_tile()
        
        self.update_tile_drops()
        self.update_placed_tiles(time_scale)
        self.update_items(time_scale)
        self.update_projectiles(time_scale)

        edge_rects = [pygame.Rect(0, self.player.pos[1] - 300, self.TILE_SIZE, 600), pygame.Rect(self.TILE_SIZE * (self.WINDOW_TILE_SIZE[0] - 1), self.player.pos[1] - 300, self.TILE_SIZE, 600)]
        tile_rects = [pygame.Rect(self.TILE_SIZE * pos[0], self.TILE_SIZE * pos[1], self.TILE_SIZE, self.TILE_SIZE) for pos in self.tiles]
        
        if not self.dead:
            collisions = self.player.update(self.tile_drop_rects + edge_rects + tile_rects, self.time_scale * time_scale)
            self.handle_player_collisions(collisions)
        else:
            self.player.opacity = 80; self.player.update([], self.time_scale * time_scale); self.player.rotation -= 16
        
        self.update_sparks(time_scale)
        self.update_world_scroll()
        
        if self.freeze_timer > 0: self.freeze_timer -= 1 * time_scale

        # Check for perk offering
        if not self.dead and not self.perk_selection_active:
            score_interval = 75
            if self.coins > 0 and self.coins // score_interval > self.last_perk_score // score_interval:
                self.last_perk_score = self.coins
                available_perks = [p for p in self.PERKS.keys() if p not in self.active_perks]
                if available_perks:
                    self.perk_selection_active = True
                    self.perks_to_offer = random.sample(available_perks, k=min(3, len(available_perks)))
                    self.perk_selection_choice = 0
                    self.sounds['warp'].play()
    
    def render_gameplay(self, surface):
        current_biome = self.BIOMES[self.current_biome_index]
        surface.fill(current_biome['bg_color'])
        
        if self.backgrounds['far']:
            scroll_y = (self.height * 0.2) % self.game.DISPLAY_SIZE[1]
            surface.blit(self.backgrounds['far'], (0, scroll_y)); surface.blit(self.backgrounds['far'], (0, scroll_y - self.game.DISPLAY_SIZE[1]))
        if self.backgrounds['near']:
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
            freeze_overlay.fill((170, 200, 255, alpha))
            surface.blit(freeze_overlay, (0, 0))

        surface.blit(self.border_img_light, (0, -math.sin(self.master_clock / 30) * 4 - 7))
        surface.blit(self.border_img, (0, -math.sin(self.master_clock / 40) * 7 - 14))
        surface.blit(pygame.transform.flip(self.border_img_light, False, True), (0, self.game.DISPLAY_SIZE[1] + math.sin(self.master_clock / 40) * 3 + 9 - self.border_img.get_height()))
        surface.blit(pygame.transform.flip(self.border_img, False, True), (0, self.game.DISPLAY_SIZE[1] + math.sin(self.master_clock / 30) * 3 + 16 - self.border_img.get_height()))


    # --- FULLY PORTED METHODS FROM HERE DOWN ---
    # Methods are alphabetized for clarity

    def buy_upgrade(self):
        key = self.upgrade_keys[self.upgrade_selection]
        upgrade = self.UPGRADES[key]
        level = self.save_data['upgrades'][key]
        cost = int(upgrade['base_cost'] * (1.5 ** level))
        if level < upgrade['max_level'] and self.save_data['banked_coins'] >= cost:
            self.save_data['banked_coins'] -= cost
            self.save_data['upgrades'][key] += 1
            self.write_save(self.save_data)
            if 'upgrade' in self.sounds:
                self.sounds['upgrade'].play()

    def create_item_class(self):
        gs_ref = self
        class Item(Entity):
            def __init__(self, *args, velocity=[0, 0]):
                super().__init__(*args)
                self.velocity = velocity
                self.time = 0
            def update(self, tiles, time_scale=1.0):
                self.time += 1 * time_scale
                self.velocity[1] = min(self.velocity[1] + 0.2, 3)
                self.velocity[0] = gs_ref.normalize(self.velocity[0], 0.05)
                self.move(self.velocity, tiles, time_scale)
        return Item
    
    def create_player_class(self):
        gs_ref = self
        class Player(Entity):
            def __init__(self, *args):
                super().__init__(*args)
                self.velocity = [0, 0]
                self.right = False
                self.left = False
                self.speed = 1.4
                self.jumps = 2
                self.jumps_max = 2
                self.jumping = False
                self.jump_rot = 0
                self.air_time = 0
                self.coyote_timer = 0
                self.jump_buffer_timer = 0
                self.dash_timer = 0
                self.DASH_SPEED = 8
                self.DASH_DURATION = 8
                self.focus_meter = 100
                self.FOCUS_METER_MAX = 100
                self.is_charging_dash = False
                self.FOCUS_DASH_COST = 50
                self.FOCUS_RECHARGE_RATE = 0.4
                self.wall_contact_timer = 0

            def attempt_jump(self):
                jump_velocity = -5
                if 'acrobat' in gs_ref.active_perks and self.wall_contact_timer > 0:
                    jump_velocity = -6.5
                    self.wall_contact_timer = 0
                if self.jumps > 0 or self.coyote_timer > 0:
                    if self.jumps == self.jumps_max or self.coyote_timer > 0:
                        self.velocity[1] = jump_velocity
                    else:
                        self.velocity[1] = -4
                        for i in range(24):
                            physics_on = random.choice([False, False, True])
                            direction = 1 if i % 2 else -1
                            gs_ref.sparks.append([[self.center[0] + random.uniform(-7, 7), self.center[1]], [direction * (random.uniform(0.05, 0.1)) + (random.uniform(-2, 2)) * physics_on, random.uniform(0.05, 0.1) + random.uniform(0, 2) * physics_on], random.uniform(3, 6), 0.04 - 0.02 * physics_on, (6, 4, 1), physics_on, 0.05 * physics_on])
                    if self.coyote_timer <= 0:
                        self.jumps -= 1
                    self.coyote_timer = 0
                    self.jumping = True
                    self.jump_rot = 0
            
            def update(self, tiles, time_scale=1.0):
                super().update(1 / 60, time_scale)
                self.air_time += 1
                if self.coyote_timer > 0: self.coyote_timer -= 1
                if self.jump_buffer_timer > 0: self.jump_buffer_timer -= 1
                if self.dash_timer > 0: self.dash_timer -= 1 * time_scale

                if not self.is_charging_dash:
                    self.focus_meter = min(self.FOCUS_METER_MAX, self.focus_meter + self.FOCUS_RECHARGE_RATE * time_scale)
                if self.dash_timer > 0:
                    direction = 1 if self.flip[0] else -1
                    self.velocity[0] = direction * self.DASH_SPEED
                    gs_ref.sparks.append([[self.center[0] - direction * 6, self.center[1] + random.uniform(-3, 3)], [-direction * (random.uniform(1, 2)), random.uniform(-0.5, 0.5)], random.uniform(2, 5), 0.15, (200, 220, 255), False, 0])
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
                    self.jump_rot += 16 * time_scale
                    if self.jump_rot >= 360: self.jump_rot = 0; self.jumping = False
                    self.rotation = -self.jump_rot if self.flip[0] else self.jump_rot
                    self.scale[1] = 0.7
                else: self.scale[1] = 1
                if self.is_charging_dash: self.set_action('idle')
                elif self.dash_timer > 0: self.set_action('jump')
                elif self.air_time > 3: self.set_action('jump')
                elif abs(self.velocity[0]) > 0.1: self.set_action('run')
                else: self.set_action('idle')
                was_on_ground = self.air_time <= 1
                collisions = self.move(self.velocity, tiles, time_scale)
                if collisions['left'] or collisions['right']: self.wall_contact_timer = 15
                if self.wall_contact_timer > 0: self.wall_contact_timer -= 1
                if collisions['bottom']:
                    self.velocity[1] = 0; self.air_time = 0; self.jumps = self.jumps_max
                    self.jumping = False; self.rotation = 0
                    if self.jump_buffer_timer > 0:
                        self.jump_buffer_timer = 0
                        gs_ref.sounds['jump'].play()
                        self.attempt_jump()
                elif was_on_ground: self.coyote_timer = 6
                return collisions
        return Player

    def create_projectile_class(self):
        gs_ref = self
        class Projectile(Entity):
            def __init__(self, *args, velocity=[0, 0]):
                super().__init__(*args)
                self.velocity = velocity
                self.health = 2 if 'technician' in gs_ref.active_perks else 1
            def update(self, time_scale=1.0):
                super().update(1/60, time_scale)
                self.pos[0] += self.velocity[0] * time_scale
                self.pos[1] += self.velocity[1] * time_scale
        return Projectile

    def glow_img(self, size, color):
        if (size, color) not in self.GLOW_CACHE:
            surf = pygame.Surface((size * 2 + 2, size * 2 + 2))
            pygame.draw.circle(surf, color, (surf.get_width() // 2, surf.get_height() // 2), size)
            surf.set_colorkey((0, 0, 0))
            self.GLOW_CACHE[(size, color)] = surf
        return self.GLOW_CACHE[(size, color)]
        
    def handle_death(self):
        if self.player_shielded:
            self.player_shielded = False
            if 'explosion' in self.sounds: self.sounds['explosion'].play()
            self.screen_shake = 15
            for i in range(60):
                angle = random.random() * math.pi * 2; speed = random.random() * 2
                self.sparks.append([self.player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.uniform(2, 4), 0.05, (170, 200, 255), True, 0.05])
            return

        if not self.dead:
            self.sounds['death'].play(); self.screen_shake = 20
            if self.coins > self.save_data['high_score']:
                self.save_data['high_score'] = self.coins; self.new_high_score = True
                self.write_save(self.save_data)
            self.dead = True; self.run_coins_banked = False; self.upgrade_selection = 0
            self.player.velocity = [1.3, -6]
            for i in range(380):
                angle = random.random() * math.pi; speed = random.random() * 1.5
                physics_on = random.choice([False, True, True])
                self.sparks.append([self.player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.02, (12, 2, 2), physics_on, 0.1 * physics_on])

    def handle_input(self, event):
        if event.type == KEYDOWN:
            if self.perk_selection_active:
                if event.key in [K_DOWN, K_s]: self.perk_selection_choice = (self.perk_selection_choice + 1) % len(self.perks_to_offer)
                if event.key in [K_UP, K_w]: self.perk_selection_choice = (self.perk_selection_choice - 1 + len(self.perks_to_offer)) % len(self.perks_to_offer)
                if event.key in [K_RETURN, K_e, K_x]:
                    chosen_perk = self.perks_to_offer[self.perk_selection_choice]
                    self.active_perks.add(chosen_perk); self.perk_selection_active = False
                    if 'upgrade' in self.sounds: self.sounds['upgrade'].play()
                return

            if not self.dead:
                if event.key in [K_c, K_l] and self.player.focus_meter >= self.player.FOCUS_DASH_COST: self.player.is_charging_dash = True
                if event.key in [K_RIGHT, K_d]: self.player.right = True
                if event.key in [K_LEFT, K_a]: self.player.left = True
                if event.key in [K_UP, K_w, K_SPACE]:
                    self.player.jump_buffer_timer = 8
                    if self.player.air_time < 2 or self.player.coyote_timer > 0 or self.player.jumps > 0: self.sounds['jump'].play(); self.player.attempt_jump()
                if event.key in [K_z, K_k]: self.use_projectile()
                if event.key in [K_e, K_x]: self.use_item()
            else:
                if self.run_coins_banked:
                    if event.key == K_DOWN: self.upgrade_selection = (self.upgrade_selection + 1) % len(self.upgrade_keys)
                    if event.key == K_UP: self.upgrade_selection = (self.upgrade_selection - 1 + len(self.upgrade_keys)) % len(self.upgrade_keys)
                    if event.key == K_RETURN: self.buy_upgrade()
            if event.key == K_r and self.dead: self.reset_run()
            
        if event.type == KEYUP and not self.dead:
            if event.key in [K_c, K_l] and self.player.is_charging_dash:
                self.player.is_charging_dash = False; self.player.focus_meter -= self.player.FOCUS_DASH_COST; self.player.dash_timer = self.player.DASH_DURATION
                if 'explosion' in self.sounds: self.sounds['explosion'].play()
            if event.key in [K_RIGHT, K_d]: self.player.right = False
            if event.key in [K_LEFT, K_a]: self.player.left = False

    def handle_player_collisions(self, collisions):
        if not collisions['bottom'] and not self.dead:
            is_sliding = False
            if ((self.player.rect.left - 2) // self.TILE_SIZE, self.player.rect.centery // self.TILE_SIZE) in self.tiles and self.tiles[((self.player.rect.left - 2) // self.TILE_SIZE, self.player.rect.centery // self.TILE_SIZE)]['type'] == 'sticky': is_sliding = True
            if ((self.player.rect.right + 2) // self.TILE_SIZE, self.player.rect.centery // self.TILE_SIZE) in self.tiles and self.tiles[((self.player.rect.right + 2) // self.TILE_SIZE, self.player.rect.centery // self.TILE_SIZE)]['type'] == 'sticky': is_sliding = True
            if is_sliding: self.player.velocity[1] = min(self.player.velocity[1], 1.0)
        if collisions['bottom']:
            tile_pos_below = (self.player.rect.midbottom[0] // self.TILE_SIZE, self.player.rect.midbottom[1] // self.TILE_SIZE)
            if tile_pos_below in self.tiles:
                tile_type_below = self.tiles[tile_pos_below]['type']
                if tile_type_below == 'fragile' and 'timer' not in self.tiles[tile_pos_below]['data']: self.sounds['block_land'].play(); self.tiles[tile_pos_below]['data']['timer'] = 90
                elif tile_type_below == 'bounce':
                    self.player.velocity[1] = -9; self.player.jumps = self.player.jumps_max; self.sounds['super_jump'].play(); self.screen_shake = 10; self.combo_multiplier += 0.5; self.combo_timer = self.COMBO_DURATION
                    for i in range(40):
                        angle = random.random() * math.pi - math.pi; speed = random.random() * 2
                        self.sparks.append([[self.player.rect.centerx, self.player.rect.bottom], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 2, 0.04, (8, 2, 12), True, 0.1])
                elif tile_type_below == 'spike': self.handle_death(); self.player.velocity = [0, -4]
        
        # New magnetic tile logic
        for tile_pos, tile_data in self.tiles.items():
            if tile_data['type'] == 'magnetic':
                tile_screen_y = self.TILE_SIZE * tile_pos[1] + int(self.height)
                if 0 < tile_screen_y < self.game.DISPLAY_SIZE[1]:
                    distance = (tile_pos[0] * self.TILE_SIZE + self.TILE_SIZE // 2) - self.player.center[0]
                    self.player.velocity[0] += max(-0.25, min(0.25, distance / 80)) * self.time_scale

    def load_assets(self):
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
        self.motherlode_tile_img = self.load_img('data/images/motherlode_tile.png') 
        self.unstable_tile_img = self.load_img('data/images/unstable_tile.png')
        self.coin_icon = self.load_img('data/images/coin_icon.png')
        self.item_slot_img = self.load_img('data/images/item_slot.png')
        self.item_slot_flash_img = self.load_img('data/images/item_slot_flash.png')
        self.border_img = self.load_img('data/images/border.png')
        self.border_img_light = self.border_img.copy(); self.border_img_light.set_alpha(100)
        self.tile_top_img = self.load_img('data/images/tile_top.png')
        self.greed_tile_img = self.load_img('data/images/greed_tile.png')
        self.white_font = Font('data/fonts/small_font.png', (251, 245, 239))
        self.black_font = Font('data/fonts/small_font.png', (0, 0, 1))
        
        self.sounds = {s.split('/')[-1].split('.')[0] : pygame.mixer.Sound('data/sfx/' + s) for s in os.listdir('data/sfx')}
        for sound_name, sound in self.sounds.items(): sound.set_volume(0.5) # Generic volume, adjust specifics below
        self.sounds['block_land'].set_volume(0.5); self.sounds['coin'].set_volume(0.6); self.sounds['chest_open'].set_volume(0.8)
        self.sounds['coin_end'] = pygame.mixer.Sound('data/sfx/coin.wav'); self.sounds['coin_end'].set_volume(0.35)
        if 'upgrade' in self.sounds: self.sounds['upgrade'].set_volume(0.7)
        if 'explosion' in self.sounds: self.sounds['explosion'].set_volume(0.8)
        if 'combo_end' in self.sounds: self.sounds['combo_end'].set_volume(0.6)
        
        self.item_icons = {item: self.load_img(f'data/images/{item}_icon.png') for item in ['cube', 'warp', 'jump', 'bomb', 'freeze', 'shield']}
        self.shield_aura_img = self.load_img('data/images/shield_aura.png'); self.shield_aura_img.set_alpha(150)
        
        self.perk_icons = {}
        for perk_name in self.PERKS.keys():
            try: self.perk_icons[perk_name] = self.load_img(f'data/images/perk_icons/{perk_name}.png')
            except pygame.error: print(f"Warning: Could not load icon for perk '{perk_name}'.")

    def load_biome_bgs(self, biome_info):
        self.backgrounds = {}
        try:
            bg_far_path, bg_near_path = biome_info['bg_layers']
            self.backgrounds['far'] = pygame.transform.scale(pygame.image.load(bg_far_path).convert(), self.game.DISPLAY_SIZE)
            self.backgrounds['near'] = pygame.transform.scale(self.load_img(bg_near_path), self.game.DISPLAY_SIZE)
        except (pygame.error, FileNotFoundError) as e:
            self.backgrounds['far'] = None; self.backgrounds['near'] = None
            print(f"Warning: Could not load background for biome {biome_info['name']}. Reason: {e}")

    def load_img(self, path):
        img = pygame.image.load(path).convert()
        img.set_colorkey((0, 0, 0))
        return img
        
    def load_save(self):
        try:
            with open(self.SAVE_FILE, 'r') as f: data = json.load(f)
            if 'high_score' not in data: data['high_score'] = 0
            if 'coin_magnet' not in data['upgrades']: data['upgrades']['coin_magnet'] = 0
            return data
        except (FileNotFoundError, json.JSONDecodeError):
            default_save = {"banked_coins": 100, "upgrades": {"jumps": 0, "speed": 0, "item_luck": 0, "coin_magnet": 0}, "high_score": 0}
            self.write_save(default_save); return default_save

    def lookup_nearby(self, tiles_dict, pos):
        rects = []
        for offset in [(0, 0), (-1, -1), (-1, 0), (-1, 1), (0, 1), (0, -1), (1, -1), (1, 0), (1, 1)]:
            lookup_pos = (pos[0] // self.TILE_SIZE + offset[0], pos[1] // self.TILE_SIZE + offset[1])
            if lookup_pos in tiles_dict:
                rects.append(pygame.Rect(lookup_pos[0] * self.TILE_SIZE, lookup_pos[1] * self.TILE_SIZE, self.TILE_SIZE, self.TILE_SIZE))
        return rects
    
    @staticmethod
    def normalize(val, amt):
        if val > amt: val -= amt
        elif val < -amt: val += amt
        else: val = 0
        return val

    def recalculate_stack_heights(self):
        new_heights = [self.WINDOW_TILE_SIZE[1] for i in range(self.WINDOW_TILE_SIZE[0] - 2)]
        for tile_x, tile_y in self.tiles:
            if 1 <= tile_x < self.WINDOW_TILE_SIZE[0] - 1:
                new_heights[tile_x - 1] = min(new_heights[tile_x - 1], tile_y)
        self.stack_heights = new_heights

    # (the other rendering functions go here...)

    def use_item(self): pass # stubbed for now
    def use_projectile(self): pass # stubbed for now
    def update_tile_drops(self): pass # stubbed for now
    def update_placed_tiles(self, ts): pass
    def update_items(self, ts): pass
    def update_projectiles(self, ts): pass
    def update_sparks(self, ts): pass
    def update_world_scroll(self): pass

    def render_placed_tiles(self, surface): pass # stubbed
    def render_items(self, surface): pass
    def render_projectiles(self, surface): pass
    def render_sparks(self, surface): pass
    def render_shield_aura(self, surface): pass
    
    def spawn_tile(self):
        current_biome = self.BIOMES[self.current_biome_index]
        minimum = min(self.stack_heights); options = []
        for i, stack in enumerate(self.stack_heights):
            if i != self.last_place:
                offset = stack - minimum
                for j in range(int(offset ** (2.2 - min(20000, self.master_clock) / 10000)) + 1): options.append(i)
        
        tile_type = 'tile'
        elite_roll = random.randint(1, 100)
        if elite_roll <= 2: tile_type = 'motherlode'
        elif elite_roll <= 5: tile_type = 'unstable'
        else:
            roll = random.randint(1, 30)
            if roll == 1: tile_type = 'chest'
            elif roll < 4: tile_type = 'fragile'
            elif roll < 6: tile_type = 'bounce'
            elif roll == 7: tile_type = 'spike'
            for special_tile, spawn_chance in current_biome['special_spawn_rate'].items():
                if roll == spawn_chance: tile_type = special_tile
        if tile_type not in current_biome['available_tiles']: tile_type = 'tile'
        c = random.choice(options); self.last_place = c
        self.tile_drops.append([(c + 1) * self.TILE_SIZE, -self.height - self.TILE_SIZE, tile_type])

    def write_save(self, data):
        with open(self.SAVE_FILE, 'w') as f: json.dump(data, f, indent=4)