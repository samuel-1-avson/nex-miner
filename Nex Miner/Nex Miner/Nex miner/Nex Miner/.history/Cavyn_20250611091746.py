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
# <-- MODIFIED: New widescreen resolution
DISPLAY_SIZE = (384, 216)
# <-- MODIFIED: Increased scale factor for a larger window
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

white_font = Font('data/fonts/small_font.png', (251, 245, 239))
black_font = Font('data/fonts/small_font.png', (0, 0, 1))

sounds = {sound.split('/')[-1].split('.')[0] : pygame.mixer.Sound('data/sfx/' + sound) for sound in os.listdir('data/sfx')}
sounds['block_land'].set_volume(0.5)
sounds['coin'].set_volume(0.6)
sounds['chest_open'].set_volume(0.8)
sounds['coin_end'] = pygame.mixer.Sound('data/sfx/coin.wav')
sounds['coin_end'].set_volume(0.35)

item_icons = {
    'cube': load_img('data/images/cube_icon.png'),
    'warp': load_img('data/images/warp_icon.png'),
    'jump': load_img('data/images/jump_icon.png'),
}

animation_manager = AnimationManager()

# --- HELPER FUNCTIONS ---
def normalize(val, amt):
    if val > amt: val -= amt
    elif val < -amt: val += amt
    else: val = 0
    return val

def render_panel(surf, pos, size, panel_image):
    corner_size = panel_image.get_width() // 3
    center_pos = (pos[0] + corner_size, pos[1] + corner_size)
    center_size = (size[0] - corner_size * 2, size[1] - corner_size * 2)

    if center_size[0] < 0: center_size = (0, center_size[1]); center_pos = (center_pos[0], pos[1] + corner_size)
    if center_size[1] < 0: center_size = (center_size[0], 0); center_pos = (pos[0] + corner_size, center_pos[1])

    # center
    center = pygame.transform.scale(panel_image.subsurface(corner_size, corner_size, corner_size, corner_size), center_size)
    surf.blit(center, center_pos)
    # corners
    surf.blit(panel_image, pos, (0, 0, corner_size, corner_size))
    surf.blit(panel_image, (pos[0] + size[0] - corner_size, pos[1]), (corner_size * 2, 0, corner_size, corner_size))
    surf.blit(panel_image, (pos[0], pos[1] + size[1] - corner_size), (0, corner_size * 2, corner_size, corner_size))
    surf.blit(panel_image, (pos[0] + size[0] - corner_size, pos[1] + size[1] - corner_size), (corner_size * 2, corner_size * 2, corner_size, corner_size))
    # edges
    top_edge = pygame.transform.scale(panel_image.subsurface(corner_size, 0, corner_size, corner_size), (size[0] - corner_size * 2, corner_size))
    surf.blit(top_edge, (pos[0] + corner_size, pos[1]))
    bottom_edge = pygame.transform.scale(panel_image.subsurface(corner_size, corner_size * 2, corner_size, corner_size), (size[0] - corner_size * 2, corner_size))
    surf.blit(bottom_edge, (pos[0] + corner_size, pos[1] + size[1] - corner_size))
    left_edge = pygame.transform.scale(panel_image.subsurface(0, corner_size, corner_size, corner_size), (corner_size, size[1] - corner_size * 2))
    surf.blit(left_edge, (pos[0], pos[1] + corner_size))
    right_edge = pygame.transform.scale(panel_image.subsurface(corner_size * 2, corner_size, corner_size, corner_size), (corner_size, size[1] - corner_size * 2))
    surf.blit(right_edge, (pos[0] + size[0] - corner_size, pos[1] + corner_size))

