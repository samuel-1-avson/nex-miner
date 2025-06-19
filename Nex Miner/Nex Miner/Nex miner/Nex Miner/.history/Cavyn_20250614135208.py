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
            if 'coin_magnet' not in data['upgrades']: # Handle old save files
                data['upgrades']['coin_magnet'] = 0
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        default_save = {"banked_coins": 100, "upgrades": {"jumps": 0, "speed": 0, "item_luck": 0, "coin_magnet": 0}, "high_score": 0}
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
    'coin_magnet': {'name': 'Coin Magnet', 'desc': 'Coins pull to you', 'base_cost': 150, 'max_level': 4},
}
upgrade_keys = list(UPGRADES.keys())

# -- NEW: BIOME SYSTEM --
BIOMES = [
    {
        'name': 'The Depths',
        'score_req': 0,
        'bg_color': (22, 19, 40),
        'bg_layers': ('data/images/background.png', 'data/images/background.png'),
        'available_tiles': ['tile', 'chest', 'fragile', 'bounce', 'spike', 'greed', 'magnetic'],
        'special_spawn_rate': {'magnetic': 9}, # Normal spawn rate for magnetic
    },
    {
        'name': 'Goo-Grotto',
        'score_req': 125,
        'bg_color': (19, 40, 30),
        'bg_layers': ('data/images/background_cave.png', 'data/images/background_cave.png'),
        'available_tiles': ['tile', 'chest', 'fragile', 'bounce', 'spike', 'greed', 'sticky'],
        'special_spawn_rate': {'sticky': 8}, # Rate at which sticky tiles will spawn (lower number = more common)
    },
    # You can easily add a third biome here later!
]

# -- NEW: PERK SYSTEM DATA --
PERKS = {
    'acrobat': {'name': 'Acrobat', 'desc': 'First jump after wall contact is higher.'},
    'overcharge': {'name': 'Overcharge', 'desc': 'Dashing through tiles creates an explosion.'},
    'feather_fall': {'name': 'Feather Fall', 'desc': 'You fall 20% slower.'},
    'technician': {'name': 'Technician', 'desc': 'Projectiles pierce one tile.'},
    'greedy': {'name': 'Greedy', 'desc': 'Chests & Greed Tiles drop double coins.'},
    'glass_cannon': {'name': 'Glass Cannon', 'desc': 'Faster combo, but instant death.'},
}

# --- Player's perks for the current run ---
active_perks = set()


current_biome_index = 0

def load_img(path):
    img = pygame.image.load(path).convert()
    img.set_colorkey((0, 0, 0))
    return img

# -- MODIFIED: Dynamic Background Loading --
backgrounds = {}
def load_biome_bgs(biome_info):
    try:
        bg_far_path, bg_near_path = biome_info['bg_layers']
        
        # Load far layer
        far_surf = pygame.image.load(bg_far_path).convert()
        backgrounds['far'] = pygame.transform.scale(far_surf, DISPLAY_SIZE)
        
        # Load near layer
        near_surf = load_img(bg_near_path)
        backgrounds['near'] = pygame.transform.scale(near_surf, DISPLAY_SIZE)
        
    except (pygame.error, FileNotFoundError) as e:
        print(f"Warning: Could not load background for biome {biome_info['name']}. Reason: {e}")
        backgrounds['far'] = None
        backgrounds['near'] = None

load_biome_bgs(BIOMES[0]) # Load the initial biome's background


tile_img = load_img('data/images/tile.png')
placed_tile_img = load_img('data/images/placed_tile.png')
chest_img = load_img('data/images/chest.png')
ghost_chest_img = load_img('data/images/ghost_chest.png')
opened_chest_img = load_img('data/images/opened_chest.png')
edge_tile_img = load_img('data/images/edge_tile.png')
fragile_tile_img = load_img('data/images/fragile_tile.png')
bounce_tile_img = load_img('data/images/bounce_tile.png')
spike_tile_img = load_img('data/images/spike_tile.png')
magnetic_tile_img = load_img('data/images/magnetic_tile.png')
sticky_tile_img = load_img('data/images/sticky_tile.png')
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

# -- NEW: TIME SLOWDOWN SOUNDS --
sounds['time_slow_start'] = pygame.mixer.Sound('data/sfx/warp.wav')
sounds['time_slow_start'].set_volume(0.4)
sounds['time_slow_end'] = pygame.mixer.Sound('data/sfx/chest_open.wav')
sounds['time_slow_end'].set_volume(0.3)
sounds['time_empty'] = pygame.mixer.Sound('data/sfx/death.wav')
sounds['time_empty'].set_volume(0.25)


item_icons = {
    'cube': load_img('data/images/cube_icon.png'),
    'warp': load_img('data/images/warp_icon.png'),
    'jump': load_img('data/images/jump_icon.png'),
    'bomb': load_img('data/images/bomb_icon.png'),
    'freeze': load_img('data/images/freeze_icon.png'),
    'shield': load_img('data/images/shield_icon.png'),
}
shield_aura_img = load_img('data/images/shield_aura.png')
shield_aura_img.set_alpha(150)

