# this is very spaghetti because it was written in under 8 hours
# -- REIMAGINED AND IMPROVED BY AN AI --

import os
import sys
import random
import math
import json
from collections import deque

import pygame
from pygame.locals import *

from data.scripts.entity import Entity
from data.scripts.anim_loader import AnimationManager
from data.scripts.text import Font

# -- GAMEPLAY & VISUAL IMPROVEMENTS --
# 1. New screen size for a better view
# 2. Synthwave/Outrun color theme
# 3. Smooth horizontal camera follow
# 4. Player "ghost" trail effect
# 5. New Conveyor Tile gameplay mechanic
# 6. Redesigned HUD and Game Over screen
# 7. Scrolling perspective grid background & vignette

TILE_SIZE = 16

clock = pygame.time.Clock()
from pygame.locals import *
pygame.init()
pygame.display.set_caption('CAVYNWAVE')
# NEW: Larger display size for a better gameplay area
DISPLAY_SIZE = (240, 320)
# NEW: Scaled up to a more modern window size
screen = pygame.display.set_mode((DISPLAY_SIZE[0] * 2, DISPLAY_SIZE[1] * 2), 0, 32)
display = pygame.Surface(DISPLAY_SIZE)
pygame.mouse.set_visible(False)

WINDOW_TILE_SIZE = (int(display.get_width() // 16), int(display.get_height() // 16))

# Save data and upgrade system
SAVE_FILE = 'save.json'

def load_save():
    try:
        with open(SAVE_FILE, 'r') as f:
            data = json.load(f)
            if 'high_score' not in data: # Handle old save files
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

# -- NEW: SYNTHWAVE THEME PALETTES --
LEVEL_PALETTES = [
    {'score': 0,   'bg': ((20, 10, 30), (40, 15, 60)), 'grid': (60, 30, 90), 'particles': [(200, 255, 255), (255, 100, 255)]},
    {'score': 75,  'bg': ((30, 10, 40), (60, 15, 70)), 'grid': (80, 40, 110), 'particles': [(200, 255, 255), (255, 100, 255), (100, 255, 200)]},
    {'score': 200, 'bg': ((10, 20, 40), (15, 40, 70)), 'grid': (40, 80, 110), 'particles': [(200, 255, 255), (100, 255, 200), (100, 200, 255)]},
    {'score': 400, 'bg': ((40, 20, 10), (70, 40, 15)), 'grid': (110, 80, 40), 'particles': [(255, 255, 200), (255, 150, 100), (255, 200, 100)]},
]
current_palette_index = 0

def load_img(path):
    img = pygame.image.load(path).convert()
    img.set_colorkey((0, 0, 0))
    return img

# -- THEME-AWARE ASSET LOADING --
tile_img = load_img('data/images/tile.png')
pygame.draw.rect(tile_img, (100, 255, 255, 100), tile_img.get_rect(), 1) # Add outline
chest_img = load_img('data/images/chest.png')
ghost_chest_img = load_img('data/images/ghost_chest.png')
opened_chest_img = load_img('data/images/opened_chest.png')
placed_tile_img = load_img('data/images/placed_tile.png')
pygame.draw.rect(placed_tile_img, (255, 100, 255, 100), placed_tile_img.get_rect(), 1) # Add outline
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

# -- NEW: Procedurally generate Conveyor Tile animation --
conveyor_frames_left = []
conveyor_frames_right = []
for i in range(8): # 8 frames of animation
    img = tile_img.copy()
    for j in range(4): # 4 chevrons
        offset_x = (j * 8 - i * 2) % 32 - 8
        pygame.draw.line(img, (100, 255, 255), (offset_x, 4), (offset_x + 3, 8), 1)
        pygame.draw.line(img, (100, 255, 255), (offset_x, 12), (offset_x + 3, 8), 1)
    conveyor_frames_left.append(img)
    conveyor_frames_right.append(pygame.transform.flip(img, True, False))


# -- NEW: Themed fonts and Vignette --
white_font = Font('data/fonts/small_font.png', (200, 255, 255))
black_font = Font('data/fonts/small_font.png', (20, 10, 30))

vignette_surf = pygame.Surface(DISPLAY_SIZE)
pygame.draw.rect(vignette_surf, (50, 40, 70), (0, 0, DISPLAY_SIZE[0], DISPLAY_SIZE[1]))
pygame.draw.circle(vignette_surf, (0, 0, 0), (DISPLAY_SIZE[0] // 2, DISPLAY_SIZE[1] // 2), 160)
vignette_surf.set_colorkey((0, 0, 0))


sounds = {sound.split('/')[-1].split('.')[0] : pygame.mixer.Sound('data/sfx/' + sound) for sound in os.listdir('data/sfx')}
sounds['block_land'].set_volume(0.5)
sounds['coin'].set_volume(0.6)
sounds['chest_open'].set_volume(0.8)
sounds['coin_end'] = pygame.mixer.Sound('data/sfx/coin.wav')
sounds['coin_end'].set_volume(0.35)
if 'upgrade' in sounds:
    sounds['upgrade'].set_volume(0.7)
if 'explosion' in sounds:
    sounds['explosion'].set_volume(0.8)
if 'combo_end' in sounds:
    sounds['combo_end'].set_volume(0.6)

item_icons = {
    'cube': load_img('data/images/cube_icon.png'),
    'warp': load_img('data/images/warp_icon.png'),
    'jump': load_img('data/images/jump_icon.png'),
    'bomb': load_img('data/images/bomb_icon.png'),
}
# NEW: Scaled down jump icon for HUD
jump_icon_small = pygame.transform.scale(item_icons['jump'], (8, 8))

animation_manager = AnimationManager()

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

    def update(self, tiles):
        self.time += 1
        self.velocity[1] = min(self.velocity[1] + 0.2, 3)
        self.velocity[0] = normalize(self.velocity[0], 0.05)
        self.move(self.velocity, tiles)

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
                for i in range(24):
                    physics_on = random.choice([False, False, True])
                    direction = 1
                    if i % 2:
                        direction = -1
                    sparks.append([[player.center[0] + random.random() * 14 - 7, player.center[1]], [direction * (random.random() * 0.05 + 0.05) + (random.random() * 4 - 2) * physics_on, random.random() * 0.05 + random.random() * 2 * physics_on], random.random() * 3 + 3, 0.04 - 0.02 * physics_on, (255,100,255), physics_on, 0.05 * physics_on])

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
        if self.jumping:
            self.jump_rot += 16
            if self.jump_rot >= 360:
                self.jump_rot = 0
                self.jumping = False
            if self.flip[0]:
                self.rotation = -self.jump_rot
            else:
                self.rotation = self.jump_rot
            self.scale[1] = 0.7
        else:
            self.scale[1] = 1

        self.velocity[1] = min(self.velocity[1] + 0.3, 4)
        motion = self.velocity.copy()
        if not dead:
            if self.right:
                motion[0] += self.speed
            if self.left:
                motion[0] -= self.speed
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
            if self.jump_buffer_timer > 0:
                self.jump_buffer_timer = 0
                sounds['jump'].play()
                self.attempt_jump()
        else:
            if was_on_ground:
                self.coyote_timer = 6

        return collisions

def lookup_nearby(tiles, pos):
    rects = []
    for offset in [(0, 0), (-1, -1), (-1, 0), (-1, 1), (0, 1), (0, -1), (1, -1), (1, 0), (1, 1)]:
        lookup_pos = (pos[0] // TILE_SIZE + offset[0], pos[1] // TILE_SIZE + offset[1])
        if lookup_pos in tiles:
            rects.append(pygame.Rect(lookup_pos[0] * TILE_SIZE, lookup_pos[1] * TILE_SIZE, TILE_SIZE, TILE_SIZE))

    return rects

GLOW_CACHE = {}

def glow_img(size, color):
    key = (int(size), color)
    if key not in GLOW_CACHE:
        surf = pygame.Surface((size * 2 + 2, size * 2 + 2))
        pygame.draw.circle(surf, color, (surf.get_width() // 2, surf.get_height() // 2), size)
        surf.set_colorkey((0, 0, 0))
        GLOW_CACHE[key] = surf
    return GLOW_CACHE[key]

# --- RENDER FUNCTIONS ---

def draw_background(surface, camera_x, scroll_y, palette):
    # Gradient background
    grad_rect = pygame.Rect(0, 0, surface.get_width(), surface.get_height())
    start_color, end_color = palette['bg']
    for y in range(grad_rect.height):
        ratio = y / grad_rect.height
        color = (
            start_color[0] + (end_color[0] - start_color[0]) * ratio,
            start_color[1] + (end_color[1] - start_color[1]) * ratio,
            start_color[2] + (end_color[2] - start_color[2]) * ratio,
        )
        pygame.draw.line(surface, color, (grad_rect.left, y), (grad_rect.right, y))

    # Scrolling perspective grid
    grid_color = palette['grid']
    for i in range(16):
        y = (i * 20 - scroll_y * 0.8) % (16 * 20)
        progress = y / (16 * 20)
        width = 5 + progress * surface.get_width()
        alpha = 150 * (1 - progress)
        line_surf = pygame.Surface((width, 1))
        line_surf.fill(grid_color)
        line_surf.set_alpha(alpha)
        surface.blit(line_surf, (surface.get_width() // 2 - width // 2, y + 100))

    # Static horizontal lines
    for i in range(10):
        y = i * 32
        pygame.draw.line(surface, (0,0,0,100), (0, y), (surface.get_width(), y))

# --- GLOBAL GAME STATE ---
player = Player(animation_manager, (DISPLAY_SIZE[0] // 2 - 5, -20), (8, 16), 'player')
player.jumps_max += save_data['upgrades']['jumps']
player.speed += save_data['upgrades']['speed'] * 0.08
player.jumps = player.jumps_max

dead = False
tiles = {}
tile_drops = []
bg_particles = []
sparks = []
items = []

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

# NEW: Camera, Player Trail, Conveyor Animation
camera = [0, 0]
player_trail = deque(maxlen=8)
conveyor_frame = 0


for i in range(WINDOW_TILE_SIZE[0] - 2):
    tiles[(i + 1, WINDOW_TILE_SIZE[1] - 1)] = {'type': 'tile', 'data': {}}

tiles[(1, WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
tiles[(WINDOW_TILE_SIZE[0] - 2, WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}

stack_heights = [WINDOW_TILE_SIZE[1] - 1 for i in range(WINDOW_TILE_SIZE[0] - 2)]
stack_heights[0] -= 1
stack_heights[-1] -= 1

pygame.mixer.music.load('data/music.wav')
pygame.mixer.music.play(-1)

def handle_death():
    global dead, run_coins_banked, upgrade_selection, new_high_score, save_data, screen_shake
    if not dead:
        sounds['death'].play()
        screen_shake = 20
        if coins > save_data['high_score']:
            save_data['high_score'] = coins
            new_high_score = True
            write_save(save_data)

        dead = True
        run_coins_banked = False
        upgrade_selection = 0
        player.velocity = [1.3, -6]
        for i in range(380):
            angle = random.random() * math.pi
            speed = random.random() * 1.5
            physics_on = random.choice([False, True, True])
            sparks.append([player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.02, (255, 50, 50), physics_on, 0.1 * physics_on])

# ############################# #
# ######### MAIN LOOP ######### #
# ############################# #
while True:
    # --- PALETTE AND BACKGROUND ---
    if not dead:
        next_palette_index = 0
        for i, p in enumerate(LEVEL_PALETTES):
            if coins >= p['score']:
                next_palette_index = i
        if next_palette_index != current_palette_index:
            current_palette_index = next_palette_index

    current_palette = LEVEL_PALETTES[current_palette_index]
    draw_background(display, camera[0], height, current_palette)

    master_clock += 1
    if screen_shake > 0:
        screen_shake -= 0.5
    
    # NEW: Update conveyor animation frame
    conveyor_frame = (conveyor_frame + 0.25) % len(conveyor_frames_left)

    # --- COMBO LOGIC ---
    if combo_timer > 0:
        combo_timer -= 1
        if combo_timer == 0 and combo_multiplier > 1.0:
            if 'combo_end' in sounds:
                sounds['combo_end'].play()
            for i in range(20):
                angle = random.random() * math.pi * 2
                speed = random.random() * 1.5
                sparks.append([[DISPLAY_SIZE[0] // 2, 10], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 2 + 1, 0.05, (200, 255, 255), True, 0.05])
            combo_multiplier = 1.0

    # --- TILE SPAWNING LOGIC ---
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

            roll = random.randint(1, 35) # Adjusted for new tile
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
            # NEW: Conveyor Tile spawn chance
            elif roll < 11:
                tile_type = random.choice(['conveyor_left', 'conveyor_right'])
            else:
                tile_type = 'tile'

            c = random.choice(options) if options else random.randrange(len(stack_heights))
            last_place = c
            tile_drops.append([(c + 1) * TILE_SIZE, -height - TILE_SIZE, tile_type])

    # --- FALLING TILE LOGIC ---
    tile_drop_rects = []
    for i, tile in sorted(enumerate(tile_drops), reverse=True):
        tile[1] += 1.4
        pos = [tile[0] + TILE_SIZE // 2, tile[1] + TILE_SIZE]
        r = pygame.Rect(tile[0], tile[1], TILE_SIZE, TILE_SIZE)
        tile_drop_rects.append(r)

        graze_rect = player.rect.copy()
        graze_rect.inflate_ip(8, 8)
        if graze_rect.colliderect(r) and not player.rect.colliderect(r):
            combo_multiplier += 0.2
            combo_timer = COMBO_DURATION

        if r.colliderect(player.rect):
            handle_death()

        check_pos = (int(pos[0] // TILE_SIZE), int(math.floor(pos[1] / TILE_SIZE)))
        if check_pos in tiles:
            place_pos = (check_pos[0], check_pos[1] - 1)

            if tiles[check_pos]['type'] == 'greed':
                tile_drops.pop(i)
                sounds['chest_open'].play()
                del tiles[check_pos]
                for k in range(random.randint(5, 10)):
                    items.append(Item(animation_manager, (place_pos[0] * TILE_SIZE + 5, place_pos[1] * TILE_SIZE + 5), (6, 6), 'coin', velocity=[random.random() * 5 - 2.5, random.random() * 2 - 7]))
                recalculate_stack_heights()
                continue

            tile_drops.pop(i)
            stack_heights[place_pos[0] - 1] = place_pos[1]
            tiles[place_pos] = {'type': tile[2], 'data': {}}
            sounds['block_land'].play()

            if abs(player.pos[0] - place_pos[0] * TILE_SIZE) < 40:
                screen_shake = max(screen_shake, 4)

            if tiles[check_pos]['type'] == 'chest':
                tiles[check_pos]['type'] = 'tile'
                sounds['chest_destroy'].play()
                for spark_i in range(100):
                    angle = random.random() * math.pi * 2
                    speed = random.random() * 2.5
                    sparks.append([[place_pos[0] * TILE_SIZE + TILE_SIZE // 2, place_pos[1] * TILE_SIZE + TILE_SIZE // 2], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.09, (255,100,255), False, 0.1])
            continue
        
        render_pos = (tile[0] - camera[0], tile[1] + height)
        if tile[2] == 'greed':
             display.blit(greed_tile_img, render_pos)
        else:
             display.blit(tile_img, render_pos)

        if tile[2] == 'chest':
            display.blit(ghost_chest_img, (render_pos[0], render_pos[1] - TILE_SIZE))
        if random.randint(1, 4) == 1:
            side = random.choice([1, -1])
            sparks.append([[tile[0] + TILE_SIZE * (side == 1), tile[1]], [random.random() * 0.1 - 0.05, random.random() * 0.5], random.random() * 5 + 3, 0.15, (200, 255, 255), False, 0])

    # --- FRAGILE TILE LOGIC ---
    tiles_to_remove = []
    for tile_pos, tile_data in tiles.items():
        if tile_data['type'] == 'fragile':
            if 'timer' in tile_data['data']:
                tile_data['data']['timer'] -= 1
                if random.randint(1, 10) == 1:
                    sparks.append([[tile_pos[0] * TILE_SIZE + random.random() * 16, tile_pos[1] * TILE_SIZE + 14], [random.random() * 0.5 - 0.25, random.random() * 0.5], random.random() * 2 + 1, 0.08, (255, 200, 100), True, 0.05])
                if tile_data['data']['timer'] <= 0:
                    tiles_to_remove.append(tile_pos)
                    for i in range(20):
                        angle = random.random() * math.pi * 2; speed = random.random() * 1.5
                        sparks.append([[tile_pos[0] * TILE_SIZE + 8, tile_pos[1] * TILE_SIZE + 8], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 4 + 2, 0.05, (255, 200, 100), True, 0.1])

    for tile_pos in tiles_to_remove:
        if tile_pos in tiles:
            del tiles[tile_pos]
            recalculate_stack_heights()

    # --- TILE RENDERING AND LOGIC ---
    tile_rects = []
    for tile_pos in tiles:
        tile_rects.append(pygame.Rect(TILE_SIZE * tile_pos[0], TILE_SIZE * tile_pos[1], TILE_SIZE, TILE_SIZE))
        tile_type = tiles[tile_pos]['type']
        render_pos = (TILE_SIZE * tile_pos[0] - camera[0], TILE_SIZE * tile_pos[1] + int(height))

        img_to_blit = tile_img
        if tile_type == 'placed_tile': img_to_blit = placed_tile_img
        elif tile_type == 'greed': img_to_blit = greed_tile_img
        elif tile_type == 'fragile': img_to_blit = fragile_tile_img
        elif tile_type == 'bounce': img_to_blit = bounce_tile_img
        elif tile_type == 'spike': img_to_blit = spike_tile_img
        elif tile_type == 'conveyor_left': img_to_blit = conveyor_frames_left[int(conveyor_frame)]
        elif tile_type == 'conveyor_right': img_to_blit = conveyor_frames_right[int(conveyor_frame)]

        display.blit(img_to_blit, render_pos)

        is_top = (tile_pos[0], tile_pos[1] - 1) not in tiles
        if is_top and tile_type in ['tile', 'placed_tile']:
            display.blit(tile_top_img, render_pos)

        if tile_type == 'chest':
            display.blit(chest_img, (render_pos[0], render_pos[1] - TILE_SIZE))
            chest_r = pygame.Rect(TILE_SIZE * tile_pos[0] + 2, TILE_SIZE * (tile_pos[1] - 1) + 6, TILE_SIZE - 4, TILE_SIZE - 6)
            if random.randint(1, 20) == 1:
                sparks.append([[tile_pos[0] * TILE_SIZE + 2 + 12 * random.random(), (tile_pos[1] - 1) * TILE_SIZE + 4 + 8 * random.random()], [0, random.random() * 0.25 - 0.5], random.random() * 4 + 2, 0.023, (255,220,100), True, 0.002])
            if chest_r.colliderect(player.rect):
                sounds['chest_open'].play()
                combo_multiplier += 1.0; combo_timer = COMBO_DURATION
                for i in range(50):
                    sparks.append([[tile_pos[0] * TILE_SIZE + 8, (tile_pos[1] - 1) * TILE_SIZE + 8], [random.random() * 2 - 1, random.random() - 2], random.random() * 3 + 3, 0.01, (255,220,100), True, 0.05])
                tiles[tile_pos]['type'] = 'opened_chest'
                player.jumps += 1; player.attempt_jump(); player.velocity[1] = -3.5
                item_luck_threshold = 3 + save_data['upgrades']['item_luck']
                if random.randint(1, 5) < item_luck_threshold:
                    items.append(Item(animation_manager, (tile_pos[0] * TILE_SIZE + 5, (tile_pos[1] - 1) * TILE_SIZE + 5), (6, 6), random.choice(['warp', 'cube', 'jump', 'bomb']), velocity=[random.random() * 5 - 2.5, random.random() * 2 - 5]))
                else:
                    for i in range(random.randint(2, 6)):
                        items.append(Item(animation_manager, (tile_pos[0] * TILE_SIZE + 5, (tile_pos[1] - 1) * TILE_SIZE + 5), (6, 6), 'coin', velocity=[random.random() * 5 - 2.5, random.random() * 2 - 7]))
        elif tile_type == 'opened_chest':
            display.blit(opened_chest_img, (render_pos[0], render_pos[1] - TILE_SIZE))

    # --- LEVEL SCROLLING ---
    base_row = max(tiles, key=lambda x: x[1])[1] - 1 if tiles else WINDOW_TILE_SIZE[1] - 2
    filled = True
    for i in range(WINDOW_TILE_SIZE[0] - 2):
        if (i + 1, base_row) not in tiles: filled = False
    if filled:
        target_height = math.floor(height / TILE_SIZE) * TILE_SIZE + TILE_SIZE

    if height != target_height:
        height += (target_height - height) / 10
        if abs(target_height - height) < 0.2:
            height = target_height
            for i in range(WINDOW_TILE_SIZE[0] - 2):
                if (i + 1, base_row + 1) in tiles:
                    del tiles[(i + 1, base_row + 1)]

    # --- BORDERS ---
    for i in range(WINDOW_TILE_SIZE[1] + 2):
        pos_y = (-height // 16) - 1 + i
        display.blit(edge_tile_img, (0 - camera[0], TILE_SIZE * pos_y + int(height)))
        display.blit(edge_tile_img, (TILE_SIZE * (WINDOW_TILE_SIZE[0] - 1) - camera[0], TILE_SIZE * pos_y + int(height)))

    edge_rects = [pygame.Rect(0, -300, TILE_SIZE, 600), pygame.Rect(TILE_SIZE * (WINDOW_TILE_SIZE[0] - 1), -300, TILE_SIZE, 600)]

    # --- ITEM LOGIC AND RENDERING ---
    for i, item in sorted(enumerate(items), reverse=True):
        if (int(item.center[0] // TILE_SIZE), int(item.center[1] // TILE_SIZE)) in tiles:
            items.pop(i); continue
        item.update(edge_rects + lookup_nearby(tiles, item.center))
        if item.time > 30 and item.rect.colliderect(player.rect):
            if item.type == 'coin':
                sounds['coin'].play()
                coins += int(1 * combo_multiplier); combo_multiplier += 0.1; combo_timer = COMBO_DURATION
                for j in range(25): sparks.append([item.center.copy(), [math.cos(random.random() * math.pi * 2) * random.random() * 0.4, math.sin(random.random() * math.pi * 2) * random.random() * 0.4], random.random() * 3 + 3, 0.02, (255,220,100), random.choice([False, True]), 0.1])
            else:
                sounds['collect_item'].play()
                for j in range(50): sparks.append([item.center.copy(), [random.random() * 0.3 - 0.15, random.random() * 6 - 3], random.random() * 4 + 3, 0.01, (255,100,255), False, 0])
                current_item = item.type
            items.pop(i); continue
        r1 = int(9 + math.sin(master_clock / 30) * 3); r2 = int(5 + math.sin(master_clock / 40) * 2)
        display.blit(glow_img(r1, (255,180,50)), (item.center[0] - r1 - 1 - camera[0], item.center[1] + height - r1 - 2), special_flags=BLEND_RGBA_ADD)
        display.blit(glow_img(r2, (255,220,80)), (item.center[0] - r2 - 1 - camera[0], item.center[1] + height - r2 - 2), special_flags=BLEND_RGBA_ADD)
        item.render(display, (camera[0], -height))

    # --- PLAYER LOGIC AND RENDERING ---
    if not dead:
        collisions = player.update(tile_drop_rects + edge_rects + tile_rects)

        if collisions['bottom']:
            player_feet_pos = player.rect.midbottom
            tile_pos_below = (player_feet_pos[0] // TILE_SIZE, player_feet_pos[1] // TILE_SIZE)

            if tile_pos_below in tiles:
                tile_type_below = tiles[tile_pos_below]['type']
                if tile_type_below == 'fragile':
                    if 'timer' not in tiles[tile_pos_below]['data']:
                        sounds['block_land'].play(); tiles[tile_pos_below]['data']['timer'] = 90
                elif tile_type_below == 'bounce':
                    player.velocity[1] = -9; player.jumps = player.jumps_max
                    sounds['super_jump'].play(); screen_shake = 10; combo_multiplier += 0.5; combo_timer = COMBO_DURATION
                    for i in range(40): sparks.append([[player.rect.centerx, player.rect.bottom], [math.cos(random.random() * math.pi - math.pi) * random.random() * 2, math.sin(random.random() * math.pi - math.pi) * random.random() * 2], random.random() * 3 + 2, 0.04, (255,100,255), True, 0.1])
                elif tile_type_below == 'spike':
                    handle_death(); player.velocity = [0, -4]
                # NEW: Conveyor logic
                elif tile_type_below == 'conveyor_left':
                    player.pos[0] -= 1.2
                elif tile_type_below == 'conveyor_right':
                    player.pos[0] += 1.2
    else:
        player.opacity = 80; player.update([]); player.rotation -= 16
    
    # NEW: Player trail
    if not dead:
        player_trail.append((player.img.copy(), (player.pos[0], player.pos[1] + int(height)), player.flip))
    for i, trail in enumerate(player_trail):
        img, pos, flip = trail
        img.set_alpha(i * 15)
        display.blit(img, (pos[0] - camera[0] - (4 if not flip[0] else -4), pos[1] - 2))

    player.render(display, (camera[0], -int(height)))

    # --- PARTICLE RENDERING ---
    for i, spark in sorted(enumerate(sparks), reverse=True):
        if len(spark) < 8: spark.append(False)
        if not spark[-1]: spark[1][1] = min(spark[1][1] + spark[-2], 3)
        spark[0][0] += spark[1][0]
        if spark[5]:
            if ((int(spark[0][0] // TILE_SIZE), int(spark[0][1] // TILE_SIZE)) in tiles) or (spark[0][0] < TILE_SIZE) or (spark[0][0] > DISPLAY_SIZE[0] - TILE_SIZE):
                spark[0][0] -= spark[1][0]; spark[1][0] *= -0.7
        spark[0][1] += spark[1][1]
        if spark[5]:
            if (int(spark[0][0] // TILE_SIZE), int(spark[0][1] // TILE_SIZE)) in tiles:
                spark[0][1] -= spark[1][1]; spark[1][1] *= -0.7
                if abs(spark[1][1]) < 0.1: spark[1][1] = 0; spark[-1] = True
        spark[2] -= spark[3]
        if spark[2] <= 1: sparks.pop(i)
        else:
            render_pos = (spark[0][0] - camera[0], spark[0][1] + height)
            display.blit(glow_img(int(spark[2] * 1.5 + 2), tuple([c/2 for c in spark[4]])), (render_pos[0] - spark[2] * 2, render_pos[1] - spark[2] * 2), special_flags=BLEND_RGBA_ADD)
            display.blit(glow_img(int(spark[2]), spark[4]), (render_pos[0] - spark[2], render_pos[1] - spark[2]), special_flags=BLEND_RGBA_ADD)
            display.set_at((int(render_pos[0]), int(render_pos[1])), (255, 255, 255))

    # --- VIGNETTE & CAMERA ---
    display.blit(vignette_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    
    # NEW: Update camera
    if not dead:
        target_camera_x = player.rect.centerx - DISPLAY_SIZE[0] / 2
        camera[0] += (target_camera_x - camera[0]) / 15 # Smooth follow

    # --- UI & HUD ---
    if not dead:
        # Score
        display.blit(coin_icon, (4, 4)); black_font.render(str(coins), display, (17, 6)); white_font.render(str(coins), display, (16, 5))
        # Jumps
        for i in range(player.jumps): display.blit(jump_icon_small, (5 + i * 10, 18))
        # Combo
        if combo_multiplier > 1.0:
            combo_text = f"x{combo_multiplier:.1f}"; text_width = white_font.width(combo_text)
            black_font.render(combo_text, display, (DISPLAY_SIZE[0] // 2 - text_width // 2 + 1, 6))
            white_font.render(combo_text, display, (DISPLAY_SIZE[0] // 2 - text_width // 2, 5))
            bar_width = (combo_timer / COMBO_DURATION) * 40; bar_x = DISPLAY_SIZE[0] // 2 - 20
            pygame.draw.rect(display, (20,10,30), [bar_x + 1, 15, 40, 3]); pygame.draw.rect(display, (200,255,255), [bar_x, 14, bar_width, 3])
        # Item Slot
        display.blit(item_slot_img, (DISPLAY_SIZE[0] - 20, 4))
        if current_item:
            if (master_clock % 50 < 12) or (abs(master_clock % 50 - 20) < 3): display.blit(item_slot_flash_img, (DISPLAY_SIZE[0] - 20, 4))
            display.blit(item_icons[current_item], (DISPLAY_SIZE[0] - 15, 9))
            if not item_used and (master_clock % 100 < 80) or (abs(master_clock % 100 - 90) < 3):
                black_font.render('E/X', display, (DISPLAY_SIZE[0] - white_font.width('E/X') - 23, 10)); white_font.render('E/X', display, (DISPLAY_SIZE[0] - white_font.width('E/X') - 24, 9))
    else: # Game Over Screen
        y_offset = 60
        black_font.render('GAME OVER', display, (DISPLAY_SIZE[0] // 2 - white_font.width('GAME OVER') // 2 + 1, y_offset + 1))
        white_font.render('GAME OVER', display, (DISPLAY_SIZE[0] // 2 - white_font.width('GAME OVER') // 2, y_offset)); y_offset += 20

        if new_high_score:
            hs_text = "NEW HIGH SCORE!"
            hs_color = (255, 230, 90) if master_clock % 40 < 20 else (255, 100, 100)
            hs_font = Font('data/fonts/small_font.png', hs_color)
            hs_font.render(hs_text, display, (DISPLAY_SIZE[0] // 2 - hs_font.width(hs_text) // 2, y_offset))
        else:
            hs_text = f"High Score: {save_data['high_score']}"; white_font.render(hs_text, display, (DISPLAY_SIZE[0] // 2 - white_font.width(hs_text) // 2, y_offset))
        y_offset += 15

        score_text = f"Score: {coins}"; white_font.render(score_text, display, (DISPLAY_SIZE[0] // 2 - white_font.width(score_text) // 2, y_offset)); y_offset += 15
        
        if end_coin_count != coins:
            if master_clock % 3 == 0: sounds['coin_end'].play(); end_coin_count = min(end_coin_count + 1, coins)
        elif not run_coins_banked:
            save_data['banked_coins'] += end_coin_count; write_save(save_data); run_coins_banked = True

        bank_text = f"Bank: {save_data['banked_coins']}"; black_font.render(bank_text, display, (DISPLAY_SIZE[0] // 2 - white_font.width(bank_text) // 2 + 1, y_offset + 1)); white_font.render(bank_text, display, (DISPLAY_SIZE[0] // 2 - white_font.width(bank_text) // 2, y_offset)); y_offset += 15

        if run_coins_banked:
            y_offset += 10; black_font.render("UPGRADES", display, (DISPLAY_SIZE[0]//2 - black_font.width("UPGRADES")//2, y_offset)); y_offset += 15
            for i, key in enumerate(upgrade_keys):
                upgrade = UPGRADES[key]; level = save_data['upgrades'][key]; cost = int(upgrade['base_cost'] * (1.5 ** level))
                color = (255, 230, 90) if i == upgrade_selection else white_font.color
                temp_font = Font('data/fonts/small_font.png', color)
                if i == upgrade_selection: white_font.render('>', display, (10, y_offset))
                level_text = f"[{level}/{upgrade['max_level']}]" if level < upgrade['max_level'] else "[MAX]"
                name_text = f"{upgrade['name']} {level_text}"; temp_font.render(name_text, display, (22, y_offset))
                if level < upgrade['max_level']:
                    cost_text = str(cost); display.blit(coin_icon, (DISPLAY_SIZE[0] - 22 - white_font.width(cost_text), y_offset - 2)); temp_font.render(cost_text, display, (DISPLAY_SIZE[0] - white_font.width(cost_text) - 18, y_offset))
                y_offset += 15

            y_offset += 5
            help_text = "Up/Down:Select - Enter:Buy"
            white_font.render(help_text, display, (DISPLAY_SIZE[0] // 2 - white_font.width(help_text) // 2, y_offset)); y_offset += 15
            white_font.render('press R to restart', display, (DISPLAY_SIZE[0] // 2 - white_font.width('press R to restart') // 2, y_offset))

    # --- EVENT HANDLING ---
    for event in pygame.event.get():
        if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
            pygame.quit(); sys.exit()
        if event.type == KEYDOWN:
            if not dead:
                if event.key in [K_RIGHT, K_d]: player.right = True
                if event.key in [K_LEFT, K_a]: player.left = True
                if event.key in [K_UP, K_w, K_SPACE]:
                    player.jump_buffer_timer = 8
                    if player.air_time < 2 or player.coyote_timer > 0 or player.jumps > 0:
                        sounds['jump'].play(); player.attempt_jump()
                if event.key in [K_e, K_x] and current_item:
                    item_used = True
                    if current_item == 'warp':
                        sounds['warp'].play(); screen_shake = 15
                        max_point = min(enumerate(stack_heights), key=lambda x: x[1])
                        player.pos[0] = (max_point[0] + 1) * TILE_SIZE + 4; player.pos[1] = (max_point[1] - 1) * TILE_SIZE
                        for i in range(60): sparks.append([player.center.copy(), [math.cos(random.random() * math.pi * 2) * random.random() * 1.75, math.sin(random.random() * math.pi * 2) * random.random() * 1.75], random.random() * 3 + 3, 0.02, (255,100,255), True, 0.1 * random.choice([0,1])])
                    if current_item == 'jump':
                        sounds['super_jump'].play(); screen_shake = 12
                        player.jumps += 1; player.attempt_jump(); player.velocity[1] = -8
                    if current_item == 'cube':
                        sounds['block_land'].play()
                        place_pos = (int(player.center[0] // TILE_SIZE), int(player.pos[1] // TILE_SIZE) + 1)
                        if 0 < place_pos[0] < WINDOW_TILE_SIZE[0]-1:
                           stack_heights[place_pos[0] - 1] = place_pos[1]
                           current_base_row = max(tiles, key=lambda x: x[1])[1] - 1 if tiles else WINDOW_TILE_SIZE[1] - 2
                           for i in range(place_pos[1], current_base_row + 2):
                               tiles[(place_pos[0], i)] = {'type': 'placed_tile', 'data': {}}
                    if current_item == 'bomb':
                        if 'explosion' in sounds: sounds['explosion'].play()
                        screen_shake = 25; tiles_to_bomb = []
                        bomb_radius = 4 * TILE_SIZE
                        for tile_pos in tiles:
                            tile_center = (tile_pos[0] * TILE_SIZE + 8, tile_pos[1] * TILE_SIZE + 8)
                            if math.sqrt((player.center[0] - tile_center[0])**2 + (player.center[1] - tile_center[1])**2) < bomb_radius:
                                tiles_to_bomb.append(list(tile_pos))
                        for tile_pos in tiles_to_bomb:
                            if tuple(tile_pos) in tiles:
                                for i in range(15): sparks.append([[tile_pos[0] * TILE_SIZE + 8, tile_pos[1] * TILE_SIZE + 8], [math.cos(random.random()*math.pi*2) * random.random()*2, math.sin(random.random()*math.pi*2) * random.random()*2], random.random() * 4 + 2, 0.08, (255,50,50), True, 0.1])
                                del tiles[tuple(tile_pos)]
                        recalculate_stack_heights()
                    current_item = None
            elif run_coins_banked:
                if event.key == K_DOWN: upgrade_selection = (upgrade_selection + 1) % len(upgrade_keys)
                if event.key == K_UP: upgrade_selection = (upgrade_selection - 1 + len(upgrade_keys)) % len(upgrade_keys)
                if event.key == K_RETURN:
                    key = upgrade_keys[upgrade_selection]; upgrade = UPGRADES[key]
                    level = save_data['upgrades'][key]; cost = int(upgrade['base_cost'] * (1.5 ** level))
                    if level < upgrade['max_level'] and save_data['banked_coins'] >= cost:
                        save_data['banked_coins'] -= cost; save_data['upgrades'][key] += 1
                        write_save(save_data)
                        if 'upgrade' in sounds: sounds['upgrade'].play()
                        else: sounds['collect_item'].play()

            if event.key == K_r and dead:
                player = Player(animation_manager, (DISPLAY_SIZE[0] // 2 - 5, -20), (8, 16), 'player')
                player.jumps_max += save_data['upgrades']['jumps']; player.speed += save_data['upgrades']['speed'] * 0.08
                player.jumps = player.jumps_max
                dead = False; tiles = {}; tile_drops = []; sparks = []
                game_timer = 0; height = 0; target_height = 0; coins = 0; end_coin_count = 0
                current_item = None; master_clock = 0; combo_multiplier = 1.0; combo_timer = 0
                run_coins_banked = False; screen_shake = 0; new_high_score = False; current_palette_index = 0
                camera = [0, 0]; player_trail.clear()
                for i in range(WINDOW_TILE_SIZE[0] - 2): tiles[(i + 1, WINDOW_TILE_SIZE[1] - 1)] = {'type': 'tile', 'data': {}}
                tiles[(1, WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}; tiles[(WINDOW_TILE_SIZE[0] - 2, WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
                stack_heights = [WINDOW_TILE_SIZE[1] - 1 for i in range(WINDOW_TILE_SIZE[0] - 2)]; stack_heights[0] -= 1; stack_heights[-1] -= 1
                items = []

        if event.type == KEYUP:
            if event.key in [K_RIGHT, K_d]: player.right = False
            if event.key in [K_LEFT, K_a]: player.left = False

    # --- FINAL RENDER ---
    render_offset = [0, 0]
    if screen_shake > 0:
        render_offset[0] = random.randint(0, int(screen_shake)) - int(screen_shake) // 2
        render_offset[1] = random.randint(0, int(screen_shake)) - int(screen_shake) // 2

    screen.blit(pygame.transform.scale(display, screen.get_size()), render_offset)
    pygame.display.update()
    clock.tick(60)