# --- CLASSES ---
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
            # Differentiate double jump particles
            if self.jumps < self.jumps_max:
                for i in range(24):
                    physics_on = random.choice([False, False, True])
                    direction = 1
                    if i % 2: direction = -1
                    sparks.append([[self.center[0] + random.random() * 14 - 7, self.center[1]], [direction * (random.random() * 0.05 + 0.05) + (random.random() * 4 - 2) * physics_on, random.random() * 0.05 + random.random() * 2 * physics_on], random.random() * 3 + 3, 0.04 - 0.02 * physics_on, (12, 8, 2), physics_on, 0.05 * physics_on])

            if self.jumps == self.jumps_max: self.velocity[1] = -5
            else: self.velocity[1] = -4
            
            self.jumps -= 1
            self.jumping = True
            self.jump_rot = 0

    def update(self, tiles, dt=1/60):
        super().update(dt)
        self.air_time += 1
        if self.jumping:
            self.jump_rot += 16
            if self.jump_rot >= 360:
                self.jump_rot = 0
                self.jumping = False
            self.rotation = self.jump_rot if not self.flip[0] else -self.jump_rot
            self.scale[1] = 0.7
        else:
            self.scale[1] = 1

        self.velocity[1] = min(self.velocity[1] + 0.3, 4)
        motion = self.velocity.copy()
        if not dead:
            if self.right: motion[0] += self.speed
            if self.left: motion[0] -= self.speed
            if motion[0] > 0: self.flip[0] = True
            if motion[0] < 0: self.flip[0] = False

        if self.air_time > 3: self.set_action('jump')
        elif motion[0] != 0: self.set_action('run')
        else: self.set_action('idle')

        collisions = self.move(motion, tiles)
        if collisions['bottom']:
            if self.jumps != self.jumps_max:
                for i in range(10):
                    sparks.append([[self.rect.midbottom[0] + random.random() * 8 - 4, self.rect.bottom], [random.random() * 1 - 0.5, random.random() * 1 - 1.5], random.random() * 2 + 1, 0.1, (6, 4, 1), True, 0.1])
            self.jumps = self.jumps_max
            self.jumping = False
            self.rotation = 0
            self.velocity[1] = 0
            self.air_time = 0
            
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

# --- GLOBAL VARIABLES ---
player, dead, tiles, tile_drops, bg_particles, sparks = None, False, {}, [], [], []
game_timer, height, target_height, coins, end_coin_count, current_item, master_clock, last_place, item_used = 0, 0, 0, 0, 0, None, 0, 0, False
combo_multiplier, combo_timer, combo_text_scale, stack_heights, items = 1.0, 0, 1.0, [], []
COMBO_DURATION = 180
camera_offset = [0, 0]

game_state, banked_coins, upgrades, game_over_selection, upgrade_selection = 'playing', 0, {}, 0, 0

UPGRADE_DEFINITIONS = {
    'jumps': {'name': 'Extra Jump', 'description': 'Increases your maximum number of jumps.', 'base_cost': 100, 'cost_increase': 150},
    'speed': {'name': 'Faster Movement', 'description': 'Increases your horizontal speed.', 'base_cost': 75, 'cost_increase': 75},
    'item_luck': {'name': 'Item Luck', 'description': 'Increases the chance of finding items in chests.', 'base_cost': 200, 'cost_increase': 200}
}

# --- SAVE/LOAD & STATE MANAGEMENT ---
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
    with open('save.json', 'w') as f:
        json.dump({'banked_coins': banked_coins, 'upgrades': upgrades}, f)

