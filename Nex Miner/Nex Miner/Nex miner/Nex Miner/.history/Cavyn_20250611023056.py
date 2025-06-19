# this is very spaghetti because it was written in under 8 hours

import os
import sys
import random
import math

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
DISPLAY_SIZE = (192, 256)
screen = pygame.display.set_mode((DISPLAY_SIZE[0] * 3, DISPLAY_SIZE[1] * 3), 0, 32)
display = pygame.Surface(DISPLAY_SIZE)
pygame.mouse.set_visible(False)

WINDOW_TILE_SIZE = (int(display.get_width() // 16), int(display.get_height() // 16))

def load_img(path):
    img = pygame.image.load(path).convert()
    img.set_colorkey((0, 0, 0))
    return img

tile_img = load_img('data/images/tile.png')
chest_img = load_img('data/images/chest.png')
ghost_chest_img = load_img('data/images/ghost_chest.png')
opened_chest_img = load_img('data/images/opened_chest.png')
placed_tile_img = load_img('data/images/placed_tile.png')
edge_tile_img = load_img('data/images/edge_tile.png')
coin_icon = load_img('data/images/coin_icon.png')
item_slot_img = load_img('data/images/item_slot.png')
item_slot_flash_img = load_img('data/images/item_slot_flash.png')
border_img = load_img('data/images/border.png')
border_img_light = border_img.copy()
border_img_light.set_alpha(100)
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

def normalize(val, amt):
    if val > amt:
        val -= amt
    elif val < -amt:
        val += amt
    else:
        val = 0
    return val

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
                    physics_on = random.choice([False, False, True])
                    direction = 1
                    if i % 2:
                        direction = -1
                    sparks.append([[player.center[0] + random.random() * 14 - 7, player.center[1]], [direction * (random.random() * 0.05 + 0.05) + (random.random() * 4 - 2) * physics_on, random.random() * 0.05 + random.random() * 2 * physics_on], random.random() * 3 + 3, 0.04 - 0.02 * physics_on, (6, 4, 1), physics_on, 0.05 * physics_on])
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
            self.jumps = self.jumps_max
            self.jumping = False
            self.rotation = 0
            self.velocity[1] = 0
            self.air_time = 0

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

for i in range(WINDOW_TILE_SIZE[0] - 2):
    tiles[(i + 1, WINDOW_TILE_SIZE[1] - 1)] = 'tile'

tiles[(1, WINDOW_TILE_SIZE[1] - 2)] = 'tile'
tiles[(WINDOW_TILE_SIZE[0] - 2, WINDOW_TILE_SIZE[1] - 2)] = 'tile'

stack_heights = [WINDOW_TILE_SIZE[1] - 1 for i in range(WINDOW_TILE_SIZE[0] - 2)]
stack_heights[0] -= 1
stack_heights[-1] -= 1

items = []

pygame.mixer.music.load('data/music.wav')
pygame.mixer.music.play(-1)

while True:
    display.fill((22, 19, 40))

    master_clock += 1

    parallax = random.random()
    for i in range(2):
        bg_particles.append([[random.random() * DISPLAY_SIZE[0], DISPLAY_SIZE[1] - height * parallax], parallax, random.randint(1, 8), random.random() * 1 + 1, random.choice([(0, 0, 0), (22, 19, 40)])])

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

            tile_type = 'tile'
            if random.randint(1, 10) == 1:
                tile_type = 'chest'
            c = random.choice(options)
            last_place = c
            tile_drops.append([(c + 1) * TILE_SIZE, -height - TILE_SIZE, tile_type])


    tile_drop_rects = []
    for i, tile in sorted(enumerate(tile_drops), reverse=True):
        tile[1] += 1.4
        pos = [tile[0] + TILE_SIZE // 2, tile[1] + TILE_SIZE]
        r = pygame.Rect(tile[0], tile[1], TILE_SIZE, TILE_SIZE)
        tile_drop_rects.append(r)

        if r.colliderect(player.rect):
            if not dead:
                sounds['death'].play()
                player.velocity = [1.3, -6]
                for i in range(380):
                    angle = random.random() * math.pi
                    speed = random.random() * 1.5
                    physics_on = random.choice([False, True, True])
                    sparks.append([player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.02, (12, 2, 2), physics_on, 0.1 * physics_on])
            dead = True

        check_pos = (int(pos[0] // TILE_SIZE), int(math.floor(pos[1] / TILE_SIZE)))
        if check_pos in tiles:
            tile_drops.pop(i)
            place_pos = (check_pos[0], check_pos[1] - 1)
            stack_heights[place_pos[0] - 1] = place_pos[1]
            tiles[place_pos] = tile[2]
            sounds['block_land'].play()
            if tiles[check_pos] == 'chest':
                tiles[check_pos] = 'tile'
                sounds['chest_destroy'].play()
                for i in range(100):
                    angle = random.random() * math.pi * 2
                    speed = random.random() * 2.5
                    sparks.append([[place_pos[0] * TILE_SIZE + TILE_SIZE // 2, place_pos[1] * TILE_SIZE + TILE_SIZE // 2], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.09, (12, 8, 2), False, 0.1])
            continue
        if random.randint(1, 4) == 1:
            side = random.choice([1, -1])
            sparks.append([[tile[0] + TILE_SIZE * (side == 1), tile[1]], [random.random() * 0.1 - 0.05, random.random() * 0.5], random.random() * 5 + 3, 0.15, (4, 2, 12), False, 0])
        display.blit(tile_img, (tile[0], tile[1] + height))
        if tile[2] == 'chest':
            display.blit(ghost_chest_img, (tile[0], tile[1] + height - TILE_SIZE))

    tile_rects = []
    for tile in tiles:
        display.blit(tile_img, (TILE_SIZE * tile[0], TILE_SIZE * tile[1] + int(height)))
        if tiles[tile] == 'placed_tile':
            display.blit(placed_tile_img, (TILE_SIZE * tile[0], TILE_SIZE * tile[1] + int(height)))
        if tiles[tile] == 'chest':
            display.blit(chest_img, (TILE_SIZE * tile[0], TILE_SIZE * (tile[1] - 1) + int(height)))
            chest_r = pygame.Rect(TILE_SIZE * tile[0] + 2, TILE_SIZE * (tile[1] - 1) + 6, TILE_SIZE - 4, TILE_SIZE - 6)
            if random.randint(1, 20) == 1:
                sparks.append([[tile[0] * TILE_SIZE + 2 + 12 * random.random(), (tile[1] - 1) * TILE_SIZE + 4 + 8 * random.random()], [0, random.random() * 0.25 - 0.5], random.random() * 4 + 2, 0.023, (12, 8, 2), True, 0.002])
            if chest_r.colliderect(player.rect):
                sounds['chest_open'].play()
                for i in range(50):
                    sparks.append([[tile[0] * TILE_SIZE + 8, (tile[1] - 1) * TILE_SIZE + 8], [random.random() * 2 - 1, random.random() - 2], random.random() * 3 + 3, 0.01, (12, 8, 2), True, 0.05])
                tiles[tile] = 'opened_chest'
                player.jumps += 1
                player.attempt_jump()
                player.velocity[1] = -3.5
                if random.randint(1, 5) < 3:
                    items.append(Item(animation_manager, (tile[0] * TILE_SIZE + 5, (tile[1] - 1) * TILE_SIZE + 5), (6, 6), random.choice(['warp', 'cube', 'jump']), velocity=[random.random() * 5 - 2.5, random.random() * 2 - 5]))
                else:
                    for i in range(random.randint(2, 6)):
                        items.append(Item(animation_manager, (tile[0] * TILE_SIZE + 5, (tile[1] - 1) * TILE_SIZE + 5), (6, 6), 'coin', velocity=[random.random() * 5 - 2.5, random.random() * 2 - 7]))
        elif tiles[tile] == 'opened_chest':
            display.blit(opened_chest_img, (TILE_SIZE * tile[0], TILE_SIZE * (tile[1] - 1) + int(height)))

    base_row = max(tiles, key=lambda x: x[1])[1] - 1
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
                del tiles[(i + 1, base_row + 1)]

    for i in range(WINDOW_TILE_SIZE[1] + 2):
        pos_y = (-height // 16) - 1 + i
        display.blit(edge_tile_img, (0, TILE_SIZE * pos_y + int(height)))
        display.blit(edge_tile_img, (TILE_SIZE * (WINDOW_TILE_SIZE[0] - 1), TILE_SIZE * pos_y + int(height)))

    tile_rects.append(pygame.Rect(0, player.pos[1] - 300, TILE_SIZE, 600))
    tile_rects.append(pygame.Rect(TILE_SIZE * (WINDOW_TILE_SIZE[0] - 1), player.pos[1] - 300, TILE_SIZE, 600))

    for i, item in sorted(enumerate(items), reverse=True):
        lookup_pos = (int(item.center[0] // TILE_SIZE), int(item.center[1] // TILE_SIZE))
        if lookup_pos in tiles:
            items.pop(i)
            continue
        item.update(tile_rects + lookup_nearby(tiles, item.center))
        if item.time > 30:
            if item.rect.colliderect(player.rect):
                if item.type == 'coin':
                    sounds['coin'].play()
                    coins += 1
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

    if not dead:
        player.update(tile_drop_rects + tile_rects + lookup_nearby(tiles, player.center))
    else:
        player.opacity = 80
        player.update([])
        player.rotation -= 16
    player.render(display, (0, -int(height)))

    for i, spark in sorted(enumerate(sparks), reverse=True):
        # pos, vel, size, decay, color, physics, gravity, dead

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
        #if spark[-2]:
        #    spark[1][0] = normalize(spark[1][0], 0.03)
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

    # UI
    if not dead:
        display.blit(coin_icon, (4, 4))
        black_font.render(str(coins), display, (13, 6))
        white_font.render(str(coins), display, (12, 5))

        display.blit(item_slot_img, (DISPLAY_SIZE[0] - 20, 4))
        if current_item:
            if (master_clock % 50 < 12) or (abs(master_clock % 50 - 20) < 3):
                display.blit(item_slot_flash_img, (DISPLAY_SIZE[0] - 20, 4))
            display.blit(item_icons[current_item], (DISPLAY_SIZE[0] - 15, 9))
            if not item_used:
                if (master_clock % 100 < 80) or (abs(master_clock % 100 - 90) < 3):
                    black_font.render('press E/X to use', display, (DISPLAY_SIZE[0] - white_font.width('press E/X to use') - 23, 10))
                    white_font.render('press E/X to use', display, (DISPLAY_SIZE[0] - white_font.width('press E/X to use') - 24, 9))
    else:
        black_font.render('game over', display, (DISPLAY_SIZE[0] // 2 - white_font.width('game over') // 2 + 1, 51))
        white_font.render('game over', display, (DISPLAY_SIZE[0] // 2 - white_font.width('game over') // 2, 50))
        coin_count_width = white_font.width(str(end_coin_count))
        display.blit(coin_icon, (DISPLAY_SIZE[0] // 2 - (coin_count_width + 4 + coin_icon.get_width()) // 2, 63))
        black_font.render(str(end_coin_count), display, ((DISPLAY_SIZE[0] + 5 + coin_icon.get_width()) // 2 - coin_count_width // 2, 65))
        white_font.render(str(end_coin_count), display, ((DISPLAY_SIZE[0] + 4 + coin_icon.get_width()) // 2 - coin_count_width // 2, 64))
        if master_clock % 3 == 0:
            if end_coin_count != coins:
                sounds['coin_end'].play()
            end_coin_count = min(end_coin_count + 1, coins)
        if (master_clock % 100 < 80) or (abs(master_clock % 100 - 90) < 3):
            black_font.render('press R to restart', display, (DISPLAY_SIZE[0] // 2 - white_font.width('press R to restart') // 2 + 1, 79))
            white_font.render('press R to restart', display, (DISPLAY_SIZE[0] // 2 - white_font.width('press R to restart') // 2, 78))

    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        if event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                pygame.quit()
                sys.exit()
            if event.key in [K_RIGHT, K_d]:
                player.right = True
            if event.key in [K_LEFT, K_a]:
                player.left = True
            if event.key in [K_UP, K_w, K_SPACE]:
                if not dead:
                    if player.jumps:
                        sounds['jump'].play()
                    player.attempt_jump()
            if event.key in [K_e, K_x]:
                if not dead:
                    if current_item:
                        item_used = True
                    if current_item == 'warp':
                        sounds['warp'].play()
                        max_point = min(enumerate(stack_heights), key=lambda x: x[1])
                        for i in range(60):
                            angle = random.random() * math.pi * 2
                            speed = random.random() * 3
                            physics_on = random.choice([False, True])
                            sparks.append([player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.02, (12, 8, 2), physics_on, 0.1 * physics_on])
                        player.pos[0] = (max_point[0] + 1) * TILE_SIZE + 4
                        player.pos[1] = (max_point[1] - 1) * TILE_SIZE
                        for i in range(60):
                            angle = random.random() * math.pi * 2
                            speed = random.random() * 1.75
                            physics_on = random.choice([False, True, True])
                            sparks.append([player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.02, (12, 8, 2), physics_on, 0.1 * physics_on])
                    if current_item == 'jump':
                        sounds['super_jump'].play()
                        player.jumps += 1
                        player.attempt_jump()
                        player.velocity[1] = -8
                        for i in range(60):
                            angle = random.random() * math.pi / 2 + math.pi / 4
                            if random.randint(1, 5) == 1:
                                angle = -math.pi / 2
                            speed = random.random() * 3
                            physics_on = random.choice([False, True])
                            sparks.append([player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.02, (12, 8, 2), physics_on, 0.1 * physics_on])
                    if current_item == 'cube':
                        sounds['block_land'].play()
                        place_pos = (int(player.center[0] // TILE_SIZE), int(player.pos[1] // TILE_SIZE) + 1)
                        stack_heights[place_pos[0] - 1] = place_pos[1]
                        for i in range(place_pos[1], base_row + 2):
                            tiles[(place_pos[0], i)] = 'placed_tile'
                            for j in range(8):
                                sparks.append([[place_pos[0] * TILE_SIZE + TILE_SIZE, i * TILE_SIZE + j * 2], [random.random() * 0.5, random.random() * 0.5 - 0.25], random.random() * 4 + 4, 0.02, (12, 8, 2), False, 0])
                                sparks.append([[place_pos[0] * TILE_SIZE, i * TILE_SIZE + j * 2], [-random.random() * 0.5, random.random() * 0.5 - 0.25], random.random() * 4 + 4, 0.02, (12, 8, 2), False, 0])
                    current_item = None
            if event.key == K_r:
                if dead:
                    player = Player(animation_manager, (DISPLAY_SIZE[0] // 2 - 5, -20), (8, 16), 'player')
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

                    for i in range(WINDOW_TILE_SIZE[0] - 2):
                        tiles[(i + 1, WINDOW_TILE_SIZE[1] - 1)] = 'tile'

                    tiles[(1, WINDOW_TILE_SIZE[1] - 2)] = 'tile'
                    tiles[(WINDOW_TILE_SIZE[0] - 2, WINDOW_TILE_SIZE[1] - 2)] = 'tile'

                    stack_heights = [WINDOW_TILE_SIZE[1] - 1 for i in range(WINDOW_TILE_SIZE[0] - 2)]
                    stack_heights[0] -= 1
                    stack_heights[-1] -= 1

                    items = []

        if event.type == KEYUP:
            if event.key in [K_RIGHT, K_d]:
                player.right = False
            if event.key in [K_LEFT, K_a]:
                player.left = False

    screen.blit(pygame.transform.scale(display, screen.get_size()), (0, 0))
    pygame.display.update()
    clock.tick(60)