# --- NEW: LOAD PERK ICONS ---
perk_icons = {}
perk_icon_path = 'data/images/perk_icons/'
for perk_name in PERKS.keys():
    try:
        # Assumes icon filename matches the perk key
        perk_icons[perk_name] = load_img(perk_icon_path + perk_name + '.png')
    except pygame.error:
        print(f"Warning: Could not load icon for perk '{perk_name}'.")

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

    def update(self, tiles, time_scale=1.0):
        self.time += 1 * time_scale
        self.velocity[1] = min(self.velocity[1] + 0.2, 3)
        self.velocity[0] = normalize(self.velocity[0], 0.05)
        self.move(self.velocity, tiles, time_scale)

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

        # Dashing
        self.dash_timer = 0
        self.DASH_SPEED = 8 # A bit faster since it's a special move
        self.DASH_DURATION = 8 # frames
        
        # === NEW: Focus Dash Meter ===
        self.focus_meter = 100
        self.FOCUS_METER_MAX = 100
        self.is_charging_dash = False
        self.FOCUS_DASH_COST = 50
        self.FOCUS_RECHARGE_RATE = 0.4
        self.wall_contact_timer = 0


    def attempt_jump(self):
        jump_velocity = -5 # Base jump velocity
        
        # PERK EFFECT
        if 'acrobat' in active_perks and self.wall_contact_timer > 0:
            jump_velocity = -6.5 # Stronger wall jump
            self.wall_contact_timer = 0 # Use up the wall contact buff

        if self.jumps > 0 or self.coyote_timer > 0:
            if self.jumps == self.jumps_max or self.coyote_timer > 0:
                self.velocity[1] = jump_velocity
            else:
                self.velocity[1] = -4 # Subsequent jumps are a bit weaker
                for i in range(24):
                    # Particle effect for double jump
                    physics_on = random.choice([False, False, True])
                    direction = 1 if i % 2 else -1
                    sparks.append([[self.center[0] + random.uniform(-7, 7), self.center[1]], [direction * (random.uniform(0.05, 0.1)) + (random.uniform(-2, 2)) * physics_on, random.uniform(0.05, 0.1) + random.uniform(0, 2) * physics_on], random.uniform(3, 6), 0.04 - 0.02 * physics_on, (6, 4, 1), physics_on, 0.05 * physics_on])

            if self.coyote_timer <= 0:
                self.jumps -= 1

            self.coyote_timer = 0
            self.jumping = True
            self.jump_rot = 0
    
    def update(self, tiles, time_scale=1.0):
        super().update(1 / 60, time_scale)

        # === TIMER MANAGEMENT ===
        self.air_time += 1
        if self.coyote_timer > 0: self.coyote_timer -= 1
        if self.jump_buffer_timer > 0: self.jump_buffer_timer -= 1
        if self.dash_timer > 0: self.dash_timer -= 1 * time_scale

        # === FOCUS METER RECHARGE ===
        if not self.is_charging_dash:
            self.focus_meter = min(self.FOCUS_METER_MAX, self.focus_meter + self.FOCUS_RECHARGE_RATE * time_scale)

        # === HORIZONTAL MOVEMENT ===
        if self.dash_timer > 0:
            # Player is dashing: Force velocity.
            direction = 1 if self.flip[0] else -1
            self.velocity[0] = direction * self.DASH_SPEED
            
            # Particle trail
            sparks.append([[self.center[0] - direction * 6, self.center[1] + random.uniform(-3, 3)], [-direction * (random.uniform(1, 2)), random.uniform(-0.5, 0.5)], random.uniform(2, 5), 0.15, (200, 220, 255), False, 0])
        else:
            # Player is NOT dashing: Normal acceleration/deceleration.
            target_velocity_x = 0
            if self.right:
                target_velocity_x = self.speed
            elif self.left:
                target_velocity_x = -self.speed
            
            self.velocity[0] += (target_velocity_x - self.velocity[0]) * 0.3
            if abs(self.velocity[0]) < 0.1:
                self.velocity[0] = 0

        # === VERTICAL MOVEMENT (GRAVITY) ===
        if self.dash_timer > 0:
            self.velocity[1] = 0
        else:
            gravity = 0.3
            if 'feather_fall' in active_perks: # PERK EFFECT
                gravity = 0.24 # 20% less gravity
            self.velocity[1] = min(self.velocity[1] + gravity, 4)

        # === ANIMATION AND VISUALS ===
        if not dead and self.dash_timer <= 0:
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

        if self.is_charging_dash:
            self.set_action('idle') # A specific "charge" animation would be great here
        elif self.dash_timer > 0:
            self.set_action('jump')
        elif self.air_time > 3:
            self.set_action('jump')
        elif abs(self.velocity[0]) > 0.1:
            self.set_action('run')
        else:
            self.set_action('idle')

        # === COLLISION AND STATE CHANGES ===
        was_on_ground = self.air_time <= 1
        collisions = self.move(self.velocity, tiles, time_scale)

        # PERK EFFECT: Check for wall contact
        if collisions['left'] or collisions['right']:
            self.wall_contact_timer = 15 # Wall contact lasts for 15 frames
        
        if self.wall_contact_timer > 0:
            self.wall_contact_timer -= 1

        if collisions['bottom']:
            self.velocity[1] = 0
            self.air_time = 0
            self.jumps = self.jumps_max
            self.jumping = False
            self.rotation = 0
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
        self.health = 1 # Give projectile 1 hp
        if 'technician' in active_perks: # PERK EFFECT
            self.health = 2 # Give 2 hp if perk is active


    def update(self, time_scale=1.0):
        super().update(1/60, time_scale)
        self.pos[0] += self.velocity[0] * time_scale
        self.pos[1] += self.velocity[1] * time_scale


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

# -- NEW: TIME SLOWDOWN ABILITY --
time_meter = 120
time_meter_max = 120
time_scale = 1.0
slowing_time = False