def reset_game():
    global player, dead, tiles, tile_drops, sparks, game_timer, height, target_height, coins, end_coin_count, current_item, master_clock, last_place, item_used, combo_multiplier, combo_timer, stack_heights, items
    player = Player(animation_manager, (DISPLAY_SIZE[0] // 2 - 5, -20), (8, 16), 'player')
    player.jumps_max = 2 + upgrades.get('jumps', 0)
    player.speed = 1.4 + (upgrades.get('speed', 0) * 0.1)
    dead, tiles, tile_drops, sparks, items = False, {}, [], [], []
    game_timer, height, target_height, coins, end_coin_count, current_item, master_clock, last_place, item_used = 0, 0, 0, 0, 0, None, 0, 0, False
    combo_multiplier, combo_timer = 1.0, 0
    
    for i in range(WINDOW_TILE_SIZE[0] - 2):
        tiles[(i + 1, WINDOW_TILE_SIZE[1] - 1)] = {'type': 'tile', 'data': {}}
    tiles[(1, WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
    tiles[(WINDOW_TILE_SIZE[0] - 2, WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
    stack_heights = [WINDOW_TILE_SIZE[1] - 1 for i in range(WINDOW_TILE_SIZE[0] - 2)]
    stack_heights[0] -= 1
    stack_heights[-1] -= 1

# --- GAME LOGIC LOOPS ---
def game_loop():
    global master_clock, game_timer, dead, last_place, height, target_height, combo_timer, combo_multiplier, combo_text_scale, banked_coins, game_state, coins, camera_offset

    master_clock += 1

    if combo_timer > 0:
        combo_timer -= 1
        if combo_timer == 0:
            combo_multiplier = 1.0
    combo_text_scale += (1 - combo_text_scale) * 0.2

    # Dynamic Camera
    camera_offset[1] = height
    camera_offset[0] += (player.center[0] - camera_offset[0] - DISPLAY_SIZE[0] / 2) / 20
    render_offset = [int(camera_offset[0]), int(camera_offset[1])]
    
    display.fill((22, 19, 40))

    parallax = random.random()
    for i in range(2):
        bg_particles.append([[random.random() * DISPLAY_SIZE[0] + render_offset[0], DISPLAY_SIZE[1] + render_offset[1] - height * parallax], parallax, random.randint(1, 8), random.random() * 1 + 1, random.choice([(0, 0, 0), (22, 19, 40)])])

    for i, p in sorted(enumerate(bg_particles), reverse=True):
        p[2] -= 0.01; p[0][1] -= p[3]
        if p[2] < 0: bg_particles.pop(i); continue
        
        if p[-1] != (0, 0, 0):
            pygame.draw.circle(display, p[-1], (p[0][0] - render_offset[0], p[0][1] - render_offset[1]), int(p[2] * 5 + 4), 4)
        else:
            pygame.draw.circle(display, p[-1], (p[0][0] - render_offset[0], p[0][1] - render_offset[1]), int(p[2]))

    if master_clock > 180:
        game_timer += 1
        if game_timer > 10 + 25 * (20000 - min(20000, master_clock)) / 20000:
            game_timer = 0
            if stack_heights:
                minimum = min(stack_heights)
                options = [i for i, stack in enumerate(stack_heights) if i != last_place for j in range(int((stack - minimum) ** (2.2 - min(20000, master_clock) / 10000)) + 1)]
                if options:
                    roll = random.randint(1, 25)
                    if roll == 1: tile_type = 'chest'
                    elif roll < 4: tile_type = 'fragile'
                    elif roll < 6: tile_type = 'bounce'
                    elif roll == 7: tile_type = 'spike'
                    else: tile_type = 'tile'
                    c = random.choice(options)
                    last_place = c
                    tile_drops.append([(c + 1) * TILE_SIZE, -render_offset[1] - TILE_SIZE, tile_type])

    tile_drop_rects = []
    for i, tile in sorted(enumerate(tile_drops), reverse=True):
        tile[1] += 1.4
        r = pygame.Rect(tile[0], tile[1], TILE_SIZE, TILE_SIZE)
        tile_drop_rects.append(r)

        graze_rect = player.rect.copy(); graze_rect.inflate_ip(8, 8) 
        if graze_rect.colliderect(r) and not player.rect.colliderect(r):
            combo_multiplier += 0.2; combo_timer = COMBO_DURATION; combo_text_scale = 1.5

        if r.colliderect(player.rect) and not dead:
            sounds['death'].play()
            player.velocity = [1.3, -6]
            for i in range(380):
                angle = random.random() * math.pi; speed = random.random() * 1.5
                sparks.append([player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.02, (12, 2, 2), True, 0.1])
            dead = True; banked_coins += coins; save_progress(); game_state = 'game_over'

        check_pos = (int(r.centerx // TILE_SIZE), int(math.floor(r.bottom / TILE_SIZE)))
        if check_pos in tiles:
            tile_drops.pop(i); place_pos = (check_pos[0], check_pos[1] - 1)
            stack_heights[place_pos[0] - 1] = place_pos[1]
            tiles[place_pos] = {'type': tile[2], 'data': {}}
            sounds['block_land'].play()
            if tiles[check_pos]['type'] == 'chest':
                tiles[check_pos]['type'] = 'tile'
                sounds['chest_destroy'].play()
                for i in range(100):
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
                sparks.append([[tile_pos[0] * 16 + random.random() * 16, tile_pos[1] * 16 + 14], [random.random()*0.5-0.25, random.random()*0.5], random.random()*2+1, 0.08, (6,4,1), True, 0.05])
            if tile_data['data']['timer'] <= 0:
                tiles_to_remove.append(tile_pos)
                for i in range(20):
                    angle = random.random() * math.pi * 2; speed = random.random() * 1.5
                    sparks.append([[tile_pos[0]*16+8, tile_pos[1]*16+8], [math.cos(angle)*speed, math.sin(angle)*speed], random.random()*4+2, 0.05, (6,4,1), True, 0.1])
    for tile_pos in tiles_to_remove:
        if tile_pos in tiles: del tiles[tile_pos]

    tile_rects = []
    for tile_pos, tile_data in tiles.items():
        tile_rects.append(pygame.Rect(TILE_SIZE * tile_pos[0], TILE_SIZE * tile_pos[1], TILE_SIZE, TILE_SIZE))
        tile_type = tile_data['type']
        display.blit(tile_img, (TILE_SIZE*tile_pos[0]-render_offset[0], TILE_SIZE*tile_pos[1]-render_offset[1]))
        
        if tile_type == 'placed_tile': display.blit(placed_tile_img, (TILE_SIZE*tile_pos[0]-render_offset[0], TILE_SIZE*tile_pos[1]-render_offset[1]))
        if tile_type == 'fragile': display.blit(fragile_tile_img, (TILE_SIZE*tile_pos[0]-render_offset[0], TILE_SIZE*tile_pos[1]-render_offset[1]))
        if tile_type == 'bounce': display.blit(bounce_tile_img, (TILE_SIZE*tile_pos[0]-render_offset[0], TILE_SIZE*tile_pos[1]-render_offset[1]))
        if tile_type == 'spike': display.blit(spike_tile_img, (TILE_SIZE*tile_pos[0]-render_offset[0], TILE_SIZE*tile_pos[1]-render_offset[1]))

        if tile_type == 'chest':
            display.blit(chest_img, (TILE_SIZE*tile_pos[0]-render_offset[0], TILE_SIZE*(tile_pos[1]-1)-render_offset[1]))
            chest_r = pygame.Rect(TILE_SIZE*tile_pos[0]+2, TILE_SIZE*(tile_pos[1]-1)+6, TILE_SIZE-4, TILE_SIZE-6)
            if chest_r.colliderect(player.rect):
                sounds['chest_open'].play()
                combo_multiplier += 1.0; combo_timer = COMBO_DURATION; combo_text_scale = 1.5
                for i in range(50):
                    sparks.append([[tile_pos[0]*16+8, (tile_pos[1]-1)*16+8], [random.random()*2-1, random.random()-2], random.random()*3+3, 0.01, (12,8,2), True, 0.05])
                tiles[tile_pos]['type'] = 'opened_chest'
                player.jumps += 1; player.attempt_jump(); player.velocity[1] = -3.5
                if random.randint(1, 10) < 3 + upgrades.get('item_luck', 0):
                    items.append(Item(animation_manager, (tile_pos[0]*16+5, (tile_pos[1]-1)*16+5), (6,6), random.choice(['warp','cube','jump']), velocity=[random.random()*5-2.5, random.random()*2-5]))
                else:
                    for i in range(random.randint(2, 6)):
                        items.append(Item(animation_manager, (tile_pos[0]*16+5, (tile_pos[1]-1)*16+5), (6,6), 'coin', velocity=[random.random()*5-2.5, random.random()*2-7]))
        elif tile_type == 'opened_chest':
            display.blit(opened_chest_img, (TILE_SIZE*tile_pos[0]-render_offset[0], TILE_SIZE*(tile_pos[1]-1)-render_offset[1]))

    if tiles:
        base_row = max(tiles, key=lambda x: x[1])[1] - 1
        filled = all((i + 1, base_row) in tiles for i in range(WINDOW_TILE_SIZE[0] - 2))
        if filled: target_height = math.floor(height/TILE_SIZE) * TILE_SIZE + TILE_SIZE
    
    if height != target_height:
        height += (target_height - height) / 10
        if abs(target_height - height) < 0.2:
            height = target_height
            base_row = int(height/TILE_SIZE) - (WINDOW_TILE_SIZE[1]-1)
            for i in range(WINDOW_TILE_SIZE[0] - 2):
                if (i+1, base_row+1) in tiles: del tiles[(i+1, base_row+1)]

    for i in range(WINDOW_TILE_SIZE[1] + 4):
        pos_y = (-(height % TILE_SIZE)) - TILE_SIZE + (i * TILE_SIZE)
        display.blit(edge_tile_img, (0 - render_offset[0], pos_y - render_offset[1]))
        display.blit(edge_tile_img, (TILE_SIZE * (WINDOW_TILE_SIZE[0]-1) - render_offset[0], pos_y - render_offset[1]))

    edge_rects = [pygame.Rect(0, player.pos[1]-300, TILE_SIZE, 600), pygame.Rect(TILE_SIZE*(WINDOW_TILE_SIZE[0]-1), player.pos[1]-300, TILE_SIZE, 600)]

    for i, item in sorted(enumerate(items), reverse=True):
        if int(item.center[0]//TILE_SIZE), int(item.center[1]//TILE_SIZE) in tiles: items.pop(i); continue
        item.update(edge_rects + lookup_nearby(tiles, item.center))
        if item.time > 30 and item.rect.colliderect(player.rect):
            if item.type == 'coin':
                sounds['coin'].play(); coins += int(1*combo_multiplier); combo_multiplier += 0.1; combo_timer = COMBO_DURATION; combo_text_scale = 1.5
                for j in range(25):
                    sparks.append([item.center.copy(), [math.cos(random.random()*math.pi*2)*0.4, math.sin(random.random()*math.pi*2)*0.4], random.random()*3+3, 0.02, (12,8,2), True, 0.1])
            else:
                sounds['collect_item'].play(); current_item = item.type
                for j in range(50): sparks.append([item.center.copy(), [random.random()*0.3-0.15, random.random()*6-3], random.random()*4+3, 0.01, (12,8,2), False, 0])
            items.pop(i); continue
        
        r1=int(9+math.sin(master_clock/30)*3); r2=int(5+math.sin(master_clock/40)*2)
        display.blit(glow_img(r1,(12,8,2)), (item.center[0]-r1-1-render_offset[0], item.center[1]-r1-2-render_offset[1]), special_flags=BLEND_RGBA_ADD)
        display.blit(glow_img(r2,(24,16,3)), (item.center[0]-r2-1-render_offset[0], item.center[1]-r2-2-render_offset[1]), special_flags=BLEND_RGBA_ADD)
        item.render(display, render_offset)

    if not dead:
        collisions = player.update(tile_drop_rects + edge_rects + tile_rects)
        if collisions['bottom']:
            tile_pos_below = (player.rect.midbottom[0]//TILE_SIZE, player.rect.midbottom[1]//TILE_SIZE)
            if tile_pos_below in tiles:
                tile_type_below = tiles[tile_pos_below]['type']
                if tile_type_below == 'fragile' and 'timer' not in tiles[tile_pos_below]['data']:
                    sounds['block_land'].play(); tiles[tile_pos_below]['data']['timer'] = 90
                elif tile_type_below == 'bounce':
                    player.velocity[1] = -9; player.jumps=player.jumps_max; sounds['super_jump'].play(); combo_multiplier+=0.5; combo_timer=COMBO_DURATION; combo_text_scale=1.5
                    for i in range(40):
                        sparks.append([[player.rect.centerx,player.rect.bottom], [math.cos(random.random()*math.pi-math.pi)*2, math.sin(random.random()*math.pi-math.pi)*2], random.random()*3+2, 0.04, (8,2,12), True, 0.1])
                elif tile_type_below == 'spike': 
                    sounds['death'].play(); player.velocity=[0,-4]
                    for i in range(380):
                        sparks.append([player.center.copy(), [math.cos(random.random()*math.pi)*1.5, math.sin(random.random()*math.pi)*1.5], random.random()*3+3, 0.02, (12,2,2), True, 0.1])
                    dead=True; banked_coins+=coins; save_progress(); game_state='game_over'
    else:
        player.opacity = 80; player.update([]); player.rotation -= 16
    
    if player: player.render(display, render_offset)

    for i, spark in sorted(enumerate(sparks), reverse=True):
        spark[0][0]+=spark[1][0]; spark[0][1]+=spark[1][1]; spark[2]-=spark[3]
        if spark[5]:
            spark[1][1] = min(spark[1][1] + spark[6], 3)
            if int(spark[0][0]//TILE_SIZE), int(spark[0][1]//TILE_SIZE) in tiles or spark[0][0] < TILE_SIZE or spark[0][0] > DISPLAY_SIZE[0] - TILE_SIZE:
                spark[1][0] *= -0.7
            if int(spark[0][0]//TILE_SIZE), int(spark[0][1]//TILE_SIZE) in tiles:
                spark[1][1] *= -0.7
        if spark[2] <= 1: sparks.pop(i); continue
        display.blit(glow_img(spark[2], spark[4]), (spark[0][0]-spark[2]-render_offset[0], spark[0][1]-spark[2]-render_offset[1]), special_flags=BLEND_RGBA_ADD)

    # UI Rendering
    if not dead:
        coins_text_width = white_font.width(str(coins))
        render_panel(display, (4, 4), (20 + coins_text_width, 16), panel_img)
        display.blit(coin_icon, (8, 7))
        white_font.render(str(coins), display, (22, 9))

        if combo_multiplier > 1.0:
            combo_text = f"x{combo_multiplier:.1f}"
            width = white_font.width(combo_text)
            pos = (DISPLAY_SIZE[0] // 2 - width // 2, 8)
            
            scaled_font_surf = pygame.transform.scale(white_font.letters[white_font.font_order.index('x')], (int(white_font.letters[white_font.font_order.index('x')].get_width() * combo_text_scale), int(white_font.letters[white_font.font_order.index('x')].get_height() * combo_text_scale)))
            
            white_font.render(combo_text, display, (pos[0], pos[1] - (scaled_font_surf.get_height() - white_font.line_height) / 2))

        render_panel(display, (DISPLAY_SIZE[0] - 30, 4), (26, 26), panel_img)
        if current_item:
            display.blit(item_icons[current_item], (DISPLAY_SIZE[0] - 23, 11))

    display.blit(vignette_img, (0, 0), special_flags=BLEND_RGBA_MULT)

def upgrade_loop():
    global banked_coins, upgrades, upgrade_selection
    display.fill((22, 19, 40))
    render_panel(display, (DISPLAY_SIZE[0] // 2 - 130, 10), (260, 196), panel_img)
    
    black_font.render('Upgrades', display, (DISPLAY_SIZE[0]//2 - white_font.width('Upgrades')//2 + 1, 21))
    white_font.render('Upgrades', display, (DISPLAY_SIZE[0]//2 - white_font.width('Upgrades')//2, 20))
    
    bank_text = f"Coins: {banked_coins}"; coin_pos_x = DISPLAY_SIZE[0]//2 - (white_font.width(bank_text) + 9)//2
    display.blit(coin_icon, (coin_pos_x, 37))
    white_font.render(bank_text, display, (coin_pos_x + 14, 38))
    
    y_offset = 70
    for i, key in enumerate(UPGRADE_DEFINITIONS.keys()):
        info = UPGRADE_DEFINITIONS[key]; current_level = upgrades.get(key, 0)
        cost = info['base_cost'] + (current_level * info['cost_increase'])
        h_color, nh_color, na_color = (251,245,239), (100,100,120), (150,40,40)
        name_font = Font('data/fonts/small_font.png', h_color if i==upgrade_selection else nh_color)
        cost_font = Font('data/fonts/small_font.png', h_color if banked_coins>=cost else na_color)
        
        name_font.render(f"{info['name']} [Lvl {current_level}]", display, (80, y_offset))
        cost_font.render(f"Cost: {cost}", display, (DISPLAY_SIZE[0] - 140 - cost_font.width(f"Cost: {cost}"), y_offset))
        y_offset += 25
    
    selected_desc = UPGRADE_DEFINITIONS[list(UPGRADE_DEFINITIONS.keys())[upgrade_selection]]['description']
    white_font.render(selected_desc, display, (DISPLAY_SIZE[0]//2-white_font.width(selected_desc)//2, y_offset+10))
    white_font.render("Press Enter/Space to buy. ESC to go back.", display, (DISPLAY_SIZE[0]//2-white_font.width("Press Enter/Space to buy. ESC to go back.")//2, DISPLAY_SIZE[1]-30))
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
                    if event.key in [K_RIGHT,K_d]: player.right=True
                    if event.key in [K_LEFT,K_a]: player.left=True
                    if event.key in [K_UP,K_w,K_SPACE]:
                        if player.jumps: sounds['jump'].play()
                        player.attempt_jump()
                    if event.key in [K_e,K_x] and current_item:
                        item_used=True
                        if current_item == 'warp' and stack_heights:
                            sounds['warp'].play()
                            max_point = min(enumerate(stack_heights), key=lambda x: x[1])
                            player.pos = [(max_point[0]+1)*TILE_SIZE+4, (max_point[1]-1)*TILE_SIZE]
                        # ... other item logic
                        current_item=None
            if event.type == KEYUP and not dead:
                if event.key in [K_RIGHT,K_d]: player.right=False
                if event.key in [K_LEFT,K_a]: player.left=False
    elif game_state == 'game_over':
        display.fill((22,19,40))
        render_panel(display, (DISPLAY_SIZE[0]//2-100, 40), (200, 130), panel_img)
        
        white_font.render('game over', display, (DISPLAY_SIZE[0]//2-white_font.width('game over')//2, 50))
        white_font.render(f"Score: {coins}", display, (DISPLAY_SIZE[0]//2-white_font.width(f"Score: {coins}")//2, 65))
        
        h_color, nh_color = (251,245,239), (100,100,120)
        restart_font = Font('data/fonts/small_font.png', h_color if game_over_selection==0 else nh_color)
        upgrades_font = Font('data/fonts/small_font.png', h_color if game_over_selection==1 else nh_color)
        restart_font.render("Restart", display, (DISPLAY_SIZE[0]//2-restart_font.width("Restart")//2, 100))
        upgrades_font.render("Upgrades", display, (DISPLAY_SIZE[0]//2-upgrades_font.width("Upgrades")//2, 120))
        
        display.blit(vignette_img, (0,0), special_flags=BLEND_RGBA_MULT)

        for event in pygame.event.get():
            if event.type==QUIT: pygame.quit(); sys.exit()
            if event.type==KEYDOWN:
                if event.key==K_ESCAPE: game_state='upgrades'
                if event.key in [K_UP,K_DOWN,K_w,K_s]: game_over_selection=1-game_over_selection
                if event.key in [K_RETURN,K_SPACE,K_e,K_x]:
                    if game_over_selection==0: reset_game(); game_state='playing'
                    else: game_state='upgrades'
    elif game_state == 'upgrades':
        upgrade_loop()
        for event in pygame.event.get():
            if event.type==QUIT: pygame.quit(); sys.exit()
            if event.type==KEYDOWN:
                if event.key==K_ESCAPE: game_state='game_over'
                if event.key in [K_DOWN,K_s]: upgrade_selection=(upgrade_selection+1)%len(UPGRADE_DEFINITIONS)
                if event.key in [K_UP,K_w]: upgrade_selection=(upgrade_selection-1)%len(UPGRADE_DEFINITIONS)
                if event.key in [K_RETURN,K_SPACE,K_e,K_x]:
                    key=list(UPGRADE_DEFINITIONS.keys())[upgrade_selection]
                    info=UPGRADE_DEFINITIONS[key]; current_level=upgrades.get(key,0)
                    cost=info['base_cost']+(current_level*info['cost_increase'])
                    if banked_coins>=cost:
                        sounds['coin'].play(); banked_coins-=cost; upgrades[key]=current_level+1; save_progress()

    screen.blit(pygame.transform.scale(display, screen.get_size()), (0, 0))
    pygame.display.update()
    clock.tick(60)