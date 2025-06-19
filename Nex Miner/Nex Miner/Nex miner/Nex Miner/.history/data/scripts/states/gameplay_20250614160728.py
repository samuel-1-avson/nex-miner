import os
import sys
import random
import math
import json
import pygame
from pygame.locals import *

# We must now import relative to the scripts folder
from ..entity import Entity
from ..anim_loader import AnimationManager
from ..text import Font
from .state_base import State # Import the base class

# Re-define Player and Item classes here for simplicity, or move them to their own modules
# This prevents circular import issues with a dedicated Game class if they needed it
class Item(Entity):
    def __init__(self, *args, velocity=[0, 0]):
        super().__init__(*args)
        self.velocity = velocity
        self.time = 0

    def update(self, tiles, time_scale=1.0):
        self.time += 1 * time_scale
        self.velocity[1] = min(self.velocity[1] + 0.2, 3)
        self.velocity[0] = self.normalize_helper(self.velocity[0], 0.05)
        self.move(self.velocity, tiles, time_scale)
        
    def normalize_helper(self, val, amt):
        if val > amt:
            val -= amt
        elif val < -amt:
            val += amt
        else:
            val = 0
        return val

class Player(Entity):
    def __init__(self, assets, pos, size, type, gameplay_state):
        super().__init__(assets, pos, size, type)
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

        # Dashing
        self.dash_timer = 0
        self.DASH_SPEED = 8
        self.DASH_DURATION = 8
        
        # Focus Dash Meter
        self.focus_meter = 100
        self.FOCUS_METER_MAX = 100
        self.is_charging_dash = False
        self.FOCUS_DASH_COST = 50
        self.FOCUS_RECHARGE_RATE = 0.4
        self.wall_contact_timer = 0

    def attempt_jump(self):
        jump_velocity = -5 # Base jump velocity
        
        # PERK EFFECT
        if 'acrobat' in self.gameplay.active_perks and self.wall_contact_timer > 0:
            jump_velocity = -6.5 # Stronger wall jump
            self.wall_contact_timer = 0

        if self.jumps > 0 or self.coyote_timer > 0:
            if self.jumps == self.jumps_max or self.coyote_timer > 0:
                self.velocity[1] = jump_velocity
            else:
                self.velocity[1] = -4 # Subsequent jumps are a bit weaker
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
            if self.right:
                target_velocity_x = self.speed
            elif self.left:
                target_velocity_x = -self.speed
            
            self.velocity[0] += (target_velocity_x - self.velocity[0]) * 0.3
            if abs(self.velocity[0]) < 0.1: self.velocity[0] = 0

        if self.dash_timer > 0:
            self.velocity[1] = 0
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
                self.jump_rot = 0
                self.jumping = False
            self.rotation = -self.jump_rot if self.flip[0] else self.jump_rot
            self.scale[1] = 0.7
        else:
            self.scale[1] = 1

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
            self.jumping = False
            self.rotation = 0
            if self.jump_buffer_timer > 0:
                self.jump_buffer_timer = 0
                self.gameplay.sounds['jump'].play()
                self.attempt_jump()
        else:
            if was_on_ground: self.coyote_timer = 6

        return collisions

class Projectile(Entity):
    def __init__(self, *args, velocity=[0, 0]):
        super().__init__(*args)
        self.velocity = velocity
        self.health = 1
        if 'technician' in self.game.gameplay_state.active_perks: # A bit tricky to access state
            self.health = 2

    def update(self, time_scale=1.0):
        super().update(1/60, time_scale)
        self.pos[0] += self.velocity[0] * time_scale
        self.pos[1] += self.velocity[1] * time_scale


