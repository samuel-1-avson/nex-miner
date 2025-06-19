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
                # Continuing from the bounce particle effect...
                for i in range(40):
                    angle = random.random() * math.pi - math.pi
                    speed = random.random() * 2
                    self.particle_system.add_spark(
                        [tile_pos_below[0] * TILE_SIZE + TILE_SIZE // 2, tile_pos_below[1] * TILE_SIZE],
                        [math.cos(angle) * speed, math.sin(angle) * speed],
                        random.random() * 3 + 2,
                        0.03,
                        (100, 200, 255),
                        True,
                        0.08
                    )
            elif tile_type_below == TileType.SPIKE.value:
                self.handle_death()
            elif tile_type_below == TileType.CHEST.value:
                self._open_chest(tile_pos_below)
            elif tile_type_below == TileType.GREED.value:
                if not self.state.current_item:
                    self.handle_death()
                else:
                    # Greed tile consumes item but gives coins
                    coins_gained = 15 * int(self.state.combo_multiplier)
                    self.state.coins += coins_gained
                    self.state.current_item = None
                    self.state.combo_multiplier += 1.0
                    self.state.combo_timer = COMBO_DURATION
                    self.resources.sounds['coin'].play()
                    
                    # Add greed particle effect
                    for i in range(30):
                        angle = random.random() * math.pi * 2
                        speed = random.random() * 1.5
                        self.particle_system.add_spark(
                            [tile_pos_below[0] * TILE_SIZE + TILE_SIZE // 2, tile_pos_below[1] * TILE_SIZE],
                            [math.cos(angle) * speed, math.sin(angle) * speed],
                            random.random() * 2 + 2,
                            0.04,
                            (200, 150, 0),
                            True,
                            0.06
                        )
                    
                    # Remove the greed tile
                    del self.tile_manager.tiles[tile_pos_below]
                    self.tile_manager.recalculate_stack_heights()
    
    def _open_chest(self, chest_pos: Tuple[int, int]):
        """Open a chest and spawn loot"""
        self.tile_manager.tiles[chest_pos]['type'] = TileType.OPENED_CHEST.value
        self.resources.sounds['chest_open'].play()
        self.state.screen_shake = 5
        
        # Determine loot based on item luck upgrade
        item_luck = self.save_data['upgrades']['item_luck']
        loot_roll = random.randint(1, 100)
        
        # Adjust probabilities based on item luck
        coin_threshold = 60 - (item_luck * 10)  # Better items with higher luck
        rare_threshold = 85 - (item_luck * 5)
        
        if loot_roll <= coin_threshold:
            # Spawn coins
            coin_count = random.randint(3, 8 + item_luck * 2)
            for i in range(coin_count):
                angle = random.random() * math.pi * 2
                speed = random.random() * 2 + 1
                self.items.append({
                    'type': ItemType.COIN.value,
                    'pos': [chest_pos[0] * TILE_SIZE + TILE_SIZE // 2, chest_pos[1] * TILE_SIZE],
                    'velocity': [math.cos(angle) * speed, math.sin(angle) * speed - 2],
                    'timer': 0,
                    'collected': False
                })
        elif loot_roll <= rare_threshold:
            # Spawn common items
            item_types = [ItemType.CUBE.value, ItemType.JUMP.value]
            if item_luck >= 2:
                item_types.append(ItemType.WARP.value)
            
            item_type = random.choice(item_types)
            self.items.append({
                'type': item_type,
                'pos': [chest_pos[0] * TILE_SIZE + TILE_SIZE // 2, chest_pos[1] * TILE_SIZE],
                'velocity': [0, -3],
                'timer': 0,
                'collected': False
            })
        else:
            # Spawn rare items
            rare_items = [ItemType.BOMB.value]
            if item_luck >= 3:
                rare_items.append(ItemType.WARP.value)
            
            item_type = random.choice(rare_items)
            self.items.append({
                'type': item_type,
                'pos': [chest_pos[0] * TILE_SIZE + TILE_SIZE // 2, chest_pos[1] * TILE_SIZE],
                'velocity': [0, -3],
                'timer': 0,
                'collected': False
            })
        
        # Add chest opening particles
        for i in range(25):
            angle = random.random() * math.pi - math.pi / 2
            speed = random.random() * 2 + 0.5
            self.particle_system.add_spark(
                [chest_pos[0] * TILE_SIZE + TILE_SIZE // 2, chest_pos[1] * TILE_SIZE],
                [math.cos(angle) * speed, math.sin(angle) * speed],
                random.random() * 2 + 2,
                0.03,
                (255, 215, 0),
                True,
                0.05
            )
    
    def _update_items(self):
        """Update item logic"""
        for i, item in sorted(enumerate(self.items), reverse=True):
            item['timer'] += 1
            
            # Apply gravity to items
            item['velocity'][1] = min(item['velocity'][1] + 0.2, 3)
            item['pos'][0] += item['velocity'][0]
            item['pos'][1] += item['velocity'][1]
            
            # Handle item collision with tiles
            item_rect = pygame.Rect(item['pos'][0] - 4, item['pos'][1] - 4, 8, 8)
            tile_rects = self.tile_manager.lookup_nearby_tiles(item['pos'])
            
            for tile_rect in tile_rects:
                if item_rect.colliderect(tile_rect):
                    if item['velocity'][1] > 0:  # Falling down
                        item['pos'][1] = tile_rect.top - 4
                        item['velocity'][1] = item['velocity'][1] * -0.6
                        item['velocity'][0] *= 0.8
                        if abs(item['velocity'][1]) < 0.5:
                            item['velocity'][1] = 0
                    break
            
            # Check collision with player
            player_rect = self.player.rect
            if not self.state.dead and item_rect.colliderect(player_rect) and not item['collected']:
                self._collect_item(item, i)
            
            # Remove items that fall too far or are too old
            if item['pos'][1] > DISPLAY_SIZE[1] + 100 or item['timer'] > 1800:
                self.items.pop(i)
    
    def _collect_item(self, item: Dict, item_index: int):
        """Handle item collection"""
        item['collected'] = True
        
        if item['type'] == ItemType.COIN.value:
            coins_gained = int(1 * self.state.combo_multiplier)
            self.state.coins += coins_gained
            self.state.combo_multiplier += 0.1
            self.state.combo_timer = COMBO_DURATION
            self.resources.sounds['coin'].play()
            
            # Add coin collection particles
            for i in range(12):
                angle = random.random() * math.pi * 2
                speed = random.random() * 1.2
                self.particle_system.add_spark(
                    item['pos'].copy(),
                    [math.cos(angle) * speed, math.sin(angle) * speed],
                    random.random() * 2 + 1,
                    0.05,
                    (255, 215, 0)
                )
        else:
            # Handle item pickup
            if not self.state.current_item:
                self.state.current_item = item['type']
                self.resources.sounds['item_pickup'].play()
            else:
                # Replace current item
                self.state.current_item = item['type']
                self.resources.sounds['item_pickup'].play()
        
        self.items.pop(item_index)
    
    def _update_tiles(self):
        """Update tile logic"""
        # Update falling tiles
        for i, tile_drop in sorted(enumerate(self.tile_manager.tile_drops), reverse=True):
            tile_drop[1] += 2.5
            
            # Check if tile has landed
            tile_pos = (int(tile_drop[0] // TILE_SIZE), int(tile_drop[1] // TILE_SIZE))
            if tile_pos in self.tile_manager.tiles or tile_drop[1] >= DISPLAY_SIZE[1] - TILE_SIZE - self.state.height:
                # Place the tile
                place_y = tile_pos[1]
                while (tile_pos[0], place_y) in self.tile_manager.tiles:
                    place_y -= 1
                
                if place_y >= 0:
                    self.tile_manager.tiles[(tile_pos[0], place_y)] = {
                        'type': tile_drop[2],
                        'data': {}
                    }
                    self.tile_manager.recalculate_stack_heights()
                
                self.tile_manager.tile_drops.pop(i)
        
        # Update tile timers and effects
        tiles_to_remove = []
        for tile_pos, tile_data in self.tile_manager.tiles.items():
            if tile_data['type'] == TileType.FRAGILE.value:
                if 'timer' in tile_data['data']:
                    tile_data['data']['timer'] -= 1
                    if tile_data['data']['timer'] <= 0:
                        tiles_to_remove.append(tile_pos)
                        # Add destruction particles
                        for j in range(15):
                            angle = random.random() * math.pi * 2
                            speed = random.random() * 1.5
                            self.particle_system.add_spark(
                                [tile_pos[0] * TILE_SIZE + TILE_SIZE // 2, tile_pos[1] * TILE_SIZE + TILE_SIZE // 2],
                                [math.cos(angle) * speed, math.sin(angle) * speed],
                                random.random() * 2 + 1,
                                0.04,
                                (139, 69, 19),
                                True,
                                0.06
                            )
        
        # Remove destroyed tiles
        for tile_pos in tiles_to_remove:
            del self.tile_manager.tiles[tile_pos]
        
        if tiles_to_remove:
            self.tile_manager.recalculate_stack_heights()
        
        # Update height smoothly
        if not self.state.dead:
            player_height = -self.player.pos[1] + 150
            if player_height > self.state.target_height:
                self.state.target_height = player_height
        
        self.state.height += (self.state.target_height - self.state.height) * 0.1
    
    def _use_item(self):
        """Use the currently held item"""
        if not self.state.current_item or self.state.item_used:
            return
        
        item_type = self.state.current_item
        self.state.current_item = None
        self.state.item_used = True
        
        if item_type == ItemType.CUBE.value:
            # Place a tile below the player
            tile_pos = (int(self.player.rect.centerx // TILE_SIZE), 
                       int((self.player.rect.bottom + 8) // TILE_SIZE))
            
            if tile_pos not in self.tile_manager.tiles:
                self.tile_manager.tiles[tile_pos] = {
                    'type': TileType.PLACED_TILE.value,
                    'data': {}
                }
                self.tile_manager.recalculate_stack_heights()
                self.resources.sounds['place_block'].play()
                
                # Add placement particles
                for i in range(20):
                    angle = random.random() * math.pi * 2
                    speed = random.random() * 1.0
                    self.particle_system.add_spark(
                        [tile_pos[0] * TILE_SIZE + TILE_SIZE // 2, tile_pos[1] * TILE_SIZE + TILE_SIZE // 2],
                        [math.cos(angle) * speed, math.sin(angle) * speed],
                        random.random() * 2 + 1,
                        0.03,
                        (100, 100, 100)
                    )
        
        elif item_type == ItemType.JUMP.value:
            # Give extra jump
            self.player.jumps = min(self.player.jumps + 1, self.player.jumps_max + 1)
            self.resources.sounds['item_use'].play()
            
            # Add jump item particles
            for i in range(15):
                angle = random.random() * math.pi * 2
                speed = random.random() * 1.5
                self.particle_system.add_spark(
                    [self.player.rect.centerx, self.player.rect.centery],
                    [math.cos(angle) * speed, math.sin(angle) * speed],
                    random.random() * 2 + 1,
                    0.04,
                    (0, 255, 100)
                )
        
        elif item_type == ItemType.WARP.value:
            # Teleport player upward
            self.player.pos[1] -= 80
            self.player.velocity[1] = -2
            self.resources.sounds['warp'].play()
            self.state.screen_shake = 8
            
            # Add warp particles
            for i in range(50):
                angle = random.random() * math.pi * 2
                speed = random.random() * 2.5
                self.particle_system.add_spark(
                    [self.player.rect.centerx, self.player.rect.centery + 40],
                    [math.cos(angle) * speed, math.sin(angle) * speed],
                    random.random() * 3 + 2,
                    0.02,
                    (255, 0, 255),
                    True,
                    0.03
                )
        
        elif item_type == ItemType.BOMB.value:
            # Destroy tiles in radius around player
            bomb_center = (int(self.player.rect.centerx // TILE_SIZE), 
                          int(self.player.rect.centery // TILE_SIZE))
            tiles_to_destroy = []
            
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if dx * dx + dy * dy <= 4:  # Circular radius
                        tile_pos = (bomb_center[0] + dx, bomb_center[1] + dy)
                        if tile_pos in self.tile_manager.tiles:
                            tiles_to_destroy.append(tile_pos)
            
            # Remove tiles and add explosion effects
            for tile_pos in tiles_to_destroy:
                del self.tile_manager.tiles[tile_pos]
                
                # Add explosion particles for each destroyed tile
                for j in range(25):
                    angle = random.random() * math.pi * 2
                    speed = random.random() * 3 + 1
                    self.particle_system.add_spark(
                        [tile_pos[0] * TILE_SIZE + TILE_SIZE // 2, tile_pos[1] * TILE_SIZE + TILE_SIZE // 2],
                        [math.cos(angle) * speed, math.sin(angle) * speed],
                        random.random() * 3 + 2,
                        0.03,
                        (255, 100, 0),
                        True,
                        0.08
                    )
            
            if tiles_to_destroy:
                self.tile_manager.recalculate_stack_heights()
                self.resources.sounds['explosion'].play()
                self.state.screen_shake = 15
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            
            elif event.type == KEYDOWN:
                if not self.state.dead:
                    if event.key == K_SPACE:
                        self.resources.sounds['jump'].play()
                        self.player.attempt_jump()
                    elif event.key == K_z or event.key == K_x:
                        self._use_item()
                else:
                    # Handle death screen input
                    if event.key == K_r:
                        self._restart_game()
                    elif event.key == K_SPACE:
                        self._handle_upgrade_purchase()
                    elif event.key == K_UP:
                        self.state.upgrade_selection = (self.state.upgrade_selection - 1) % len(self.config.UPGRADES)
                    elif event.key == K_DOWN:
                        self.state.upgrade_selection = (self.state.upgrade_selection + 1) % len(self.config.UPGRADES)
        
        # Handle continuous input
        keys = pygame.key.get_pressed()
        if not self.state.dead:
            self.player.right = keys[K_RIGHT] or keys[K_d]
            self.player.left = keys[K_LEFT] or keys[K_a]
            
            # Handle jump buffering
            if keys[K_SPACE] and self.player.jump_buffer_timer <= 0:
                self.player.jump_buffer_timer = 8
        
        # Reset item used flag when not pressing use keys
        if not (keys[K_z] or keys[K_x]):
            self.state.item_used = False
    
    def _restart_game(self):
        """Restart the game"""
        # Bank coins if not already done
        if not self.state.run_coins_banked:
            self.save_data['banked_coins'] += self.state.coins
            self.state.run_coins_banked = True
            SaveManager.write_save(self.save_data)
        
        # Reset game state
        self.state = GameState()
        self.tile_manager = TileManager(self.window_tile_size)
        self.particle_system = ParticleSystem()
        self.player = self._create_player()
        self.items = []
        
        # Reset background particles
        for i in range(60):
            self.particle_system.add_bg_particle(
                [random.random() * DISPLAY_SIZE[0], random.random() * DISPLAY_SIZE[1]],
                random.random() * 0.4 + 0.1,
                random.randint(1, 3),
                random.random() * 0.3 + 0.1,
                random.choice(self.config.LEVEL_PALETTES[0]['particles'])
            )
    
    def _handle_upgrade_purchase(self):
        """Handle upgrade purchases in death screen"""
        upgrade_keys = list(self.config.UPGRADES.keys())
        upgrade_key = upgrade_keys[self.state.upgrade_selection]
        upgrade_info = self.config.UPGRADES[upgrade_key]
        
        current_level = self.save_data['upgrades'][upgrade_key]
        if current_level >= upgrade_info['max_level']:
            return
        
        cost = upgrade_info['base_cost'] + (current_level * upgrade_info['base_cost'] // 2)
        
        if self.save_data['banked_coins'] >= cost:
            self.save_data['banked_coins'] -= cost
            self.save_data['upgrades'][upgrade_key] += 1
            SaveManager.write_save(self.save_data)
            self.resources.sounds['upgrade'].play()
            
            # Add upgrade purchase particles
            for i in range(30):
                angle = random.random() * math.pi * 2
                speed = random.random() * 2
                self.particle_system.add_spark(
                    [DISPLAY_SIZE[0] // 2, DISPLAY_SIZE[1] // 2],
                    [math.cos(angle) * speed, math.sin(angle) * speed],
                    random.random() * 3 + 2,
                    0.04,
                    (0, 255, 0)
                )
    
    def render(self):
        """Render the game"""
        # Get current palette
        current_palette = self.config.LEVEL_PALETTES[self.state.current_palette_index]
        
        # Clear screen with background color
        self.display.fill(current_palette['bg'])
        
        # Update and render background particles
        self._render_background_particles(current_palette)
        
        if not self.state.dead:
            self._render_game()
        else:
            self._render_death_screen()
        
        # Render particles
        self.particle_system.update_sparks(self.display, self.state.height, 
                                         self.tile_manager.tiles, self.resources)
    
    def _render_background_particles(self, palette: Dict):
        """Render animated background particles"""
        for i, particle in sorted(enumerate(self.particle_system.bg_particles), reverse=True):
            particle[0][1] += particle[3] * particle[1]  # Move particle
            
            # Wrap particle position
            if particle[0][1] > DISPLAY_SIZE[1] + 10:
                particle[0][1] = -10
                particle[0][0] = random.random() * DISPLAY_SIZE[0]
            
            # Render particle
            render_pos = (int(particle[0][0] + self.state.height * particle[1] * 0.1), 
                         int(particle[0][1] + self.state.height * particle[1]))
            
            if 0 <= render_pos[0] < DISPLAY_SIZE[0] and 0 <= render_pos[1] < DISPLAY_SIZE[1]:
                if particle[2] == 1:
                    self.display.set_at(render_pos, particle[4])
                else:
                    pygame.draw.circle(self.display, particle[4], render_pos, particle[2])
        
        # Maintain particle count
        while len(self.particle_system.bg_particles) < 60:
            self.particle_system.add_bg_particle(
                [random.random() * DISPLAY_SIZE[0], -10],
                random.random() * 0.4 + 0.1,
                random.randint(1, 3),
                random.random() * 0.3 + 0.1,
                random.choice(palette['particles'])
            )
    
    def _render_game(self):
        """Render main game elements"""
        # Render tiles
        self._render_tiles()
        
        # Render falling tiles
        for tile_drop in self.tile_manager.tile_drops:
            tile_img = self._get_tile_image(tile_drop[2])
            self.display.blit(tile_img, (int(tile_drop[0]), int(tile_drop[1] + self.state.height)))
        
        # Render items
        for item in self.items:
            if not item['collected']:
                self._render_item(item)
        
        # Render player
        self.player.render(self.display, offset=(0, self.state.height))
        
        # Render UI
        self._render_ui()
    
    def _render_tiles(self):
        """Render all placed tiles"""
        for tile_pos, tile_data in self.tile_manager.tiles.items():
            render_pos = (tile_pos[0] * TILE_SIZE, tile_pos[1] * TILE_SIZE + self.state.height)
            
            # Skip tiles outside render area
            if render_pos[1] < -TILE_SIZE or render_pos[1] > DISPLAY_SIZE[1]:
                continue
            
            tile_img = self._get_tile_image(tile_data['type'])
            
            # Handle fragile tile flashing
            if tile_data['type'] == TileType.FRAGILE.value and 'timer' in tile_data['data']:
                if tile_data['data']['timer'] < 30 and (tile_data['data']['timer'] // 3) % 2:
                    continue  # Skip rendering for flash effect
            
            self.display.blit(tile_img, render_pos)
    
    def _get_tile_image(self, tile_type: str) -> pygame.Surface:
        """Get the appropriate image for a tile type"""
        tile_image_map = {
            TileType.TILE.value: 'tile',
            TileType.PLACED_TILE.value: 'placed_tile',
            TileType.FRAGILE.value: 'fragile_tile',
            TileType.BOUNCE.value: 'bounce_tile',
            TileType.SPIKE.value: 'spike_tile',
            TileType.CHEST.value: 'chest',
            TileType.OPENED_CHEST.value: 'opened_chest',
            TileType.GREED.value: 'greed_tile'
        }
        return self.resources.images[tile_image_map.get(tile_type, 'tile')]
    
    def _render_item(self, item: Dict):
        """Render an item"""
        render_pos = (int(item['pos'][0] - 4), int(item['pos'][1] + self.state.height - 4))
        
        if item['type'] == ItemType.COIN.value:
            # Animate coin with floating effect
            float_offset = math.sin(item['timer'] * 0.1) * 2
            coin_pos = (render_pos[0], int(render_pos[1] + float_offset))
            self.display.blit(self.resources.images['coin_icon'], coin_pos)
        else:
            # Render item icon
            if item['type'] in self.resources.images['item_icons']:
                item_img = self.resources.images['item_icons'][item['type']]
                self.display.blit(item_img, render_pos)
    
    def _render_ui(self):
        """Render game UI elements"""
        # Render coin count
        coin_text = f"{self.state.coins}"
        if self.state.combo_multiplier > 1.0:
            coin_text += f" x{self.state.combo_multiplier:.1f}"
        
        self.resources.fonts['white'].render(self.display, coin_text, (8, 8))
        self.display.blit(self.resources.images['coin_icon'], (8 + len(str(self.state.coins)) * 6, 6))
        
        # Render height
        height_text = f"Height: {int(self.state.target_height)}"
        self.resources.fonts['white'].render(self.display, height_text, (8, 20))
        
        # Render current item
        if self.state.current_item:
            item_slot_img = self.resources.images['item_slot_flash'] if self.state.master_clock % 20 < 10 else self.resources.images['item_slot']
            self.display.blit(item_slot_img, (DISPLAY_SIZE[0] - 24, 8))
            
            if self.state.current_item in self.resources.images['item_icons']:
                item_img = self.resources.images['item_icons'][self.state.current_item]
                self.display.blit(item_img, (DISPLAY_SIZE[0] - 20, 12))
        else:
            self.display.blit(self.resources.images['item_slot'], (DISPLAY_SIZE[0] - 24, 8))
        
        # Render border
        self.display.blit(self.resources.images['border'], (0, 0))
    
    def _render_death_screen(self):
        """Render death/upgrade screen"""
        # Render semi-transparent overlay
        overlay = pygame.Surface(DISPLAY_SIZE)
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.display.blit(overlay, (0, 0))
        
        # Render death text
        center_x = DISPLAY_SIZE[0] // 2
        self.resources.fonts['white'].render(self.display, "GAME OVER", (center_x - 30, 40))
        
        if self.state.new_high_score:
            self.resources.fonts['white'].render(self.display, "NEW HIGH SCORE!", (center_x - 42, 55))
        
        self.resources.fonts['white'].render(self.display, f"Score: {self.state.coins}", (center_x - 24, 70))
        self.resources.fonts['white'].render(self.display, f"High Score: {self.save_data['high_score']}", (center_x - 36, 85))
        
        # Render upgrade shop
        self.resources.fonts['white'].render(self.display, "UPGRADES", (center_x - 24, 110))
        self.resources.fonts['white'].render(self.display, f"Coins: {self.save_data['banked_coins']}", (8, 125))
        
        # Render upgrade options
        y_offset = 140
        upgrade_keys = list(self.config.UPGRADES.keys())
        
        for i, upgrade_key in enumerate(upgrade_keys):
            upgrade_info = self.config.UPGRADES[upgrade_key]
            current_level = self.save_data['upgrades'][upgrade_key]
            
            # Selection indicator
            if i == self.state.upgrade_selection:
                pygame.draw.rect(self.display, (50, 50, 50), (4, y_offset - 2, DISPLAY_SIZE[0] - 8, 20))
            
            # Render upgrade info
            level_text = f"[{current_level}/{upgrade_info['max_level']}]"
            name_text = f"{upgrade_info['name']} {level_text}"
            
            if current_level >= upgrade_info['max_level']:
                self.resources.fonts['white'].render(self.display, f"{name_text} MAX", (8, y_offset))
            else:
                cost = upgrade_info['base_cost'] + (current_level * upgrade_info['base_cost'] // 2)
                self.resources.fonts['white'].render(self.display, f"{