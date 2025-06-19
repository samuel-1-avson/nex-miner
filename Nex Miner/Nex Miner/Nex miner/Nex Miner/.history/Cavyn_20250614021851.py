# Enhanced Cavyn: Recharged with improved graphics and visual effects

import os
import sys
import random
import math
import json

import pygame
from pygame.locals import *

from data.scripts.entity import Entity
from data.scripts.anim_loader import AnimationManager
from data.scripts.text import Font

TILE_SIZE = 16

clock = pygame.time.Clock()
from pygame.locals import *
pygame.init()
pygame.display.set_caption('Cavyn: Recharged - Enhanced Edition')
DISPLAY_SIZE = (320, 180)
SCALE = 3
screen = pygame.display.set_mode((DISPLAY_SIZE[0] * SCALE, DISPLAY_SIZE[1] * SCALE), 0, 32)
display = pygame.Surface(DISPLAY_SIZE)
pygame.mouse.set_visible(False)

WINDOW_TILE_SIZE = (int(display.get_width() // 16), int(display.get_height() // 16))

# Save data and upgrade system
SAVE_FILE = 'save.json'

def load_save():
    try:
        with open(SAVE_FILE, 'r') as f:
            data = json.load(f)
            if 'high_score' not in data:
                data['high_score'] = 0
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        default_save = {"banked_coins": 100, "upgrades": {"jumps": 0, "speed": 0, "item_luck": 0}, "high_score": 0}
        write_save(default_save)
        return default_save

def write_save(data):
    with open(SAVE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

save_data = load_save()

UPGRADES = {
    'jumps': {'name': 'Extra Jump', 'desc': 'Max jumps +1', 'base_cost': 50, 'max_level': 2},
    'speed': {'name': 'Move Speed', 'desc': 'Run faster', 'base_cost': 40, 'max_level': 5},
    'item_luck': {'name': 'Item Luck', 'desc': 'Better chest loot', 'base_cost': 100, 'max_level': 3},
}
upgrade_keys = list(UPGRADES.keys())

# Enhanced visual level progression with more dramatic effects
LEVEL_PALETTES = [
    {'score': 0, 'bg': (22, 19, 40), 'particles': [(0, 0, 0), (22, 19, 40), (45, 38, 80)], 'accent': (120, 100, 200)},
    {'score': 75, 'bg': (40, 19, 30), 'particles': [(0, 0, 0), (40, 19, 30), (80, 38, 60)], 'accent': (200, 80, 120)},
    {'score': 200, 'bg': (19, 30, 40), 'particles': [(0, 0, 0), (19, 30, 40), (38, 60, 80)], 'accent': (80, 150, 200)},
    {'score': 400, 'bg': (40, 30, 19), 'particles': [(0, 0, 0), (40, 30, 19), (80, 60, 38)], 'accent': (200, 150, 80)},
    {'score': 800, 'bg': (35, 15, 45), 'particles': [(0, 0, 0), (35, 15, 45), (70, 30, 90)], 'accent': (180, 80, 220)},
]
current_palette_index = 0
palette_transition_timer = 0

def load_img(path):
    try:
        img = pygame.image.load(path).convert()
        img.set_colorkey((0, 0, 0))
        return img
    except pygame.error:
        # Create a fallback colored rectangle if image is missing
        surf = pygame.Surface((16, 16))
        surf.fill((100, 100, 100))
        surf.set_colorkey((0, 0, 0))
        return surf

# Enhanced graphics loading with fallbacks
try:
    background_img = pygame.image.load('data/images/background.png').convert()
    background_img = pygame.transform.scale(background_img, DISPLAY_SIZE)
except pygame.error:
    background_img = None

# Load all game images with fallbacks
tile_img = load_img('data/images/tile.png')
placed_tile_img = load_img('data/images/placed_tile.png')
chest_img = load_img('data/images/chest.png')
ghost_chest_img = load_img('data/images/ghost_chest.png')
opened_chest_img = load_img('data/images/opened_chest.png')
edge_tile_img = load_img('data/images/edge_tile.png')
fragile_tile_img = load_img('data/images/fragile_tile.png')
bounce_tile_img = load_img('data/images/bounce_tile.png')
spike_tile_img = load_img('data/images/spike_tile.png')
coin_icon = load_img('data/images/coin_icon.png')
item_slot_img = load_img('data/images/item_slot.png')
item_slot_flash_img = load_img('data/images/item_slot_flash.png')
border_img = load_img('data/images/border.png')
border_img_light = border_img.copy()
border_img_light.set_alpha(100)
tile_top_img = load_img('data/images/tile_top.png')
greed_tile_img = load_img('data/images/greed_tile.png')

white_font = Font('data/fonts/small_font.png', (251, 245, 239))
black_font = Font('data/fonts/small_font.png', (0, 0, 1))

# Load sounds with error handling
sounds = {}
try:
    for sound_file in os.listdir('data/sfx'):
        if sound_file.endswith('.wav'):
            sounds[sound_file.split('.')[0]] = pygame.mixer.Sound(f'data/sfx/{sound_file}')
except FileNotFoundError:
    pass

# Set sound volumes
for sound_name, volume in [('block_land', 0.5), ('coin', 0.6), ('chest_open', 0.8), ('upgrade', 0.7), ('explosion', 0.8), ('combo_end', 0.6)]:
    if sound_name in sounds:
        sounds[sound_name].set_volume(volume)

# Create coin_end sound
if 'coin' in sounds:
    sounds['coin_end'] = sounds['coin'].copy()
    sounds['coin_end'].set_volume(0.35)

item_icons = {
    'cube': load_img('data/images/cube_icon.png'),
    'warp': load_img('data/images/warp_icon.png'),
    'jump': load_img('data/images/jump_icon.png'),
    'bomb': load_img('data/images/bomb_icon.png'),
    'freeze': load_img('data/images/freeze_icon.png'),
}

animation_manager = AnimationManager()

# Enhanced particle system
class EnhancedParticle:
    def __init__(self, pos, velocity, color, size, lifetime, particle_type='default'):
        self.pos = list(pos)
        self.velocity = list(velocity)
        self.color = color
        self.size = size
        self.max_size = size
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.particle_type = particle_type
        self.rotation = random.random() * 360
        self.scale = 1.0
        
    def update(self):
        self.pos[0] += self.velocity[0]
        self.pos[1] += self.velocity[1]
        self.lifetime -= 1
        self.rotation += 5
        
        # Different particle behaviors
        if self.particle_type == 'sparkle':
            self.velocity[0] *= 0.98
            self.velocity[1] *= 0.98
            self.scale = self.lifetime / self.max_lifetime
        elif self.particle_type == 'smoke':
            self.velocity[1] -= 0.05  # Float upward
            self.velocity[0] *= 0.95
            self.scale = 1.0 + (1 - self.lifetime / self.max_lifetime) * 0.5
        elif self.particle_type == 'explosion':
            self.velocity[0] *= 0.9
            self.velocity[1] *= 0.9
            self.scale = 1.0 + math.sin((1 - self.lifetime / self.max_lifetime) * math.pi) * 0.5
            
        return self.lifetime > 0

enhanced_particles = []

def create_enhanced_particles(pos, count, particle_type='default', color=None):
    if color is None:
        color = (255, 255, 255)
    
    for _ in range(count):
        velocity = [random.uniform(-2, 2), random.uniform(-3, 1)]
        size = random.uniform(2, 6)
        lifetime = random.randint(30, 60)
        
        if particle_type == 'sparkle':
            velocity = [random.uniform(-1, 1), random.uniform(-2, 0)]
            size = random.uniform(1, 3)
            lifetime = random.randint(20, 40)
        elif particle_type == 'explosion':
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.5, 3)
            velocity = [math.cos(angle) * speed, math.sin(angle) * speed]
            size = random.uniform(3, 8)
            lifetime = random.randint(20, 50)
            
        enhanced_particles.append(EnhancedParticle(pos, velocity, color, size, lifetime, particle_type))

def normalize(val, amt):
    if val > amt:
        val -= amt
    elif val < -amt:
        val += amt
    else:
        val = 0
    return val

def recalculate_stack_heights():
    global stack_heights
    new_heights = [WINDOW_TILE_SIZE[1] for i in range(WINDOW_TILE_SIZE[0] - 2)]
    for tile_x, tile_y in tiles:
        if 1 <= tile_x < WINDOW_TILE_SIZE[0] - 1:
            col_index = tile_x - 1
            new_heights[col_index] = min(new_heights[col_index], tile_y)
    stack_heights = new_heights

class Item(Entity):
    def __init__(self, *args, velocity=[0, 0]):
        super().__init__(*args)
        self.velocity = velocity
        self.time = 0
        self.bob_offset = 0

    def update(self, tiles):
        self.time += 1
        self.velocity[1] = min(self.velocity[1] + 0.2, 3)
        self.velocity[0] = normalize(self.velocity[0], 0.05)
        self.move(self.velocity, tiles)
        
        # Enhanced floating animation
        self.bob_offset = math.sin(self.time * 0.1) * 2

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
        self.trail_particles = []
        self.dash_particles = []

    def attempt_jump(self):
        if self.jumps or self.coyote_timer > 0:
            if self.jumps == self.jumps_max or self.coyote_timer > 0:
                self.velocity[1] = -5
            else:
                self.velocity[1] = -4
                # Enhanced jump particles
                create_enhanced_particles(self.center, 15, 'sparkle', (200, 200, 255))

            is_coyote_jump = self.coyote_timer > 0 and self.jumps == self.jumps_max
            if not is_coyote_jump:
                self.jumps -= 1

            self.coyote_timer = 0
            self.jumping = True
            self.jump_rot = 0

    def update(self, tiles):
        super().update(1 / 60)

        if self.coyote_timer > 0:
            self.coyote_timer -= 1
        if self.jump_buffer_timer > 0:
            self.jump_buffer_timer -= 1

        self.air_time += 1
        
        # Enhanced jumping animation with smoother rotation
        if self.jumping:
            self.jump_rot += 16
            if self.jump_rot >= 360:
                self.jump_rot = 0
                self.jumping = False
            if self.flip[0]:
                self.rotation = -self.jump_rot * 0.5  # Smoother rotation
            else:
                self.rotation = self.jump_rot * 0.5
            self.scale[1] = 0.8 + math.sin(self.jump_rot * math.pi / 180) * 0.2
        else:
            self.scale[1] = 1

        self.velocity[1] = min(self.velocity[1] + 0.3, 4)
        motion = self.velocity.copy()
        
        if not dead:
            if self.right:
                motion[0] += self.speed
                # Movement trail particles
                if random.random() < 0.3:
                    create_enhanced_particles([self.rect.left, self.rect.centery], 1, 'sparkle', (100, 150, 255))
            if self.left:
                motion[0] -= self.speed
                if random.random() < 0.3:
                    create_enhanced_particles([self.rect.right, self.rect.centery], 1, 'sparkle', (100, 150, 255))
                    
            if motion[0] > 0:
                self.flip[0] = True
            if motion[0] < 0:
                self.flip[0] = False

        if self.air_time > 3:
            self.set_action('jump')
        elif motion[0] != 0:
            self.set_action('run')
        else:
            self.set_action('idle')

        was_on_ground = self.air_time == 0
        collisions = self.move(motion, tiles)

        if collisions['bottom']:
            self.jumps = self.jumps_max
            self.jumping = False
            self.rotation = 0
            self.velocity[1] = 0
            self.air_time = 0
            
            # Landing particles
            if was_on_ground == False:
                create_enhanced_particles([self.rect.centerx, self.rect.bottom], 8, 'explosion', (255, 255, 100))
                
            if self.jump_buffer_timer > 0:
                self.jump_buffer_timer = 0
                if 'jump' in sounds:
                    sounds['jump'].play()
                self.attempt_jump()
        else:
            if was_on_ground:
                self.coyote_timer = 6

        return collisions

class Projectile(Entity):
    def __init__(self, *args, velocity=[0, 0]):
        super().__init__(*args)
        self.velocity = velocity
        self.trail_timer = 0

    def update(self):
        super().update(1/60)
        self.pos[0] += self.velocity[0]
        self.pos[1] += self.velocity[1]
        
        # Enhanced projectile trail
        self.trail_timer += 1
        if self.trail_timer % 3 == 0:
            create_enhanced_particles(self.center, 2, 'sparkle', (255, 200, 100))

def lookup_nearby(tiles, pos):
    rects = []
    for offset in [(0, 0), (-1, -1), (-1, 0), (-1, 1), (0, 1), (0, -1), (1, -1), (1, 0), (1, 1)]:
        lookup_pos = (pos[0] // TILE_SIZE + offset[0], pos[1] // TILE_SIZE + offset[1])
        if lookup_pos in tiles:
            rects.append(pygame.Rect(lookup_pos[0] * TILE_SIZE, lookup_pos[1] * TILE_SIZE, TILE_SIZE, TILE_SIZE))
    return rects

GLOW_CACHE = {}

def glow_img(size, color):
    if (size, color) not in GLOW_CACHE:
        surf = pygame.Surface((size * 2 + 2, size * 2 + 2))
        pygame.draw.circle(surf, color, (surf.get_width() // 2, surf.get_height() // 2), size)
        surf.set_colorkey((0, 0, 0))
        GLOW_CACHE[(size, color)] = surf
    return GLOW_CACHE[(size, color)]

# Enhanced glow effect with gradient
def enhanced_glow_img(size, inner_color, outer_color):
    cache_key = (size, inner_color, outer_color)
    if cache_key not in GLOW_CACHE:
        surf = pygame.Surface((size * 4 + 4, size * 4 + 4))
        center = (surf.get_width() // 2, surf.get_height() // 2)
        
        # Create gradient glow
        for i in range(size * 2, 0, -1):
            alpha = int(255 * (1 - i / (size * 2)))
            blend_color = [
                int(outer_color[j] + (inner_color[j] - outer_color[j]) * (1 - i / (size * 2)))
                for j in range(3)
            ]
            glow_surf = pygame.Surface((i * 2, i * 2))
            glow_surf.set_alpha(alpha)
            glow_surf.fill(blend_color)
            surf.blit(glow_surf, (center[0] - i, center[1] - i), special_flags=BLEND_RGBA_ADD)
        
        surf.set_colorkey((0, 0, 0))
        GLOW_CACHE[cache_key] = surf
    return GLOW_CACHE[cache_key]

player = Player(animation_manager, (DISPLAY_SIZE[0] // 2 - 5, -20), (8, 16), 'player')
player.jumps_max += save_data['upgrades']['jumps']
player.speed += save_data['upgrades']['speed'] * 0.08
player.jumps = player.jumps_max

dead = False
tiles = {}
tile_drops = []
bg_particles = []
sparks = []
projectiles = []
freeze_timer = 0
game_timer = 0
height = 0
target_height = 0
coins = 0
end_coin_count = 0
current_item = None
master_clock = 0
last_place = 0
item_used = False
combo_multiplier = 1.0
combo_timer = 0
COMBO_DURATION = 180
run_coins_banked = False
upgrade_selection = 0
screen_shake = 0
new_high_score = False

# Initialize starting tiles
for i in range(WINDOW_TILE_SIZE[0] - 2):
    tiles[(i + 1, WINDOW_TILE_SIZE[1] - 1)] = {'type': 'tile', 'data': {}}

tiles[(1, WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
tiles[(WINDOW_TILE_SIZE[0] - 2, WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}

stack_heights = [WINDOW_TILE_SIZE[1] - 1 for i in range(WINDOW_TILE_SIZE[0] - 2)]
stack_heights[0] -= 1
stack_heights[-1] -= 1

items = []

# Load music
try:
    pygame.mixer.music.load('data/music.wav')
    pygame.mixer.music.play(-1)
except pygame.error:
    pass

def handle_death():
    global dead, run_coins_banked, upgrade_selection, new_high_score, save_data, screen_shake
    if not dead:
        if 'death' in sounds:
            sounds['death'].play()
        screen_shake = 20
        
        # Enhanced death particle explosion
        create_enhanced_particles(player.center, 50, 'explosion', (255, 100, 100))
        
        if coins > save_data['high_score']:
            save_data['high_score'] = coins
            new_high_score = True
            write_save(save_data)

        dead = True
        run_coins_banked = False
        upgrade_selection = 0
        player.velocity = [1.3, -6]

# Enhanced background rendering with animated elements
def render_enhanced_background():
    current_palette = LEVEL_PALETTES[current_palette_index]
    
    if background_img:
        # Tint the background based on current palette
        tinted_bg = background_img.copy()
        tint_overlay = pygame.Surface(DISPLAY_SIZE)
        tint_overlay.fill(current_palette['accent'])
        tint_overlay.set_alpha(30)
        tinted_bg.blit(tint_overlay, (0, 0))
        display.blit(tinted_bg, (0, 0))
    else:
        # Gradient background
        for y in range(DISPLAY_SIZE[1]):
            color_ratio = y / DISPLAY_SIZE[1]
            bg_color = current_palette['bg']
            accent_color = current_palette['accent']
            blended_color = [
                int(bg_color[i] + (accent_color[i] - bg_color[i]) * color_ratio * 0.3)
                for i in range(3)
            ]
            pygame.draw.line(display, blended_color, (0, y), (DISPLAY_SIZE[0], y))

# Main game loop
while True:
    # Enhanced visual level progression with smooth transitions
    if not dead:
        next_palette_index = 0
        for i, p in enumerate(LEVEL_PALETTES):
            if coins >= p['score']:
                next_palette_index = i
        if next_palette_index != current_palette_index:
            current_palette_index = next_palette_index
            palette_transition_timer = 60
            # Transition effect particles
            create_enhanced_particles([DISPLAY_SIZE[0] // 2, DISPLAY_SIZE[1] // 2], 30, 'sparkle', LEVEL_PALETTES[current_palette_index]['accent'])

    if palette_transition_timer > 0:
        palette_transition_timer -= 1

    current_palette = LEVEL_PALETTES[current_palette_index]

    # Enhanced background rendering
    render_enhanced_background()

    master_clock += 1

    if screen_shake > 0:
        screen_shake -= 0.5

    # Enhanced freeze effect
    if freeze_timer > 0:
        freeze_timer -= 1
        freeze_overlay = pygame.Surface(DISPLAY_SIZE, pygame.SRCALPHA)
        alpha = int(40 + math.sin(master_clock / 3) * 20)
        freeze_overlay.fill((150, 200, 255, alpha))
        display.blit(freeze_overlay, (0, 0))
        
        # Freeze particles
        if random.random() < 0.1:
            create_enhanced_particles([random.randint(0, DISPLAY_SIZE[0]), random.randint(0, DISPLAY_SIZE[1])], 1, 'sparkle', (200, 230, 255))

    # Enhanced combo system
    if combo_timer > 0:
        combo_timer -= 1
        if combo_timer == 0 and combo_multiplier > 1.0:
            if 'combo_end' in sounds:
                sounds['combo_end'].play()
            create_enhanced_particles([DISPLAY_SIZE[0] // 2, 10], 25, 'explosion', (255, 255, 100))
            combo_multiplier = 1.0

    # Enhanced background particles
    parallax = random.random()
    particle_color = random.choice(current_palette['particles'])
    for i in range(3):  # More particles
        pos = [random.random() * DISPLAY_SIZE[0], DISPLAY_SIZE[1] - height * parallax]
        size = random.randint(1, 4)
        speed = random.random() * 2 + 0.5
        bg_particles.append([pos, parallax, size, speed, particle_color])

    # Update background particles with enhanced effects
    for i, p in sorted(enumerate(bg_particles), reverse=True):
        size = p[2]
        if p[-1] != (0, 0, 0):
            size = size * 3 + 2
        p[2] -= 0.02
        p[0][1] -= p[3]
        
        render_y = int(p[0][1] + height * p[1])
        if 0 <= render_y < DISPLAY_SIZE[1] and 0 <= p[0][0] < DISPLAY_SIZE[0]:
            if size < 1:
                display.set_at((int(p[0][0]), render_y), p[-1])
            else:
                if p[-1] != (0, 0, 0):
                    # Enhanced particle rendering with glow
                    pygame.draw.circle(display, p[-1], (int(p[0][0]), render_y), int(size))
                    if size > 2:
                        glow_size = int(size * 1.5)
                        glow_color = [min(255, c + 50) for c in p[-1]]
                        display.blit(glow_img(glow_size, glow_color), 
                                   (int(p[0][0]) - glow_size, render_y - glow_size), 
                                   special_flags=BLEND_RGBA_ADD)
                else:
                    pygame.draw.circle(display, p[-1], (int(p[0][0]), render_y), int(size))
        
        if size < 0:
            bg_particles.pop(i)

    # Update enhanced particles
    for i, particle in sorted(enumerate(enhanced_particles), reverse=True):
        if not particle.update():
            enhanced_particles.pop(i)
            continue
            
        # Render enhanced particles
        render_pos = [int(particle.pos[0]), int(particle.pos[1] + height)]
        if 0 <= render_pos[0] < DISPLAY_SIZE[0] and 0 <= render_pos[1] < DISPLAY_SIZE[1]:
            size = int(particle.size * particle.scale)
            if size > 0:
                if particle.particle_type == 'sparkle':
                    # Sparkle particles with rotation
                    points = []
                    for j in range(4):
                        angle = particle.rotation + j * 90
                        x = render_pos[0] + math.cos(math.radians(angle)) * size
                        y = render_pos[1] + math.sin(math.radians(angle)) * size
                        points.append([x, y])
                    if len(points) >= 3:
                        pygame.draw.polygon(display, particle.color, points)
                else:
                    pygame.draw.circle(display, particle.color, render_pos, size)
                    
                # Add glow effect
                if size > 2:
                    glow_color = [min(255, c + 30) for c in particle.color]
                    display.blit(glow_img(size + 2, glow_color), 
                               (render_pos[0] - size - 2, render_pos[1] - size - 2), 
                               special_flags=BLEND_RGBA_ADD)

    # Tile dropping logic (unchanged but with enhanced effects)
    if master_clock > 180:
        game_timer += 1
        if game_timer > 10 + 25 * (20000 - min(20000, master_clock)) / 20000:
            game_timer = 0
            minimum = min(stack_heights)
            options = []
            for i, stack in enumerate(stack_heights):
                if i != last_place:
                    offset = stack - minimum
                    for j in range(int(offset ** (2.2 - min(20000, master_clock) / 10000)) + 1):
                        options.append(i)

            roll = random.randint(1, 30)
            if roll == 1:
                tile_type = 'chest'
            elif roll < 4:
                tile_type = 'fragile'
            elif roll < 6:
                tile_type = 'bounce'
            elif roll == 7:
                tile_type = 'spike'
            elif roll == 8:
                tile_type = 'greed'
            else:
                tile_type = 'tile'

            c = random.choice(options)
            last_place = c
            tile_drops.append([(c + 1) * TILE_SIZE, -height - TILE_SIZE, tile_type])

    # Update tile drops with enhanced effects
    tile_drop_rects = []
    for i, tile in sorted(enumerate(tile_drops), reverse=True):
        if freeze_timer <= 0:
            tile[1] += 1.4
        pos = [tile[0] + TILE_SIZE // 2, tile[1] + TILE_SIZE]
        r = pygame.Rect(tile[0], tile[1], TILE_SIZE, TILE_SIZE)
        tile_drop_rects.append(r)

        # Enhanced graze detection with particles
        graze_rect = player.rect.copy()
        graze_rect.inflate_ip(8, 8)
        if graze_rect.colliderect(r) and not player.rect.colliderect(r):
            combo_multiplier += 0.2
            combo_timer = COMBO_DURATION
            create_enhanced_particles(player.center, 5, 'sparkle', (100, 255, 100))

        if r.colliderect(player.rect):
            handle_death()

        check_pos = (int(pos[0] // TILE_SIZE), int(math.floor(pos[1] / TILE_SIZE)))
        if check_pos in tiles:
            place_pos =