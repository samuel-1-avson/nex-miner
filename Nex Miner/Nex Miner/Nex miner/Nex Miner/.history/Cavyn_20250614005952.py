# Cavyn - Improved Version
# Refactored for better organization, performance, and maintainability

import os
import sys
import random
import math
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

import pygame
from pygame.locals import *

from data.scripts.entity import Entity
from data.scripts.anim_loader import AnimationManager
from data.scripts.text import Font

# Constants
TILE_SIZE = 16
DISPLAY_SIZE = (192, 256)
SAVE_FILE = 'save.json'
COMBO_DURATION = 180

class TileType(Enum):
    TILE = 'tile'
    PLACED_TILE = 'placed_tile'
    FRAGILE = 'fragile'
    BOUNCE = 'bounce'
    SPIKE = 'spike'
    CHEST = 'chest'
    OPENED_CHEST = 'opened_chest'
    GREED = 'greed'

class ItemType(Enum):
    COIN = 'coin'
    WARP = 'warp'
    CUBE = 'cube'
    JUMP = 'jump'
    BOMB = 'bomb'

@dataclass
class GameState:
    """Central game state management"""
    dead: bool = False
    game_timer: int = 0
    height: float = 0
    target_height: float = 0
    coins: int = 0
    end_coin_count: int = 0
    current_item: Optional[str] = None
    master_clock: int = 0
    last_place: int = 0
    item_used: bool = False
    combo_multiplier: float = 1.0
    combo_timer: int = 0
    run_coins_banked: bool = False
    upgrade_selection: int = 0
    screen_shake: float = 0
    new_high_score: bool = False
    current_palette_index: int = 0

class GameConfig:
    """Game configuration and constants"""
    UPGRADES = {
        'jumps': {'name': 'Extra Jump', 'desc': 'Max jumps +1', 'base_cost': 50, 'max_level': 2},
        'speed': {'name': 'Move Speed', 'desc': 'Run faster', 'base_cost': 40, 'max_level': 5},
        'item_luck': {'name': 'Item Luck', 'desc': 'Better chest loot', 'base_cost': 100, 'max_level': 3},
    }
    
    LEVEL_PALETTES = [
        {'score': 0, 'bg': (22, 19, 40), 'particles': [(0, 0, 0), (22, 19, 40)]},
        {'score': 75, 'bg': (40, 19, 30), 'particles': [(0, 0, 0), (40, 19, 30), (80, 20, 40)]},
        {'score': 200, 'bg': (19, 30, 40), 'particles': [(0, 0, 0), (19, 30, 40), (20, 60, 80)]},
        {'score': 400, 'bg': (40, 30, 19), 'particles': [(0, 0, 0), (40, 30, 19), (120, 60, 20)]},
    ]

