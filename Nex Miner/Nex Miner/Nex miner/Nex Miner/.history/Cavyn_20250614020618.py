# this is very spaghetti because it was written in under 8 hours

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
pygame.display.set_caption('Cavyn: Recharged') # New title!
DISPLAY_SIZE = (320, 180) # New Widescreen Resolution
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

# -- NEW FEATURE: VISUAL LEVEL PROGRESSION --
LEVEL_PALETTES = [
    {'score': 0, 'bg': (22, 19, 40), 'particles': [(0, 0, 0), (22, 19, 40)]},
    {'score': 75, 'bg': (40, 19, 30), 'particles': [(0, 0, 0), (40, 19, 30), (80, 20, 40)]},
    {'score': 200, 'bg': (19, 30, 40), 'particles': [(0, 0, 0), (19, 30, 40), (20, 60, 80)]},
    {'score': 400, 'bg': (40, 30, 19), 'particles': [(0, 0, 0), (40, 30, 19), (120, 60, 20)]},
]
current_palette_index = 0

def load_img(path):
    img = pygame.image.load(path).convert()
    img.set_colorkey((0, 0, 0))
    return img

# -- NEW FEATURE: GRAPHICS OVERHAUL --
try:
    background_img = pygame.image.load('data/images/background.jpg').convert()
    background_img = pygame.transform.scale(background_img, DISPLAY_SIZE)
except pygame.error:
    background_img = None # Fallback if image is missing

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
# -- NEW FEATURE: COMBO END --
if 'combo_end' in sounds:
    sounds['combo_end'].set_volume(0.6)

item_icons = {
    'cube': load_img('data/images/cube_icon.png'),
    'warp': load_img('data/images/warp_icon.png'),
    'jump': load_img('data/images/jump_icon.png'),
    'bomb': load_img('data/images/bomb_icon.png'),
    'freeze': load_img('data/images/freeze_icon.png'), # NEW
}

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
                    sparks.append([[player.center[0] + random.random() * 14 - 7, player.center[1]], [direction * (random.random() * 0.05 + 0.05) + (random.random() * 4 - 2) * physics_on, random.random() * 0.05 + random.random() * 2 * physics_on], random.random() * 3 + 3, 0.04 - 0.02 * physics_on, (6, 4, 1), physics_on, 0.05 * physics_on])

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

# -- NEW FEATURE: PLAYER PROJECTILE --
class Projectile(Entity):
    def __init__(self, *args, velocity=[0, 0]):
        super().__init__(*args)
        self.velocity = velocity

    def update(self):
        super().update(1/60)
        self.pos[0] += self.velocity[0]
        self.pos[1] += self.velocity[1]


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