combo_multiplier = 1.0
combo_timer = 0
COMBO_DURATION = 180
run_coins_banked = False
upgrade_selection = 0
screen_shake = 0
player_shielded = False
current_biome_index = 0
perk_selection_active = False
perk_selection_choice = 0
perks_to_offer = []
last_perk_score = 0
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
    global dead, run_coins_banked, upgrade_selection, new_high_score, save_data, screen_shake, player_shielded
    
    # CHECK FOR SHIELD
    if player_shielded:
        player_shielded = False
        if 'explosion' in sounds:
            sounds['explosion'].play()
        else: # Fallback sound
            sounds['super_jump'].play()
        screen_shake = 15
        # Particle burst for shield breaking
        for i in range(60):
            angle = random.random() * math.pi * 2
            speed = random.random() * 2
            sparks.append([player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.uniform(2, 4), 0.05, (170, 200, 255), True, 0.05])
        return # Exit the function, preventing death

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
    display_copy = display.copy()

    if not perk_selection_active:
        # -- NEW: BIOME TRANSITION LOGIC --
        if not dead:
            # Check if we should transition to a new biome
            next_biome_index = current_biome_index
            if current_biome_index + 1 < len(BIOMES):
                if coins >= BIOMES[current_biome_index + 1]['score_req']:
                    next_biome_index += 1
            
            # If we have a new biome, trigger transition
            if next_biome_index != current_biome_index:
                current_biome_index = next_biome_index
                load_biome_bgs(BIOMES[current_biome_index])
                
                # --- TRANSITION EFFECT ---
                sounds['warp'].play()
                screen_shake = 15
                # Flash the screen white
                flash_overlay = pygame.Surface(DISPLAY_SIZE)
                flash_overlay.fill((200, 200, 220))
                for i in range(120, 0, -5):
                    flash_overlay.set_alpha(i)
                    display.blit(flash_overlay, (0, 0))
                    pygame.display.update()
                    pygame.time.delay(5)

        current_biome = BIOMES[current_biome_index]
        
        # -- RENDER PARALLAX BACKGROUND --
        display.fill(current_biome['bg_color'])

        if backgrounds['far']:
            scroll_y = (height * 0.2) % DISPLAY_SIZE[1]
            display.blit(backgrounds['far'], (0, scroll_y))
            display.blit(backgrounds['far'], (0, scroll_y - DISPLAY_SIZE[1]))

        if backgrounds['near']:
            scroll_y = (height * 0.4) % DISPLAY_SIZE[1]
            display.blit(backgrounds['near'], (0, scroll_y))
            display.blit(backgrounds['near'], (0, scroll_y - DISPLAY_SIZE[1]))


        master_clock += 1
        
        # -- NEW: INTEGRATED TIME SLOWDOWN LOGIC --
        time_scale = 1.0
        if not dead:
            # Time slows if EITHER the normal slow key is held OR the player is charging a dash
            is_slowing_now = (pygame.key.get_pressed()[K_LSHIFT] and time_meter > 0) or player.is_charging_dash
            
            if is_slowing_now and not slowing_time:
                 sounds['time_slow_start'].play()
            elif not is_slowing_now and slowing_time:
                 sounds['time_slow_end'].play()

            slowing_time = is_slowing_now

            if slowing_time:
                time_scale = 0.4
                # Drain the correct meter
                if player.is_charging_dash:
                    player.focus_meter = max(0, player.focus_meter - 1.5) # Draining focus is faster
                    if player.focus_meter <= 0: # If you run out of juice, stop charging
                        player.is_charging_dash = False
                elif pygame.key.get_pressed()[K_LSHIFT]:
                     time_meter = max(0, time_meter - 0.75)
                     if time_meter <= 0:
                          sounds['time_empty'].play()
            else:
                # Only recharge the normal time meter when not slowing
                time_meter = min(time_meter_max, time_meter + 0.2)
        
        if dead:
            slowing_time = False
            time_scale = 1.0


        if screen_shake > 0:
            screen_shake -= 0.5 * time_scale

        # -- NEW FEATURE: FREEZE TIME POWERUP --
        if freeze_timer > 0:
            freeze_timer -= 1 * time_scale
            # Visual effect for frozen time
            freeze_overlay = pygame.Surface(DISPLAY_SIZE, pygame.SRCALPHA)
            alpha = 60 + math.sin(master_clock / 5) * 10
            freeze_overlay.fill((170, 200, 255, alpha))
            display.blit(freeze_overlay, (0, 0))


        # -- NEW FEATURE: COMBO END --
        if combo_timer > 0:
            depletion_rate = 1
            if 'glass_cannon' in active_perks:
                depletion_rate = 2
            combo_timer -= depletion_rate * time_scale
            
            if combo_timer <= 0 and combo_multiplier > 1.0:
                combo_timer = 0
                if 'combo_end' in sounds:
                    sounds['combo_end'].play()
                # Particle burst at combo meter location
                for i in range(20):
                    angle = random.random() * math.pi * 2
                    speed = random.random() * 1.5
                    sparks.append([[DISPLAY_SIZE[0] // 2, 10], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 2 + 1, 0.05, (251, 245, 239), True, 0.05])
                combo_multiplier = 1.0

        if master_clock > 180:
            game_timer += time_scale
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
                
                # Standard tile types
                if roll == 1:
                    tile_type = 'chest'
                elif roll < 4:
                    tile_type = 'fragile'
                elif roll < 6:
                    tile_type = 'bounce'
                elif roll == 7:
                    tile_type = 'spike'
                else:
                    tile_type = 'tile'
                
                # Check for biome-specific special tiles
                for special_tile, spawn_chance in current_biome['special_spawn_rate'].items():
                    if roll == spawn_chance:
                        tile_type = special_tile

                # Ensure we only spawn tiles that are actually available in the biome
                if tile_type not in current_biome['available_tiles']:
                    tile_type = 'tile'

                c = random.choice(options)
                last_place = c
                tile_drops.append([(c + 1) * TILE_SIZE, -height - TILE_SIZE, tile_type])


        tile_drop_rects = []
        for i, tile in sorted(enumerate(tile_drops), reverse=True):
            if freeze_timer <= 0: # Check if time is frozen
                tile[1] += 1.4 * time_scale
            pos = [tile[0] + TILE_SIZE // 2, tile[1] + TILE_SIZE]
            r = pygame.Rect(tile[0], tile[1], TILE_SIZE, TILE_SIZE)
            tile_drop_rects.append(r)

            graze_rect = player.rect.copy()
            graze_rect.inflate_ip(8, 8)
            if graze_rect.colliderect(r) and not player.rect.colliderect(r):
                graze_bonus = 0.2
                if 'glass_cannon' in active_perks:
                    graze_bonus *= 2
                combo_multiplier += graze_bonus
                combo_timer = COMBO_DURATION
            
            # === DASH DESTRUCTION LOGIC ===
            if player.dash_timer > 0 and r.colliderect(player.rect):
                tile_drops.pop(i)
                coins += 2
                dash_bonus = 0.3
                if 'glass_cannon' in active_perks:
                    dash_bonus *= 2
                combo_multiplier += dash_bonus
                combo_timer = COMBO_DURATION
                if 'explosion' in sounds:
                    sounds['explosion'].play()
                else: # Fallback sound
                    sounds['block_land'].play()
                screen_shake = max(screen_shake, 6)
                for k in range(20):
                    angle = random.random() * math.pi * 2
                    speed = random.random() * 2.5
                    sparks.append([[r.centerx, r.centery], [math.cos(angle) * speed, math.sin(angle) * speed], random.uniform(2, 5), 0.08, (251, 245, 239), True, 0.1])
                
                # PERK EFFECT: Overcharge
                if 'overcharge' in active_perks:
                    indices_to_remove = []
                    # Iterate through tile drops again to find adjacent ones
                    for k_inner, other_tile in enumerate(tile_drops):
                        other_r = pygame.Rect(other_tile[0], other_tile[1], TILE_SIZE, TILE_SIZE)
                        # Check for distance from the tile we just destroyed
                        if r.colliderect(other_r.inflate(TILE_SIZE, TILE_SIZE)):
                            indices_to_remove.append(k_inner)

                    indices_to_remove.sort(reverse=True)
                    for k_rem in indices_to_remove:
                         other_r = pygame.Rect(tile_drops[k_rem][0], tile_drops[k_rem][1], TILE_SIZE, TILE_SIZE)
                         # Explode this tile too
                         for p__ in range(15): # Particle effect for chained explosion
                              angle = random.random() * math.pi * 2
                              speed = random.random() * 2
                              sparks.append([[other_r.centerx, other_r.centery], [math.cos(angle) * speed, math.sin(angle) * speed], random.uniform(1, 4), 0.1, (255,100,80), True, 0.1])
                         tile_drops.pop(k_rem)
                         coins += 1 # Bonus coin

                continue
            # === END OF DASH DESTRUCTION LOGIC ===

            # PERK EFFECT: Glass Cannon instant death
            if 'glass_cannon' in active_perks and r.colliderect(player.rect):
                # We need to bypass the shield check in handle_death()
                # A simple way is to force 'player_shielded' to false just for this call.
                temp_shield_state = player_shielded
                player_shielded = False
                handle_death()
                player_shielded = temp_shield_state # Restore it just in case
            elif r.colliderect(player.rect):
                handle_death()

            check_pos = (int(pos[0] // TILE_SIZE), int(math.floor(pos[1] / TILE_SIZE)))
            if check_pos in tiles:
                place_pos = (check_pos[0], check_pos[1] - 1)

                if tiles[check_pos]['type'] == 'greed':
                    tile_drops.pop(i)
                    sounds['chest_open'].play()
                    del tiles[check_pos]
                    
                    # PERK EFFECT: Greedy
                    coin_multiplier_perk = 1
                    if 'greedy' in active_perks:
                        coin_multiplier_perk = 2

                    for k in range(random.randint(5, 10) * coin_multiplier_perk): # <-- APPLY MULTIPLIER
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
                    if 'chest_destroy' in sounds: sounds['chest_destroy'].play()
                    for i_inner in range(100):
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
                    tile_data['data']['timer'] -= 1 * time_scale
                    if random.randint(1, 10) == 1:
                        sparks.append([
                            [tile_pos[0] * TILE_SIZE + random.random() * 16, tile_pos[1] * TILE_SIZE + 14],
                            [random.random() * 0.5 - 0.25, random.random() * 0.5],
                            random.random() * 2 + 1, 0.08, (6, 4, 1), True, 0.05
                        ])
                    if tile_data['data']['timer'] <= 0:
                        tiles_to_remove.append(tile_pos)
                        for i_inner in range(20):
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

            if tile_type == 'magnetic':
                display.blit(magnetic_tile_img, (TILE_SIZE * tile_pos[0], TILE_SIZE * tile_pos[1] + int(height)))
                # Add a subtle particle effect
                if random.randint(1, 15) == 1:
                    sparks.append([[tile_pos[0] * TILE_SIZE + 8, tile_pos[1] * TILE_SIZE + 8], [random.uniform(-1, 1), random.uniform(-1, 1)], random.uniform(1, 2), 0.1, (180, 100, 255), False, 0])
            if tile_type == 'sticky':
                display.blit(sticky_tile_img, (TILE_SIZE * tile_pos[0], TILE_SIZE * tile_pos[1] + int(height)))
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
                    chest_bonus = 1.0
                    if 'glass_cannon' in active_perks:
                        chest_bonus *= 2
                    combo_multiplier += chest_bonus
                    combo_timer = COMBO_DURATION
                    for i_inner in range(50):
                        sparks.append([[tile_pos[0] * TILE_SIZE + 8, (tile_pos[1] - 1) * TILE_SIZE + 8], [random.random() * 2 - 1, random.random() - 2], random.random() * 3 + 3, 0.01, (12, 8, 2), True, 0.05])
                    tiles[tile_pos]['type'] = 'opened_chest'
                    player.jumps += 1
                    player.attempt_jump()
                    player.velocity[1] = -3.5
                    item_luck_threshold = 3 + save_data['upgrades']['item_luck']

                    # PERK EFFECT: Greedy
                    coin_multiplier_perk = 1
                    if 'greedy' in active_perks:
                        coin_multiplier_perk = 2

                    if random.randint(1, 5) < item_luck_threshold:
                        items.append(Item(animation_manager, (tile_pos[0] * TILE_SIZE + 5, (tile_pos[1] - 1) * TILE_SIZE + 5), (6, 6), random.choice(['warp', 'cube', 'jump', 'bomb', 'freeze', 'shield']), velocity=[random.random() * 5 - 2.5, random.random() * 2 - 5]))
                    else:
                        for i_inner in range(random.randint(2, 6) * coin_multiplier_perk): # <-- APPLY MULTIPLIER
                            items.append(Item(animation_manager, (tile_pos[0] * TILE_SIZE + 5, (tile_pos[1] - 1) * TILE_SIZE + 5), (6, 6), 'coin', velocity=[random.random() * 5 - 2.5, random.random() * 2 - 7]))
            elif tile_type == 'opened_chest':
                display.blit(opened_chest_img, (TILE_SIZE * tile_pos[0], TILE_SIZE * (tile_pos[1] - 1) + int(height)))

        base_row = max(tiles, key=lambda x: x[1])[1] - 1 if tiles else WINDOW_TILE_SIZE[1] - 2
        filled = True
        for i_inner in range(WINDOW_TILE_SIZE[0] - 2):
            if (i_inner + 1, base_row) not in tiles:
                filled = False
        if filled:
            target_height = math.floor(height / TILE_SIZE) * TILE_SIZE + TILE_SIZE

        if height != target_height:
            height += (target_height - height) / 10
            if abs(target_height - height) < 0.2:
                height = target_height
                for i_inner in range(WINDOW_TILE_SIZE[0] - 2):
                    if (i_inner + 1, base_row + 1) in tiles:
                        del tiles[(i_inner + 1, base_row + 1)]

        for i_inner in range(WINDOW_TILE_SIZE[1] + 2):
            pos_y = (-height // 16) - 1 + i_inner
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
            item.update(edge_rects + lookup_nearby(tiles, item.center), time_scale)
            
            # NEW: COIN MAGNET LOGIC
            if item.type == 'coin' and not dead:
                magnet_level = save_data['upgrades']['coin_magnet']
                if magnet_level > 0:
                    # Base radius and strength, increases with level
                    pull_radius = 20 + magnet_level * 10
                    pull_strength = 0.05 + magnet_level * 0.05
                    
                    dist_x = player.center[0] - item.center[0]
                    dist_y = player.center[1] - item.center[1]
                    distance = math.sqrt(dist_x**2 + dist_y**2)

                    if distance < pull_radius:
                        item.velocity[0] += (dist_x / distance) * pull_strength * time_scale
                        item.velocity[1] += (dist_y / distance) * pull_strength * time_scale
            # END NEW LOGIC

            if item.time > 30:
                if item.rect.colliderect(player.rect):
                    if item.type == 'coin':
                        sounds['coin'].play()
                        coins += int(1 * combo_multiplier)
                        
                        coin_bonus = 0.1
                        if 'glass_cannon' in active_perks:
                            coin_bonus *= 2
                        combo_multiplier += coin_bonus
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
                        # NEW SHIELD LOGIC
                        if item.type == 'shield':
                            player_shielded = True
                            if 'upgrade' in sounds:
                                sounds['upgrade'].play()
                            else:
                                sounds['collect_item'].play()
                        else:
                            current_item = item.type
                        # END NEW LOGIC
                    items.pop(i)
                    continue
            r1 = int(9 + math.sin(master_clock / 30) * 3)
            r2 = int(5 + math.sin(master_clock / 40) * 2)
            display.blit(glow_img(r1, (12, 8, 2)), (item.center[0] - r1 - 1, item.center[1] + height - r1 - 2), special_flags=BLEND_RGBA_ADD)
            display.blit(glow_img(r2, (24, 16, 3)), (item.center[0] - r2 - 1, item.center[1] + height - r2 - 2), special_flags=BLEND_RGBA_ADD)
            item.render(display, (0, -height))

        # -- NEW FEATURE: PROJECTILE LOGIC --
        for i, p in sorted(enumerate(projectiles), reverse=True):
            p.update(time_scale)
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

                    p.health -= 1 # Projectile takes damage
                    
                    # Particles
                    for k in range(15):
                        angle = random.random() * math.pi * 2
                        speed = random.random() * 2
                        sparks.append([[tile_drop[0] + 8, tile_drop[1] + 8], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 2, 0.08, (251, 245, 239), True, 0.1])
                    tile_drops.pop(j)
                    
                    if p.health <= 0: # Only destroy projectile if out of health
                        projectiles.pop(i)
                        hit_tile = True
                        
                    coins += 1 # Small reward
                    combo_multiplier += 0.05
                    combo_timer = COMBO_DURATION
                    break # Projectile is used up
            if hit_tile:
                continue

        # NEW: MAGNETIC TILE LOGIC
        if not dead:
            for tile_pos, tile_data in tiles.items():
                if tile_data['type'] == 'magnetic':
                    tile_screen_y = TILE_SIZE * tile_pos[1] + int(height)
                    # Only apply force if the tile is visible on screen
                    if 0 < tile_screen_y < DISPLAY_SIZE[1]:
                        tile_x_center = tile_pos[0] * TILE_SIZE + TILE_SIZE // 2
                        player_x_center = player.center[0]
                        
                        # Pull the player towards the tile's X position
                        distance = tile_x_center - player_x_center
                        # The force gets weaker further away, but has a max strength
                        pull_force = max(-0.25, min(0.25, distance / 80)) # / 80 is the pull sensitivity
                        player.velocity[0] += pull_force * time_scale

        if not dead:
            collisions = player.update(tile_drop_rects + edge_rects + tile_rects, time_scale)

            # NEW: STICKY TILE / WALL SLIDE LOGIC
            if not collisions['bottom'] and not dead: # Only check for wall slide if in the air
                is_sliding = False
                # Check for tile to the left
                tile_pos_left = ((player.rect.left - 2) // TILE_SIZE, player.rect.centery // TILE_SIZE)
                if tile_pos_left in tiles and tiles[tile_pos_left]['type'] == 'sticky':
                    is_sliding = True
                
                # Check for tile to the right
                tile_pos_right = ((player.rect.right + 2) // TILE_SIZE, player.rect.centery // TILE_SIZE)
                if tile_pos_right in tiles and tiles[tile_pos_right]['type'] == 'sticky':
                    is_sliding = True
                
                if is_sliding:
                    # If sliding, cap vertical fall speed
                    player.velocity[1] = min(player.velocity[1], 1.0)
                    # You could add a wall-jump here by checking for jump input and applying horizontal velocity

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
            player.update([], time_scale)
            player.rotation -= 16
        
        # NEW: DRAW SHIELD AURA
        if player_shielded and not dead:
            aura_pos = (player.rect.centerx - shield_aura_img.get_width()//2, player.rect.centery - shield_aura_img.get_height()//2 - int(height))
            # Add a subtle pulse effect
            pulse = math.sin(master_clock / 8) * 2
            pulsing_aura = pygame.transform.scale(shield_aura_img, (int(shield_aura_img.get_width() + pulse), int(shield_aura_img.get_height() + pulse)))
            pulsing_aura.set_alpha(150 - pulse * 10)
            display.blit(pulsing_aura, aura_pos, special_flags=BLEND_RGBA_ADD)
            
        player.render(display, (0, -int(height)))

        for i, spark in sorted(enumerate(sparks), reverse=True):
            if len(spark) < 8:
                spark.append(False)

            if not spark[-1]:
                spark[1][1] = min(spark[1][1] + spark[-2], 3)

            spark[0][0] += spark[1][0] * time_scale
            if spark[5]:
                if ((int(spark[0][0] // TILE_SIZE), int(spark[0][1] // TILE_SIZE)) in tiles) or (spark[0][0] < TILE_SIZE) or (spark[0][0] > DISPLAY_SIZE[0] - TILE_SIZE):
                    spark[0][0] -= spark[1][0]
                    spark[1][0] *= -0.7
            spark[0][1] += spark[1][1] * time_scale
            if spark[5]:
                if (int(spark[0][0] // TILE_SIZE), int(spark[0][1] // TILE_SIZE)) in tiles:
                    spark[0][1] -= spark[1][1]
                    spark[1][1] *= -0.7
                    if abs(spark[1][1]) < 0.1:
                        spark[1][1] = 0
                        spark[-1] = True
            spark[2] -= spark[3] * time_scale
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

        # --- NEW: PERK OFFERING LOGIC ---
        if not dead and not perk_selection_active:
            score_interval = 75
            if coins > 0 and coins // score_interval > last_perk_score // score_interval:
                last_perk_score = coins
                
                # Find perks the player doesn't have yet
                available_perks = [p for p in PERKS.keys() if p not in active_perks]
                
                if available_perks:
                    perk_selection_active = True
                    perks_to_offer = random.sample(available_perks, k=min(3, len(available_perks)))
                    perk_selection_choice = 0
                    sounds['warp'].play() # Announce the perk screen

        if not dead:
            hud_panel = pygame.Surface((DISPLAY_SIZE[0], 28))
            hud_panel.set_alpha(100)
            hud_panel.fill((0, 0, 1))
            display.blit(hud_panel, (0, 0))

            display.blit(coin_icon, (4, 4))
            black_font.render(str(coins), display, (17, 6))
            white_font.render(str(coins), display, (16, 5))

            # -- TIME SLOWDOWN METER HUD --
            time_bar_pos_x = 4
            time_bar_pos_y = 17
            time_bar_w = 40
            time_bar_h = 6
            pygame.draw.rect(display, (0, 0, 1), [time_bar_pos_x, time_bar_pos_y, time_bar_w, time_bar_h])
            bar_fill_width = (time_meter / time_meter_max) * (time_bar_w - 2)
            bar_color = (80, 150, 255)
            if slowing_time and not player.is_charging_dash: # only flash blue bar if it's the one being used
                if master_clock % 10 < 5: 
                    bar_color = (255, 255, 100)
            pygame.draw.rect(display, bar_color, [time_bar_pos_x + 1, time_bar_pos_y + 1, bar_fill_width, time_bar_h - 2])

            display.blit(item_slot_img, (DISPLAY_SIZE[0] - 20, 4))
            
            # === NEW & CORRECTED: FOCUS DASH METER HUD ===
            focus_bar_x = DISPLAY_SIZE[0] - 25 # X position
            focus_bar_y = 8                     # Y position of the TOP of the bar
            focus_bar_w = 8                     # Width
            focus_bar_h = 16                    # Max Height
            
            # Background/empty part of the bar
            pygame.draw.rect(display, (0, 0, 1), [focus_bar_x, focus_bar_y, focus_bar_w, focus_bar_h])
            
            # Determine the color based on state
            bar_color = (255, 150, 40) # Orange for focus
            if player.is_charging_dash:
                if master_clock % 10 < 5: bar_color = (255, 255, 255) # Flash while charging
            elif player.focus_meter < player.FOCUS_DASH_COST:
                bar_color = (100, 60, 20) # Dull orange when not enough charge

            # Calculate the height of the filled part of the bar
            fill_ratio = player.focus_meter / player.FOCUS_METER_MAX
            current_fill_h = int(focus_bar_h * fill_ratio)
            
            # The bar fills from the BOTTOM UP. We need to calculate its top Y-coordinate.
            fill_y = (focus_bar_y + focus_bar_h) - current_fill_h

            # Draw the filled part
            pygame.draw.rect(display, bar_color, [focus_bar_x + 1, fill_y, focus_bar_w - 2, current_fill_h])

            if combo_multiplier > 1.0:
                combo_text = f"x{combo_multiplier:.1f}"
                scale = 2
                text_width = white_font.width(combo_text, scale=scale)
                pos_x = DISPLAY_SIZE[0] // 2 - text_width // 2
                pos_y = 4
                
                combo_color = (255, 150, 40)
                if master_clock % 20 > 10:
                    combo_color = (255, 255, 255)
                
                combo_font = Font('data/fonts/small_font.png', combo_color)
                
                black_font.render(combo_text, display, (pos_x + 1, pos_y + 1), scale=scale)
                combo_font.render(combo_text, display, (pos_x, pos_y), scale=scale)

                bar_width = (combo_timer / COMBO_DURATION) * 60
                bar_x = DISPLAY_SIZE[0] // 2 - 30
                bar_y = 20
                pygame.draw.rect(display, (0, 0, 1), [bar_x + 1, bar_y + 1, 60, 4])
                pygame.draw.rect(display, (251, 245, 239), [bar_x, bar_y, bar_width, 4])


            display.blit(item_slot_img, (DISPLAY_SIZE[0] - 20, 4))
            
            # === NEW: FOCUS DASH METER HUD ===
            focus_bar_pos_x = DISPLAY_SIZE[0] - 24
            focus_bar_pos_y = 23
            focus_bar_w = 6
            focus_bar_h = -15 # Draw upwards
            
            # Background/empty part of the bar
            pygame.draw.rect(display, (0, 0, 1), [focus_bar_pos_x + 1, focus_bar_pos_y, focus_bar_w-2, focus_bar_h])
            
            # Filled part of the bar
            bar_fill_height = (player.focus_meter / player.FOCUS_METER_MAX) * (focus_bar_h)
            bar_color = (255, 150, 40) # Orange for focus
            if player.is_charging_dash:
                if master_clock % 10 < 5: bar_color = (255, 255, 255) # Flash while charging
            elif player.focus_meter < player.FOCUS_DASH_COST:
                bar_color = (100, 60, 20) # Dull orange when not enough charge
            
            pygame.draw.rect(display, bar_color, [focus_bar_pos_x + 1, focus_bar_pos_y -1, focus_bar_w - 2, bar_fill_height])

            if current_item:
                if (master_clock % 50 < 12) or (abs(master_clock % 50 - 20) < 3):
                    display.blit(item_slot_flash_img, (DISPLAY_SIZE[0] - 20, 4))
                display.blit(item_icons[current_item], (DISPLAY_SIZE[0] - 15, 9))
                if not item_used:
                    if (master_clock % 100 < 80) or (abs(master_clock % 100 - 90) < 3):
                        use_text = 'E/X'
                        text_w = white_font.width(use_text)
                        black_font.render(use_text, display, (DISPLAY_SIZE[0] - text_w - 23, 10))
                        white_font.render(use_text, display, (DISPLAY_SIZE[0] - text_w - 24, 9))
            
            # --- NEW: DRAW ACTIVE PERK ICONS ---
            perk_x_offset = 5
            perk_y_pos = DISPLAY_SIZE[1] - 12 # Position icons at the bottom of the screen
            
            for perk_key in sorted(list(active_perks)): # Sort to keep a consistent order
                if perk_key in perk_icons:
                    icon = perk_icons[perk_key]
                    # Create a simple dark background for contrast
                    icon_bg = pygame.Surface((icon.get_width() + 2, icon.get_height() + 2), pygame.SRCALPHA)
                    icon_bg.fill((0,0,1,150))
                    display.blit(icon_bg, (perk_x_offset - 1, perk_y_pos - 1))

                    display.blit(icon, (perk_x_offset, perk_y_pos))
                    perk_x_offset += icon.get_width() + 4 # Move to the right for the next icon
        else:
            # -- GUI OVERHAUL: STYLIZED GAME OVER SCREEN --

            # UI Style Elements
            PANEL_COLOR = (15, 12, 28, 220)
            BORDER_COLOR = (200, 200, 220, 230)
            TITLE_COLOR = (255, 255, 255)
            HIGHLIGHT_COLOR = (255, 230, 90)
            AFFORD_COLOR = (140, 245, 150)
            CANT_AFFORD_COLOR = (120, 120, 130)
            NEW_BEST_COLOR = (100, 255, 120)

            # Create Font objects for different colors
            highlight_font = Font('data/fonts/small_font.png', HIGHLIGHT_COLOR)
            cant_afford_font = Font('data/fonts/small_font.png', CANT_AFFORD_COLOR)
            afford_font = Font('data/fonts/small_font.png', AFFORD_COLOR)
            new_best_font = Font('data/fonts/small_font.png', NEW_BEST_COLOR)
            title_font = Font('data/fonts/small_font.png', TITLE_COLOR)

            # Main Panel
            panel_rect = pygame.Rect(10, 8, DISPLAY_SIZE[0] - 20, DISPLAY_SIZE[1] - 16)
            panel_surf = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
            panel_surf.fill(PANEL_COLOR)
            display.blit(panel_surf, panel_rect.topleft)
            pygame.draw.rect(display, BORDER_COLOR, panel_rect, 1, border_radius=3)
            
            # Title
            title_text = "GAME OVER"
            text_w = white_font.width(title_text, scale=3)
            black_font.render(title_text, display, (DISPLAY_SIZE[0]//2 - text_w//2 + 2, panel_rect.top + 8 + 2), scale=3)
            title_font.render(title_text, display, (DISPLAY_SIZE[0]//2 - text_w//2, panel_rect.top + 8), scale=3)
            
            # Scores
            line_y1 = panel_rect.top + 30
            pygame.draw.line(display, BORDER_COLOR, (panel_rect.left + 10, line_y1), (panel_rect.right - 10, line_y1), 1)

            score_text = f"SCORE: {coins}"
            hs_text = f"HIGH SCORE: {save_data['high_score']}"
            score_w = white_font.width(score_text, scale=2)
            hs_w = white_font.width(hs_text, scale=2)
            
            black_font.render(score_text, display, (DISPLAY_SIZE[0]/2 - score_w/2 + 1, line_y1 + 7 + 1), scale=2)
            white_font.render(score_text, display, (DISPLAY_SIZE[0]/2 - score_w/2, line_y1 + 7), scale=2)
            
            hs_font = white_font
            if new_high_score and master_clock % 40 < 20:
                hs_font = highlight_font
            
            black_font.render(hs_text, display, (DISPLAY_SIZE[0]/2 - hs_w/2 + 1, line_y1 + 22 + 1), scale=2)
            hs_font.render(hs_text, display, (DISPLAY_SIZE[0]/2 - hs_w/2, line_y1 + 22), scale=2)
            
            if new_high_score and master_clock % 30 < 20:
                new_text = "NEW!"
                new_best_font.render(new_text, display, (DISPLAY_SIZE[0]/2 + hs_w/2 + 5, line_y1 + 22), scale=2)
                
            # Upgrade section
            line_y2 = line_y1 + 42
            pygame.draw.line(display, BORDER_COLOR, (panel_rect.left + 10, line_y2), (panel_rect.right - 10, line_y2), 1)
            
            # Coin banking animation logic
            if end_coin_count != coins:
                if master_clock % 3 == 0:
                    sounds['coin_end'].play()
                    end_coin_count = min(end_coin_count + 1, coins)
            elif not run_coins_banked:
                save_data['banked_coins'] += end_coin_count
                write_save(save_data)
                run_coins_banked = True
                
            if run_coins_banked:
                # Upgrade menu
                upgrade_title_pos = (panel_rect.left + 15, line_y2 + 7)
                black_font.render("Upgrades", display, (upgrade_title_pos[0]+1, upgrade_title_pos[1]+1), scale=2)
                white_font.render("Upgrades", display, upgrade_title_pos, scale=2)
                
                # Bank display
                bank_text = f"Bank: {save_data['banked_coins']}"
                bank_w = white_font.width(bank_text)
                bank_pos = (panel_rect.right - bank_w - 15, line_y2 + 9)
                display.blit(coin_icon, (bank_pos[0] - coin_icon.get_width() - 3, bank_pos[1] - 1))
                black_font.render(bank_text, display, (bank_pos[0]+1, bank_pos[1]+1))
                white_font.render(bank_text, display, bank_pos)

                list_y = line_y2 + 28
                for i, key in enumerate(upgrade_keys):
                    upgrade = UPGRADES[key]
                    level = save_data['upgrades'][key]
                    name_text = f"{upgrade['name']}"
                    level_text = f"Lvl {level}"
                    if level >= upgrade['max_level']: level_text = "MAX"
                    
                    font = white_font
                    if i == upgrade_selection:
                        font = highlight_font
                        pygame.draw.rect(display, (40, 30, 60, 150), [panel_rect.left + 5, list_y-2, panel_rect.width//2-10, 11], 0)
                    
                    font.render(name_text, display, (panel_rect.left + 10, list_y))
                    font.render(level_text, display, (panel_rect.left + 80, list_y))
                    list_y += 13
                    
                # Details for selected upgrade
                detail_x = panel_rect.centerx + 5
                detail_y = line_y2 + 28
                
                sel_key = upgrade_keys[upgrade_selection]
                sel_upgrade = UPGRADES[sel_key]
                sel_level = save_data['upgrades'][sel_key]
                cost = int(sel_upgrade['base_cost'] * (1.5 ** sel_level))
                can_afford = save_data['banked_coins'] >= cost
                
                highlight_font.render(sel_upgrade['name'], display, (detail_x, detail_y))
                white_font.render(sel_upgrade['desc'], display, (detail_x, detail_y + 12))
                
                if sel_level < sel_upgrade['max_level']:
                    cost_font = afford_font if can_afford else cant_afford_font
                    cost_text = f"{cost}"
                    buy_text = "[Buy]"
                    cost_pos_y = detail_y + 26
                    
                    display.blit(coin_icon, (detail_x, cost_pos_y))
                    cost_font.render(cost_text, display, (detail_x + coin_icon.get_width() + 4, cost_pos_y))
                    cost_font.render(buy_text, display, (panel_rect.right - cost_font.width(buy_text) - 15, cost_pos_y))
                else:
                     white_font.render("Max Level Reached", display, (detail_x, detail_y + 26))

            else:
                # Banking coins... message
                banking_text = "Banking coins..."
                if master_clock % 40 > 20: banking_text = "Banking coins.."
                if master_clock % 40 > 30: banking_text = "Banking coins."
                
                text_w = white_font.width(banking_text)
                black_font.render(banking_text, display, (DISPLAY_SIZE[0]//2 - text_w//2 + 1, line_y2 + 25 + 1))
                white_font.render(banking_text, display, (DISPLAY_SIZE[0]//2 - text_w//2, line_y2 + 25))

            # Bottom controls prompt
            prompt_text = "Up/Down: Select  -  Enter: Buy  -  R: Restart"
            prompt_w = white_font.width(prompt_text)
            black_font.render(prompt_text, display, (DISPLAY_SIZE[0]//2 - prompt_w//2 + 1, panel_rect.bottom - 12 + 1))
            white_font.render(prompt_text, display, (DISPLAY_SIZE[0]//2 - prompt_w//2, panel_rect.bottom - 12))
    
    else: # perk_selection_active is True
        display.blit(display_copy, (0, 0)) # Redraw the frozen game screen

        # Dark overlay to focus the view
        overlay = pygame.Surface(DISPLAY_SIZE, pygame.SRCALPHA)
        overlay.fill((10, 5, 20, 200))
        display.blit(overlay, (0, 0))
        
        # --- UI DRAWING CODE ---
        title_text = "CHOOSE A PERK"
        text_w = white_font.width(title_text, scale=2)
        title_pos = (DISPLAY_SIZE[0]//2 - text_w//2, 20)
        black_font.render(title_text, display, (title_pos[0]+1, title_pos[1]+1), scale=2)
        white_font.render(title_text, display, title_pos, scale=2)
        
        panel_y_start = 50
        panel_h = 35
        panel_margin = 5
        
        for i, perk_key in enumerate(perks_to_offer):
            panel_rect = pygame.Rect(40, panel_y_start + i * (panel_h + panel_margin), DISPLAY_SIZE[0] - 80, panel_h)
            
            # Highlight the selected perk
            if i == perk_selection_choice:
                pygame.draw.rect(display, (255, 230, 90), panel_rect, 1) # Highlight border
            else:
                pygame.draw.rect(display, (150, 150, 180), panel_rect, 1) # Normal border
            
            # Draw Perk Info
            perk_name = PERKS[perk_key]['name'].upper()
            perk_desc = PERKS[perk_key]['desc']
            white_font.render(perk_name, display, (panel_rect.x + 8, panel_rect.y + 7))
            black_font.render(perk_desc, display, (panel_rect.x + 9, panel_rect.y + 19))
            white_font.render(perk_desc, display, (panel_rect.x + 8, panel_rect.y + 18))


    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()

        if event.type == KEYDOWN:
            # --- NEW PERK SELECTION INPUT ---
            if perk_selection_active:
                if event.key in [K_DOWN, K_s]:
                    perk_selection_choice = (perk_selection_choice + 1) % len(perks_to_offer)
                if event.key in [K_UP, K_w]:
                    perk_selection_choice = (perk_selection_choice - 1 + len(perks_to_offer)) % len(perks_to_offer)
                if event.key in [K_RETURN, K_e, K_x]:
                    chosen_perk = perks_to_offer[perk_selection_choice]
                    active_perks.add(chosen_perk)
                    perk_selection_active = False
                    if 'upgrade' in sounds:
                        sounds['upgrade'].play()
                    else:
                        sounds['collect_item'].play()
                continue # IMPORTANT: Skip all other game inputs while this screen is up
            
            if event.key == K_ESCAPE:
                pygame.quit()
                sys.exit()

            if not dead:
                # FOCUS DASH KEYDOWN (CHARGE)
                if event.key in [K_c, K_l]:
                    if player.focus_meter >= player.FOCUS_DASH_COST:
                        player.is_charging_dash = True

                # Movement
                if event.key in [K_RIGHT, K_d]:
                    player.right = True
                if event.key in [K_LEFT, K_a]:
                    player.left = True

                # Jumping
                if event.key in [K_UP, K_w, K_SPACE]:
                    player.jump_buffer_timer = 8
                    if player.air_time < 2 or player.coyote_timer > 0 or player.jumps > 0:
                        sounds['jump'].play()
                        player.attempt_jump()

                # Shooting
                if event.key in [K_z, K_k]:
                    if len(projectiles) < 4:
                        sounds['jump'].play()
                        pressed_keys = pygame.key.get_pressed()
                        proj_speed = 4
                        vel = [0, 0]
                        if pressed_keys[K_UP] or pressed_keys[K_w]:
                            vel = [0, -proj_speed]
                            proj_pos = [player.rect.centerx, player.rect.top]
                        elif pressed_keys[K_DOWN] or pressed_keys[K_s]:
                            vel = [0, proj_speed]
                            proj_pos = [player.rect.centerx, player.rect.bottom]
                        elif player.flip[0]:
                            vel = [proj_speed, 0]
                            proj_pos = [player.rect.right, player.rect.centery]
                        else:
                            vel = [-proj_speed, 0]
                            proj_pos = [player.rect.left, player.rect.centery]
                        projectiles.append(Projectile(animation_manager, proj_pos, (6, 2), 'projectile', velocity=vel))

                # Item Usage
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
                                for i_inner in range(15):
                                    angle = random.random() * math.pi * 2
                                    speed = random.random() * 2
                                    sparks.append([
                                        [tile_pos[0] * TILE_SIZE + 8, tile_pos[1] * TILE_SIZE + 8],
                                        [math.cos(angle) * speed, math.sin(angle) * speed],
                                        random.random() * 4 + 2, 0.08, (12, 2, 2), True, 0.1
                                    ])
                                del tiles[tuple(tile_pos)]
                        recalculate_stack_heights()
                    elif current_item == 'freeze':
                        sounds['warp'].play()
                        screen_shake = 10
                        freeze_timer = 360
                        for i in range(40):
                            angle = random.random() * math.pi * 2
                            speed = random.random() * 2
                            sparks.append([player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 4 + 2, 0.08, (150, 200, 255), True, 0.1])
                    if current_item:
                        current_item = None
            # Dead / Game Over Controls
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

            # Restart Key
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
                    projectiles = []
                    freeze_timer = 0
                    game_timer = 0
                    height = 0
                    target_height = 0
                    coins = 0
                    end_coin_count = 0
                    current_item = None
                    master_clock = 0
                    slowing_time = False
                    time_meter = time_meter_max
                    combo_multiplier = 1.0
                    combo_timer = 0
                    run_coins_banked = False
                    screen_shake = 0
                    current_biome_index = 0
                    player_shielded = False
                    new_high_score = False
                    # -- PERK RESETS --
                    active_perks.clear()
                    last_perk_score = 0
                    perk_selection_active = False

                    for i_inner in range(WINDOW_TILE_SIZE[0] - 2):
                        tiles[(i_inner + 1, WINDOW_TILE_SIZE[1] - 1)] = {'type': 'tile', 'data': {}}
                    tiles[(1, WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
                    tiles[(WINDOW_TILE_SIZE[0] - 2, WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
                    stack_heights = [WINDOW_TILE_SIZE[1] - 1 for i_inner in range(WINDOW_TILE_SIZE[0] - 2)]
                    stack_heights[0] -= 1
                    stack_heights[-1] -= 1
                    items = []

        if event.type == KEYUP:
            if not dead:
                # FOCUS DASH KEYUP (RELEASE)
                if event.key in [K_c, K_l]:
                    if player.is_charging_dash:
                        player.is_charging_dash = False
                        player.focus_meter -= player.FOCUS_DASH_COST
                        player.dash_timer = player.DASH_DURATION
                        if 'explosion' in sounds:
                            sounds['explosion'].play()
                        else:
                            # Fallback sound if explosion.wav is missing
                            sounds['block_land'].play() 

                # Movement
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