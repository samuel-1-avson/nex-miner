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

# HELPER CLASSES that are only used in Gameplay can stay here.
class Item(Entity):
    def __init__(self, *args, velocity=[0, 0]):
        super().__init__(*args)
        self.velocity = velocity
        self.time = 0

    def update(self, tiles, time_scale=1.0):
        self.time += 1 * time_scale
        self.velocity[1] = min(self.velocity[1] + 0.2, 3)
        self.velocity[0] = Gameplay.normalize(self.velocity[0], 0.05)
        self.move(self.velocity, tiles, time_scale)

class Player(Entity):
    def __init__(self, gameplay_state, *args):
        super().__init__(gameplay_state.animation_manager, *args)
        self.gameplay = gameplay_state
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
        if 'acrobat' in self.gameplay.active_perks and self.wall_contact_timer > 0:
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
                    self.gameplay.sparks.append([[self.center[0] + random.uniform(-7, 7), self.center[1]], [direction * (random.uniform(0.05, 0.1)) + (random.uniform(-2, 2)) * physics_on, random.uniform(0.05, 0.1) + random.uniform(0, 2) * physics_on], random.uniform(3, 6), 0.04 - 0.02 * physics_on, (6, 4, 1), physics_on, 0.05 * physics_on])
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
            self.gameplay.sparks.append([[self.center[0] - direction * 6, self.center[1] + random.uniform(-3, 3)], [-direction * (random.uniform(1, 2)), random.uniform(-0.5, 0.5)], random.uniform(2, 5), 0.15, (200, 220, 255), False, 0])
        else:
            target_velocity_x = 0
            if self.right: target_velocity_x = self.speed
            elif self.left: target_velocity_x = -self.speed
            self.velocity[0] += (target_velocity_x - self.velocity[0]) * 0.3
            if abs(self.velocity[0]) < 0.1: self.velocity[0] = 0

        if self.dash_timer > 0: self.velocity[1] = 0
        else:
            gravity = 0.3
            if 'feather_fall' in self.gameplay.active_perks: gravity = 0.24
            self.velocity[1] = min(self.velocity[1] + gravity, 4)

        if not self.gameplay.dead and self.dash_timer <= 0:
            if self.velocity[0] > 0.1: self.flip[0] = True
            if self.velocity[0] < -0.1: self.flip[0] = False

        if self.jumping:
            self.jump_rot += 16 * time_scale
            if self.jump_rot >= 360:
                self.jump_rot, self.jumping = 0, False
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
            self.velocity[1] = 0
            self.air_time = 0
            self.jumps = self.jumps_max
            self.jumping, self.rotation = False, 0
            if self.jump_buffer_timer > 0:
                self.jump_buffer_timer = 0
                self.gameplay.sounds['jump'].play()
                self.attempt_jump()
        elif was_on_ground: self.coyote_timer = 6
        return collisions

class Projectile(Entity):
    def __init__(self, gameplay_state, *args, velocity=[0, 0]):
        super().__init__(gameplay_state.animation_manager, *args)
        self.velocity = velocity
        self.health = 1
        if 'technician' in gameplay_state.active_perks: self.health = 2
    def update(self, time_scale=1.0):
        super().update(1/60, time_scale)
        self.pos[0] += self.velocity[0] * time_scale
        self.pos[1] += self.velocity[1] * time_scale