class GameplayState(State):
    def __init__(self, game):
        super().__init__(game)
        
        # --- Constants and Definitions ---
        self.TILE_SIZE = 16
        self.WINDOW_TILE_SIZE = (int(self.game.display.get_width() // 16), int(self.game.display.get_height() // 16))
        
        self.SAVE_FILE = 'save.json'
        self.save_data = self.load_save()
        
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
            'acrobat': {'name': 'Acrobat', 'desc': 'First jump after wall contact is higher.'}, 'overcharge': {'name': 'Overcharge', 'desc': 'Dashing through tiles creates an explosion.'}, 'feather_fall': {'name': 'Feather Fall', 'desc': 'You fall 20% slower.'}, 'technician': {'name': 'Technician', 'desc': 'Projectiles pierce one tile.'}, 'greedy': {'name': 'Greedy', 'desc': 'Chests & Greed Tiles drop double coins.'}, 'glass_cannon': {'name': 'Glass Cannon', 'desc': 'Faster combo, but instant death.'},
        }
        
        # --- Asset Loading ---
        self.GLOW_CACHE = {}
        self.load_assets()

        # --- Game State Init ---
        self.reset_run()
        pygame.mixer.music.load('data/music.wav')
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)

    def reset_run(self):
        # The logic from your old 'K_r' restart block now lives here
        self.animation_manager = AnimationManager()
        self.player = Player(self.animation_manager, (self.game.DISPLAY_SIZE[0] // 2 - 5, -20), (8, 16), 'player', self)
        self.player.jumps_max += self.save_data['upgrades']['jumps']
        self.player.speed += self.save_data['upgrades']['speed'] * 0.08
        self.player.jumps = self.player.jumps_max
        
        self.dead = False
        self.tiles = {}
        self.tile_drops = []
        self.bg_particles = []
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
        self.active_perks = set()
        self.last_perk_score = 0
        self.new_high_score = False

        # Load initial background
        self.load_biome_bgs(self.BIOMES[0])

        # Setup initial level
        for i in range(self.WINDOW_TILE_SIZE[0] - 2):
            self.tiles[(i + 1, self.WINDOW_TILE_SIZE[1] - 1)] = {'type': 'tile', 'data': {}}

        self.tiles[(1, self.WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
        self.tiles[(self.WINDOW_TILE_SIZE[0] - 2, self.WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
        
        self.stack_heights = [self.WINDOW_TILE_SIZE[1] - 1 for i in range(self.WINDOW_TILE_SIZE[0] - 2)]
        self.stack_heights[0] -= 1
        self.stack_heights[-1] -= 1

    def update(self, dt, events):
        time_scale_multiplier = dt * 60 # To keep old logic compatible
        self.time_scale = 1.0 # Default time scale
        
        # --- Handle all input from the 'events' list ---
        for event in events:
            if event.type == KEYDOWN:
                self.handle_keydown(event.key)
            if event.type == KEYUP:
                self.handle_keyup(event.key)
                
        self.display_copy = self.game.display.copy()

        # Game Logic Update
        if not self.perk_selection_active:
            # Most of your old main loop logic goes here
            if not self.dead:
                # Update time slowdown
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
        
            if self.dead:
                self.slowing_time = False
                self.time_scale = 1.0

            if self.screen_shake > 0:
                self.screen_shake -= 0.5 * self.time_scale
                
            if self.combo_timer > 0:
                depletion_rate = 1
                if 'glass_cannon' in self.active_perks: depletion_rate = 2
                self.combo_timer -= depletion_rate * self.time_scale
            # ... and so on.
            
            # --- Move all your game update logic here ---
            # ... biome updates, tile drop logic, entity updates, etc ...
            
        self.master_clock += 1
        
        # update player
        tile_rects = [pygame.Rect(pos[0] * self.TILE_SIZE, pos[1] * self.TILE_SIZE, self.TILE_SIZE, self.TILE_SIZE) for pos in self.tiles]
        edge_rects = [
            pygame.Rect(0, self.player.pos[1] - 300, self.TILE_SIZE, 600),
            pygame.Rect(self.TILE_SIZE * (self.WINDOW_TILE_SIZE[0] - 1), self.player.pos[1] - 300, self.TILE_SIZE, 600)
        ]

        if not self.dead:
            collisions = self.player.update(self.tile_drops + edge_rects + tile_rects, self.time_scale)
            # handle collisions logic...
        else:
            self.player.opacity = 80
            self.player.update([], self.time_scale)
            self.player.rotation -= 16

    def render(self, surface):
        # All drawing code goes here, drawing to 'surface'
        surface.fill((0,0,1)) # Default background
        if self.perk_selection_active:
            surface.blit(self.display_copy, (0,0))
            overlay = pygame.Surface(self.game.DISPLAY_SIZE, pygame.SRCALPHA)
            overlay.fill((10, 5, 20, 200))
            surface.blit(overlay, (0, 0))
            # ... draw perk selection UI ...
        else:
            current_biome = self.BIOMES[self.current_biome_index]
            surface.fill(current_biome['bg_color'])
            
            # --- Rendering backgrounds, tiles, entities...
            if self.backgrounds['far']:
                scroll_y = (self.height * 0.2) % self.game.DISPLAY_SIZE[1]
                surface.blit(self.backgrounds['far'], (0, scroll_y))
                surface.blit(self.backgrounds['far'], (0, scroll_y - self.game.DISPLAY_SIZE[1]))
                
            #... and so on for all rendering calls, blitting to 'surface'.
            
            self.player.render(surface, (0, -int(self.height)))
            
            if not self.dead:
                # Render HUD
                pass
            else:
                # Render Game Over screen
                pass
                
        # Handle screen shake at the very end
        if self.screen_shake > 0:
            offset = [
                random.randint(0, int(self.screen_shake)) - int(self.screen_shake) // 2,
                random.randint(0, int(self.screen_shake)) - int(self.screen_shake) // 2
            ]
            shaken_surface = surface.copy()
            surface.fill((0,0,0))
            surface.blit(shaken_surface, offset)
        

    def handle_keydown(self, key):
        if self.perk_selection_active:
            # Handle perk selection input...
            return

        if key == K_r:
            if self.dead:
                self.reset_run()
                
        if not self.dead:
            if key in [K_c, K_l] and self.player.focus_meter >= self.player.FOCUS_DASH_COST:
                self.player.is_charging_dash = True
            if key in [K_RIGHT, K_d]: self.player.right = True
            if key in [K_LEFT, K_a]: self.player.left = True
            if key in [K_UP, K_w, K_SPACE]:
                self.player.jump_buffer_timer = 8
                if self.player.air_time < 2 or self.player.coyote_timer > 0 or self.player.jumps > 0:
                    self.sounds['jump'].play()
                    self.player.attempt_jump()
            # ... etc for other controls ...
        else: # Game Over Controls
            if self.run_coins_banked:
                #... handle upgrade buying input ...
                pass


    def handle_keyup(self, key):
        if self.dead: return
        if key in [K_c, K_l] and self.player.is_charging_dash:
            self.player.is_charging_dash = False
            self.player.focus_meter -= self.player.FOCUS_DASH_COST
            self.player.dash_timer = self.player.DASH_DURATION
            if 'explosion' in self.sounds: self.sounds['explosion'].play()
            else: self.sounds['block_land'].play()
        if key in [K_RIGHT, K_d]: self.player.right = False
        if key in [K_LEFT, K_a]: self.player.left = False

    # --- Helper Functions (Now as methods) ---

    def handle_death(self):
        if self.player_shielded:
            #...shield logic...
            return
        if not self.dead:
            self.sounds['death'].play()
            self.screen_shake = 20
            if self.coins > self.save_data['high_score']:
                self.save_data['high_score'] = self.coins
                self.new_high_score = True
                self.write_save(self.save_data)
            self.dead = True
            #... etc
            
    def load_save(self):
        try:
            with open(self.SAVE_FILE, 'r') as f:
                data = json.load(f)
            # handle old save files...
            return data
        except (FileNotFoundError, json.JSONDecodeError):
            default_save = {"banked_coins": 100, "upgrades": {"jumps": 0, "speed": 0, "item_luck": 0, "coin_magnet": 0}, "high_score": 0}
            self.write_save(default_save)
            return default_save

    def write_save(self, data):
        with open(self.SAVE_FILE, 'w') as f:
            json.dump(data, f, indent=4)
            
    def load_assets(self):
        self.backgrounds = {}
        # Load Images
        self.tile_img = self.load_img_helper('data/images/tile.png')
        # ... and all other images...
        
        # Load Fonts
        self.white_font = Font('data/fonts/small_font.png', (251, 245, 239))
        self.black_font = Font('data/fonts/small_font.png', (0, 0, 1))

        # Load Sounds
        self.sounds = {sound.split('/')[-1].split('.')[0] : pygame.mixer.Sound('data/sfx/' + sound) for sound in os.listdir('data/sfx')}
        self.sounds['block_land'].set_volume(0.5)
        #... set all other sound volumes...

    def load_img_helper(self, path):
        img = pygame.image.load(path).convert()
        img.set_colorkey((0, 0, 0))
        return img

    def load_biome_bgs(self, biome_info):
        # Logic to load and store biome backgrounds
        try:
            bg_far_path, bg_near_path = biome_info['bg_layers']
            far_surf = pygame.image.load(bg_far_path).convert()
            self.backgrounds['far'] = pygame.transform.scale(far_surf, self.game.DISPLAY_SIZE)
            near_surf = self.load_img_helper(bg_near_path)
            self.backgrounds['near'] = pygame.transform.scale(near_surf, self.game.DISPLAY_SIZE)
        except (pygame.error, FileNotFoundError) as e:
            print(f"Warning: Could not load background for biome {biome_info['name']}. Reason: {e}")
            self.backgrounds['far'] = None
            self.backgrounds['near'] = None