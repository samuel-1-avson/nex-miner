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
pygame.display.set_caption('Cavyn')
DISPLAY_SIZE = (384, 216)
screen = pygame.display.set_mode((DISPLAY_SIZE[0] * 3, DISPLAY_SIZE[1] * 3), 0, 32)
display = pygame.Surface(DISPLAY_SIZE)
pygame.mouse.set_visible(False)

WINDOW_TILE_SIZE = (int(display.get_width() // 16), int(display.get_height() // 16))

def load_img(path):
    img = pygame.image.load(path).convert()
    img.set_colorkey((0, 0, 0))
    return img

# --- ASSET LOADING ---
tile_img = load_img('data/images/tile.png')
chest_img = load_img('data/images/chest.png')
ghost_chest_img = load_img('data/images/ghost_chest.png')
opened_chest_img = load_img('data/images/opened_chest.png')
placed_tile_img = load_img('data/images/placed_tile.png')
edge_tile_img = load_img('data/images/edge_tile.png')
fragile_tile_img = load_img('data/images/fragile_tile.png')
bounce_tile_img = load_img('data/images/bounce_tile.png')
spike_tile_img = load_img('data/images/spike_tile.png')
coin_icon = load_img('data/images/coin_icon.png')
item_slot_img = load_img('data/images/item_slot.png')
item_slot_flash_img = load_img('data/images/item_slot_flash.png')
vignette_img = load_img('data/images/vignette.png')
panel_img = load_img('data/images/panel.png')
shield_icon_img = load_img('data/images/shield_icon.png')
shield_effect_img = load_img('data/images/shield_effect.png')

white_font = Font('data/fonts/small_font.png', (251, 245, 239))
black_font = Font('data/fonts/small_font.png', (0, 0, 1))

sounds = {sound.split('/')[-1].split('.')[0] : pygame.mixer.Sound('data/sfx/' + sound) for sound in os.listdir('data/sfx')}
sounds['block_land'].set_volume(0.5)
sounds['coin'].set_volume(0.6)
sounds['chest_open'].set_volume(0.8)
sounds['coin_end'] = pygame.mixer.Sound('data/sfx/coin.wav')
sounds['coin_end'].set_volume(0.35)
sounds['shield_break'] = pygame.mixer.Sound('data/sfx/chest_destroy.wav')
sounds['shield_break'].set_volume(0.7)

item_icons = {
    'cube': load_img('data/images/cube_icon.png'),
    'warp': load_img('data/images/warp_icon.png'),
    'jump': load_img('data/images/jump_icon.png'),
    'shield': shield_icon_img,
}

animation_manager = AnimationManager()

# --- HELPER FUNCTIONS ---
def normalize(val, amt):
    if val > amt:
        val -= amt
    elif val < -amt:
        val += amt
    else:
        val = 0
    return val

def render_panel(surf, pos, size, panel_image):
    corner_size = 4
    surf.blit(panel_image, pos, (0, 0, corner_size, corner_size))
    surf.blit(panel_image, (pos[0] + size[0] - corner_size, pos[1]), (corner_size * 2, 0, corner_size, corner_size))
    surf.blit(panel_image, (pos[0], pos[1] + size[1] - corner_size), (0, corner_size * 2, corner_size, corner_size))
    surf.blit(panel_image, (pos[0] + size[0] - corner_size, pos[1] + size[1] - corner_size), (corner_size * 2, corner_size * 2, corner_size, corner_size))
    top_edge = pygame.transform.scale(panel_image.subsurface(corner_size, 0, corner_size, corner_size), (size[0] - corner_size * 2, corner_size))
    surf.blit(top_edge, (pos[0] + corner_size, pos[1]))
    bottom_edge = pygame.transform.scale(panel_image.subsurface(corner_size, corner_size * 2, corner_size, corner_size), (size[0] - corner_size * 2, corner_size))
    surf.blit(bottom_edge, (pos[0] + corner_size, pos[1] + size[1] - corner_size))
    left_edge = pygame.transform.scale(panel_image.subsurface(0, corner_size, corner_size, corner_size), (corner_size, size[1] - corner_size * 2))
    surf.blit(left_edge, (pos[0], pos[1] + corner_size))
    right_edge = pygame.transform.scale(panel_image.subsurface(corner_size * 2, corner_size, corner_size, corner_size), (corner_size, size[1] - corner_size * 2))
    surf.blit(right_edge, (pos[0] + size[0] - corner_size, pos[1] + corner_size))
    center = pygame.transform.scale(panel_image.subsurface(corner_size, corner_size, corner_size, corner_size), (size[0] - corner_size * 2, size[1] - corner_size * 2))
    surf.blit(center, (pos[0] + corner_size, pos[1] + corner_size))

# --- CLASSES & GLOBAL DEFS ---
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

    def attempt_jump(self):
        if self.jumps:
            if self.jumps == self.jumps_max:
                self.velocity[1] = -5
            else:
                self.velocity[1] = -4
                for i in range(24):
                    angle = random.random() * math.pi * 2
                    speed = random.random() * 1.5
                    sparks.append([list(self.center), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 2 + 2, 0.08, (12, 10, 14), True, 0.05])
            self.jumps -= 1
            self.jumping = True
            self.jump_rot = 0

    def update(self, tiles):
        super().update(1 / 60)
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

        collisions = self.move(motion, tiles)
        if collisions['bottom']:
            if self.air_time > 5:
                for i in range(4):
                    sparks.append([self.rect.midbottom, [random.random() * 1.4 - 0.7, -random.random() * 0.8], random.random() + 1, 0.1, (10, 8, 5), True, 0.05])
            self.jumps = self.jumps_max
            self.jumping = False
            self.rotation = 0
            self.velocity[1] = 0
            self.air_time = 0
            
        return collisions

def lookup_nearby(tiles, pos, render_offset):
    rects = []
    lookup_pos_x = (pos[0] + render_offset[0]) // TILE_SIZE
    lookup_pos_y = (pos[1] + render_offset[1]) // TILE_SIZE
    for offset in [(0, 0), (-1, -1), (-1, 0), (-1, 1), (0, 1), (0, -1), (1, -1), (1, 0), (1, 1)]:
        lookup_pos = (lookup_pos_x + offset[0], lookup_pos_y + offset[1])
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

player = None
dead = False
tiles = {}
tile_drops = []
bg_particles = []
sparks = []
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
stack_heights = []
items = []
camera_pos = [0, 0]
combo_pop = 0
shield_active = False
invincibility_timer = 0

game_state = 'playing'
banked_coins = 0
upgrades = {}
game_over_selection = 0
upgrade_selection = 0

UPGRADE_DEFINITIONS = {
    'jumps': {
        'name': 'Extra Jump',
        'description': 'Increases your maximum number of jumps.',
        'base_cost': 100,
        'cost_increase': 150
    },
    'speed': {
        'name': 'Faster Movement',
        'description': 'Increases your horizontal speed.',
        'base_cost': 75,
        'cost_increase': 75
    },
    'item_luck': {
        'name': 'Item Luck',
        'description': 'Increases the chance of finding items in chests.',
        'base_cost': 200,
        'cost_increase': 200
    }
}

def load_progress():
    global banked_coins, upgrades
    try:
        with open('save.json', 'r') as f:
            data = json.load(f)
            banked_coins = data['banked_coins']
            upgrades = data['upgrades']
    except FileNotFoundError:
        banked_coins = 0
        upgrades = {"jumps": 0, "speed": 0, "item_luck": 0}
        save_progress()

def save_progress():
    global banked_coins, upgrades
    data = {
        'banked_coins': banked_coins,
        'upgrades': upgrades
    }
    with open('save.json', 'w') as f:
        json.dump(data, f)

def reset_game():
    global player, dead, tiles, tile_drops, sparks, game_timer, height, target_height, coins, end_coin_count, current_item, master_clock, last_place, item_used, combo_multiplier, combo_timer, stack_heights, items, camera_pos, shield_active, invincibility_timer

    player = Player(animation_manager, (DISPLAY_SIZE[0] // 2, -20), (8, 16), 'player')
    
    player.jumps_max = 2 + upgrades.get('jumps', 0)
    player.speed = 1.4 + (upgrades.get('speed', 0) * 0.1)

    dead = False
    tiles = {}
    tile_drops = []
    sparks = []
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
    items = []
    camera_pos = [player.pos[0], player.pos[1]]
    shield_active = False
    invincibility_timer = 0

    for i in range(WINDOW_TILE_SIZE[0] - 2):
        tiles[(i + 1, WINDOW_TILE_SIZE[1] - 1)] = {'type': 'tile', 'data': {}}
    tiles[(1, WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
    tiles[(WINDOW_TILE_SIZE[0] - 2, WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}

    stack_heights = [WINDOW_TILE_SIZE[1] - 1 for i in range(WINDOW_TILE_SIZE[0] - 2)]
    stack_heights[0] -= 1
    stack_heights[-1] -= 1

def game_loop():
    global master_clock, game_timer, dead, last_place, height, target_height, combo_timer, combo_multiplier, combo_pop, banked_coins, game_state, end_coin_count, coins, player, tiles, tile_drops, bg_particles, sparks, current_item, item_used, stack_heights, items, COMBO_DURATION, camera_pos, shield_active, invincibility_timer

    display.fill((22, 19, 40))

    master_clock += 1

    if invincibility_timer > 0:
        invincibility_timer -= 1

    if combo_pop > 0:
        combo_pop -= 0.1
    
    camera_pos[0] += (player.pos[0] - camera_pos[0] - DISPLAY_SIZE[0] // 2) / 20
    camera_pos[1] = height
    render_offset = [int(camera_pos[0]), int(camera_pos[1])]

    if combo_timer > 0:
        combo_timer -= 1
        if combo_timer == 0:
            combo_multiplier = 1.0

    parallax = random.random()
    for i in range(2):
        bg_particles.append([[random.random() * DISPLAY_SIZE[0], DISPLAY_SIZE[1] - (render_offset[1] % DISPLAY_SIZE[1]) * parallax], parallax, random.randint(1, 8), random.random() * 1 + 1, random.choice([(0, 0, 0), (22, 19, 40)])])

    for i, p in sorted(enumerate(bg_particles), reverse=True):
        size = p[2]
        p[2] -= 0.01
        p[0][1] -= p[3]
        if size < 0.5:
            display.set_at((int(p[0][0]), int(p[0][1] + render_offset[1] * p[1])), (0, 0, 0))
        else:
            pygame.draw.circle(display, p[-1], (p[0][0], p[0][1]), int(size))
        if size < 0:
            bg_particles.pop(i)

    if master_clock > 180:
        game_timer += 1
        if game_timer > 10 + 25 * (20000 - min(20000, master_clock)) / 20000:
            game_timer = 0
            if stack_heights:
                minimum = min(stack_heights)
                options = []
                for i, stack in enumerate(stack_heights):
                    if i != last_place:
                        offset = stack - minimum
                        for j in range(int(offset ** (2.2 - min(20000, master_clock) / 10000)) + 1):
                            options.append(i)
                if options:
                    roll = random.randint(1, 25)
                    tile_type = 'tile'
                    if roll == 1: tile_type = 'chest'
                    elif roll < 4: tile_type = 'fragile'
                    elif roll < 6: tile_type = 'bounce'
                    elif roll == 7: tile_type = 'spike'
                    
                    c = random.choice(options)
                    last_place = c
                    tile_drops.append([(c + 1) * TILE_SIZE, -render_offset[1] - TILE_SIZE, tile_type])

    tile_drop_rects = []
    for i, tile in sorted(enumerate(tile_drops), reverse=True):
        tile[1] += 1.4
        r = pygame.Rect(tile[0], tile[1], TILE_SIZE, TILE_SIZE)
        tile_drop_rects.append(r)

        graze_rect = player.rect.copy()
        graze_rect.inflate_ip(12, 12)
        if graze_rect.colliderect(r) and not player.rect.colliderect(r):
            combo_multiplier += 0.2; combo_timer = COMBO_DURATION; combo_pop = 1

        if r.colliderect(player.rect) and not dead and invincibility_timer == 0:
            if shield_active:
                shield_active = False; invincibility_timer = 60; sounds['shield_break'].play()
                for j in range(60):
                    angle = random.random() * math.pi * 2; speed = random.random() * 2.5
                    sparks.append([list(player.center), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 2, 0.05, (20, 18, 25), True, 0.1])
            else:
                sounds['death'].play(); player.velocity = [1.3, -6]
                dead = True; banked_coins += coins; save_progress(); game_state = 'game_over'
                for k in range(380):
                    angle = random.random() * math.pi; speed = random.random() * 1.5
                    sparks.append([list(player.center), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.02, (12, 2, 2), True, 0.1])

        check_pos = (int(r.centerx // TILE_SIZE), int(math.floor(r.bottom / TILE_SIZE)))
        if check_pos in tiles:
            tile_drops.pop(i)
            place_pos = (check_pos[0], check_pos[1] - 1)
            if 0 <= place_pos[0] - 1 < len(stack_heights):
                stack_heights[place_pos[0] - 1] = place_pos[1]
                tiles[place_pos] = {'type': tile[2], 'data': {}}
                sounds['block_land'].play()
                if tiles[check_pos]['type'] == 'chest':
                    tiles[check_pos]['type'] = 'tile'
                    sounds['chest_destroy'].play()
                    for j in range(100):
                        angle = random.random() * math.pi * 2; speed = random.random() * 2.5
                        sparks.append([[place_pos[0] * TILE_SIZE + 8, place_pos[1] * TILE_SIZE + 8], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.09, (12, 8, 2), False, 0.1])
            continue
        
        display.blit(tile_img, (tile[0] - render_offset[0], tile[1] - render_offset[1]))
        if tile[2] == 'chest':
            display.blit(ghost_chest_img, (tile[0] - render_offset[0], tile[1] - TILE_SIZE - render_offset[1]))

    tiles_to_remove = []
    for tile_pos, tile_data in tiles.items():
        if tile_data['type'] == 'fragile' and 'timer' in tile_data['data']:
            tile_data['data']['timer'] -= 1
            if random.randint(1, 10) == 1:
                sparks.append([[tile_pos[0] * TILE_SIZE + random.random() * 16, tile_pos[1] * TILE_SIZE + 14], [random.random() * 0.5 - 0.25, random.random() * 0.5], random.random() * 2 + 1, 0.08, (6, 4, 1), True, 0.05])
            if tile_data['data']['timer'] <= 0:
                tiles_to_remove.append(tile_pos)
                for i in range(20):
                    angle = random.random() * math.pi * 2; speed = random.random() * 1.5
                    sparks.append([[tile_pos[0] * TILE_SIZE + 8, tile_pos[1] * TILE_SIZE + 8], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 4 + 2, 0.05, (6, 4, 1), True, 0.1])
    
    for tile_pos in tiles_to_remove:
        if tile_pos in tiles:
            del tiles[tile_pos]

    tile_rects = []
    for tile_pos, tile_data in tiles.items():
        tile_type = tile_data['type']
        tile_rects.append(pygame.Rect(tile_pos[0] * TILE_SIZE, tile_pos[1] * TILE_SIZE, TILE_SIZE, TILE_SIZE))
        
        display.blit(tile_img, (tile_pos[0] * TILE_SIZE - render_offset[0], tile_pos[1] * TILE_SIZE - render_offset[1]))
        if tile_type == 'placed_tile': display.blit(placed_tile_img, (tile_pos[0] * TILE_SIZE - render_offset[0], tile_pos[1] * TILE_SIZE - render_offset[1]))
        if tile_type == 'fragile': display.blit(fragile_tile_img, (tile_pos[0] * TILE_SIZE - render_offset[0], tile_pos[1] * TILE_SIZE - render_offset[1]))
        if tile_type == 'bounce': display.blit(bounce_tile_img, (tile_pos[0] * TILE_SIZE - render_offset[0], tile_pos[1] * TILE_SIZE - render_offset[1]))
        if tile_type == 'spike': display.blit(spike_tile_img, (tile_pos[0] * TILE_SIZE - render_offset[0], tile_pos[1] * TILE_SIZE - render_offset[1]))

        if tile_type == 'chest':
            display.blit(chest_img, (tile_pos[0] * TILE_SIZE - render_offset[0], tile_pos[1] * TILE_SIZE - TILE_SIZE - render_offset[1]))
            chest_r = pygame.Rect(tile_pos[0] * TILE_SIZE, tile_pos[1] * TILE_SIZE - TILE_SIZE, TILE_SIZE, TILE_SIZE)
            if player.rect.colliderect(chest_r):
                sounds['chest_open'].play(); combo_multiplier += 1.0; combo_timer = COMBO_DURATION; combo_pop = 1
                tiles[tile_pos]['type'] = 'opened_chest' 
                player.jumps += 1; player.attempt_jump(); player.velocity[1] = -3.5
                if random.randint(1, 10) < 3 + upgrades.get('item_luck', 0):
                    items.append(Item(animation_manager, (chest_r.x + 5, chest_r.y + 5), (6, 6), random.choice(['warp', 'cube', 'jump', 'shield']), velocity=[random.random() * 5 - 2.5, random.random() * 2 - 5]))
                else:
                    for i in range(random.randint(2, 6)): items.append(Item(animation_manager, (chest_r.x + 5, chest_r.y + 5), (6, 6), 'coin', velocity=[random.random() * 5 - 2.5, random.random() * 2 - 7]))
        elif tile_type == 'opened_chest':
            display.blit(opened_chest_img, (tile_pos[0] * TILE_SIZE - render_offset[0], tile_pos[1] * TILE_SIZE - TILE_SIZE - render_offset[1]))

    if tiles:
        base_row = max(tiles, key=lambda x: x[1])[1] - 1
        filled = True
        for i in range(WINDOW_TILE_SIZE[0] - 2):
            if (i + 1, base_row) not in tiles:
                filled = False
        if filled:
            target_height = math.floor(render_offset[1] / TILE_SIZE) * TILE_SIZE + TILE_SIZE
    
    if height != target_height:
        height += (target_height - height) / 10
        if abs(target_height - height) < 0.2:
            height = target_height
            base_row = int(height / TILE_SIZE) - (WINDOW_TILE_SIZE[1] - 1)
            for i in range(WINDOW_TILE_SIZE[0] - 2):
                if (i + 1, base_row) in tiles:
                    del tiles[(i + 1, base_row)]

    for i in range(-1, WINDOW_TILE_SIZE[0] + 1):
        display.blit(edge_tile_img, (i * TILE_SIZE - render_offset[0] % TILE_SIZE, -render_offset[1] % TILE_SIZE - TILE_SIZE))
        display.blit(edge_tile_img, (i * TILE_SIZE - render_offset[0] % TILE_SIZE, -render_offset[1] % TILE_SIZE + DISPLAY_SIZE[1]))

    edge_rects = [pygame.Rect(0, player.pos[1] - 300, TILE_SIZE, 600), pygame.Rect(DISPLAY_SIZE[0] - TILE_SIZE, player.pos[1] - 300, TILE_SIZE, 600)]

    for i, item in sorted(enumerate(items), reverse=True):
        item.update(edge_rects + lookup_nearby(tiles, item.center, [0, 0]))
        if item.time > 30 and item.rect.colliderect(player.rect):
            if item.type == 'coin':
                sounds['coin'].play(); coins += int(1 * combo_multiplier); combo_multiplier += 0.1; combo_timer = COMBO_DURATION; combo_pop = 1
            else:
                sounds['collect_item'].play(); current_item = item.type
            items.pop(i)
        item.render(display, render_offset)

    if not dead:
        collisions = player.update(tile_drop_rects + edge_rects + tile_rects)
        if collisions['bottom']:
            player_feet_pos = player.rect.midbottom
            tile_pos_below = (player_feet_pos[0] // TILE_SIZE, player_feet_pos[1] // TILE_SIZE)
            if tile_pos_below in tiles:
                tile_type_below = tiles[tile_pos_below]['type']
                if tile_type_below == 'fragile' and 'timer' not in tiles[tile_pos_below]['data']:
                    sounds['block_land'].play(); tiles[tile_pos_below]['data']['timer'] = 90
                elif tile_type_below == 'bounce':
                    player.velocity[1] = -9; player.jumps = player.jumps_max; sounds['super_jump'].play(); combo_multiplier += 0.5; combo_timer = COMBO_DURATION; combo_pop = 1
                elif tile_type_below == 'spike' and invincibility_timer == 0:
                    if shield_active:
                        shield_active = False; invincibility_timer = 60; sounds['shield_break'].play()
                        if tile_pos_below in tiles: tiles_to_remove.append(tile_pos_below)
                        for j in range(60):
                            angle = random.random() * math.pi * 2; speed = random.random() * 2.5
                            sparks.append([list(player.center), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 2, 0.05, (20, 18, 25), True, 0.1])
                    else:
                        sounds['death'].play(); player.velocity = [0, -4]; dead = True; banked_coins += coins; save_progress(); game_state = 'game_over'
    else:
        player.opacity = 80; player.update([]); player.rotation -= 16
    
    player_render_pos = (player.pos[0] - render_offset[0], player.pos[1] - render_offset[1])
    if shield_active:
        shield_img_copy = shield_effect_img.copy()
        pulse = math.sin(master_clock / 15) * 2
        shield_img_copy = pygame.transform.scale(shield_img_copy, (int(16 + pulse), int(16 + pulse)))
        shield_img_copy.set_alpha(150 + math.sin(master_clock / 15) * 50)
        display.blit(shield_img_copy, (player_render_pos[0] - shield_img_copy.get_width() // 2 + player.size[0] // 2, player_render_pos[1] - shield_img_copy.get_height() // 2 + player.size[1] // 2))

    if invincibility_timer > 0:
        if invincibility_timer % 10 < 5:
            player.render(display, render_offset)
    else:
        player.render(display, render_offset)

    for i, spark in sorted(enumerate(sparks), reverse=True):
        spark[0] = list(spark[0])
        spark[1] = list(spark[1])
        if len(spark) > 5:
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
            if spark[2] <= 1:
                sparks.pop(i)
            else:
                glow_center = (int(spark[0][0] - render_offset[0]), int(spark[0][1] - render_offset[1]))
                display.blit(glow_img(int(spark[2]), spark[4]), (glow_center[0] - int(spark[2]), glow_center[1] - int(spark[2])), special_flags=BLEND_RGBA_ADD)
        else:
            spark[0][0] += spark[1][0]; spark[0][1] += spark[1][1]; spark[2] -= spark[3]
            if spark[2] <= 0: sparks.pop(i)
            else: pygame.draw.circle(display, spark[4], [int(spark[0][0] - render_offset[0]), int(spark[0][1] - render_offset[1])], int(spark[2]))

    if not dead:
        panel_width = 40 + white_font.width(str(coins))
        render_panel(display, (6, 6), (panel_width, 18), panel_img)
        display.blit(coin_icon, (11, 10))
        white_font.render(str(coins), display, (24, 11))

        if combo_multiplier > 1.0:
            combo_text = f"x{combo_multiplier:.1f}"
            pop_amt = int(combo_pop * 3)
            temp_font = Font('data/fonts/small_font.png', (255, 255, 150))
            w = temp_font.width(combo_text, scale=1 + pop_amt / 10)
            temp_font.render(combo_text, display, (DISPLAY_SIZE[0] // 2 - w // 2, 12 - pop_amt // 2), scale=1 + pop_amt / 10)

        render_panel(display, (DISPLAY_SIZE[0] - 32, 6), (26, 26), panel_img)
        if current_item:
            if (master_clock % 50 < 12) or (abs(master_clock % 50 - 20) < 3):
                display.blit(item_slot_flash_img, (DISPLAY_SIZE[0] - 30, 8))
            display.blit(item_icons[current_item], (DISPLAY_SIZE[0] - 27, 11))
    
    display.blit(vignette_img, (0, 0), special_flags=BLEND_RGBA_MULT)

def upgrade_loop():
    global banked_coins, upgrades, upgrade_selection
    
    display.fill((22, 19, 40))
    render_panel(display, (DISPLAY_SIZE[0] // 2 - 120, 14), (240, 188), panel_img)

    black_font.render('Upgrades', display, (DISPLAY_SIZE[0] // 2 - white_font.width('Upgrades') // 2 + 1, 25))
    white_font.render('Upgrades', display, (DISPLAY_SIZE[0] // 2 - white_font.width('Upgrades') // 2, 24))
    
    bank_text = f"Coins: {banked_coins}"
    display.blit(coin_icon, (DISPLAY_SIZE[0] // 2 - (white_font.width(bank_text) + 9) // 2, 38))
    white_font.render(bank_text, display, (DISPLAY_SIZE[0] // 2 - (white_font.width(bank_text) - 9) // 2 + 5, 39))
    
    y_offset = 70
    upgrade_keys = list(UPGRADE_DEFINITIONS.keys())
    
    for i, key in enumerate(upgrade_keys):
        upgrade_info = UPGRADE_DEFINITIONS[key]
        current_level = upgrades.get(key, 0)
        cost = upgrade_info['base_cost'] + (current_level * upgrade_info['cost_increase'])
        
        h_color = (251, 245, 239); nh_color = (100, 100, 120); cant_afford_color = (150, 40, 40)
        
        name_font = Font('data/fonts/small_font.png', h_color if i == upgrade_selection else nh_color)
        name_font.render(f"{upgrade_info['name']} [Lvl {current_level}]", display, (85, y_offset))
        
        cost_color = h_color if banked_coins >= cost else cant_afford_color
        cost_font = Font('data/fonts/small_font.png', cost_color)
        cost_text = f"Cost: {cost}"
        cost_font.render(cost_text, display, (DISPLAY_SIZE[0] - 85 - cost_font.width(cost_text), y_offset))
        
        y_offset += 30
    
    selected_key = list(UPGRADE_DEFINITIONS.keys())[upgrade_selection]
    selected_desc = UPGRADE_DEFINITIONS[selected_key]['description']
    white_font.render(selected_desc, display, (DISPLAY_SIZE[0] // 2 - white_font.width(selected_desc) // 2, y_offset + 10))

    white_font.render("Press Enter/Space to buy.", display, (85, DISPLAY_SIZE[1] - 40))
    white_font.render("Press ESC to go back.", display, (85, DISPLAY_SIZE[1] - 30))
    
    display.blit(vignette_img, (0, 0), special_flags=BLEND_RGBA_MULT)

# --- MAIN CONTROL LOOP ---
load_progress()
reset_game()
pygame.mixer.music.load('data/music.wav')
pygame.mixer.music.play(-1)

while True:
    if game_state == 'playing':
        game_loop()
        
        for event in pygame.event.get():
            if event.type == QUIT: pygame.quit(); sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE: pygame.quit(); sys.exit()
                if not dead:
                    if event.key in [K_RIGHT, K_d]: player.right = True
                    if event.key in [K_LEFT, K_a]: player.left = True
                    if event.key in [K_UP, K_w, K_SPACE]:
                        if player.jumps: sounds['jump'].play()
                        player.attempt_jump()
                    if event.key in [K_e, K_x] and current_item:
                        item_used = True
                        if current_item == 'shield':
                            sounds['super_jump'].play()
                            shield_active = True
                        elif current_item == 'warp' and stack_heights:
                            sounds['warp'].play()
                            max_point = min(enumerate(stack_heights), key=lambda x: x[1])
                            player.pos = [(max_point[0] + 1) * TILE_SIZE + 4, (max_point[1] - 1) * TILE_SIZE]
                        elif current_item == 'jump':
                            sounds['super_jump'].play(); player.jumps += 1; player.attempt_jump(); player.velocity[1] = -8
                        elif current_item == 'cube':
                            sounds['block_land'].play()
                            place_pos = (int(player.center[0] // TILE_SIZE), int(player.pos[1] // TILE_SIZE) + 1)
                            if 0 <= place_pos[0] - 1 < len(stack_heights):
                                stack_heights[place_pos[0] - 1] = place_pos[1]
                                if tiles:
                                    current_base_row = max(tiles, key=lambda x: x[1])[1] - 1
                                    for i in range(place_pos[1], current_base_row + 2):
                                        tiles[(place_pos[0], i)] = {'type': 'placed_tile', 'data': {}}
                        current_item = None
            if event.type == KEYUP and not dead:
                if event.key in [K_RIGHT, K_d]: player.right = False
                if event.key in [K_LEFT, K_a]: player.left = False

    elif game_state == 'game_over':
        display.fill((22, 19, 40))
        render_panel(display, (DISPLAY_SIZE[0] // 2 - 80, 40), (160, 120), panel_img)
        
        black_font.render('game over', display, (DISPLAY_SIZE[0] // 2 - white_font.width('game over') // 2 + 1, 51))
        white_font.render('game over', display, (DISPLAY_SIZE[0] // 2 - white_font.width('game over') // 2, 50))
        
        score_text = f"Score: {coins}"
        black_font.render(score_text, display, (DISPLAY_SIZE[0] // 2 - white_font.width(score_text) // 2 + 1, 66))
        white_font.render(score_text, display, (DISPLAY_SIZE[0] // 2 - white_font.width(score_text) // 2, 65))
        
        h_color = (251, 245, 239); nh_color = (100, 100, 120)
        restart_font = Font('data/fonts/small_font.png', h_color if game_over_selection == 0 else nh_color)
        upgrades_font = Font('data/fonts/small_font.png', h_color if game_over_selection == 1 else nh_color)

        restart_font.render("Restart", display, (DISPLAY_SIZE[0] // 2 - restart_font.width("Restart") // 2, 100))
        upgrades_font.render("Upgrades", display, (DISPLAY_SIZE[0] // 2 - upgrades_font.width("Upgrades") // 2, 115))
        display.blit(vignette_img, (0, 0), special_flags=BLEND_RGBA_MULT)

        for event in pygame.event.get():
            if event.type == QUIT: pygame.quit(); sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE: game_state = 'upgrades' 
                if event.key in [K_UP, K_DOWN, K_w, K_s]: game_over_selection = 1 - game_over_selection
                if event.key in [K_RETURN, K_SPACE, K_e, K_x]:
                    if game_over_selection == 0: reset_game(); game_state = 'playing'
                    else: game_state = 'upgrades'

    elif game_state == 'upgrades':
        upgrade_loop()

        for event in pygame.event.get():
            if event.type == QUIT: pygame.quit(); sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE: game_state = 'game_over'
                if event.key in [K_DOWN, K_s]: upgrade_selection = (upgrade_selection + 1) % len(UPGRADE_DEFINITIONS)
                if event.key in [K_UP, K_w]: upgrade_selection = (upgrade_selection - 1) % len(UPGRADE_DEFINITIONS)
                if event.key in [K_RETURN, K_SPACE, K_e, K_x]:
                    key = list(UPGRADE_DEFINITIONS.keys())[upgrade_selection]
                    upgrade_info = UPGRADE_DEFINITIONS[key]
                    current_level = upgrades.get(key, 0)
                    cost = upgrade_info['base_cost'] + (current_level * upgrade_info['cost_increase'])
                    if banked_coins >= cost:
                        sounds['coin'].play(); banked_coins -= cost; upgrades[key] = current_level + 1; save_progress()

    screen.blit(pygame.transform.scale(display, screen.get_size()), (0, 0))
    pygame.display.update()
    clock.tick(60)