class ResourceManager:
    """Handles loading and caching of game resources"""
    
    def __init__(self):
        self.images = {}
        self.sounds = {}
        self.fonts = {}
        self.glow_cache = {}
        self._load_resources()
    
    def _load_resources(self):
        """Load all game resources"""
        # Load images
        image_files = {
            'tile': 'data/images/tile.png',
            'chest': 'data/images/chest.png',
            'ghost_chest': 'data/images/ghost_chest.png',
            'opened_chest': 'data/images/opened_chest.png',
            'placed_tile': 'data/images/placed_tile.png',
            'edge_tile': 'data/images/edge_tile.png',
            'fragile_tile': 'data/images/fragile_tile.png',
            'bounce_tile': 'data/images/bounce_tile.png',
            'spike_tile': 'data/images/spike_tile.png',
            'coin_icon': 'data/images/coin_icon.png',
            'item_slot': 'data/images/item_slot.png',
            'item_slot_flash': 'data/images/item_slot_flash.png',
            'border': 'data/images/border.png',
            'tile_top': 'data/images/tile_top.png',
            'greed_tile': 'data/images/greed_tile.png'
        }
        
        for name, path in image_files.items():
            self.images[name] = self._load_image(path)
        
        # Create border light variant
        self.images['border_light'] = self.images['border'].copy()
        self.images['border_light'].set_alpha(100)
        
        # Load item icons
        item_icons = {
            'cube': 'data/images/cube_icon.png',
            'warp': 'data/images/warp_icon.png',
            'jump': 'data/images/jump_icon.png',
            'bomb': 'data/images/bomb_icon.png',
        }
        
        self.images['item_icons'] = {}
        for name, path in item_icons.items():
            self.images['item_icons'][name] = self._load_image(path)
        
        # Load sounds
        for sound_file in os.listdir('data/sfx'):
            if sound_file.endswith('.wav'):
                name = sound_file.split('.')[0]
                sound = pygame.mixer.Sound(f'data/sfx/{sound_file}')
                self._set_sound_volume(name, sound)
                self.sounds[name] = sound
        
        # Create special coin_end sound
        if 'coin' in self.sounds:
            self.sounds['coin_end'] = pygame.mixer.Sound('data/sfx/coin.wav')
            self.sounds['coin_end'].set_volume(0.35)
        
        # Load fonts
        self.fonts['white'] = Font('data/fonts/small_font.png', (251, 245, 239))
        self.fonts['black'] = Font('data/fonts/small_font.png', (0, 0, 1))
    
    def _load_image(self, path: str) -> pygame.Surface:
        """Load and prepare an image"""
        img = pygame.image.load(path).convert()
        img.set_colorkey((0, 0, 0))
        return img
    
    def _set_sound_volume(self, name: str, sound: pygame.mixer.Sound):
        """Set appropriate volume for different sound effects"""
        volume_settings = {
            'block_land': 0.5,
            'coin': 0.6,
            'chest_open': 0.8,
            'upgrade': 0.7,
            'explosion': 0.8,
            'combo_end': 0.6
        }
        
        if name in volume_settings:
            sound.set_volume(volume_settings[name])
    
    def get_glow_image(self, size: int, color: Tuple[int, int, int]) -> pygame.Surface:
        """Get cached glow effect image"""
        key = (size, color)
        if key not in self.glow_cache:
            surf = pygame.Surface((size * 2 + 2, size * 2 + 2))
            pygame.draw.circle(surf, color, (surf.get_width() // 2, surf.get_height() // 2), size)
            surf.set_colorkey((0, 0, 0))
            self.glow_cache[key] = surf
        return self.glow_cache[key]

class SaveManager:
    """Handles game save/load operations"""
    
    @staticmethod
    def load_save() -> Dict[str, Any]:
        """Load save data from file"""
        try:
            with open(SAVE_FILE, 'r') as f:
                data = json.load(f)
                # Handle old save files
                if 'high_score' not in data:
                    data['high_score'] = 0
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            default_save = {
                "banked_coins": 100,
                "upgrades": {"jumps": 0, "speed": 0, "item_luck": 0},
                "high_score": 0
            }
            SaveManager.write_save(default_save)
            return default_save
    
    @staticmethod
    def write_save(data: Dict[str, Any]):
        """Write save data to file"""
        with open(SAVE_FILE, 'w') as f:
            json.dump(data, f, indent=4)

class TileManager:
    """Manages tile operations and calculations"""
    
    def __init__(self, window_tile_size: Tuple[int, int]):
        self.window_tile_size = window_tile_size
        self.tiles = {}
        self.stack_heights = []
        self.tile_drops = []
        self._initialize_tiles()
    
    def _initialize_tiles(self):
        """Initialize starting tile configuration"""
        # Create base tiles
        for i in range(self.window_tile_size[0] - 2):
            self.tiles[(i + 1, self.window_tile_size[1] - 1)] = {'type': TileType.TILE.value, 'data': {}}
        
        # Add edge tiles
        self.tiles[(1, self.window_tile_size[1] - 2)] = {'type': TileType.TILE.value, 'data': {}}
        self.tiles[(self.window_tile_size[0] - 2, self.window_tile_size[1] - 2)] = {'type': TileType.TILE.value, 'data': {}}
        
        # Calculate initial stack heights
        self.recalculate_stack_heights()
    
    def recalculate_stack_heights(self):
        """Recalculate stack heights for tile generation"""
        new_heights = [self.window_tile_size[1] for i in range(self.window_tile_size[0] - 2)]
        for tile_x, tile_y in self.tiles:
            if 1 <= tile_x < self.window_tile_size[0] - 1:
                col_index = tile_x - 1
                new_heights[col_index] = min(new_heights[col_index], tile_y)
        self.stack_heights = new_heights
    
    def get_random_tile_type(self, master_clock: int) -> str:
        """Generate random tile type based on probability"""
        roll = random.randint(1, 30)
        if roll == 1:
            return TileType.CHEST.value
        elif roll < 4:
            return TileType.FRAGILE.value
        elif roll < 6:
            return TileType.BOUNCE.value
        elif roll == 7:
            return TileType.SPIKE.value
        elif roll == 8:
            return TileType.GREED.value
        else:
            return TileType.TILE.value
    
    def lookup_nearby_tiles(self, pos: Tuple[float, float]) -> List[pygame.Rect]:
        """Get collision rectangles for tiles near a position"""
        rects = []
        offsets = [(0, 0), (-1, -1), (-1, 0), (-1, 1), (0, 1), (0, -1), (1, -1), (1, 0), (1, 1)]
        
        for offset in offsets:
            lookup_pos = (pos[0] // TILE_SIZE + offset[0], pos[1] // TILE_SIZE + offset[1])
            if lookup_pos in self.tiles:
                rects.append(pygame.Rect(lookup_pos[0] * TILE_SIZE, lookup_pos[1] * TILE_SIZE, TILE_SIZE, TILE_SIZE))
        
        return rects

class ParticleSystem:
    """Manages visual effects and particles"""
    
    def __init__(self):
        self.sparks = []
        self.bg_particles = []
    
    def add_spark(self, pos: List[float], velocity: List[float], size: float, 
                  decay: float, color: Tuple[int, int, int], physics: bool = False, gravity: float = 0):
        """Add a spark particle"""
        self.sparks.append([pos, velocity, size, decay, color, physics, gravity, False])
    
    def add_bg_particle(self, pos: List[float], parallax: float, size: int, 
                       speed: float, color: Tuple[int, int, int]):
        """Add a background particle"""
        self.bg_particles.append([pos, parallax, size, speed, color])
    
    def update_sparks(self, display: pygame.Surface, height: float, tiles: Dict, resources: ResourceManager):
        """Update and render spark particles"""
        for i, spark in sorted(enumerate(self.sparks), reverse=True):
            # Ensure spark has all required elements
            if len(spark) < 8:
                spark.append(False)
            
            # Apply gravity if physics enabled
            if not spark[-1] and spark[5]:  # physics enabled and not grounded
                spark[1][1] = min(spark[1][1] + spark[6], 3)
            
            # Update position
            spark[0][0] += spark[1][0]
            spark[0][1] += spark[1][1]
            
            # Handle collisions if physics enabled
            if spark[5]:
                self._handle_spark_physics(spark, tiles, display)
            
            # Update size
            spark[2] -= spark[3]
            
            # Remove if too small
            if spark[2] <= 1:
                self.sparks.pop(i)
            else:
                self._render_spark(spark, display, height, resources)
    
    def _handle_spark_physics(self, spark: List, tiles: Dict, display: pygame.Surface):
        """Handle physics collisions for sparks"""
        # X collision
        tile_pos_x = (int(spark[0][0] // TILE_SIZE), int(spark[0][1] // TILE_SIZE))
        if (tile_pos_x in tiles) or (spark[0][0] < TILE_SIZE) or (spark[0][0] > DISPLAY_SIZE[0] - TILE_SIZE):
            spark[0][0] -= spark[1][0]
            spark[1][0] *= -0.7
        
        # Y collision
        tile_pos_y = (int(spark[0][0] // TILE_SIZE), int(spark[0][1] // TILE_SIZE))
        if tile_pos_y in tiles:
            spark[0][1] -= spark[1][1]
            spark[1][1] *= -0.7
            if abs(spark[1][1]) < 0.1:
                spark[1][1] = 0
                spark[-1] = True  # Mark as grounded
    
    def _render_spark(self, spark: List, display: pygame.Surface, height: float, resources: ResourceManager):
        """Render a single spark particle"""
        size = int(spark[2])
        pos_x = int(spark[0][0] - size)
        pos_y = int(spark[0][1] + height - size)
        
        # Render glow effect
        glow_img = resources.get_glow_image(int(spark[2] * 1.5 + 2), 
                                          (int(spark[4][0] / 2), int(spark[4][1] / 2), int(spark[4][2] / 2)))
        display.blit(glow_img, (pos_x - size, pos_y - size), special_flags=BLEND_RGBA_ADD)
        
        glow_img2 = resources.get_glow_image(size, spark[4])
        display.blit(glow_img2, (pos_x, pos_y), special_flags=BLEND_RGBA_ADD)
        
        # Render center pixel
        if 0 <= int(spark[0][0]) < DISPLAY_SIZE[0] and 0 <= int(spark[0][1] + height) < DISPLAY_SIZE[1]:
            display.set_at((int(spark[0][0]), int(spark[0][1] + height)), (255, 255, 255))

class Game:
    """Main game class that orchestrates everything"""
    
    def __init__(self):
        # Initialize Pygame
        pygame.init()
        pygame.display.set_caption('Cavyn')
        
        # Create display surfaces
        self.screen = pygame.display.set_mode((DISPLAY_SIZE[0] * 3, DISPLAY_SIZE[1] * 3), 0, 32)
        self.display = pygame.Surface(DISPLAY_SIZE)
        pygame.mouse.set_visible(False)
        
        # Initialize game systems
        self.clock = pygame.time.Clock()
        self.window_tile_size = (int(self.display.get_width() // 16), int(self.display.get_height() // 16))
        
        # Initialize managers
        self.resources = ResourceManager()
        self.save_data = SaveManager.load_save()
        self.state = GameState()
        self.config = GameConfig()
        self.tile_manager = TileManager(self.window_tile_size)
        self.particle_system = ParticleSystem()
        
        # Initialize game objects
        self.animation_manager = AnimationManager()
        self.player = self._create_player()
        self.items = []
        
        # Start music
        pygame.mixer.music.load('data/music.wav')
        pygame.mixer.music.play(-1)
        
        # Utility functions
        self.normalize = lambda val, amt: val - amt if val > amt else val + amt if val < -amt else 0
    
    def _create_player(self):
        """Create and configure the player"""
        from data.scripts.entity import Entity  # Assuming Player extends Entity
        
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
            
            def attempt_jump(self):
                if self.jumps or self.coyote_timer > 0:
                    if self.jumps == self.jumps_max or self.coyote_timer > 0:
                        self.velocity[1] = -5
                    else:
                        self.velocity[1] = -4
                        # Add jump particles
                        for i in range(24):
                            physics_on = random.choice([False, False, True])
                            direction = 1 if i % 2 == 0 else -1
                            game.particle_system.add_spark(
                                [self.center[0] + random.random() * 14 - 7, self.center[1]],
                                [direction * (random.random() * 0.05 + 0.05) + (random.random() * 4 - 2) * physics_on,
                                 random.random() * 0.05 + random.random() * 2 * physics_on],
                                random.random() * 3 + 3,
                                0.04 - 0.02 * physics_on,
                                (6, 4, 1),
                                physics_on,
                                0.05 * physics_on
                            )
                    
                    is_coyote_jump = self.coyote_timer > 0 and self.jumps == self.jumps_max
                    if not is_coyote_jump:
                        self.jumps -= 1
                    
                    self.coyote_timer = 0
                    self.jumping = True
                    self.jump_rot = 0
            
            def update(self, tiles):
                super().update(1 / 60)
                
                # Update timers
                if self.coyote_timer > 0:
                    self.coyote_timer -= 1
                if self.jump_buffer_timer > 0:
                    self.jump_buffer_timer -= 1
                
                self.air_time += 1
                
                # Handle jumping animation
                if self.jumping:
                    self.jump_rot += 16
                    if self.jump_rot >= 360:
                        self.jump_rot = 0
                        self.jumping = False
                    self.rotation = -self.jump_rot if self.flip[0] else self.jump_rot
                    self.scale[1] = 0.7
                else:
                    self.scale[1] = 1
                
                # Apply gravity
                self.velocity[1] = min(self.velocity[1] + 0.3, 4)
                motion = self.velocity.copy()
                
                # Handle movement input
                if not game.state.dead:
                    if self.right:
                        motion[0] += self.speed
                    if self.left:
                        motion[0] -= self.speed
                    if motion[0] > 0:
                        self.flip[0] = True
                    elif motion[0] < 0:
                        self.flip[0] = False
                
                # Set animation
                if self.air_time > 3:
                    self.set_action('jump')
                elif motion[0] != 0:
                    self.set_action('run')
                else:
                    self.set_action('idle')
                
                was_on_ground = self.air_time == 0
                collisions = self.move(motion, tiles)
                
                # Handle ground landing
                if collisions['bottom']:
                    self.jumps = self.jumps_max
                    self.jumping = False
                    self.rotation = 0
                    self.velocity[1] = 0
                    self.air_time = 0
                    if self.jump_buffer_timer > 0:
                        self.jump_buffer_timer = 0
                        game.resources.sounds['jump'].play()
                        self.attempt_jump()
                else:
                    if was_on_ground:
                        self.coyote_timer = 6
                
                return collisions
        
        player = Player(self.animation_manager, (DISPLAY_SIZE[0] // 2 - 5, -20), (8, 16), 'player')
        player.jumps_max += self.save_data['upgrades']['jumps']
        player.speed += self.save_data['upgrades']['speed'] * 0.08
        player.jumps = player.jumps_max
        return player
    
    def update_visual_progression(self):
        """Update visual level progression based on score"""
        if not self.state.dead:
            next_palette_index = 0
            for i, palette in enumerate(self.config.LEVEL_PALETTES):
                if self.state.coins >= palette['score']:
                    next_palette_index = i
            
            if next_palette_index != self.state.current_palette_index:
                self.state.current_palette_index = next_palette_index
    
    def handle_death(self):
        """Handle player death"""
        if not self.state.dead:
            self.resources.sounds['death'].play()
            self.state.screen_shake = 20
            
            # Check for high score
            if self.state.coins > self.save_data['high_score']:
                self.save_data['high_score'] = self.state.coins
                self.state.new_high_score = True
                SaveManager.write_save(self.save_data)
            
            self.state.dead = True
            self.state.run_coins_banked = False
            self.state.upgrade_selection = 0
            self.player.velocity = [1.3, -6]
            
            # Add death particles
            for i in range(380):
                angle = random.random() * math.pi
                speed = random.random() * 1.5
                physics_on = random.choice([False, True, True])
                self.particle_system.add_spark(
                    self.player.center.copy(),
                    [math.cos(angle) * speed, math.sin(angle) * speed],
                    random.random() * 3 + 3,
                    0.02,
                    (12, 2, 2),
                    physics_on,
                    0.1 * physics_on
                )
    
    def run(self):
        """Main game loop"""
        while True:
            self.update()
            self.render()
            self.handle_events()
            
            # Apply screen shake
            render_offset = [0, 0]
            if self.state.screen_shake > 0:
                render_offset[0] = random.randint(0, int(self.state.screen_shake)) - int(self.state.screen_shake) // 2
                render_offset[1] = random.randint(0, int(self.state.screen_shake)) - int(self.state.screen_shake) // 2
            
            self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()), render_offset)
            pygame.display.update()
            self.clock.tick(60)
    
    def update(self):
        """Update game logic"""
        self.state.master_clock += 1
        
        if self.state.screen_shake > 0:
            self.state.screen_shake -= 0.5
        
        self.update_visual_progression()
        
        # Update combo system
        if self.state.combo_timer > 0:
            self.state.combo_timer -= 1
            if self.state.combo_timer == 0 and self.state.combo_multiplier > 1.0:
                if 'combo_end' in self.resources.sounds:
                    self.resources.sounds['combo_end'].play()
                # Add combo end particles
                for i in range(20):
                    angle = random.random() * math.pi * 2
                    speed = random.random() * 1.5
                    self.particle_system.add_spark(
                        [DISPLAY_SIZE[0] // 2, 10],
                        [math.cos(angle) * speed, math.sin(angle) * speed],
                        random.random() * 2 + 1,
                        0.05,
                        (251, 245, 239),
                        True,
                        0.05
                    )
                self.state.combo_multiplier = 1.0
        
        # Update game systems
        self._update_tile_generation()
        self._update_player()
        self._update_items()
        self._update_tiles()
    
    def _update_tile_generation(self):
        """Update tile generation logic"""
        if self.state.master_clock > 180:
            self.state.game_timer += 1
            if self.state.game_timer > 10 + 25 * (20000 - min(20000, self.state.master_clock)) / 20000:
                self.state.game_timer = 0
                minimum = min(self.tile_manager.stack_heights)
                options = []
                
                for i, stack in enumerate(self.tile_manager.stack_heights):
                    if i != self.state.last_place:
                        offset = stack - minimum
                        weight = int(offset ** (2.2 - min(20000, self.state.master_clock) / 10000)) + 1
                        options.extend([i] * weight)
                
                if options:
                    c = random.choice(options)
                    self.state.last_place = c
                    tile_type = self.tile_manager.get_random_tile_type(self.state.master_clock)
                    self.tile_manager.tile_drops.append(
                        [(c + 1) * TILE_SIZE, -self.state.height - TILE_SIZE, tile_type]
                    )
    
    def _update_player(self):
        """Update player logic"""
        if not self.state.dead:
            # Create collision rectangles
            tile_drop_rects = [pygame.Rect(tile[0], tile[1], TILE_SIZE, TILE_SIZE) 
                             for tile in self.tile_manager.tile_drops]
            edge_rects = [
                pygame.Rect(0, self.player.pos[1] - 300, TILE_SIZE, 600),
                pygame.Rect(TILE_SIZE * (self.window_tile_size[0] - 1), self.player.pos[1] - 300, TILE_SIZE, 600)
            ]
            tile_rects = [pygame.Rect(TILE_SIZE * pos[0], TILE_SIZE * pos[1], TILE_SIZE, TILE_SIZE) 
                         for pos in self.tile_manager.tiles]
            
            collisions = self.player.update(tile_drop_rects + edge_rects + tile_rects)
            
            # Handle tile interactions
            if collisions['bottom']:
                self._handle_tile_collision()
        else:
            self.player.opacity = 80
            self.player.update([])
            self.player.rotation -= 16
    
    def _handle_tile_collision(self):
        """Handle player collision with tiles"""
        player_feet_pos = self.player.rect.midbottom
        tile_pos_below = (player_feet_pos[0] // TILE_SIZE, player_feet_pos[1] // TILE_SIZE)
        
        if tile_pos_below in self.tile_manager.tiles:
            tile_type_below = self.tile_manager.tiles[tile_pos_below]['type']
            
            if tile_type_below == TileType.FRAGILE.value:
                if 'timer' not in self.tile_manager.tiles[tile_pos_below]['data']:
                    self.resources.sounds['block_land'].play()
                    self.tile_manager.tiles[tile_pos_below]['data']['timer'] = 90
            elif tile_type_below == TileType.BOUNCE.value:
                self.player.velocity[1] = -9
                self.player.jumps = self.player.jumps_max
                self.resources.sounds['super_jump'].play()
                self.state.screen_shake = 10
                self.state.combo_multiplier += 0.5
                self.state.combo_timer = COMBO_DURATION
                # Add bounce particles
                for i in range(40):
                    angle = random.random() * math.pi - math.pi
                    speed = random.random() * 2
                    self.particle_system