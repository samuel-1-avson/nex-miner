# Cavyn Source/data/scripts/gameplay_state.py

import pygame, sys, random, math, json
from pygame.locals import *

from .state import State
from .entity import Entity
from .text import Font

# =========================================================================
# === UTILITY & HELPER FUNCTIONS FOR THIS STATE ===
# =========================================================================

GLOW_CACHE = {}
def glow_img(size, color):
    if (size, color) not in GLOW_CACHE:
        surf = pygame.Surface((size * 2 + 2, size * 2 + 2))
        pygame.draw.circle(surf, color, (surf.get_width() // 2, surf.get_height() // 2), size)
        surf.set_colorkey((0, 0, 0))
        GLOW_CACHE[(size, color)] = surf
    return GLOW_CACHE[(size, color)]

def normalize(val, amt):
    if val > amt: val -= amt
    elif val < -amt: val += amt
    else: val = 0
    return val

def load_img(path):
    img = pygame.image.load(path).convert()
    img.set_colorkey((0, 0, 0))
    return img

# =========================================================================
# === GAME-SPECIFIC ENTITY CLASSES ===
# =========================================================================

class Item(Entity):
    def __init__(self, assets, pos, size, type, state, velocity=[0, 0]):
        super().__init__(assets, pos, size, type)
        self.state = state
        self.velocity = velocity
        self.time = 0

    def update(self, tiles, time_scale=1.0):
        self.time += 1 * time_scale
        self.velocity[1] = min(self.velocity[1] + 0.2, 3)
        self.velocity[0] = normalize(self.velocity[0], 0.05)
        self.move(self.velocity, tiles, time_scale)

class Player(Entity):
    def __init__(self, assets, pos, size, type, state):
        super().__init__(assets, pos, size, type)
        self.state = state
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
        self.dash_timer = 0
        self.DASH_SPEED = 8
        self.DASH_DURATION = 8
        self.focus_meter = 100
        self.FOCUS_METER_MAX = 100
        self.is_charging_dash = False
        self.FOCUS_DASH_COST = 50
        self.FOCUS_RECHARGE_RATE = 0.4
        self.wall_contact_timer = 0

    def attempt_jump(self):
        jump_velocity = -5
        if 'acrobat' in self.state.active_perks and self.wall_contact_timer > 0:
            jump_velocity = -6.5
            self.wall_contact_timer = 0

        if self.jumps > 0 or self.coyote_timer > 0:
            if self.jumps == self.jumps_max or self.coyote_timer > 0:
                self.velocity[1] = jump_velocity
            else:
                self.velocity[1] = -4
                for i in range(24):
                    physics = random.choice([False, False, True])
                    direction = 1 if i % 2 else -1
                    self.state.sparks.append([[self.center[0] + random.uniform(-7, 7), self.center[1]], [direction * (random.uniform(0.05, 0.1)) + (random.uniform(-2, 2)) * physics, random.uniform(0.05, 0.1) + random.uniform(0, 2) * physics], random.uniform(3, 6), 0.04 - 0.02 * physics, (6, 4, 1), physics, 0.05 * physics])

            if self.coyote_timer <= 0: self.jumps -= 1
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
            self.state.sparks.append([[self.center[0] - direction * 6, self.center[1] + random.uniform(-3, 3)], [-direction * random.uniform(1, 2), random.uniform(-0.5, 0.5)], random.uniform(2, 5), 0.15, (200, 220, 255), False, 0])
        else:
            target_vel_x = self.speed if self.right else -self.speed if self.left else 0
            self.velocity[0] += (target_vel_x - self.velocity[0]) * 0.3
            if abs(self.velocity[0]) < 0.1: self.velocity[0] = 0

        if self.dash_timer > 0:
            self.velocity[1] = 0
        else:
            gravity = 0.24 if 'feather_fall' in self.state.active_perks else 0.3
            self.velocity[1] = min(self.velocity[1] + gravity, 4)

        if not self.state.dead and self.dash_timer <= 0:
            if self.velocity[0] > 0.1: self.flip[0] = True
            if self.velocity[0] < -0.1: self.flip[0] = False

        if self.jumping:
            self.jump_rot += 16 * time_scale
            if self.jump_rot >= 360: self.jump_rot = 0; self.jumping = False
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
                self.state.game.sounds['jump'].play()
                self.attempt_jump()
        elif was_on_ground:
            self.coyote_timer = 6
        return collisions

class Projectile(Entity):
    def __init__(self, assets, pos, size, type, state, velocity=[0, 0]):
        super().__init__(assets, pos, size, type)
        self.state = state
        self.velocity = velocity
        self.health = 2 if 'technician' in self.state.active_perks else 1

    def update(self, time_scale=1.0):
        super().update(1/60, time_scale)
        self.pos[0] += self.velocity[0] * time_scale
        self.pos[1] += self.velocity[1] * time_scale

# =========================================================================
# === MAIN GAMEPLAY STATE CLASS ===
# =========================================================================

class GameplayState(State):
    def __init__(self, game):
        super().__init__(game)
        self.load_state_assets()
        self.reset()

    def load_state_assets(self):
        """Loads assets specific to the gameplay state."""
        self.tile_img = load_img('data/images/tile.png')
        self.placed_tile_img = load_img('data/images/placed_tile.png')
        self.chest_img = load_img('data/images/chest.png')
        self.ghost_chest_img = load_img('data/images/ghost_chest.png')
        self.opened_chest_img = load_img('data/images/opened_chest.png')
        self.edge_tile_img = load_img('data/images/edge_tile.png')
        self.fragile_tile_img = load_img('data/images/fragile_tile.png')
        self.bounce_tile_img = load_img('data/images/bounce_tile.png')
        self.spike_tile_img = load_img('data/images/spike_tile.png')
        self.magnetic_tile_img = load_img('data/images/magnetic_tile.png')
        self.sticky_tile_img = load_img('data/images/sticky_tile.png')
        self.motherlode_tile_img = load_img('data/images/motherlode_tile.png')
        self.unstable_tile_img = load_img('data/images/unstable_tile.png')
        self.coin_icon = load_img('data/images/coin_icon.png')
        self.item_slot_img = load_img('data/images/item_slot.png')
        self.item_slot_flash_img = load_img('data/images/item_slot_flash.png')
        self.border_img = load_img('data/images/border.png')
        self.border_img_light = self.border_img.copy()
        self.border_img_light.set_alpha(100)
        self.tile_top_img = load_img('data/images/tile_top.png')
        self.greed_tile_img = load_img('data/images/greed_tile.png')
        self.shield_aura_img = load_img('data/images/shield_aura.png')
        self.shield_aura_img.set_alpha(150)
        self.item_icons = {
            'cube': load_img('data/images/cube_icon.png'), 'warp': load_img('data/images/warp_icon.png'),
            'jump': load_img('data/images/jump_icon.png'), 'bomb': load_img('data/images/bomb_icon.png'),
            'freeze': load_img('data/images/freeze_icon.png'), 'shield': load_img('data/images/shield_icon.png'),
        }
        self.perk_icons = {}
        for perk_name in self.game.PERKS.keys():
            try: self.perk_icons[perk_name] = load_img(f'data/images/perk_icons/{perk_name}.png')
            except pygame.error: print(f"Warning: Could not load icon for perk '{perk_name}'.")

    def reset(self):
        """Resets the game to its initial state for a new run."""
        self.player = Player(self.game.animation_manager, (self.game.DISPLAY_SIZE[0] // 2 - 5, -20), (8, 16), 'player', self)
        self.player.jumps_max = 2 + self.game.save_data['upgrades']['jumps']
        self.player.speed = 1.4 + self.game.save_data['upgrades']['speed'] * 0.08
        self.player.jumps = self.player.jumps_max

        self.dead, self.tiles, self.tile_drops, self.sparks, self.projectiles, self.items = False, {}, [], [], [], []
        self.freeze_timer, self.game_timer, self.master_clock = 0, 0, 0
        self.height, self.target_height = 0, 0
        self.coins, self.end_coin_count = 0, 0
        self.current_item, self.item_used = None, False
        self.time_meter, self.time_scale, self.slowing_time = self.game.time_meter_max, 1.0, False
        self.combo_multiplier, self.combo_timer = 1.0, 0
        self.run_coins_banked, self.upgrade_selection = False, 0
        self.screen_shake, self.player_shielded, self.new_high_score = 0, False, False
        self.active_perks, self.last_perk_score, self.perk_selection_active = set(), 0, False
        self.perk_selection_choice, self.perks_to_offer = 0, []
        self.current_biome_index, self.last_place = 0, 0

        self.game.load_biome_bgs(self.game.BIOMES[self.current_biome_index])

        for i in range(self.game.WINDOW_TILE_SIZE[0] - 2):
            self.tiles[(i + 1, self.game.WINDOW_TILE_SIZE[1] - 1)] = {'type': 'tile', 'data': {}}
        self.tiles[(1, self.game.WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
        self.tiles[(self.game.WINDOW_TILE_SIZE[0] - 2, self.game.WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
        self.recalculate_stack_heights()

    # --- MAIN LOOPS ---
    def handle_events(self, events):
        super().handle_events(events)
        for event in events:
            if event.type == KEYDOWN:
                if self.perk_selection_active:
                    self.handle_perk_selection_input(event.key)
                    continue

                if not self.dead:
                    if event.key in [K_c, K_l] and self.player.focus_meter >= self.player.FOCUS_DASH_COST: self.player.is_charging_dash = True
                    if event.key in [K_RIGHT, K_d]: self.player.right = True
                    if event.key in [K_LEFT, K_a]: self.player.left = True
                    if event.key in [K_UP, K_w, K_SPACE]:
                        self.player.jump_buffer_timer = 8
                        if self.player.air_time < 2 or self.player.coyote_timer > 0 or self.player.jumps > 0:
                            self.game.sounds['jump'].play(); self.player.attempt_jump()
                    if event.key in [K_z, K_k] and len(self.projectiles) < 4: self.fire_projectile(pygame.key.get_pressed())
                    if event.key in [K_e, K_x] and self.current_item: self.use_item()
                else: self.handle_game_over_input(event.key)

                if event.key == K_r and self.dead: self.reset()

            if event.type == KEYUP and not self.dead:
                if event.key in [K_c, K_l] and self.player.is_charging_dash:
                    self.player.is_charging_dash = False; self.player.focus_meter -= self.player.FOCUS_DASH_COST
                    self.player.dash_timer = self.player.DASH_DURATION
                    self.game.sounds['explosion'].play() if 'explosion' in self.game.sounds else self.game.sounds['block_land'].play()
                if event.key in [K_RIGHT, K_d]: self.player.right = False
                if event.key in [K_LEFT, K_a]: self.player.left = False

    def update(self):
        self.display_copy = self.game.display.copy()
        if self.perk_selection_active: return

        self.master_clock += 1
        self.update_time_scale()
        if not self.dead:
            self.update_biome()
            self.update_combo_meter()
            self.update_perk_offering()
            self.update_tile_spawning()

        if self.screen_shake > 0: self.screen_shake -= 0.5 * self.time_scale
        if self.freeze_timer > 0: self.freeze_timer -= 1 * self.time_scale

        self.update_falling_tiles()
        self.update_placed_tiles()
        self.update_items()
        self.update_projectiles()
        self.update_player()
        self.update_sparks()
        self.update_scrolling()

    def render(self, surface):
        if self.perk_selection_active:
            self.render_perk_selection_ui(surface)
            return

        self.render_background(surface)
        if self.freeze_timer > 0:
            freeze_overlay = pygame.Surface(self.game.DISPLAY_SIZE, pygame.SRCALPHA)
            alpha = 60 + math.sin(self.master_clock / 5) * 10
            freeze_overlay.fill((170, 200, 255, alpha)); surface.blit(freeze_overlay, (0, 0))

        self.render_placed_tiles(surface)
        self.render_falling_tiles(surface)
        self.render_items(surface)
        self.render_projectiles(surface)
        if self.player_shielded and not self.dead: self.render_shield_aura(surface)
        self.player.render(surface, (0, -int(self.height)))
        self.render_sparks(surface)
        self.render_borders(surface)

        if not self.dead: self.render_hud(surface)
        else: self.render_game_over_ui(surface)

    # --- HELPER & LOGIC METHODS ---
    def recalculate_stack_heights(self):
        new_heights = [self.game.WINDOW_TILE_SIZE[1] for i in range(self.game.WINDOW_TILE_SIZE[0] - 2)]
        for tile_x, tile_y in self.tiles:
            if 1 <= tile_x < self.game.WINDOW_TILE_SIZE[0] - 1:
                new_heights[tile_x - 1] = min(new_heights[tile_x - 1], tile_y)
        self.stack_heights = new_heights

    def handle_death(self):
        if self.player_shielded:
            self.player_shielded = False
            self.game.sounds['explosion'].play() if 'explosion' in self.game.sounds else self.game.sounds['super_jump'].play()
            self.screen_shake = 15
            for i in range(60):
                angle, speed = random.random() * math.pi * 2, random.random() * 2
                self.sparks.append([self.player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.uniform(2, 4), 0.05, (170, 200, 255), True, 0.05])
            return

        if not self.dead:
            self.game.sounds['death'].play(); self.screen_shake = 20
            if self.coins > self.game.save_data['high_score']:
                self.game.save_data['high_score'] = self.coins
                self.new_high_score = True
                self.game.write_save(self.game.save_data)
            self.dead, self.run_coins_banked, self.upgrade_selection = True, False, 0
            self.player.velocity = [1.3, -6]
            for i in range(380):
                angle, speed = random.random() * math.pi, random.random() * 1.5; physics = random.choice([False, True, True])
                self.sparks.append([self.player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.02, (12, 2, 2), physics, 0.1 * physics])

    def update_biome(self):
        next_biome_index = self.current_biome_index
        if self.current_biome_index + 1 < len(self.game.BIOMES) and self.coins >= self.game.BIOMES[self.current_biome_index + 1]['score_req']:
            next_biome_index += 1
        if next_biome_index != self.current_biome_index:
            self.current_biome_index = next_biome_index
            self.game.load_biome_bgs(self.game.BIOMES[self.current_biome_index])
            self.game.sounds['warp'].play(); self.screen_shake = 15

    def update_time_scale(self):
        self.time_scale = 1.0
        if self.dead: self.slowing_time = False; return
        is_slowing_now = (pygame.key.get_pressed()[K_LSHIFT] and self.time_meter > 0) or self.player.is_charging_dash
        if is_slowing_now and not self.slowing_time: self.game.sounds['time_slow_start'].play()
        elif not is_slowing_now and self.slowing_time: self.game.sounds['time_slow_end'].play()
        self.slowing_time = is_slowing_now

        if self.slowing_time:
            self.time_scale = 0.4
            if self.player.is_charging_dash:
                self.player.focus_meter = max(0, self.player.focus_meter - 1.5)
                if self.player.focus_meter <= 0: self.player.is_charging_dash = False
            elif pygame.key.get_pressed()[K_LSHIFT]:
                self.time_meter = max(0, self.time_meter - 0.75)
                if self.time_meter <= 0: self.game.sounds['time_empty'].play()
        else: self.time_meter = min(self.game.time_meter_max, self.time_meter + 0.2)

    def update_combo_meter(self):
        if self.combo_timer > 0:
            self.combo_timer -= (2 if 'glass_cannon' in self.active_perks else 1) * self.time_scale
            if self.combo_timer <= 0 and self.combo_multiplier > 1.0:
                self.combo_timer = 0
                if 'combo_end' in self.game.sounds: self.game.sounds['combo_end'].play()
                for i in range(20):
                    angle, speed = random.random() * math.pi * 2, random.random() * 1.5
                    self.sparks.append([[self.game.DISPLAY_SIZE[0] // 2, 10], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 2 + 1, 0.05, (251, 245, 239), True, 0.05])
                self.combo_multiplier = 1.0

    def update_perk_offering(self):
        score_interval = 75
        if self.coins > 0 and self.coins // score_interval > self.last_perk_score // score_interval:
            self.last_perk_score = self.coins
            available_perks = [p for p in self.game.PERKS.keys() if p not in self.active_perks]
            if available_perks:
                self.perk_selection_active, self.perk_selection_choice = True, 0
                self.perks_to_offer = random.sample(available_perks, k=min(3, len(available_perks)))
                self.game.sounds['warp'].play()

    def update_tile_spawning(self):
        if self.master_clock < 180: return
        self.game_timer += self.time_scale
        if self.game_timer > 10 + 25 * (20000 - min(20000, self.master_clock)) / 20000:
            self.game_timer = 0; options = []
            for i, stack in enumerate(self.stack_heights):
                if i != self.last_place:
                    for _ in range(int((stack - min(self.stack_heights)) ** (2.2 - min(20000, self.master_clock) / 10000)) + 1): options.append(i)
            
            biome = self.game.BIOMES[self.current_biome_index]; tile_type = 'tile'
            elite = random.randint(1, 100)
            if elite <= 2: tile_type = 'motherlode'
            elif elite <= 5: tile_type = 'unstable'
            else:
                roll = random.randint(1, 30)
                if roll == 1: tile_type = 'chest'
                elif roll < 4: tile_type = 'fragile'
                elif roll < 6: tile_type = 'bounce'
                elif roll == 7: tile_type = 'spike'
                for special, chance in biome['special_spawn_rate'].items():
                    if roll == chance: tile_type = special
            if tile_type not in biome['available_tiles']: tile_type = 'tile'

            c = random.choice(options); self.last_place = c
            self.tile_drops.append([(c + 1) * self.game.TILE_SIZE, -self.height - self.game.TILE_SIZE, tile_type])
            
    def update_falling_tiles(self):
        tile_drop_rects = []
        for i, tile in sorted(enumerate(self.tile_drops), reverse=True):
            if self.freeze_timer <= 0:
                tile[1] += (1.8 if tile[2] == 'motherlode' else 1.4) * self.time_scale
            
            r = pygame.Rect(tile[0], tile[1], self.game.TILE_SIZE, self.game.TILE_SIZE); tile_drop_rects.append(r)
            graze_r = self.player.rect.copy(); graze_r.inflate_ip(8, 8)
            if graze_r.colliderect(r) and not self.player.rect.colliderect(r):
                self.combo_multiplier += 0.2 * (2 if 'glass_cannon' in self.active_perks else 1)
                self.combo_timer = self.game.COMBO_DURATION
            
            if self.player.dash_timer > 0 and r.colliderect(self.player.rect):
                self.tile_drops.pop(i); self.coins += 2
                self.combo_multiplier += 0.3 * (2 if 'glass_cannon' in self.active_perks else 1)
                self.combo_timer = self.game.COMBO_DURATION
                self.game.sounds['explosion'].play() if 'explosion' in self.game.sounds else self.game.sounds['block_land'].play()
                self.screen_shake = max(self.screen_shake, 6)
                for k in range(20):
                    angle, speed = random.random() * math.pi * 2, random.random() * 2.5
                    self.sparks.append([[r.centerx, r.centery], [math.cos(angle) * speed, math.sin(angle) * speed], random.uniform(2, 5), 0.08, (251, 245, 239), True, 0.1])
                
                if 'overcharge' in self.active_perks:
                    to_remove = []
                    for k_inner, other_tile in enumerate(self.tile_drops):
                        if r.colliderect(pygame.Rect(other_tile[0], other_tile[1], self.game.TILE_SIZE, self.game.TILE_SIZE).inflate(self.game.TILE_SIZE, self.game.TILE_SIZE)):
                            to_remove.append(k_inner)
                    for k_rem in sorted(to_remove, reverse=True):
                         other_r = pygame.Rect(self.tile_drops[k_rem][0], self.tile_drops[k_rem][1], self.game.TILE_SIZE, self.game.TILE_SIZE)
                         for p__ in range(15):
                              angle, speed = random.random() * math.pi * 2, random.random() * 2
                              self.sparks.append([[other_r.centerx, other_r.centery], [math.cos(angle) * speed, math.sin(angle) * speed], random.uniform(1, 4), 0.1, (255,100,80), True, 0.1])
                         self.tile_drops.pop(k_rem); self.coins += 1
                continue
                
            if 'glass_cannon' in self.active_perks and r.colliderect(self.player.rect): temp_shield = self.player_shielded; self.player_shielded = False; self.handle_death(); self.player_shielded = temp_shield 
            elif r.colliderect(self.player.rect): self.handle_death()

            check_pos = (int((r.centerx) // self.game.TILE_SIZE), int(math.floor(r.bottom / self.game.TILE_SIZE)))
            if check_pos in self.tiles:
                self.tile_drops.pop(i)
                place_pos = (check_pos[0], check_pos[1] - 1)
                if tile[2] == 'motherlode':
                    self.game.sounds['chest_open'].play(); self.screen_shake = max(self.screen_shake, 8)
                    coins_mult = 2 if 'greedy' in self.active_perks else 1
                    for k in range(random.randint(8, 15) * coins_mult): self.items.append(Item(self.game.animation_manager, (place_pos[0] * self.game.TILE_SIZE + 5, (place_pos[1] -1) * self.game.TILE_SIZE + 5), (6, 6), 'coin', self, velocity=[random.random() * 6 - 3, random.random() * 2 - 8]))
                    self.tiles[place_pos] = {'type': 'chest', 'data': {}}
                elif self.tiles[check_pos]['type'] == 'greed':
                    self.game.sounds['chest_open'].play(); del self.tiles[check_pos]
                    coins_mult = 2 if 'greedy' in self.active_perks else 1
                    for k in range(random.randint(5, 10) * coins_mult): self.items.append(Item(self.game.animation_manager, (place_pos[0] * self.game.TILE_SIZE + 5, place_pos[1] * self.game.TILE_SIZE + 5), (6, 6), 'coin', self, velocity=[random.random() * 5 - 2.5, random.random() * 2 - 7]))
                else:
                    self.tiles[place_pos] = {'type': tile[2], 'data': {}}
                    if tile[2] == 'unstable': self.tiles[place_pos]['data']['timer'] = 180
                    self.game.sounds['block_land'].play()
                    if abs(self.player.pos[0] - place_pos[0] * self.game.TILE_SIZE) < 40: self.screen_shake = max(self.screen_shake, 4)
                    if self.tiles[check_pos]['type'] == 'chest':
                        self.tiles[check_pos]['type'] = 'tile'
                        if 'chest_destroy' in self.game.sounds: self.game.sounds['chest_destroy'].play()
                        for _ in range(100):
                            angle, speed = random.random() * math.pi * 2, random.random() * 2.5
                            self.sparks.append([[place_pos[0] * self.game.TILE_SIZE + self.game.TILE_SIZE // 2, place_pos[1] * self.game.TILE_SIZE + self.game.TILE_SIZE // 2], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.09, (12, 8, 2), False, 0.1])
                self.recalculate_stack_heights()
                continue
        self.tile_drop_rects = tile_drop_rects
        
    def update_placed_tiles(self):
        to_remove = []
        for tile_pos, tile_data in self.tiles.items():
            if tile_data['type'] == 'unstable' and 'timer' in tile_data['data']:
                tile_data['data']['timer'] -= 1 * self.time_scale
                if random.randint(1, 8) == 1: self.sparks.append([[tile_pos[0] * self.game.TILE_SIZE + 8, tile_pos[1] * self.game.TILE_SIZE + 8], [random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5)], random.uniform(2, 4), 0.1, (255, 100, 20), False, 0])
                if tile_data['data']['timer'] <= 0:
                    if tile_pos not in to_remove: to_remove.append(tile_pos)
                    if 'explosion' in self.game.sounds: self.game.sounds['explosion'].play()
                    self.screen_shake = max(self.screen_shake, 12)
                    for y_offset in range(-1, 2):
                        for x_offset in range(-1, 2):
                            neighbor_pos = (tile_pos[0] + x_offset, tile_pos[1] + y_offset)
                            if neighbor_pos in self.tiles and neighbor_pos not in to_remove: to_remove.append(neighbor_pos)
                    for _ in range(40):
                        angle, speed = random.random() * math.pi * 2, random.random() * 2.5
                        self.sparks.append([[tile_pos[0] * self.game.TILE_SIZE + 8, tile_pos[1] * self.game.TILE_SIZE + 8], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 5 + 3, 0.08, (255, 120, 40), True, 0.1])
            if tile_data['type'] == 'fragile' and 'timer' in tile_data['data']:
                tile_data['data']['timer'] -= 1 * self.time_scale
                if random.randint(1, 10) == 1: self.sparks.append([[tile_pos[0] * self.game.TILE_SIZE + random.random() * 16, tile_pos[1] * self.game.TILE_SIZE + 14], [random.random() * 0.5 - 0.25, random.random() * 0.5], random.random() * 2 + 1, 0.08, (6, 4, 1), True, 0.05])
                if tile_data['data']['timer'] <= 0:
                    if tile_pos not in to_remove: to_remove.append(tile_pos)
                    for _ in range(20):
                        angle, speed = random.random() * math.pi * 2, random.random() * 1.5
                        self.sparks.append([[tile_pos[0] * self.game.TILE_SIZE + 8, tile_pos[1] * self.game.TILE_SIZE + 8], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 4 + 2, 0.05, (6, 4, 1), True, 0.1])
        if to_remove:
            for p in to_remove:
                if p in self.tiles: del self.tiles[p]
            self.recalculate_stack_heights()

    def update_items(self):
        edge_rects = [pygame.Rect(0, 0, self.game.TILE_SIZE, self.game.DISPLAY_SIZE[1]), pygame.Rect(self.game.DISPLAY_SIZE[0] - self.game.TILE_SIZE, 0, self.game.TILE_SIZE, self.game.DISPLAY_SIZE[1])]
        for i, item in sorted(enumerate(self.items), reverse=True):
            if (int(item.center[0] // self.game.TILE_SIZE), int(item.center[1] // self.game.TILE_SIZE)) in self.tiles:
                self.items.pop(i); continue
            item.update(edge_rects + self.lookup_nearby(item.center), self.time_scale)

            if item.type == 'coin' and not self.dead:
                magnet_lvl = self.game.save_data['upgrades']['coin_magnet']
                if magnet_lvl > 0:
                    dist_x, dist_y = self.player.center[0] - item.center[0], self.player.center[1] - item.center[1]
                    dist = math.sqrt(dist_x**2 + dist_y**2)
                    if dist < 20 + magnet_lvl * 10:
                        pull_strength = 0.05 + magnet_lvl * 0.05
                        item.velocity[0] += (dist_x / dist) * pull_strength * self.time_scale
                        item.velocity[1] += (dist_y / dist) * pull_strength * self.time_scale
            
            if item.time > 30 and item.rect.colliderect(self.player.rect):
                if item.type == 'coin':
                    self.game.sounds['coin'].play()
                    self.coins += int(1 * self.combo_multiplier)
                    self.combo_multiplier += 0.1 * (2 if 'glass_cannon' in self.active_perks else 1)
                    self.combo_timer = self.game.COMBO_DURATION
                    for _ in range(25):
                        angle, speed, physics = random.random() * math.pi * 2, random.random() * 0.4, random.choice([False, False, False, False, True])
                        self.sparks.append([item.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.02, (12, 8, 2), physics, 0.1 * physics])
                else:
                    self.game.sounds['collect_item'].play()
                    for _ in range(50): self.sparks.append([item.center.copy(), [random.random() * 0.3 - 0.15, random.random() * 6 - 3], random.random() * 4 + 3, 0.01, (12, 8, 2), False, 0])
                    if item.type == 'shield': self.player_shielded = True; (self.game.sounds['upgrade'] if 'upgrade' in self.game.sounds else self.game.sounds['collect_item']).play()
                    else: self.current_item = item.type
                self.items.pop(i)

    def update_projectiles(self):
        for i, p in sorted(enumerate(self.projectiles), reverse=True):
            p.update(self.time_scale)
            if not p.rect.colliderect(self.game.display.get_rect()): self.projectiles.pop(i); continue
            
            hit_tile = False
            for j, tile_drop in sorted(enumerate(self.tile_drops), reverse=True):
                r = pygame.Rect(tile_drop[0], tile_drop[1], self.game.TILE_SIZE, self.game.TILE_SIZE)
                if p.rect.colliderect(r):
                    self.game.sounds['block_land'].play(); p.health -= 1
                    for _ in range(15):
                        angle, speed = random.random() * math.pi * 2, random.random() * 2
                        self.sparks.append([[tile_drop[0] + 8, tile_drop[1] + 8], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 2, 0.08, (251, 245, 239), True, 0.1])
                    self.tile_drops.pop(j)
                    if p.health <= 0:
                        self.projectiles.pop(i); hit_tile = True
                    self.coins += 1; self.combo_multiplier += 0.05; self.combo_timer = self.game.COMBO_DURATION; break
            if hit_tile: continue

    def update_player(self):
        if not self.dead:
            for tile_pos, tile_data in self.tiles.items():
                if tile_data['type'] == 'magnetic' and 0 < tile_pos[1] * self.game.TILE_SIZE + self.height < self.game.DISPLAY_SIZE[1]:
                    self.player.velocity[0] += max(-0.25, min(0.25, (tile_pos[0] * self.game.TILE_SIZE + self.game.TILE_SIZE // 2 - self.player.center[0]) / 80)) * self.time_scale

            tile_rects = [pygame.Rect(p[0] * self.game.TILE_SIZE, p[1] * self.game.TILE_SIZE, self.game.TILE_SIZE, self.game.TILE_SIZE) for p in self.tiles]
            edge_rects = [pygame.Rect(0, self.player.pos[1] - 300, self.game.TILE_SIZE, 600), pygame.Rect(self.game.TILE_SIZE * (self.game.WINDOW_TILE_SIZE[0] - 1), self.player.pos[1] - 300, self.game.TILE_SIZE, 600)]
            collisions = self.player.update(self.tile_drop_rects + edge_rects + tile_rects, self.time_scale)

            if not collisions['bottom']:
                for side in ['left', 'right']:
                    tile_pos_side = ((self.player.rect.left - 2 if side == 'left' else self.player.rect.right + 2) // self.game.TILE_SIZE, self.player.rect.centery // self.game.TILE_SIZE)
                    if tile_pos_side in self.tiles and self.tiles[tile_pos_side]['type'] == 'sticky':
                        self.player.velocity[1] = min(self.player.velocity[1], 1.0)

            if collisions['bottom']:
                tile_pos_below = (self.player.rect.midbottom[0] // self.game.TILE_SIZE, self.player.rect.midbottom[1] // self.game.TILE_SIZE)
                if tile_pos_below in self.tiles:
                    tile_type = self.tiles[tile_pos_below]['type']
                    if tile_type == 'fragile' and 'timer' not in self.tiles[tile_pos_below]['data']: self.game.sounds['block_land'].play(); self.tiles[tile_pos_below]['data']['timer'] = 90
                    elif tile_type == 'bounce':
                        self.player.velocity[1] = -9; self.player.jumps = self.player.jumps_max
                        self.game.sounds['super_jump'].play(); self.screen_shake = 10
                        self.combo_multiplier += 0.5; self.combo_timer = self.game.COMBO_DURATION
                        for _ in range(40):
                            angle, speed = random.random() * math.pi - math.pi, random.random() * 2
                            self.sparks.append([[self.player.rect.centerx, self.player.rect.bottom], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 2, 0.04, (8, 2, 12), True, 0.1])
                    elif tile_type == 'spike': self.handle_death(); self.player.velocity = [0, -4]
        else:
            self.player.opacity = 80; self.player.update([], self.time_scale); self.player.rotation -= 16
    
    def update_sparks(self):
        for i, spark in sorted(enumerate(self.sparks), reverse=True):
            if len(spark) < 8: spark.append(False)
            if not spark[-1]: spark[1][1] = min(spark[1][1] + spark[-2], 3)
            spark[0][0] += spark[1][0] * self.time_scale
            if spark[5]:
                if ((int(spark[0][0] // self.game.TILE_SIZE), int(spark[0][1] // self.game.TILE_SIZE)) in self.tiles) or (spark[0][0] < self.game.TILE_SIZE) or (spark[0][0] > self.game.DISPLAY_SIZE[0] - self.game.TILE_SIZE):
                    spark[0][0] -= spark[1][0]; spark[1][0] *= -0.7
            spark[0][1] += spark[1][1] * self.time_scale
            if spark[5] and (int(spark[0][0] // self.game.TILE_SIZE), int(spark[0][1] // self.game.TILE_SIZE)) in self.tiles:
                spark[0][1] -= spark[1][1]; spark[1][1] *= -0.7
                if abs(spark[1][1]) < 0.1: spark[1][1] = 0; spark[-1] = True
            spark[2] -= spark[3] * self.time_scale
            if spark[2] <= 1: self.sparks.pop(i)
    
    def update_scrolling(self):
        if self.tiles:
            base_row = max(self.tiles, key=lambda x: x[1])[1] - 1
            if all((i + 1, base_row) in self.tiles for i in range(self.game.WINDOW_TILE_SIZE[0] - 2)):
                self.target_height = math.floor(self.height / self.game.TILE_SIZE) * self.game.TILE_SIZE + self.game.TILE_SIZE

        if self.height != self.target_height:
            self.height += (self.target_height - self.height) / 10
            if abs(self.target_height - self.height) < 0.2:
                self.height = self.target_height
                if self.tiles:
                    base_row_del = max(self.tiles, key=lambda x: x[1])[1] - 2
                    for i in range(self.game.WINDOW_TILE_SIZE[0] - 2):
                        if (i + 1, base_row_del + 1) in self.tiles: del self.tiles[(i + 1, base_row_del + 1)]
                self.recalculate_stack_heights()

    def handle_perk_selection_input(self, key):
        if key in [K_DOWN, K_s]: self.perk_selection_choice = (self.perk_selection_choice + 1) % len(self.perks_to_offer)
        if key in [K_UP, K_w]: self.perk_selection_choice = (self.perk_selection_choice - 1 + len(self.perks_to_offer)) % len(self.perks_to_offer)
        if key in [K_RETURN, K_e, K_x]:
            self.active_perks.add(self.perks_to_offer[self.perk_selection_choice]); self.perk_selection_active = False
            (self.game.sounds['upgrade'] if 'upgrade' in self.game.sounds else self.game.sounds['collect_item']).play()

    def fire_projectile(self, keys):
        self.game.sounds['jump'].play(); speed = 4; vel = [0, 0]
        if keys[K_UP] or keys[K_w]: vel, pos = [0, -speed], [self.player.rect.centerx, self.player.rect.top]
        elif keys[K_DOWN] or keys[K_s]: vel, pos = [0, speed], [self.player.rect.centerx, self.player.rect.bottom]
        elif self.player.flip[0]: vel, pos = [speed, 0], [self.player.rect.right, self.player.rect.centery]
        else: vel, pos = [-speed, 0], [self.player.rect.left, self.player.rect.centery]
        self.projectiles.append(Projectile(self.game.animation_manager, pos, (6, 2), 'projectile', self, velocity=vel))

    def use_item(self):
        self.item_used = True
        item = self.current_item
        if item == 'warp':
            self.game.sounds['warp'].play(); self.screen_shake = 15
            max_point = min(enumerate(self.stack_heights), key=lambda x: x[1])
            self.player.pos = [(max_point[0] + 1) * self.game.TILE_SIZE + 4, (max_point[1] - 1) * self.game.TILE_SIZE]
            for _ in range(60):
                angle, speed = random.random() * math.pi * 2, random.random() * 1.75
                self.sparks.append([self.player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.02, (12, 8, 2), True, 0.1 * random.choice([0,1])])
        elif item == 'jump': self.game.sounds['super_jump'].play(); self.screen_shake = 12; self.player.jumps += 1; self.player.attempt_jump(); self.player.velocity[1] = -8
        elif item == 'cube':
            self.game.sounds['block_land'].play(); place_pos = (int(self.player.center[0] // self.game.TILE_SIZE), int(self.player.pos[1] // self.game.TILE_SIZE) + 1)
            self.stack_heights[place_pos[0] - 1] = place_pos[1]
            base_row = (max(self.tiles, key=lambda x: x[1])[1] if self.tiles else self.game.WINDOW_TILE_SIZE[1]-1)
            for i in range(place_pos[1], base_row + 1): self.tiles[(place_pos[0], i)] = {'type': 'placed_tile', 'data': {}}
            self.recalculate_stack_heights()
        elif item == 'bomb':
            if 'explosion' in self.game.sounds: self.game.sounds['explosion'].play()
            self.screen_shake = 25
            to_bomb = [list(tp) for tp in self.tiles if math.sqrt((self.player.center[0] - (tp[0]*self.game.TILE_SIZE+8))**2 + (self.player.center[1] - (tp[1]*self.game.TILE_SIZE+8))**2) < 4*self.game.TILE_SIZE]
            for pos in to_bomb:
                if tuple(pos) in self.tiles:
                    for _ in range(15):
                        angle, speed = random.random() * math.pi * 2, random.random() * 2
                        self.sparks.append([[pos[0]*self.game.TILE_SIZE+8, pos[1]*self.game.TILE_SIZE+8], [math.cos(angle)*speed, math.sin(angle)*speed], random.random()*4+2, 0.08, (12,2,2), True, 0.1])
                    del self.tiles[tuple(pos)]
            self.recalculate_stack_heights()
        elif item == 'freeze': self.game.sounds['warp'].play(); self.screen_shake = 10; self.freeze_timer = 360
        self.current_item = None
        
    def handle_game_over_input(self, key):
        if not self.run_coins_banked: return
        if key == K_DOWN: self.upgrade_selection = (self.upgrade_selection + 1) % len(self.game.upgrade_keys)
        if key == K_UP: self.upgrade_selection = (self.upgrade_selection - 1 + len(self.game.upgrade_keys)) % len(self.game.upgrade_keys)
        if key == K_RETURN:
            ukey = self.game.upgrade_keys[self.upgrade_selection]
            upgrade, level = self.game.UPGRADES[ukey], self.game.save_data['upgrades'][ukey]
            cost = int(upgrade['base_cost'] * (1.5 ** level))
            if level < upgrade['max_level'] and self.game.save_data['banked_coins'] >= cost:
                self.game.save_data['banked_coins'] -= cost; self.game.save_data['upgrades'][ukey] += 1
                self.game.write_save(self.game.save_data)
                (self.game.sounds['upgrade'] if 'upgrade' in self.game.sounds else self.game.sounds['collect_item']).play()
    
    # --- RENDER METHODS ---
    def render_perk_selection_ui(self, surf):
        surf.blit(self.display_copy, (0, 0))
        overlay = pygame.Surface(self.game.DISPLAY_SIZE, pygame.SRCALPHA); overlay.fill((10, 5, 20, 200)); surf.blit(overlay, (0, 0))
        title = "CHOOSE A PERK"; title_w = self.game.white_font.width(title, 2)
        title_pos = (self.game.DISPLAY_SIZE[0]//2 - title_w//2, 20)
        self.game.black_font.render(title, surf, (title_pos[0]+1, title_pos[1]+1), scale=2); self.game.white_font.render(title, surf, title_pos, scale=2)
        
        y_start, panel_h, margin = 50, 35, 5
        for i, key in enumerate(self.perks_to_offer):
            r = pygame.Rect(40, y_start + i * (panel_h + margin), self.game.DISPLAY_SIZE[0] - 80, panel_h)
            pygame.draw.rect(surf, (255, 230, 90) if i == self.perk_selection_choice else (150, 150, 180), r, 1)
            perk = self.game.PERKS[key]
            self.game.white_font.render(perk['name'].upper(), surf, (r.x + 8, r.y + 7))
            self.game.black_font.render(perk['desc'], surf, (r.x + 9, r.y + 19)); self.game.white_font.render(perk['desc'], surf, (r.x + 8, r.y + 18))
            
    def render_background(self, surf):
        biome = self.game.BIOMES[self.current_biome_index]; surf.fill(biome['bg_color'])
        if self.game.backgrounds['far']:
            scroll_y = (self.height * 0.2) % self.game.DISPLAY_SIZE[1]
            surf.blit(self.game.backgrounds['far'], (0, scroll_y)); surf.blit(self.game.backgrounds['far'], (0, scroll_y - self.game.DISPLAY_SIZE[1]))
        if self.game.backgrounds['near']:
            scroll_y = (self.height * 0.4) % self.game.DISPLAY_SIZE[1]
            surf.blit(self.game.backgrounds['near'], (0, scroll_y)); surf.blit(self.game.backgrounds['near'], (0, scroll_y - self.game.DISPLAY_SIZE[1]))

    def render_placed_tiles(self, surf):
        for pos, data in self.tiles.items():
            blit_pos = (pos[0] * self.game.TILE_SIZE, pos[1] * self.game.TILE_SIZE + int(self.height))
            img_map = {'placed_tile': self.placed_tile_img, 'greed': self.greed_tile_img, 'magnetic': self.magnetic_tile_img,
                       'unstable': self.unstable_tile_img, 'sticky': self.sticky_tile_img, 'fragile': self.fragile_tile_img,
                       'bounce': self.bounce_tile_img, 'spike': self.spike_tile_img}
            surf.blit(img_map.get(data['type'], self.tile_img), blit_pos)
            if data['type'] in ['tile', 'placed_tile'] and (pos[0], pos[1]-1) not in self.tiles: surf.blit(self.tile_top_img, blit_pos)
            if data['type'] == 'magnetic' and random.randint(1,15) == 1: self.sparks.append([[pos[0]*self.game.TILE_SIZE+8, pos[1]*self.game.TILE_SIZE+8], [random.uniform(-1,1), random.uniform(-1,1)], random.uniform(1,2), 0.1, (180, 100, 255), False, 0])
            if data['type'] == 'chest':
                chest_pos = (pos[0]*self.game.TILE_SIZE, (pos[1]-1)*self.game.TILE_SIZE + int(self.height))
                surf.blit(self.chest_img, chest_pos)
                r = pygame.Rect(chest_pos[0]+2, chest_pos[1]+6, self.game.TILE_SIZE-4, self.game.TILE_SIZE-6)
                if random.randint(1, 20) == 1: self.sparks.append([[chest_pos[0]+2+12*random.random(), chest_pos[1]+4+8*random.random()], [0, random.random()*0.25-0.5], random.random()*4+2, 0.023, (12,8,2), True, 0.002])
                if r.colliderect(self.player.rect):
                    self.game.sounds['chest_open'].play(); self.combo_multiplier += 1.0*(2 if 'glass_cannon' in self.active_perks else 1); self.combo_timer = self.game.COMBO_DURATION
                    for _ in range(50): self.sparks.append([[chest_pos[0]+8, chest_pos[1]+8], [random.random()*2-1, random.random()-2], random.random()*3+3, 0.01, (12,8,2), True, 0.05])
                    self.tiles[pos]['type'] = 'opened_chest'; self.player.jumps += 1; self.player.attempt_jump(); self.player.velocity[1] = -3.5
                    item_luck = 3 + self.game.save_data['upgrades']['item_luck']
                    if random.randint(1, 5) < item_luck: self.items.append(Item(self.game.animation_manager, (pos[0]*self.game.TILE_SIZE+5, (pos[1]-1)*self.game.TILE_SIZE+5), (6,6), random.choice(['warp', 'cube', 'jump', 'bomb', 'freeze', 'shield']), self, velocity=[random.random()*5-2.5, random.random()*2-5]))
                    else:
                        coins_mult = 2 if 'greedy' in self.active_perks else 1
                        for _ in range(random.randint(2,6)*coins_mult): self.items.append(Item(self.game.animation_manager, (pos[0]*self.game.TILE_SIZE+5, (pos[1]-1)*self.game.TILE_SIZE+5), (6,6), 'coin', self, velocity=[random.random()*5-2.5, random.random()*2-7]))
            elif data['type'] == 'opened_chest': surf.blit(self.opened_chest_img, (pos[0]*self.game.TILE_SIZE, (pos[1]-1)*self.game.TILE_SIZE + int(self.height)))

    def render_falling_tiles(self, surf):
        for tile in self.tile_drops:
            pos = (tile[0], tile[1] + self.height)
            img_map = {'greed': self.greed_tile_img, 'motherlode': self.motherlode_tile_img, 'unstable': self.unstable_tile_img}
            surf.blit(img_map.get(tile[2], self.tile_img), pos)
            if tile[2] == 'chest': surf.blit(self.ghost_chest_img, (pos[0], pos[1] - self.game.TILE_SIZE))
            if random.randint(1, 4) == 1:
                side = random.choice([1, -1])
                self.sparks.append([[tile[0] + self.game.TILE_SIZE*(side==1), tile[1]], [random.random()*0.1-0.05, random.random()*0.5], random.random()*5+3, 0.15, (4,2,12), False, 0])

    def render_items(self, surf):
        for item in self.items:
            r1, r2 = int(9+math.sin(self.master_clock/30)*3), int(5+math.sin(self.master_clock/40)*2)
            surf.blit(glow_img(r1,(12,8,2)), (item.center[0]-r1-1, item.center[1]+self.height-r1-2), BLEND_RGBA_ADD)
            surf.blit(glow_img(r2,(24,16,3)), (item.center[0]-r2-1, item.center[1]+self.height-r2-2), BLEND_RGBA_ADD)
            item.render(surf, (0, -self.height))

    def render_projectiles(self, surf):
        for p in self.projectiles: p.render(surf, (0, -int(self.height)))

    def render_shield_aura(self, surf):
        aura_pos = (self.player.rect.centerx - self.shield_aura_img.get_width()//2, self.player.rect.centery - self.shield_aura_img.get_height()//2 - int(self.height))
        pulse = math.sin(self.master_clock / 8) * 2
        pulsing = pygame.transform.scale(self.shield_aura_img, (int(self.shield_aura_img.get_width() + pulse), int(self.shield_aura_img.get_height() + pulse)))
        pulsing.set_alpha(150 - pulse * 10); surf.blit(pulsing, aura_pos, BLEND_RGBA_ADD)
        
    def render_sparks(self, surf):
        for spark in self.sparks:
            size, pos = int(spark[2]), spark[0]
            surf.blit(glow_img(int(size * 1.5 + 2), (int(spark[4][0]/2),int(spark[4][1]/2),int(spark[4][2]/2))), (pos[0]-size*2, pos[1]+self.height-size*2), BLEND_RGBA_ADD)
            surf.blit(glow_img(size, spark[4]), (pos[0]-size, pos[1]+self.height-size), BLEND_RGBA_ADD)
            surf.set_at((int(pos[0]), int(pos[1] + self.height)), (255, 255, 255))
    
    def render_borders(self, surf):
        for i in range(self.game.WINDOW_TILE_SIZE[1] + 2):
            pos_y = (-self.height // 16) - 1 + i
            surf.blit(self.edge_tile_img, (0, self.game.TILE_SIZE * pos_y + int(self.height)))
            surf.blit(self.edge_tile_img, (self.game.TILE_SIZE * (self.game.WINDOW_TILE_SIZE[0] - 1), self.game.TILE_SIZE * pos_y + int(self.height)))
        surf.blit(self.border_img_light, (0, -math.sin(self.master_clock/30)*4-7)); surf.blit(self.border_img, (0, -math.sin(self.master_clock/40)*7-14))
        surf.blit(pygame.transform.flip(self.border_img_light, 0, 1), (0, self.game.DISPLAY_SIZE[1]+math.sin(self.master_clock/40)*3+9-self.border_img.get_height()))
        surf.blit(pygame.transform.flip(self.border_img, 0, 1), (0, self.game.DISPLAY_SIZE[1]+math.sin(self.master_clock/30)*3+16-self.border_img.get_height()))

    def render_hud(self, surf):
        panel = pygame.Surface((self.game.DISPLAY_SIZE[0], 28)); panel.set_alpha(100); panel.fill((0,0,1)); surf.blit(panel, (0,0))
        surf.blit(self.coin_icon, (4,4)); self.game.black_font.render(str(self.coins), surf, (17,6)); self.game.white_font.render(str(self.coins), surf, (16,5))
        
        # Time Bar
        bar_x, bar_y, bar_w, bar_h = 4, 17, 40, 6; pygame.draw.rect(surf, (0,0,1), [bar_x,bar_y,bar_w,bar_h])
        fill_w = (self.time_meter / self.game.time_meter_max)*(bar_w-2)
        color = (255,255,100) if self.slowing_time and not self.player.is_charging_dash and self.master_clock%10 < 5 else (80,150,255)
        pygame.draw.rect(surf, color, [bar_x+1, bar_y+1, fill_w, bar_h-2])
        
        # Combo
        if self.combo_multiplier > 1.0:
            text = f"x{self.combo_multiplier:.1f}"; w = self.game.white_font.width(text, 2); x, y = self.game.DISPLAY_SIZE[0]//2 - w//2, 4
            color = (255,255,255) if self.master_clock%20>10 else (255,150,40)
            combo_font = Font('data/fonts/small_font.png', color)
            self.game.black_font.render(text, surf, (x+1, y+1), scale=2); combo_font.render(text, surf, (x, y), scale=2)
            bar_w = (self.combo_timer / self.game.COMBO_DURATION)*60; bar_x = self.game.DISPLAY_SIZE[0]//2-30
            pygame.draw.rect(surf, (0,0,1), [bar_x+1, 21, 60, 4]); pygame.draw.rect(surf, (251,245,239), [bar_x, 20, bar_w, 4])
            
        # Item Slot
        x, y = self.game.DISPLAY_SIZE[0]-20, 4
        surf.blit(self.item_slot_img, (x, y))
        if self.current_item:
            if (self.master_clock%50 < 12) or (abs(self.master_clock%50 - 20) < 3): surf.blit(self.item_slot_flash_img, (x, y))
            surf.blit(self.item_icons[self.current_item], (x+5, y+5))
            if not self.item_used and ((self.master_clock%100<80) or (abs(self.master_clock%100-90)<3)):
                text = "E/X"; w = self.game.white_font.width(text); x_off = self.game.DISPLAY_SIZE[0]-w
                self.game.black_font.render(text, surf, (x_off-23, 10)); self.game.white_font.render(text, surf, (x_off-24, 9))

        # Focus Bar
        bar_x, bar_y, bar_w, bar_h = self.game.DISPLAY_SIZE[0]-25, 8, 8, 16; pygame.draw.rect(surf, (0,0,1), [bar_x, bar_y, bar_w, bar_h])
        if self.player.is_charging_dash: color = (255,255,255) if self.master_clock%10<5 else (255,150,40)
        else: color = (255,150,40) if self.player.focus_meter >= self.player.FOCUS_DASH_COST else (100,60,20)
        fill_h = int(bar_h * (self.player.focus_meter/self.player.FOCUS_METER_MAX))
        pygame.draw.rect(surf, color, [bar_x+1, (bar_y+bar_h)-fill_h, bar_w-2, fill_h])

        # Active Perks
        x_off, y_pos = 5, self.game.DISPLAY_SIZE[1]-12
        for key in sorted(list(self.active_perks)):
            if key in self.perk_icons:
                icon = self.perk_icons[key]
                bg = pygame.Surface((icon.get_width()+2, icon.get_height()+2), pygame.SRCALPHA); bg.fill((0,0,1,150))
                surf.blit(bg, (x_off-1, y_pos-1)); surf.blit(icon, (x_off, y_pos)); x_off += icon.get_width()+4
    
    def render_game_over_ui(self, surf):
        p_color=(15,12,28,220); b_color=(200,200,220,230); hl_color=(255,230,90)
        p_rect = pygame.Rect(10, 8, self.game.DISPLAY_SIZE[0]-20, self.game.DISPLAY_SIZE[1]-16)
        p_surf = pygame.Surface(p_rect.size, pygame.SRCALPHA); p_surf.fill(p_color); surf.blit(p_surf, p_rect.topleft)
        pygame.draw.rect(surf, b_color, p_rect, 1, 3)

        title = "GAME OVER"; w = self.game.white_font.width(title, 3)
        self.game.black_font.render(title, surf, (self.game.DISPLAY_SIZE[0]//2 - w//2 + 2, p_rect.top + 10), scale=3)
        self.game.white_font.render(title, surf, (self.game.DISPLAY_SIZE[0]//2 - w//2, p_rect.top + 8), scale=3)
        
        y1 = p_rect.top+30; pygame.draw.line(surf, b_color, (p_rect.left+10, y1), (p_rect.right-10, y1), 1)
        score_text = f"SCORE: {self.coins}"; hs_text = f"HIGH SCORE: {self.game.save_data['high_score']}"
        score_w, hs_w = self.game.white_font.width(score_text, 2), self.game.white_font.width(hs_text, 2)
        self.game.black_font.render(score_text, surf, (self.game.DISPLAY_SIZE[0]/2 - score_w/2+1, y1+8), scale=2); self.game.white_font.render(score_text, surf, (self.game.DISPLAY_SIZE[0]/2-score_w/2, y1+7), scale=2)
        hs_font = Font('data/fonts/small_font.png', hl_color) if self.new_high_score and self.master_clock%40<20 else self.game.white_font
        self.game.black_font.render(hs_text, surf, (self.game.DISPLAY_SIZE[0]/2 - hs_w/2 + 1, y1 + 23), scale=2); hs_font.render(hs_text, surf, (self.game.DISPLAY_SIZE[0]/2 - hs_w/2, y1 + 22), scale=2)
        if self.new_high_score and self.master_clock%30<20: Font('data/fonts/small_font.png', (100,255,120)).render("NEW!", surf, (self.game.DISPLAY_SIZE[0]/2 + hs_w/2 + 5, y1+22), scale=2)
        
        y2 = y1 + 42; pygame.draw.line(surf, b_color, (p_rect.left+10, y2), (p_rect.right-10, y2), 1)
        
        if self.end_coin_count != self.coins:
            if self.master_clock%3 == 0: self.game.sounds['coin_end'].play(); self.end_coin_count = min(self.end_coin_count+1, self.coins)
        elif not self.run_coins_banked:
            self.game.save_data['banked_coins'] += self.end_coin_count; self.game.write_save(self.game.save_data); self.run_coins_banked = True

        if self.run_coins_banked:
            up_pos = (p_rect.left+15, y2+7)
            self.game.black_font.render("Upgrades", surf, (up_pos[0]+1, up_pos[1]+1), scale=2); self.game.white_font.render("Upgrades", surf, up_pos, scale=2)
            bank_txt = f"Bank: {self.game.save_data['banked_coins']}"; bank_w = self.game.white_font.width(bank_txt); bank_pos = (p_rect.right - bank_w - 15, y2+9)
            surf.blit(self.coin_icon, (bank_pos[0] - self.coin_icon.get_width()-3, bank_pos[1]-1))
            self.game.black_font.render(bank_txt, surf, (bank_pos[0]+1, bank_pos[1]+1)); self.game.white_font.render(bank_txt, surf, bank_pos)
            
            list_y = y2 + 28
            for i, key in enumerate(self.game.upgrade_keys):
                upgrade = self.game.UPGRADES[key]; level = self.game.save_data['upgrades'][key]
                lvl_txt = "MAX" if level >= upgrade['max_level'] else f"Lvl {level}"
                font = Font('data/fonts/small_font.png', hl_color) if i == self.upgrade_selection else self.game.white_font
                if i == self.upgrade_selection: pygame.draw.rect(surf, (40,30,60,150), [p_rect.left+5, list_y-2, p_rect.width//2-10, 11], 0)
                font.render(f"{upgrade['name']}", surf, (p_rect.left+10, list_y)); font.render(lvl_txt, surf, (p_rect.left+80, list_y)); list_y += 13

            det_x, det_y = p_rect.centerx+5, y2+28
            sel_key = self.game.upgrade_keys[self.upgrade_selection]; sel_upg = self.game.UPGRADES[sel_key]; sel_lvl = self.game.save_data['upgrades'][sel_key]
            Font('data/fonts/small_font.png', hl_color).render(sel_upg['name'], surf, (det_x, det_y)); self.game.white_font.render(sel_upg['desc'], surf, (det_x, det_y+12))
            if sel_lvl < sel_upg['max_level']:
                cost = int(sel_upg['base_cost'] * (1.5**sel_lvl))
                font = Font('data/fonts/small_font.png', (140,245,150) if self.game.save_data['banked_coins'] >= cost else (120,120,130))
                cost_y = det_y+26; surf.blit(self.coin_icon, (det_x, cost_y))
                font.render(f"{cost}", surf, (det_x+self.coin_icon.get_width()+4, cost_y))
                font.render("[Buy]", surf, (p_rect.right-font.width("[Buy]")-15, cost_y))
            else: self.game.white_font.render("Max Level Reached", surf, (det_x, det_y+26))
        else:
            text = "Banking coins..." if self.master_clock%40<20 else "Banking coins.." if self.master_clock%40<30 else "Banking coins."
            w = self.game.white_font.width(text); pos = (self.game.DISPLAY_SIZE[0]//2 - w//2, y2+25)
            self.game.black_font.render(text, surf, (pos[0]+1, pos[1]+1)); self.game.white_font.render(text, surf, pos)
            
        prompt = "Up/Down: Select  -  Enter: Buy  -  R: Restart"; w = self.game.white_font.width(prompt); pos = (self.game.DISPLAY_SIZE[0]//2 - w//2, p_rect.bottom-12)
        self.game.black_font.render(prompt, surf, (pos[0]+1, pos[1]+1)); self.game.white_font.render(prompt, surf, pos)