# This is our main Gameplay State
class Gameplay(State):
    def __init__(self, game):
        super().__init__(game)
        self.TILE_SIZE = 16
        self.WINDOW_TILE_SIZE = (int(self.game.display.get_width() // 16), int(self.game.display.get_height() // 16))
        self.load_assets()
        self.reset_game_state()

    # --- SETUP AND LOADING ---
    def reset_game_state(self):
        """Resets all variables for a new run"""
        self.player = Player(self, (self.game.DISPLAY_SIZE[0] // 2 - 5, -20), (8, 16), 'player')
        self.player.jumps_max += self.save_data['upgrades']['jumps']
        self.player.speed += self.save_data['upgrades']['speed'] * 0.08
        self.player.jumps = self.player.jumps_max
        self.dead = False
        self.tiles, self.tile_drops, self.sparks, self.projectiles, self.items = {}, [], [], [], []
        self.freeze_timer, self.game_timer, self.height, self.target_height, self.coins, self.end_coin_count = 0, 0, 0, 0, 0, 0
        self.current_item, self.master_clock, self.last_place, self.item_used = None, 0, 0, False
        self.time_meter, self.time_meter_max, self.time_scale, self.slowing_time = 120, 120, 1.0, False
        self.combo_multiplier, self.combo_timer, self.COMBO_DURATION = 1.0, 0, 180
        self.run_coins_banked, self.upgrade_selection, self.screen_shake, self.player_shielded = False, 0, 0, False
        self.current_biome_index, self.perk_selection_active, self.perk_selection_choice = 0, False, 0
        self.perks_to_offer, self.last_perk_score, self.new_high_score = [], 0, False
        self.active_perks.clear()

        for i in range(self.WINDOW_TILE_SIZE[0] - 2): self.tiles[(i + 1, self.WINDOW_TILE_SIZE[1] - 1)] = {'type': 'tile', 'data': {}}
        self.tiles[(1, self.WINDOW_TILE_SIZE[1] - 2)], self.tiles[(self.WINDOW_TILE_SIZE[0] - 2, self.WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}, {'type': 'tile', 'data': {}}
        self.stack_heights = [self.WINDOW_TILE_SIZE[1] - 1 for i in range(self.WINDOW_TILE_SIZE[0] - 2)]
        self.stack_heights[0] -= 1
        self.stack_heights[-1] -= 1
        self.load_biome_bgs(self.BIOMES[0])

    def load_assets(self):
        """Loads all assets and data files once"""
        self.save_data = self.load_save_file()
        self.UPGRADES = {'jumps':{'name':'Extra Jump','desc':'Max jumps +1','base_cost':50,'max_level':2},'speed':{'name':'Move Speed','desc':'Run faster','base_cost':40,'max_level':5},'item_luck':{'name':'Item Luck','desc':'Better chest loot','base_cost':100,'max_level':3},'coin_magnet':{'name':'Coin Magnet','desc':'Coins pull to you','base_cost':150,'max_level':4}}
        self.upgrade_keys = list(self.UPGRADES.keys())
        self.BIOMES = [{'name':'The Depths','score_req':0,'bg_color':(22,19,40),'bg_layers':('data/images/background.png','data/images/background.png'),'available_tiles':['tile','chest','fragile','bounce','spike','greed','magnetic'],'special_spawn_rate':{'magnetic':9}},{'name':'Goo-Grotto','score_req':125,'bg_color':(19,40,30),'bg_layers':('data/images/background_cave.png','data/images/background_cave.png'),'available_tiles':['tile','chest','fragile','bounce','spike','greed','sticky'],'special_spawn_rate':{'sticky':8}}]
        self.PERKS = {'acrobat':{'name':'Acrobat','desc':'First jump after wall contact is higher.'},'overcharge':{'name':'Overcharge','desc':'Dashing through tiles creates an explosion.'},'feather_fall':{'name':'Feather Fall','desc':'You fall 20% slower.'},'technician':{'name':'Technician','desc':'Projectiles pierce one tile.'},'greedy':{'name':'Greedy','desc':'Chests & Greed Tiles drop double coins.'},'glass_cannon':{'name':'Glass Cannon','desc':'Faster combo, but instant death.'}}
        self.active_perks, self.backgrounds, self.animation_manager, self.GLOW_CACHE = set(), {}, AnimationManager(), {}

        for sound in os.listdir('data/sfx'):
            self.sounds[sound.split('/')[-1].split('.')[0]] = pygame.mixer.Sound('data/sfx/' + sound)
        
        # ... Other loading here ...

        self.white_font, self.black_font = Font('data/fonts/small_font.png', (251, 245, 239)), Font('data/fonts/small_font.png', (0, 0, 1))
        
        self.item_icons = {key: self.load_img(f'data/images/{key}_icon.png') for key in ['cube','warp','jump','bomb','freeze','shield']}
        self.perk_icons = {key: self.load_img(f'data/images/perk_icons/{key}.png') for key in self.PERKS.keys()}

        self.shield_aura_img = self.load_img('data/images/shield_aura.png')
        self.shield_aura_img.set_alpha(150)

        pygame.mixer.music.load('data/music.wav')
        pygame.mixer.music.play(-1)

    # --- HELPER FUNCTIONS (NOW METHODS) ---
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
    
    @staticmethod
    def normalize(val, amt):
        if val > amt: val -= amt
        elif val < -amt: val += amt
        else: val = 0
        return val

    def load_img(self, path):
        img = pygame.image.load(path).convert()
        img.set_colorkey((0, 0, 0))
        return img
        
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
            else: self.sounds['super_jump'].play()
            self.screen_shake = 15
            for i in range(60):
                angle = random.random() * math.pi * 2
                speed = random.random() * 2
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
                angle, speed, physics_on = random.random() * math.pi, random.random() * 1.5, random.choice([False, True, True])
                self.sparks.append([self.player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.02, (12, 2, 2), physics_on, 0.1 * physics_on])
    
    def load_biome_bgs(self, biome_info):
        try:
            bg_far_path, bg_near_path = biome_info['bg_layers']
            far_surf = pygame.image.load(bg_far_path).convert()
            self.backgrounds['far'] = pygame.transform.scale(far_surf, self.game.DISPLAY_SIZE)
            near_surf = self.load_img(bg_near_path)
            self.backgrounds['near'] = pygame.transform.scale(near_surf, self.game.DISPLAY_SIZE)
        except (pygame.error, FileNotFoundError) as e:
            print(f"Warning: Could not load background for biome {biome_info['name']}. Reason: {e}")
            self.backgrounds['far'] = None
            self.backgrounds['near'] = None
    
    # --- CORE STATE METHODS ---

    def update(self, dt):
        """Main logic update for the gameplay state."""
        
        # The dt passed in is in seconds. time_scale needs a per-frame value.
        time_scale_update = dt * 60
        
        if self.perk_selection_active:
            # Game is paused, no updates.
            return
        
        # All logic from the old while loop goes here
        # ... (update biome logic) ...
        # ... (update player) ...
        # ... (update tiles, items, sparks, etc.) ...
        self.master_clock += 1 # Update clock if not paused
        
    def draw(self, surface):
        """Main drawing method."""
        # 'surface' is the game.display surface passed from the main loop
        surface.fill((20,20,20)) # A default background

        if self.perk_selection_active:
            self.game.display_copy.set_alpha(150) # Make background a bit dim
            surface.blit(self.game.display_copy, (0,0))
            self.draw_perk_ui(surface)
        else:
            self.draw_game(surface)
        
        self.apply_screen_shake(surface)
        
    def draw_game(self, surface):
        """Draws all the normal gameplay elements."""
        # ... All of your blitting logic for the game itself goes here
        pass # placeholder

    def draw_perk_ui(self, surface):
        """Draws the perk selection UI over the frozen game screen."""
        overlay = pygame.Surface(self.game.DISPLAY_SIZE, pygame.SRCALPHA)
        overlay.fill((10, 5, 20, 200))
        surface.blit(overlay, (0, 0))
        #... perk ui drawing
        pass # placeholder

    def apply_screen_shake(self, surface):
        """Applies screen shake effect after all drawing is done."""
        if self.screen_shake > 0:
            render_offset = [random.randint(0, int(self.screen_shake)) - int(self.screen_shake) // 2, random.randint(0, int(self.screen_shake)) - int(self.screen_shake) // 2]
            surface.blit(surface, render_offset)

    def handle_event(self, event):
        """Handles all player input."""
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
            return # Block other inputs

        # --- Gameplay and Game Over Inputs ---
        if event.type == KEYDOWN:
            if event.key == K_ESCAPE: self.game.running = False
            if event.key == K_r and self.dead: self.reset_game_state()

            if not self.dead:
                if event.key in [K_c, K_l] and self.player.focus_meter >= self.player.FOCUS_DASH_COST: self.player.is_charging_dash = True
                if event.key in [K_RIGHT, K_d]: self.player.right = True
                if event.key in [K_LEFT, K_a]: self.player.left = True
                if event.key in [K_UP, K_w, K_SPACE]:
                    self.player.jump_buffer_timer = 8
                    if self.player.air_time < 2 or self.player.coyote_timer > 0 or self.player.jumps > 0:
                        self.sounds['jump'].play()
                        self.player.attempt_jump()
                # ... other game inputs
            
            else: # If dead
                if self.run_coins_banked:
                    # ... upgrade menu inputs
                    pass
        
        if event.type == KEYUP and not self.dead:
             #... game keyup inputs
             pass