player = Player(animation_manager, (DISPLAY_SIZE[0] // 2 - 5, -20), (8, 16), 'player')
player.jumps_max += save_data['upgrades']['jumps']
player.speed += save_data['upgrades']['speed'] * 0.08
player.jumps = player.jumps_max

dead = False

tiles = {}
tile_drops = []
bg_particles = []
sparks = []
projectiles = [] # NEW
freeze_timer = 0 # NEW

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
# -- NEW FEATURE: HIGH SCORE --
new_high_score = False

for i in range(WINDOW_TILE_SIZE[0] - 2):
    tiles[(i + 1, WINDOW_TILE_SIZE[1] - 1)] = {'type': 'tile', 'data': {}}

tiles[(1, WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
tiles[(WINDOW_TILE_SIZE[0] - 2, WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}


stack_heights = [WINDOW_TILE_SIZE[1] - 1 for i in range(WINDOW_TILE_SIZE[0] - 2)]
stack_heights[0] -= 1
stack_heights[-1] -= 1

items = []

pygame.mixer.music.load('data/music.wav')
pygame.mixer.music.play(-1)

def handle_death():
    global dead, run_coins_banked, upgrade_selection, new_high_score, save_data, screen_shake
    if not dead:
        sounds['death'].play()
        screen_shake = 20
        # -- NEW FEATURE: HIGH SCORE --
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
            sparks.append([player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.02, (12, 2, 2), physics_on, 0.1 * physics_on])

while True:
    # -- NEW FEATURE: VISUAL LEVEL PROGRESSION --
    if not dead:
        next_palette_index = 0
        for i, p in enumerate(LEVEL_PALETTES):
            if coins >= p['score']:
                next_palette_index = i
        if next_palette_index != current_palette_index:
            current_palette_index = next_palette_index
            # You could add a transition effect here

    current_palette = LEVEL_PALETTES[current_palette_index]

    # -- NEW FEATURE: BACKGROUND IMAGE --
    if background_img:
        display.blit(background_img, (0, 0))
    else:
        display.fill(current_palette['bg']) # Fallback

    master_clock += 1

    if screen_shake > 0:
        screen_shake -= 0.5

    # -- NEW FEATURE: FREEZE TIME POWERUP --
    if freeze_timer > 0:
        freeze_timer -= 1
        # Visual effect for frozen time
        freeze_overlay = pygame.Surface(DISPLAY_SIZE, pygame.SRCALPHA)
        alpha = 60 + math.sin(master_clock / 5) * 10
        freeze_overlay.fill((170, 200, 255, alpha))
        display.blit(freeze_overlay, (0, 0))


    # -- NEW FEATURE: COMBO END --
    if combo_timer > 0:
        combo_timer -= 1
        if combo_timer == 0 and combo_multiplier > 1.0:
            if 'combo_end' in sounds:
                sounds['combo_end'].play()
            # Particle burst at combo meter location
            for i in range(20):
                angle = random.random() * math.pi * 2
                speed = random.random() * 1.5
                sparks.append([[DISPLAY_SIZE[0] // 2, 10], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 2 + 1, 0.05, (251, 245, 239), True, 0.05])
            combo_multiplier = 1.0

    parallax = random.random()
    for i in range(2):
        bg_particles.append([[random.random() * DISPLAY_SIZE[0], DISPLAY_SIZE[1] - height * parallax], parallax, random.randint(1, 8), random.random() * 1 + 1, random.choice(current_palette['particles'])])

    for i, p in sorted(enumerate(bg_particles), reverse=True):
        size = p[2]
        if p[-1] != (0, 0, 0):
            size = size * 5 + 4
        p[2] -= 0.01
        p[0][1] -= p[3]
        if size < 1:
            display.set_at((int(p[0][0]), int(p[0][1] + height * p[1])), (0, 0, 0))
        else:
            if p[-1] != (0, 0, 0):
                pygame.draw.circle(display, p[-1], p[0], int(size), 4)
            else:
                pygame.draw.circle(display, p[-1], p[0], int(size))
        if size < 0:
            bg_particles.pop(i)

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


    tile_drop_rects = []
    for i, tile in sorted(enumerate(tile_drops), reverse=True):
        if freeze_timer <= 0: # Check if time is frozen
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
                for i in range(100):
                    angle = random.random() * math.pi * 2
                    speed = random.random() * 2.5
                    sparks.append([[place_pos[0] * TILE_SIZE + TILE_SIZE // 2, place_pos[1] * TILE_SIZE + TILE_SIZE // 2], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.09, (12, 8, 2), False, 0.1])
            continue

        if tile[2] == 'greed':
             display.blit(greed_tile_img, (tile[0], tile[1] + height))
        else:
             display.blit(tile_img, (tile[0], tile[1] + height))

        if tile[2] == 'chest':
            display.blit(ghost_chest_img, (tile[0], tile[1] + height - TILE_SIZE))
        if random.randint(1, 4) == 1:
            side = random.choice([1, -1])
            sparks.append([[tile[0] + TILE_SIZE * (side == 1), tile[1]], [random.random() * 0.1 - 0.05, random.random() * 0.5], random.random() * 5 + 3, 0.15, (4, 2, 12), False, 0])


    tiles_to_remove = []
    for tile_pos, tile_data in tiles.items():
        if tile_data['type'] == 'fragile':
            if 'timer' in tile_data['data']:
                tile_data['data']['timer'] -= 1
                if random.randint(1, 10) == 1:
                    sparks.append([
                        [tile_pos[0] * TILE_SIZE + random.random() * 16, tile_pos[1] * TILE_SIZE + 14],
                        [random.random() * 0.5 - 0.25, random.random() * 0.5],
                        random.random() * 2 + 1, 0.08, (6, 4, 1), True, 0.05
                    ])
                if tile_data['data']['timer'] <= 0:
                    tiles_to_remove.append(tile_pos)
                    for i in range(20):
                        angle = random.random() * math.pi * 2
                        speed = random.random() * 1.5
                        sparks.append([
                            [tile_pos[0] * TILE_SIZE + 8, tile_pos[1] * TILE_SIZE + 8],
                            [math.cos(angle) * speed, math.sin(angle) * speed],
                            random.random() * 4 + 2, 0.05, (6, 4, 1), True, 0.1
                        ])

    for tile_pos in tiles_to_remove:
        if tile_pos in tiles:
            del tiles[tile_pos]
            recalculate_stack_heights()

    tile_rects = []
    for tile_pos in tiles:
        tile_rects.append(pygame.Rect(TILE_SIZE * tile_pos[0], TILE_SIZE * tile_pos[1], TILE_SIZE, TILE_SIZE))
        tile_type = tiles[tile_pos]['type']

        img_to_blit = tile_img
        if tile_type == 'placed_tile':
            img_to_blit = placed_tile_img
        elif tile_type == 'greed':
            img_to_blit = greed_tile_img

        display.blit(img_to_blit, (TILE_SIZE * tile_pos[0], TILE_SIZE * tile_pos[1] + int(height)))

        is_top = (tile_pos[0], tile_pos[1] - 1) not in tiles
        if is_top and tile_type in ['tile', 'placed_tile']:
            display.blit(tile_top_img, (TILE_SIZE * tile_pos[0], TILE_SIZE * tile_pos[1] + int(height)))

        if tile_type == 'fragile':
            display.blit(fragile_tile_img, (TILE_SIZE * tile_pos[0], TILE_SIZE * tile_pos[1] + int(height)))
        if tile_type == 'bounce':
            display.blit(bounce_tile_img, (TILE_SIZE * tile_pos[0], TILE_SIZE * tile_pos[1] + int(height)))
        if tile_type == 'spike':
            display.blit(spike_tile_img, (TILE_SIZE * tile_pos[0], TILE_SIZE * tile_pos[1] + int(height)))

        if tile_type == 'chest':
            display.blit(chest_img, (TILE_SIZE * tile_pos[0], TILE_SIZE * (tile_pos[1] - 1) + int(height)))
            chest_r = pygame.Rect(TILE_SIZE * tile_pos[0] + 2, TILE_SIZE * (tile_pos[1] - 1) + 6, TILE_SIZE - 4, TILE_SIZE - 6)
            if random.randint(1, 20) == 1:
                sparks.append([[tile_pos[0] * TILE_SIZE + 2 + 12 * random.random(), (tile_pos[1] - 1) * TILE_SIZE + 4 + 8 * random.random()], [0, random.random() * 0.25 - 0.5], random.random() * 4 + 2, 0.023, (12, 8, 2), True, 0.002])
            if chest_r.colliderect(player.rect):
                sounds['chest_open'].play()
                combo_multiplier += 1.0
                combo_timer = COMBO_DURATION
                for i in range(50):
                    sparks.append([[tile_pos[0] * TILE_SIZE + 8, (tile_pos[1] - 1) * TILE_SIZE + 8], [random.random() * 2 - 1, random.random() - 2], random.random() * 3 + 3, 0.01, (12, 8, 2), True, 0.05])
                tiles[tile_pos]['type'] = 'opened_chest'
                player.jumps += 1
                player.attempt_jump()
                player.velocity[1] = -3.5
                item_luck_threshold = 3 + save_data['upgrades']['item_luck']
                if random.randint(1, 5) < item_luck_threshold:
                    items.append(Item(animation_manager, (tile_pos[0] * TILE_SIZE + 5, (tile_pos[1] - 1) * TILE_SIZE + 5), (6, 6), random.choice(['warp', 'cube', 'jump', 'bomb', 'freeze']), velocity=[random.random() * 5 - 2.5, random.random() * 2 - 5]))
                else:
                    for i in range(random.randint(2, 6)):
                        items.append(Item(animation_manager, (tile_pos[0] * TILE_SIZE + 5, (tile_pos[1] - 1) * TILE_SIZE + 5), (6, 6), 'coin', velocity=[random.random() * 5 - 2.5, random.random() * 2 - 7]))
        elif tile_type == 'opened_chest':
            display.blit(opened_chest_img, (TILE_SIZE * tile_pos[0], TILE_SIZE * (tile_pos[1] - 1) + int(height)))

    base_row = max(tiles, key=lambda x: x[1])[1] - 1 if tiles else WINDOW_TILE_SIZE[1] - 2
    filled = True
    for i in range(WINDOW_TILE_SIZE[0] - 2):
        if (i + 1, base_row) not in tiles:
            filled = False
    if filled:
        target_height = math.floor(height / TILE_SIZE) * TILE_SIZE + TILE_SIZE

    if height != target_height:
        height += (target_height - height) / 10
        if abs(target_height - height) < 0.2:
            height = target_height
            for i in range(WINDOW_TILE_SIZE[0] - 2):
                if (i + 1, base_row + 1) in tiles:
                    del tiles[(i + 1, base_row + 1)]

    for i in range(WINDOW_TILE_SIZE[1] + 2):
        pos_y = (-height // 16) - 1 + i
        display.blit(edge_tile_img, (0, TILE_SIZE * pos_y + int(height)))
        display.blit(edge_tile_img, (TILE_SIZE * (WINDOW_TILE_SIZE[0] - 1), TILE_SIZE * pos_y + int(height)))

    edge_rects = []
    edge_rects.append(pygame.Rect(0, player.pos[1] - 300, TILE_SIZE, 600))
    edge_rects.append(pygame.Rect(TILE_SIZE * (WINDOW_TILE_SIZE[0] - 1), player.pos[1] - 300, TILE_SIZE, 600))

    for i, item in sorted(enumerate(items), reverse=True):
        lookup_pos = (int(item.center[0] // TILE_SIZE), int(item.center[1] // TILE_SIZE))
        if lookup_pos in tiles:
            items.pop(i)
            continue
        item.update(edge_rects + lookup_nearby(tiles, item.center))
        if item.time > 30:
            if item.rect.colliderect(player.rect):
                if item.type == 'coin':
                    sounds['coin'].play()
                    coins += int(1 * combo_multiplier)
                    combo_multiplier += 0.1
                    combo_timer = COMBO_DURATION
                    for j in range(25):
                        angle = random.random() * math.pi * 2
                        speed = random.random() * 0.4
                        physics_on = random.choice([False, False, False, False, True])
                        sparks.append([item.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.02, (12, 8, 2), physics_on, 0.1 * physics_on])
                else:
                    sounds['collect_item'].play()
                    for j in range(50):
                        sparks.append([item.center.copy(), [random.random() * 0.3 - 0.15, random.random() * 6 - 3], random.random() * 4 + 3, 0.01, (12, 8, 2), False, 0])
                    current_item = item.type
                items.pop(i)
                continue
        r1 = int(9 + math.sin(master_clock / 30) * 3)
        r2 = int(5 + math.sin(master_clock / 40) * 2)
        display.blit(glow_img(r1, (12, 8, 2)), (item.center[0] - r1 - 1, item.center[1] + height - r1 - 2), special_flags=BLEND_RGBA_ADD)
        display.blit(glow_img(r2, (24, 16, 3)), (item.center[0] - r2 - 1, item.center[1] + height - r2 - 2), special_flags=BLEND_RGBA_ADD)
        item.render(display, (0, -height))

    # -- NEW FEATURE: PROJECTILE LOGIC --
    for i, p in sorted(enumerate(projectiles), reverse=True):
        p.update()
        p.render(display, (0, -int(height)))
        # Remove if off-screen
        if not p.rect.colliderect(display.get_rect()):
            projectiles.pop(i)
            continue
        # Check collision with falling tiles
        hit_tile = False
        for j, tile_drop in sorted(enumerate(tile_drops), reverse=True):
            r = pygame.Rect(tile_drop[0], tile_drop[1], TILE_SIZE, TILE_SIZE)
            if p.rect.colliderect(r):
                sounds['block_land'].play() # SFX for tile hit
                # Particles
                for k in range(15):
                    angle = random.random() * math.pi * 2
                    speed = random.random() * 2
                    sparks.append([[tile_drop[0] + 8, tile_drop[1] + 8], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 2, 0.08, (251, 245, 239), True, 0.1])
                tile_drops.pop(j)
                projectiles.pop(i)
                hit_tile = True
                coins += 1 # Small reward
                combo_multiplier += 0.05
                combo_timer = COMBO_DURATION
                break # Projectile is used up
        if hit_tile:
            continue


    if not dead:
        collisions = player.update(tile_drop_rects + edge_rects + tile_rects)

        if collisions['bottom']:
            player_feet_pos = player.rect.midbottom
            tile_pos_below = (player_feet_pos[0] // TILE_SIZE, player_feet_pos[1] // TILE_SIZE)

            if tile_pos_below in tiles:
                tile_type_below = tiles[tile_pos_below]['type']

                if tile_type_below == 'fragile':
                    if 'timer' not in tiles[tile_pos_below]['data']:
                        sounds['block_land'].play()
                        tiles[tile_pos_below]['data']['timer'] = 90
                elif tile_type_below == 'bounce':
                    player.velocity[1] = -9
                    player.jumps = player.jumps_max
                    sounds['super_jump'].play()
                    screen_shake = 10
                    combo_multiplier += 0.5
                    combo_timer = COMBO_DURATION
                    for i in range(40):
                        angle = random.random() * math.pi - math.pi
                        speed = random.random() * 2
                        sparks.append([
                            [player.rect.centerx, player.rect.bottom],
                            [math.cos(angle) * speed, math.sin(angle) * speed],
                            random.random() * 3 + 2, 0.04, (8, 2, 12), True, 0.1
                        ])
                elif tile_type_below == 'spike':
                    handle_death()
                    player.velocity = [0, -4]

    else:
        player.opacity = 80
        player.update([])
        player.rotation -= 16
    player.render(display, (0, -int(height)))

    for i, spark in sorted(enumerate(sparks), reverse=True):
        if len(spark) < 8:
            spark.append(False)

        if not spark[-1]:
            spark[1][1] = min(spark[1][1] + spark[-2], 3)

        spark[0][0] += spark[1][0]
        if spark[5]:
            if ((int(spark[0][0] // TILE_SIZE), int(spark[0][1] // TILE_SIZE)) in tiles) or (spark[0][0] < TILE_SIZE) or (spark[0][0] > DISPLAY_SIZE[0] - TILE_SIZE):
                spark[0][0] -= spark[1][0]
                spark[1][0] *= -0.7
        spark[0][1] += spark[1][1]
        if spark[5]:
            if (int(spark[0][0] // TILE_SIZE), int(spark[0][1] // TILE_SIZE)) in tiles:
                spark[0][1] -= spark[1][1]
                spark[1][1] *= -0.7
                if abs(spark[1][1]) < 0.1:
                    spark[1][1] = 0
                    spark[-1] = True
        spark[2] -= spark[3]
        if spark[2] <= 1:
            sparks.pop(i)
        else:
            display.blit(glow_img(int(spark[2] * 1.5 + 2), (int(spark[4][0] / 2), int(spark[4][1] / 2), int(spark[4][2] / 2))), (spark[0][0] - spark[2] * 2, spark[0][1] + height - spark[2] * 2), special_flags=BLEND_RGBA_ADD)
            display.blit(glow_img(int(spark[2]), spark[4]), (spark[0][0] - spark[2], spark[0][1] + height - spark[2]), special_flags=BLEND_RGBA_ADD)
            display.set_at((int(spark[0][0]), int(spark[0][1] + height)), (255, 255, 255))

    display.blit(border_img_light, (0, -math.sin(master_clock / 30) * 4 - 7))
    display.blit(border_img, (0, -math.sin(master_clock / 40) * 7 - 14))
    display.blit(pygame.transform.flip(border_img_light, False, True), (0, DISPLAY_SIZE[1] + math.sin(master_clock / 40) * 3 + 9 - border_img.get_height()))
    display.blit(pygame.transform.flip(border_img, False, True), (0, DISPLAY_SIZE[1] + math.sin(master_clock / 30) * 3 + 16 - border_img.get_height()))

    if not dead:
        hud_panel = pygame.Surface((DISPLAY_SIZE[0], 24))
        hud_panel.set_alpha(100)
        hud_panel.fill((0, 0, 1))
        display.blit(hud_panel, (0, 0))

        display.blit(coin_icon, (4, 4))
        black_font.render(str(coins), display, (17, 6))
        white_font.render(str(coins), display, (16, 5))

        if combo_multiplier > 1.0:
            combo_text = f"x{combo_multiplier:.1f}"
            text_width = white_font.width(combo_text)
            black_font.render(combo_text, display, (DISPLAY_SIZE[0] // 2 - text_width // 2 + 1, 6))
            white_font.render(combo_text, display, (DISPLAY_SIZE[0] // 2 - text_width // 2, 5))

            bar_width = (combo_timer / COMBO_DURATION) * 40
            bar_x = DISPLAY_SIZE[0] // 2 - 20
            pygame.draw.rect(display, (0, 0, 1), [bar_x + 1, 15, 40, 3])
            pygame.draw.rect(display, (251, 245, 239), [bar_x, 14, bar_width, 3])

        display.blit(item_slot_img, (DISPLAY_SIZE[0] - 20, 4))
        if current_item:
            if (master_clock % 50 < 12) or (abs(master_clock % 50 - 20) < 3):
                display.blit(item_slot_flash_img, (DISPLAY_SIZE[0] - 20, 4))
            display.blit(item_icons[current_item], (DISPLAY_SIZE[0] - 15, 9))
            if not item_used:
                if (master_clock % 100 < 80) or (abs(master_clock % 100 - 90) < 3):
                    black_font.render('E/X', display, (DISPLAY_SIZE[0] - white_font.width('E/X') - 23, 10))
                    white_font.render('E/X', display, (DISPLAY_SIZE[0] - white_font.width('E/X') - 24, 9))
    else:
        # -- MODIFIED FEATURE: HIGH SCORE UI --
        y_offset = 20 # Adjusted for new aspect ratio
        black_font.render('game over', display, (DISPLAY_SIZE[0] // 2 - white_font.width('game over') // 2 + 1, y_offset + 1))
        white_font.render('game over', display, (DISPLAY_SIZE[0] // 2 - white_font.width('game over') // 2, y_offset))
        y_offset += 15

        # Display High Score
        hs_text = f"High Score: {save_data['high_score']}"
        hs_font = white_font
        if new_high_score:
            if master_clock % 40 < 20:
                hs_font = Font('data/fonts/small_font.png', (255, 230, 90))
        hs_font.render(hs_text, display, (DISPLAY_SIZE[0] // 2 - hs_font.width(hs_text) // 2, y_offset))
        y_offset += 15

        if end_coin_count != coins:
            if master_clock % 3 == 0:
                sounds['coin_end'].play()
                end_coin_count = min(end_coin_count + 1, coins)
        else:
            if not run_coins_banked:
                save_data['banked_coins'] += end_coin_count
                write_save(save_data)
                run_coins_banked = True

        bank_text = f"Bank: {save_data['banked_coins']}"
        black_font.render(bank_text, display, (DISPLAY_SIZE[0] // 2 - white_font.width(bank_text) // 2 + 1, y_offset + 1))
        white_font.render(bank_text, display, (DISPLAY_SIZE[0] // 2 - white_font.width(bank_text) // 2, y_offset))
        y_offset += 10

        if run_coins_banked:
            y_offset += 5
            for i, key in enumerate(upgrade_keys):
                upgrade = UPGRADES[key]
                level = save_data['upgrades'][key]
                cost = int(upgrade['base_cost'] * (1.5 ** level))

                color = white_font.color
                if i == upgrade_selection:
                    color = (255, 230, 90)

                temp_font = Font('data/fonts/small_font.png', color)
                temp_black_font = Font('data/fonts/small_font.png', (1,1,1))

                level_text = f"[{level}/{upgrade['max_level']}]" if level < upgrade['max_level'] else "[MAX]"
                name_text = f"{upgrade['name']} {level_text}"
                temp_black_font.render(name_text, display, (11, y_offset + 1))
                temp_font.render(name_text, display, (10, y_offset))

                if level < upgrade['max_level']:
                    cost_text = str(cost)
                    display.blit(coin_icon, (DISPLAY_SIZE[0] - 14 - white_font.width(cost_text), y_offset - 2))
                    temp_black_font.render(cost_text, display, (DISPLAY_SIZE[0] - white_font.width(cost_text) - 9, y_offset + 1))
                    temp_font.render(cost_text, display, (DISPLAY_SIZE[0] - white_font.width(cost_text) - 10, y_offset))

                y_offset += 15

            y_offset += 5
            help_text = "Up/Down:Select - Enter:Buy"
            black_font.render(help_text, display, (DISPLAY_SIZE[0] // 2 - white_font.width(help_text) // 2 + 1, y_offset + 1))
            white_font.render(help_text, display, (DISPLAY_SIZE[0] // 2 - white_font.width(help_text) // 2, y_offset))
            y_offset += 15
            black_font.render('press R to restart', display, (DISPLAY_SIZE[0] // 2 - white_font.width('press R to restart') // 2 + 1, y_offset + 1))
            white_font.render('press R to restart', display, (DISPLAY_SIZE[0] // 2 - white_font.width('press R to restart') // 2, y_offset))


    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        if event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                pygame.quit()
                sys.exit()

            if not dead:
                if event.key in [K_RIGHT, K_d]:
                    player.right = True
                if event.key in [K_LEFT, K_a]:
                    player.left = True
                if event.key in [K_UP, K_w, K_SPACE]:
                    player.jump_buffer_timer = 8
                    if player.air_time < 2 or player.coyote_timer > 0 or player.jumps > 0:
                        sounds['jump'].play()
                        player.attempt_jump()

                # === MODIFIED FEATURE: 4-WAY SHOOTING ===
                if event.key in [K_z, K_k]:
                    if len(projectiles) < 4: # Limit projectiles on screen
                        sounds['jump'].play() # Reusing jump sfx for shooting

                        # Check for held direction keys to determine velocity
                        pressed_keys = pygame.key.get_pressed()
                        proj_speed = 4
                        vel = [0, 0]

                        if pressed_keys[K_UP] or pressed_keys[K_w]:
                            vel = [0, -proj_speed]
                            proj_pos = [player.rect.centerx, player.rect.top]
                        elif pressed_keys[K_DOWN] or pressed_keys[K_s]:
                            vel = [0, proj_speed]
                            proj_pos = [player.rect.centerx, player.rect.bottom]
                        elif player.flip[0]: # Facing right
                            vel = [proj_speed, 0]
                            proj_pos = [player.rect.right, player.rect.centery]
                        else: # Facing left
                            vel = [-proj_speed, 0]
                            proj_pos = [player.rect.left, player.rect.centery]

                        projectiles.append(Projectile(animation_manager, proj_pos, (6, 2), 'projectile', velocity=vel))

                if event.key in [K_e, K_x]:
                    if current_item:
                        item_used = True
                    if current_item == 'warp':
                        sounds['warp'].play()
                        screen_shake = 15
                        max_point = min(enumerate(stack_heights), key=lambda x: x[1])
                        player.pos[0] = (max_point[0] + 1) * TILE_SIZE + 4
                        player.pos[1] = (max_point[1] - 1) * TILE_SIZE
                        for i in range(60):
                            angle = random.random() * math.pi * 2
                            speed = random.random() * 1.75
                            sparks.append([player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.02, (12, 8, 2), True, 0.1 * random.choice([0,1])])
                    elif current_item == 'jump':
                        sounds['super_jump'].play()
                        screen_shake = 12
                        player.jumps += 1
                        player.attempt_jump()
                        player.velocity[1] = -8
                    elif current_item == 'cube':
                        sounds['block_land'].play()
                        place_pos = (int(player.center[0] // TILE_SIZE), int(player.pos[1] // TILE_SIZE) + 1)
                        stack_heights[place_pos[0] - 1] = place_pos[1]
                        current_base_row = max(tiles, key=lambda x: x[1])[1] - 1 if tiles else WINDOW_TILE_SIZE[1] - 2
                        for i in range(place_pos[1], current_base_row + 2):
                            tiles[(place_pos[0], i)] = {'type': 'placed_tile', 'data': {}}
                    elif current_item == 'bomb':
                        if 'explosion' in sounds:
                            sounds['explosion'].play()
                        screen_shake = 25
                        tiles_to_bomb = []
                        bomb_radius = 4 * TILE_SIZE
                        for tile_pos in tiles:
                            tile_center = (tile_pos[0] * TILE_SIZE + TILE_SIZE // 2, tile_pos[1] * TILE_SIZE + TILE_SIZE // 2)
                            dist = math.sqrt((player.center[0] - tile_center[0])**2 + (player.center[1] - tile_center[1])**2)
                            if dist < bomb_radius:
                                tiles_to_bomb.append(list(tile_pos))
                        for tile_pos in tiles_to_bomb:
                            if tuple(tile_pos) in tiles:
                                for i in range(15):
                                    angle = random.random() * math.pi * 2
                                    speed = random.random() * 2
                                    sparks.append([
                                        [tile_pos[0] * TILE_SIZE + 8, tile_pos[1] * TILE_SIZE + 8],
                                        [math.cos(angle) * speed, math.sin(angle) * speed],
                                        random.random() * 4 + 2, 0.08, (12, 2, 2), True, 0.1
                                    ])
                                del tiles[tuple(tile_pos)]
                        recalculate_stack_heights()
                    # -- NEW FEATURE: FREEZE TIME --
                    elif current_item == 'freeze':
                        sounds['warp'].play() # Reusing warp sfx
                        screen_shake = 10
                        freeze_timer = 360 # 6 seconds
                        # Particle effect for activation
                        for i in range(40):
                            angle = random.random() * math.pi * 2
                            speed = random.random() * 2
                            sparks.append([player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 4 + 2, 0.08, (150, 200, 255), True, 0.1])

                    if current_item:
                        current_item = None
            else:
                if run_coins_banked:
                    if event.key == K_DOWN:
                        upgrade_selection = (upgrade_selection + 1) % len(upgrade_keys)
                    if event.key == K_UP:
                        upgrade_selection = (upgrade_selection - 1 + len(upgrade_keys)) % len(upgrade_keys)
                    if event.key == K_RETURN:
                        key = upgrade_keys[upgrade_selection]
                        upgrade = UPGRADES[key]
                        level = save_data['upgrades'][key]
                        cost = int(upgrade['base_cost'] * (1.5 ** level))
                        if level < upgrade['max_level'] and save_data['banked_coins'] >= cost:
                            save_data['banked_coins'] -= cost
                            save_data['upgrades'][key] += 1
                            write_save(save_data)
                            if 'upgrade' in sounds:
                                sounds['upgrade'].play()
                            else:
                                sounds['collect_item'].play()

            if event.key == K_r:
                if dead:
                    player = Player(animation_manager, (DISPLAY_SIZE[0] // 2 - 5, -20), (8, 16), 'player')
                    player.jumps_max += save_data['upgrades']['jumps']
                    player.speed += save_data['upgrades']['speed'] * 0.08
                    player.jumps = player.jumps_max

                    dead = False
                    tiles = {}
                    tile_drops = []
                    sparks = []
                    projectiles = [] # NEW
                    freeze_timer = 0 # NEW
                    game_timer = 0
                    height = 0
                    target_height = 0
                    coins = 0
                    end_coin_count = 0
                    current_item = None
                    master_clock = 0
                    combo_multiplier = 1.0
                    combo_timer = 0
                    run_coins_banked = False
                    screen_shake = 0
                    # -- NEW FEATURE: HIGH SCORE --
                    new_high_score = False
                    current_palette_index = 0

                    for i in range(WINDOW_TILE_SIZE[0] - 2):
                        tiles[(i + 1, WINDOW_TILE_SIZE[1] - 1)] = {'type': 'tile', 'data': {}}
                    tiles[(1, WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
                    tiles[(WINDOW_TILE_SIZE[0] - 2, WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
                    stack_heights = [WINDOW_TILE_SIZE[1] - 1 for i in range(WINDOW_TILE_SIZE[0] - 2)]
                    stack_heights[0] -= 1
                    stack_heights[-1] -= 1
                    items = []

        if event.type == KEYUP:
            if event.key in [K_RIGHT, K_d]:
                player.right = False
            if event.key in [K_LEFT, K_a]:
                player.left = False

    render_offset = [0, 0]
    if screen_shake > 0:
        render_offset[0] = random.randint(0, int(screen_shake)) - int(screen_shake) // 2
        render_offset[1] = random.randint(0, int(screen_shake)) - int(screen_shake) // 2

    screen.blit(pygame.transform.scale(display, screen.get_size()), render_offset)
    pygame.display.update()
    clock.tick(60)