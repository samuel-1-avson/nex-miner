# Cavyn Source/data/scripts/gameplay_state.py

import pygame, sys, random, math, json
from pygame.locals import *

# Core game state and entity imports
from .state import State
from .text import Font
from .entities.player import Player
from .entities.item import Item
from .entities.projectile import Projectile
from .entities.turret import Turret 
from .entities.turret_projectile import TurretProjectile

# Imports for state transitions and utilities
from .game_states.pause_state import PauseState
from .game_states.perk_selection_state import PerkSelectionState
from .game_states.curse_selection_state import CurseSelectionState
from .core_funcs import load_img
from .ui_utils import glow_img, render_panel_9slice

# Late import to prevent circular dependency
GameOverState = None


# =========================================================================
# === MAIN GAMEPLAY STATE CLASS ===
# =========================================================================

class GameplayState(State):
    def __init__(self, game, mode="classic", challenge_config=None, start_biome_index=0, seeded_random=None):
        super().__init__(game)
        
        global GameOverState
        if GameOverState is None:
            from .game_states.game_over_state import GameOverState

        self.mode = mode
        self.challenge_config = challenge_config
        self.start_biome_index = start_biome_index
        
        if seeded_random:
            self.random = seeded_random
        else:
            self.random = random

        self.plasma_y = self.game.DISPLAY_SIZE[1] + 50
        self.special_entity_timer = 0
        self.data_nodes = []
        self.load_state_assets()
        self.reset()

    def load_state_assets(self):
        self.tile_img = load_img(self.game.get_path('data', 'images', 'tile.png'))
        self.placed_tile_img = load_img(self.game.get_path('data', 'images', 'placed_tile.png'))
        self.chest_img = load_img(self.game.get_path('data', 'images', 'chest.png'))
        self.ghost_chest_img = load_img(self.game.get_path('data', 'images', 'ghost_chest.png'))
        self.opened_chest_img = load_img(self.game.get_path('data', 'images', 'opened_chest.png'))
        self.edge_tile_img = load_img(self.game.get_path('data', 'images', 'edge_tile.png'))
        self.fragile_tile_img = load_img(self.game.get_path('data', 'images', 'fragile_tile.png'))
        self.bounce_tile_img = load_img(self.game.get_path('data', 'images', 'bounce_tile.png'))
        self.spike_tile_img = load_img(self.game.get_path('data', 'images', 'spike_tile.png'))
        self.magnetic_tile_img = load_img(self.game.get_path('data', 'images', 'magnetic_tile.png'))
        self.sticky_tile_img = load_img(self.game.get_path('data', 'images', 'sticky_tile.png'))
        self.motherlode_tile_img = load_img(self.game.get_path('data', 'images', 'motherlode_tile.png'))
        self.unstable_tile_img = load_img(self.game.get_path('data', 'images', 'unstable_tile.png'))
        self.coin_icon = load_img(self.game.get_path('data', 'images', 'coin_icon.png'))
        self.item_slot_img = load_img(self.game.get_path('data', 'images', 'item_slot.png'))
        self.item_slot_flash_img = load_img(self.game.get_path('data', 'images', 'item_slot_flash.png'))
        self.border_img = load_img(self.game.get_path('data', 'images', 'border.png'))
        self.border_img_light = self.border_img.copy()
        self.border_img_light.set_alpha(100)
        self.tile_top_img = load_img(self.game.get_path('data', 'images', 'tile_top.png'))
        self.greed_tile_img = load_img(self.game.get_path('data', 'images', 'greed_tile.png'))
        self.shield_aura_img = load_img(self.game.get_path('data', 'images', 'shield_aura.png'))
        self.shield_aura_img.set_alpha(150)
        self.panel_img = load_img(self.game.get_path('data', 'images', 'panel_9slice.png'))
        
        try:
            self.conveyor_l_img = load_img(self.game.get_path('data', 'images', 'conveyor_l.png'))
            self.conveyor_r_img = load_img(self.game.get_path('data', 'images', 'conveyor_r.png'))
        except pygame.error as e:
            print(f"WARNING: Could not load conveyor asset. Did you add it to data/images/? Error: {e}")
            self.conveyor_l_img = pygame.Surface((16, 16)); self.conveyor_l_img.fill((255, 0, 255))
            self.conveyor_r_img = pygame.Surface((16, 16)); self.conveyor_r_img.fill((255, 0, 255))

        try:
            self.prism_tile_img = load_img(self.game.get_path('data', 'images', 'prism_tile.png'))
            self.geyser_tile_img = load_img(self.game.get_path('data', 'images', 'geyser_tile.png'))
            self.data_node_img = load_img(self.game.get_path('data', 'images', 'crystal.png'))
            self.conduit_tile_img = load_img(self.game.get_path('data', 'images', 'tile_conduit.png'))
        except pygame.error as e:
            print(f"WARNING: Could not load new biome asset. Did you add it to data/images/? Error: {e}")
            self.prism_tile_img = pygame.Surface((16, 16)); self.prism_tile_img.fill((255, 0, 255))
            self.geyser_tile_img = pygame.Surface((16, 16)); self.geyser_tile_img.fill((255, 0, 255))
            self.data_node_img = pygame.Surface((16, 24)); self.data_node_img.fill((255, 0, 255))
            self.conduit_tile_img = pygame.Surface((16, 16)); self.conduit_tile_img.fill((0, 255, 255))

    def enter_state(self):
        super().enter_state()
        if self.mode == "classic" and self.perks_gained_this_run > 0 and self.perks_gained_this_run % 2 == 0:
            if self.perks_gained_this_run != self.last_curse_check:
                self.last_curse_check = self.perks_gained_this_run
                
                available_curses = list(set(self.game.curses.keys()) - self.active_curses)
                if available_curses:
                    curses_to_offer = self.random.sample(available_curses, k=min(3, len(available_curses)))
                    background_surf = self.game.display.copy()
                    self.render(background_surf)
                    self.game.push_state(CurseSelectionState(self.game, self, curses_to_offer, background_surf))

    def reset(self):
        self.game.save_data['stats']['runs_started'] += 1
        selected_char_key = self.game.save_data['characters']['selected']
        character_data = self.game.characters.get(selected_char_key, self.game.characters['operator'])
        
        for key in self.game.upgrades:
            if key not in self.game.save_data['upgrades']:
                self.game.save_data['upgrades'][key] = 0

        self.player = Player(self.game.animation_manager, (self.game.DISPLAY_SIZE[0] // 2 - 5, 20), (8, 16), selected_char_key, self)
        self.player.jumps_max = 2 + self.game.save_data['upgrades']['jumps']
        self.player.speed = 1.4 + self.game.save_data['upgrades']['speed'] * 0.08
        self.player.jumps = self.player.jumps_max
        
        self.active_perks = set(character_data['mods'].get('innate_perks', []))
        self.player.FOCUS_DASH_COST = character_data['mods'].get('FOCUS_DASH_COST', 50)
        
        self.dead = False
        self.tiles, self.tile_drops, self.sparks, self.projectiles, self.items = {}, [], [], [], []
        self.turrets = []
        self.turret_projectiles = []

        self.ghosts = []
        self.freeze_timer, self.game_timer, self.master_clock = 0, 0, 0
        self.height, self.target_height = 0, 0
        self.coins = 0
        self.invincibility_timer = 0
        
        self.current_item = None
        if self.game.save_data['upgrades'].get('starting_item', 0) > 0:
            possible_items = ['cube', 'jump', 'bomb', 'shield', 'freeze', 'hourglass']
            self.current_item = self.random.choice(possible_items)
            if self.current_item not in self.game.save_data['compendium']['items']:
                self.game.save_data['compendium']['items'].append(self.current_item)

        if 'starting_item' in character_data['mods']:
            item = character_data['mods']['starting_item']
            if item == 'random':
                possible_items = list(self.game.item_icons.keys())
                self.current_item = self.random.choice(possible_items)
            else:
                self.current_item = item

        self.tile_coin_drop_chance = 0
        self.player_shielded = False
        equipped_artifact_key = self.game.save_data['artifacts']['equipped']
        if equipped_artifact_key:
            artifact_mod = self.game.artifacts[equipped_artifact_key]['mod']
            if artifact_mod['type'] == 'start_with_shield': self.player_shielded = True
            if artifact_mod['type'] == 'focus_cost_multiplier': self.player.FOCUS_DASH_COST *= artifact_mod['value']
            if artifact_mod['type'] == 'tile_coin_drop_chance': self.tile_coin_drop_chance = artifact_mod['value']
        
        self.directive = self.game.save_data.get('active_directive')
        self.directive_progress = 0
        if self.directive:
            self.directive['completed'] = False
            self.directive = json.loads(json.dumps(self.directive))
        self.game.save_data['active_directive'] = None
        
        self.item_used = False
        self.curse_rerolls_left = self.game.save_data['upgrades'].get('curse_reroll', 0)
        
        self.time_meter = self.game.time_meter_max
        self.slowing_time = False
        self.player_time_scale = 1.0
        self.world_time_scale = 1.0

        self.screen_shake = 0
        self.combo_shield_used = False
        self.last_perk_score = 0
        self.combo_timer = 0
        self.last_curse_check = 0
        self.perks_gained_this_run = 0

        if self.mode == "daily_challenge":
             self.spawn_timer_base, self.disabled_tiles, self.active_curses, self.combo_multiplier = 45, set(), set(), 1.0
        elif self.mode == "challenge":
            self.player.pos[1] = 13 * 16
            self.tiles = {tuple(pos): {'type': tile_type, 'data': {}} for pos, tile_type in self.challenge_config['start_layout']}
            self.tile_drops = [[(idx % 18 + 1) * self.game.TILE_SIZE, -self.height - self.game.TILE_SIZE, t_type] for idx, t_type in enumerate(self.challenge_config['falling_tiles'])]
            self.spawn_timer_base, self.disabled_tiles, self.active_curses, self.combo_multiplier = 999999, set(), set(), 1.0
        elif self.mode == "zen":
            self.spawn_timer_base, self.disabled_tiles, self.active_curses, self.combo_multiplier = 80, {'spike', 'unstable'}, set(), 1.0
            pygame.mixer.music.set_volume(0.3 * self.game.save_data['settings'].get('music_volume', 1.0))
        elif self.mode == "hardcore":
            self.spawn_timer_base, self.disabled_tiles, self.combo_multiplier = 25, set(), 1.5
            curses_pool = list(self.game.curses.keys())
            self.active_curses = {self.random.choice(curses_pool)} if curses_pool else set()
        else: # Classic
            self.spawn_timer_base, self.disabled_tiles, self.active_curses, self.combo_multiplier = 45, set(), set(), 1.0

        if self.mode != "challenge":
            for i in range(self.game.WINDOW_TILE_SIZE[0] - 2): self.tiles[(i + 1, self.game.WINDOW_TILE_SIZE[1] - 1)] = {'type': 'tile', 'data': {}}
            self.tiles[(1, self.game.WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
            self.tiles[(self.game.WINDOW_TILE_SIZE[0] - 2, self.game.WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}

        self.plasma_y, self.data_nodes, self.special_entity_timer = self.game.DISPLAY_SIZE[1] + 50, [], 0
            
        self.current_biome_index = self.start_biome_index
        self.last_place = 0
        self.game.load_biome_bgs(self.game.biomes[self.current_biome_index])
        
        self.recalculate_stack_heights()

    def handle_events(self, events):
        super().handle_events(events)
        for event in events:
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.game.push_state(PauseState(self.game, self))
                    return 
                if not self.dead:
                    if event.key in [K_c, K_l] and self.player.focus_meter >= self.player.FOCUS_DASH_COST: self.player.is_charging_dash = True
                    if event.key in [K_RIGHT, K_d]: self.player.right = True
                    if event.key in [K_LEFT, K_a]: self.player.left = True
                    if event.key in [K_UP, K_w, K_SPACE]:
                        self.player.jump_buffer_timer = 8
                        if self.player.air_time < 2 or self.player.coyote_timer > 0 or self.player.jumps > 0 or self.player.is_wall_sliding:
                            if 'jump' in self.game.sounds and self.game.sounds['jump']: self.game.sounds['jump'].play()
                            self.player.attempt_jump()
                    if event.key in [K_z, K_k] and len(self.projectiles) < 4: self.fire_projectile(pygame.key.get_pressed())
                    if event.key in [K_e, K_x] and self.current_item: self.use_item()
            if event.type == KEYUP and not self.dead:
                if event.key in [K_c, K_l] and self.player.is_charging_dash:
                    self.player.is_charging_dash = False
                    if self.player.focus_meter >= self.player.FOCUS_DASH_COST:
                        self.player.focus_meter -= self.player.FOCUS_DASH_COST
                        self.player.dash_timer = self.player.DASH_DURATION
                        if 'explosion' in self.game.sounds and self.game.sounds['explosion']: self.game.sounds['explosion'].play()
                if event.key in [K_RIGHT, K_d]: self.player.right = False
                if event.key in [K_LEFT, K_a]: self.player.left = False

    def update(self):
        self.master_clock += 1
        self.update_time_scale()

        if not self.dead:
            if self.mode != "challenge":
                self.update_biome(); self.update_combo_meter(); self.update_perk_offering(); self.update_directive()
                self.update_tile_spawning(); self.update_ambient_hazards(); self.update_special_entities()

        if self.screen_shake > 0: self.screen_shake -= 0.5 * self.world_time_scale
        if self.freeze_timer > 0: self.freeze_timer -= 1
        if self.invincibility_timer > 0: self.invincibility_timer -= 1

        self.update_ghosts(); self.update_falling_tiles(); self.update_placed_tiles()
        self.update_tile_interactions(); self.update_items(); self.update_projectiles()
        self.update_sparks(); self.update_scrolling()
        
        self.update_turrets()
        self.update_turret_projectiles()

        self.update_player()

        if self.mode == 'challenge': self.check_challenge_conditions()
    
    def update_turrets(self):
        player_rect_world = self.player.rect.copy()
        player_rect_world.y += int(self.height)

        for i, turret in sorted(enumerate(self.turrets), reverse=True):
            # If the tile the turret was on is gone, destroy the turret
            if turret.parent_tile_pos not in self.tiles:
                self.destroy_turret(i, turret, cause='tile_destroyed')
                continue
                
            turret.update(player_rect_world, self.world_time_scale)
            turret_render_rect = turret.rect.copy()
            turret_render_rect.y -= int(self.height)
            
            # Check collision with player's projectiles
            for j, p_proj in sorted(enumerate(self.projectiles), reverse=True):
                proj_render_rect = p_proj.rect.copy()
                proj_render_rect.y -= int(self.height)
                if proj_render_rect.colliderect(turret_render_rect):
                    self.projectiles.pop(j)
                    if turret.take_damage(1):
                        self.destroy_turret(i, turret, cause='player_shot')
                    # Break inner loop if turret is destroyed or projectile is gone
                    break 
            if i >= len(self.turrets) or turret is not self.turrets[i]: continue

            # Check collision with dashing player
            if self.player.dash_timer > 0 and self.player.rect.colliderect(turret_render_rect):
                self.destroy_turret(i, turret, cause='player_dash')

    def update_turret_projectiles(self):
        for i, proj in sorted(enumerate(self.turret_projectiles), reverse=True):
            if proj.update(self.world_time_scale):
                self.turret_projectiles.pop(i)
                continue
            
            # Check collision with player
            proj_render_rect = proj.rect.copy()
            proj_render_rect.y -= int(self.height)
            if proj_render_rect.colliderect(self.player.rect):
                self.turret_projectiles.pop(i)
                self.handle_death()
    
    def destroy_turret(self, index, turret, cause):
        if index < len(self.turrets):
            self.turrets.pop(index)

        if 'explosion' in self.game.sounds: self.game.sounds['explosion'].play()
        self.screen_shake = max(self.screen_shake, 7)
        
        turret_center_render = turret.center.copy()
        turret_center_render[1] -= int(self.height)
        for _ in range(30):
            angle, speed = self.random.random() * math.pi * 2, self.random.random() * 2
            self.sparks.append([turret_center_render, [math.cos(angle) * speed, math.sin(angle) * speed], self.random.random() * 3 + 2, 0.08, (180, 50, 50), True, 0.1])
        
        if cause in ['player_shot', 'player_dash']:
            self.coins += 5 * int(self.combo_multiplier)
            self.combo_multiplier += 0.25
            self.combo_timer = self.game.COMBO_DURATION
    
    def update_falling_tiles(self):
        tile_drop_rects = []
        for i, tile in sorted(enumerate(self.tile_drops), reverse=True):
            if self.freeze_timer <= 0: tile[1] += (1.8 if tile[2] == 'motherlode' else 1.4) * self.world_time_scale
            
            r_real_world = pygame.Rect(tile[0], tile[1], self.game.TILE_SIZE, self.game.TILE_SIZE)
            r = pygame.Rect(tile[0], tile[1] - self.height, self.game.TILE_SIZE, self.game.TILE_SIZE)
            tile_drop_rects.append(r)
            graze_r = self.player.rect.copy(); graze_r.inflate_ip(8, 8)
            if graze_r.colliderect(r) and not self.player.rect.colliderect(r):
                self.combo_multiplier += 0.2 * (2 if 'glass_cannon' in self.active_perks else 1)
                self.combo_timer = self.game.COMBO_DURATION
            
            if self.player.dash_timer > 0 and r.colliderect(self.player.rect):
                self.tile_drops.pop(i)
                if 'brittle_blocks' not in self.active_curses:
                    self.coins += 2 * int(self.combo_multiplier)
                
                if self.directive and not self.directive.get('completed', False) and self.directive.get('objective_type') == 'destroy_tiles_dash': self.directive_progress += 1
                self.combo_multiplier += 0.3 * (2 if 'glass_cannon' in self.active_perks else 1); self.combo_timer = self.game.COMBO_DURATION
                if 'explosion' in self.game.sounds: self.game.sounds['explosion'].play()
                self.screen_shake = max(self.screen_shake, 6)
                for k in range(15):
                    angle, speed = self.random.random() * math.pi * 2, self.random.random() * 2.5
                    self.sparks.append([list(r.center), [math.cos(angle) * speed, math.sin(angle) * speed], self.random.uniform(2, 5), 0.08, (251, 245, 239), True, 0.1])
                continue
                
            if r.colliderect(self.player.rect): self.handle_death()

            check_pos_real = (int(r_real_world.centerx // self.game.TILE_SIZE), int(math.floor(r_real_world.bottom / self.game.TILE_SIZE)))
            if check_pos_real in self.tiles:
                self.tile_drops.pop(i)
                place_pos = (check_pos_real[0], check_pos_real[1] - 1)
                
                if place_pos[1] < 0: continue
                
                self.tiles[place_pos] = {'type': tile[2], 'data': {}}
                if tile[2] == 'unstable': self.tiles[place_pos]['data']['timer'] = 180
                self.game.sounds['block_land'].play()

                if tile[2] in ['tile', 'placed_tile'] and self.mode not in ["zen", "hardcore"]:
                    if self.random.randint(1, 100) <= 8:
                        turret_pos = [place_pos[0] * self.game.TILE_SIZE, (place_pos[1] - 1) * self.game.TILE_SIZE]
                        self.turrets.append(Turret(self.game.animation_manager, turret_pos, (16, 16), 'turret', self, place_pos))

                if self.random.random() < self.tile_coin_drop_chance:
                     self.items.append(Item(self.game.animation_manager, (place_pos[0] * 16 + 5, place_pos[1] * 16 + 5), (6, 6), 'coin', self, velocity=[self.random.random() * 2 - 1, self.random.random() * -2]))

                self.recalculate_stack_heights()
                continue
        self.tile_drop_rects = tile_drop_rects
    
    def use_item(self):
        if 'butter_fingers' in self.active_curses and self.random.random() < 0.5:
            self.game.sounds['combo_end'].play()
            self.current_item = None
            return

        self.item_used = True
        item = self.current_item
        if item == 'warp':
            self.game.sounds['warp'].play(); self.screen_shake = 15
            max_point = min(enumerate(self.stack_heights), key=lambda x: x[1])
            self.player.pos = [(max_point[0] + 1) * self.game.TILE_SIZE + 4, (max_point[1] - 2) * self.game.TILE_SIZE]
            for _ in range(60):
                angle, speed = self.random.random() * math.pi * 2, self.random.random() * 1.75
                self.sparks.append([self.player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], self.random.random() * 3 + 3, 0.02, (12, 8, 2), True, 0.1 * self.random.choice([0,1])])
        elif item == 'jump': 
            self.game.sounds['super_jump'].play(); self.screen_shake = 12;
            self.player.jumps = self.player.jumps_max + 1; self.player.attempt_jump(); self.player.velocity[1] = -8 
        elif item == 'cube':
            self.game.sounds['block_land'].play(); 
            place_pos_x = int(self.player.center[0] // self.game.TILE_SIZE)
            place_pos_y = int(self.player.pos[1] // self.game.TILE_SIZE) + 1
            base_row = (max(self.tiles, key=lambda x: x[1])[1] if self.tiles else self.game.WINDOW_TILE_SIZE[1]-1)
            for i in range(place_pos_y, base_row + 1): self.tiles[(place_pos_x, i)] = {'type': 'placed_tile', 'data': {}}
            self.recalculate_stack_heights()
        elif item == 'bomb':
            self.bomb_item()
        elif item == 'freeze': self.game.sounds['warp'].play(); self.screen_shake = 10; self.freeze_timer = 360
        elif item == 'hourglass':
            if 'upgrade' in self.game.sounds: self.game.sounds['upgrade'].play()
            self.screen_shake = 8
            if self.combo_multiplier > 1.0:
                self.combo_timer = self.game.COMBO_DURATION
                for i in range(40):
                    angle, speed = self.random.random() * math.pi * 2, self.random.random() * 1.5
                    self.sparks.append([[self.game.DISPLAY_SIZE[0]//2, 12], [math.cos(angle) * speed, math.sin(angle) * speed - 0.5], self.random.random() * 3 + 1, 0.04, (255,220,100), True, 0.02])
        
        if 'module_recycler' in self.active_perks and self.random.random() < 0.25:
             if self.game.sounds.get('upgrade'): self.game.sounds['upgrade'].play()
        else:
            self.current_item = None

    def bomb_item(self):
        if 'explosion' in self.game.sounds: self.game.sounds['explosion'].play()
        self.screen_shake = 25
        
        player_center_world = self.player.center.copy()
        player_center_world[1] += int(self.height)
        bomb_radius_sq = (4 * self.game.TILE_SIZE) ** 2

        # Bomb tiles
        to_bomb_tiles = [tp for tp in self.tiles if (player_center_world[0] - (tp[0] * 16 + 8))**2 + (player_center_world[1] - (tp[1] * 16 + 8))**2 < bomb_radius_sq]
        for pos in to_bomb_tiles:
            if pos in self.tiles:
                del self.tiles[pos]
                render_pos = [pos[0] * 16 + 8, pos[1] * 16 + 8 - self.height]
                for _ in range(15):
                    angle, speed = self.random.random() * math.pi * 2, self.random.random() * 2
                    self.sparks.append([render_pos, [math.cos(angle)*speed, math.sin(angle)*speed], self.random.random()*4+2, 0.08, (12,2,2), True, 0.1])
        if to_bomb_tiles:
            self.recalculate_stack_heights()

        # Bomb Turrets
        for i, turret in sorted(enumerate(self.turrets), reverse=True):
            if (player_center_world[0] - turret.center[0])**2 + (player_center_world[1] - turret.center[1])**2 < bomb_radius_sq:
                self.destroy_turret(i, turret, cause='bomb')

    def render(self, surface):
        self.render_background(surface)
        if self.freeze_timer > 0:
            freeze_overlay = pygame.Surface(self.game.DISPLAY_SIZE, pygame.SRCALPHA)
            alpha = 60 + math.sin(self.master_clock / 5) * 10
            freeze_overlay.fill((170, 200, 255, alpha)); surface.blit(freeze_overlay, (0, 0))
        
        self.render_challenge_goal(surface)
        self.render_plasma(surface); self.render_data_nodes(surface); self.render_ghosts(surface)
        self.render_placed_tiles(surface); self.render_falling_tiles(surface); self.render_items(surface)
        self.render_projectiles(surface)
        
        for turret in self.turrets: turret.render(surface, (0, int(self.height)))
        for proj in self.turret_projectiles: proj.render(surface, (0, int(self.height)))

        self.render_shield_aura(surface)

        if not (self.invincibility_timer > 0 and self.master_clock % 6 < 3):
            self.player.render(surface, (0, -int(self.height)))
            
        self.render_sparks(surface); self.render_borders(surface); self.render_hud(surface)
        
    # The rest of the functions from here down are unchanged.
    def check_challenge_conditions(self):
        win_con = self.challenge_config['win_condition']
        lose_con = self.challenge_config.get('lose_condition')
        
        if lose_con:
            if lose_con['type'] == 'max_place' and len(self.tile_drops) > lose_con['value']:
                self.handle_death()
                return
        
        if win_con['type'] == 'reach_y':
            goal_pos = None
            for pos, tile_type in self.challenge_config['start_layout']:
                if tile_type == 'goal':
                    goal_pos = tuple(pos)
                    break
            
            if goal_pos:
                goal_rect = pygame.Rect(goal_pos[0]*16, goal_pos[1]*16, 16, 16)
                goal_render_rect = goal_rect.copy()
                goal_render_rect.y -= int(self.height)
                if self.player.rect.colliderect(goal_render_rect):
                    self.handle_challenge_win()

    def handle_challenge_win(self):
        if not self.dead:
            self.dead = True
            if self.game.sounds.get('upgrade'): self.game.sounds['upgrade'].play()
            self.game.pop_state()

    def render_challenge_goal(self, surface):
        if self.mode == 'challenge':
            for pos, tile_type in self.challenge_config['start_layout']:
                if tile_type == 'goal':
                    goal_pos = (pos[0] * 16, pos[1] * 16 - int(self.height))
                    goal_icon = self.game.item_icons['jump']
                    alpha = 128 + math.sin(self.master_clock / 20) * 127
                    goal_icon.set_alpha(int(alpha))
                    surface.blit(goal_icon, goal_pos, special_flags=BLEND_RGBA_ADD)

    def handle_death(self):
        if self.invincibility_timer > 0 or self.dead: return
        
        if self.mode == "zen":
            self.player.pos[1] -= 20
            self.player.velocity[1] = -5
            if 'time_slow_start' in self.game.sounds: self.game.sounds['time_slow_start'].play()
            return
            
        if self.player_shielded:
            self.player_shielded = False
            self.game.sounds['explosion'].play() if 'explosion' in self.game.sounds else self.game.sounds['super_jump'].play()
            self.screen_shake = 15
            if 'safeguard' in self.active_perks:
                self.invincibility_timer = 120 # 2 seconds
            for _ in range(60):
                angle, speed = self.random.random() * math.pi * 2, self.random.random() * 2
                self.sparks.append([self.player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], self.random.uniform(2, 4), 0.05, (170, 200, 255), True, 0.05])
            return

        self.dead = True
        
        if self.mode == "daily_challenge":
            if self.coins > self.game.save_data['stats'].get('daily_challenge_high_score', 0):
                self.game.save_data['stats']['daily_challenge_high_score'] = self.coins
                self.game.write_save(self.game.save_data)
        else:
             self.game.save_data['stats']['total_coins'] += self.coins

        if 'death' in self.game.sounds: self.game.sounds['death'].play()
        self.screen_shake = 20
        
        for i in range(120):
            angle, speed, physics = self.random.random() * math.pi * 2, self.random.random() * 2, self.random.choice([False, True])
            self.sparks.append([self.player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], self.random.random() * 3 + 3, 0.04, (18, 2, 2), physics, 0.1 * physics])
            
        background_surf = self.game.display.copy()
        self.render(background_surf)
        
        if self.mode == 'challenge':
            self.game.pop_state()
        else:
            if GameOverState: self.game.push_state(GameOverState(self.game, self.coins, background_surf))
            
    def update_ghosts(self):
        for i, ghost in sorted(enumerate(self.ghosts), reverse=True):
            ghost[2] -= 1
            if ghost[2] <= 0: self.ghosts.pop(i)
                
    def render_ghosts(self, surface):
        for img, pos, timer, flip in self.ghosts:
            alpha = max(0, (timer / 15) * 120)
            img.set_alpha(alpha)
            render_img = pygame.transform.flip(img, flip, False)
            surface.blit(render_img, (pos[0], pos[1] - self.height))

    def recalculate_stack_heights(self):
        new_heights = [self.game.WINDOW_TILE_SIZE[1] for _ in range(self.game.WINDOW_TILE_SIZE[0] - 2)]
        for tile_x, tile_y in self.tiles:
            if 1 <= tile_x < self.game.WINDOW_TILE_SIZE[0] - 1: new_heights[tile_x - 1] = min(new_heights[tile_x - 1], tile_y)
        self.stack_heights = new_heights

    def update_biome(self):
        next_biome_index = self.current_biome_index
        if self.mode not in ["zen", "daily_challenge"] and self.current_biome_index + 1 < len(self.game.biomes) and self.coins >= self.game.biomes[self.current_biome_index + 1]['score_req']:
            next_biome_index += 1
        if next_biome_index != self.current_biome_index:
            self.current_biome_index = next_biome_index;
            self.game.load_biome_bgs(self.game.biomes[self.current_biome_index])
            new_biome_name = self.game.biomes[self.current_biome_index]['name']
            if new_biome_name not in self.game.save_data['biomes_unlocked']:
                self.game.save_data['biomes_unlocked'].append(new_biome_name)
                self.game.write_save(self.game.save_data)
            self.game.sounds['warp'].play(); self.screen_shake = 15; self.plasma_y = self.game.DISPLAY_SIZE[1] + 50; self.data_nodes = []
            self.combo_shield_used = False
            
    def update_ambient_hazards(self):
        if 'ambient_hazard' in self.game.biomes[self.current_biome_index]:
            hazard = self.game.biomes[self.current_biome_index]['ambient_hazard']
            if hazard['type'] == 'rising_plasma':
                self.plasma_y -= hazard['speed'] * self.world_time_scale
            player_render_rect = self.player.rect.copy()
            player_render_rect.y -= int(self.height)
            if player_render_rect.bottom > self.plasma_y:
                self.handle_death()


    def update_special_entities(self):
        if 'special_entities' in self.game.biomes[self.current_biome_index]:
            entity_config = self.game.biomes[self.current_biome_index]['special_entities']
            self.special_entity_timer += 1 * self.world_time_scale
            if self.special_entity_timer > entity_config['spawn_rate']:
                self.special_entity_timer = 0
                if entity_config['type'] == 'data_node':
                    valid_cols = [i for i, h in enumerate(self.stack_heights) if h > 4]
                    if valid_cols:
                        x_pos = (self.random.choice(valid_cols) + 1) * self.game.TILE_SIZE
                        self.data_nodes.append(pygame.Rect(x_pos, -self.height - 24, 16, 24))
                        
        for i, data_node_rect in sorted(enumerate(self.data_nodes), reverse=True):
            data_node_render_rect = pygame.Rect(data_node_rect.x, data_node_rect.y - self.height, data_node_rect.width, data_node_rect.height)
            if self.player.dash_timer > 0 and self.player.rect.colliderect(data_node_render_rect):
                self.data_nodes.pop(i)
                self.coins += 5 * int(self.combo_multiplier)
                self.combo_multiplier += 0.5 * (2 if 'glass_cannon' in self.active_perks else 1)
                self.combo_timer = self.game.COMBO_DURATION
                self.game.sounds['explosion'].play()
                self.screen_shake = max(self.screen_shake, 6)
                for k in range(20):
                    angle, speed = self.random.random() * math.pi * 2, self.random.random() * 2.5
                    self.sparks.append([list(data_node_render_rect.center), [math.cos(angle) * speed, math.sin(angle) * speed], self.random.uniform(2, 5), 0.08, (200, 220, 255), True, 0.1])
                continue

            if self.freeze_timer <= 0: data_node_rect.y += 1.6 * self.world_time_scale
            if self.player.rect.colliderect(data_node_render_rect): self.data_nodes.pop(i); self.handle_death()
            
            check_pos_real_world = (int(data_node_rect.centerx // self.game.TILE_SIZE), int(math.floor(data_node_rect.bottom / self.game.TILE_SIZE)))
            if check_pos_real_world in self.tiles:
                self.data_nodes.pop(i); self.screen_shake = max(self.screen_shake, 7); self.game.sounds['explosion'].play()
                for k in range(self.random.randint(4, 8)):
                    self.items.append(Item(self.game.animation_manager, (data_node_rect.centerx, data_node_rect.bottom - self.height), (6, 6), 'coin', self, velocity=[self.random.random() * 4 - 2, self.random.random() * 2 - 6]))

    def update_time_scale(self):
        self.player_time_scale = 1.0
        self.world_time_scale = 1.0
        
        if self.dead:
            self.slowing_time = False
            return
            
        is_slowing_now = (pygame.key.get_pressed()[K_LSHIFT] and self.time_meter > 0) or self.player.is_charging_dash
        
        if is_slowing_now and not self.slowing_time:
            self.game.sounds['time_slow_start'].play()
        elif not is_slowing_now and self.slowing_time:
            self.game.sounds['time_slow_end'].play()
            
        self.slowing_time = is_slowing_now

        if self.slowing_time:
            self.world_time_scale = 0.4 
            if self.player.is_charging_dash:
                self.player.focus_meter = max(0, self.player.focus_meter - 1.5)
                if self.player.focus_meter <= 0: self.player.is_charging_dash = False
            elif pygame.key.get_pressed()[K_LSHIFT]:
                self.time_meter = max(0, self.time_meter - 0.75)
                if self.time_meter <= 0: self.game.sounds['time_empty'].play()
        else:
            self.time_meter = min(self.game.time_meter_max, self.time_meter + 0.2)


    def update_combo_meter(self):
        if self.combo_timer > 0:
            combo_drain_multiplier = 1.5 if 'short_fuse' in self.active_curses else 1
            self.combo_timer -= (2 if 'glass_cannon' in self.active_perks else 1) * self.world_time_scale * combo_drain_multiplier
            
            if self.combo_timer <= 0 and self.combo_multiplier > 1.0:
                self.combo_timer = 0
                if 'combo_end' in self.game.sounds: self.game.sounds['combo_end'].play()
                
                shield_level = self.game.save_data['upgrades']['combo_shield']
                if shield_level > 0 and not self.combo_shield_used:
                    self.combo_shield_used = True
                    self.combo_multiplier = 1.0 + shield_level * 1.5
                    if 'explosion' in self.game.sounds: self.game.sounds['explosion'].play()
                    self.screen_shake = 10
                    for i in range(30):
                        angle, speed = self.random.random() * math.pi * 2, self.random.random() * 2
                        self.sparks.append([[self.game.DISPLAY_SIZE[0] // 2, 10], [math.cos(angle) * speed, math.sin(angle) * speed], self.random.random() * 2 + 1, 0.05, (255, 200, 50), True, 0.05])
                else:
                    self.combo_multiplier = 1.0
                    for i in range(20):
                        angle, speed = self.random.random() * math.pi * 2, self.random.random() * 1.5
                        self.sparks.append([[self.game.DISPLAY_SIZE[0] // 2, 10], [math.cos(angle) * speed, math.sin(angle) * speed], self.random.random() * 2 + 1, 0.05, (251, 245, 239), True, 0.05])

    def update_perk_offering(self):
        if self.mode in ['zen', 'challenge', 'daily_challenge']: return
        score_interval = 75 if self.mode != "hardcore" else 60
        if self.coins > 0 and self.coins // score_interval > self.last_perk_score // score_interval:
            self.last_perk_score = self.coins
            available_perks = [p for p in self.game.perks.keys() if p not in self.active_perks]
            if available_perks:
                perks_to_offer = self.random.sample(available_perks, k=min(3, len(available_perks)))
                background_surf = self.game.display.copy()
                self.render(background_surf)
                self.game.push_state(PerkSelectionState(self.game, perks_to_offer, background_surf))
                self.game.sounds['warp'].play()

    def update_directive(self):
        if not self.directive or self.directive.get('completed', False): return

        objective_type = self.directive.get('objective_type')
        if objective_type == 'collect_coins': self.directive_progress = self.coins
        elif objective_type == 'reach_combo': self.directive_progress = self.combo_multiplier

        if self.directive_progress >= self.directive.get('value', float('inf')):
            self.directive['completed'] = True
            self.game.sounds['directive_complete'].play()
            reward_type = self.directive.get('reward_type')
            reward_value = self.directive.get('reward_value')
            if reward_type == 'coins' and reward_value: self.coins += reward_value
            elif reward_type == 'item' and reward_value: self.current_item = reward_value

    def update_tile_spawning(self):
        if self.master_clock < 180 or self.mode == "challenge": return
        self.game_timer += self.world_time_scale
        current_spawn_rate = 10 + self.spawn_timer_base * (20000 - min(20000, self.master_clock)) / 20000
        if self.game_timer > current_spawn_rate:
            self.game_timer = 0
            
            valid_columns = [i for i in range(len(self.stack_heights)) if self.stack_heights[i] > 4]
            if not valid_columns: return

            choices = [col for col in valid_columns if col != self.last_place] if len(valid_columns) > 1 and self.last_place in valid_columns else valid_columns
            chosen_col_index = self.random.choice(choices)
            self.last_place = chosen_col_index

            biome = self.game.biomes[self.current_biome_index]
            final_tile_type = 'tile' 
            
            elite_roll = self.random.randint(1, 100)
            if elite_roll <= 2 and 'motherlode' in biome['available_tiles']: final_tile_type = 'motherlode'
            elif elite_roll <= 5 and 'unstable' in biome['available_tiles']: final_tile_type = 'unstable'
            else:
                spawn_weights = {'tile': 70, 'fragile': 8, 'bounce': 5, 'chest': 3, 'spike': 2, 'greed': 2}
                for special, chance in biome.get('special_spawn_rate', {}).items(): spawn_weights[special] = spawn_weights.get(special, 0) + chance

                available_choices = {k: v for k, v in spawn_weights.items() if k in biome['available_tiles'] and k not in self.disabled_tiles}
                if available_choices: final_tile_type = self.random.choices(list(available_choices.keys()), list(available_choices.values()), k=1)[0]
            
            if final_tile_type == 'greed' and 'high_stakes' in self.active_curses: final_tile_type = 'spike'
            self.tile_drops.append([(chosen_col_index + 1) * self.game.TILE_SIZE, -self.height - self.game.TILE_SIZE, final_tile_type])
            
    def update_placed_tiles(self):
        to_remove = []
        for tile_pos, tile_data in self.tiles.items():
            player_on_tile_rect = pygame.Rect(tile_pos[0]*16, tile_pos[1]*16-2-self.height, 16, 18)
            player_on_tile = self.player.rect.colliderect(player_on_tile_rect)
            
            if tile_data['type'] == 'unstable' and 'timer' in tile_data['data']:
                tile_data['data']['timer'] -= 1 * self.world_time_scale
                if self.random.randint(1, 8) == 1: self.sparks.append([[(tile_pos[0] + 0.5) * self.game.TILE_SIZE, (tile_pos[1] + 0.5) * self.game.TILE_SIZE - self.height], [self.random.uniform(-0.5, 0.5), self.random.uniform(-0.5, 0.5)], self.random.uniform(2, 4), 0.1, (255, 100, 20), False, 0])
                if tile_data['data']['timer'] <= 0:
                    if tile_pos not in to_remove: to_remove.append(tile_pos)

            if tile_data['type'] == 'fragile' and 'timer' in tile_data['data']:
                tile_data['data']['timer'] -= 1 * self.world_time_scale
                if self.random.randint(1, 10) == 1: self.sparks.append([[tile_pos[0] * self.game.TILE_SIZE + self.random.random() * 16, tile_pos[1] * self.game.TILE_SIZE + 14 - self.height], [self.random.random() * 0.5 - 0.25, self.random.random() * 0.5], self.random.random() * 2 + 1, 0.08, (6, 4, 1), True, 0.05])
                if tile_data['data']['timer'] <= 0:
                    if tile_pos not in to_remove: to_remove.append(tile_pos)
                    for _ in range(20):
                        angle, speed = self.random.random() * math.pi * 2, self.random.random() * 1.5
                        self.sparks.append([[tile_pos[0] * self.game.TILE_SIZE + 8, tile_pos[1] * self.game.TILE_SIZE + 8 - self.height], [math.cos(angle) * speed, math.sin(angle) * speed], self.random.random() * 4 + 2, 0.05, (6, 4, 1), True, 0.1])
            
            if tile_data['type'] == 'conduit' and 'static_shock' in self.active_curses:
                if 'timer' not in tile_data['data']: tile_data['data']['timer'] = 0
                
                if player_on_tile:
                    tile_data['data']['timer'] += 1
                    if tile_data['data']['timer'] > 120:
                        self.handle_death()
                        tile_data['data']['timer'] = -120
                elif tile_data['data']['timer'] > 0:
                     tile_data['data']['timer'] = 0
                elif tile_data['data']['timer'] < 0:
                     tile_data['data']['timer'] += 1

        if to_remove:
            for p in to_remove:
                if p in self.tiles: del self.tiles[p]
                if self.random.random() < self.tile_coin_drop_chance:
                     self.items.append(Item(self.game.animation_manager, (p[0] * 16 + 5, p[1] * 16 + 5 - self.height), (6, 6), 'coin', self, velocity=[self.random.random() * 2 - 1, self.random.random() * -2]))
            self.recalculate_stack_heights()

    def update_tile_interactions(self):
        if self.dead: return
        for pos, data in list(self.tiles.items()):
            if data['type'] == 'chest':
                chest_render_pos = (pos[0]*self.game.TILE_SIZE, (pos[1]-1)*self.game.TILE_SIZE - self.height)
                r = pygame.Rect(chest_render_pos[0]+2, chest_render_pos[1]+6, self.game.TILE_SIZE-4, self.game.TILE_SIZE-6)
                if self.player.rect.colliderect(r):
                    self.game.sounds['chest_open'].play()
                    self.combo_multiplier += 1.0*(2 if 'glass_cannon' in self.active_perks else 1)
                    self.combo_timer = self.game.COMBO_DURATION
                    for _ in range(50):
                        self.sparks.append([[chest_render_pos[0]+8, chest_render_pos[1]+8], [self.random.random()*2-1, self.random.random()-2], self.random.random()*3+3, 0.01, (12,8,2), True, 0.05])
                    self.tiles[pos]['type'] = 'opened_chest'
                    self.player.jumps = min(self.player.jumps + 1, self.player.jumps_max)
                    self.player.attempt_jump()
                    self.player.velocity[1] = -3.5
                    
                    item_luck = 3 + self.game.save_data['upgrades']['item_luck']
                    if self.random.randint(1, 5) < item_luck:
                        item_type = self.random.choice(['warp', 'cube', 'jump', 'bomb', 'freeze', 'shield', 'hourglass'])
                        self.items.append(Item(self.game.animation_manager, (pos[0]*self.game.TILE_SIZE+5, (pos[1]-1)*self.game.TILE_SIZE+5 - self.height), (6,6), item_type, self, velocity=[self.random.random()*5-2.5, self.random.random()*2-5]))
                    else:
                        coins_mult = 2 if 'greedy' in self.active_perks else 1
                        for _ in range(self.random.randint(2,6)*coins_mult):
                            self.items.append(Item(self.game.animation_manager, (pos[0]*self.game.TILE_SIZE+5, (pos[1]-1)*self.game.TILE_SIZE+5 - self.height), (6,6), 'coin', self, velocity=[self.random.random()*5-2.5, self.random.random()*2-7]))

    def update_items(self):
        solid_rects = [pygame.Rect(p[0] * self.game.TILE_SIZE, p[1] * self.game.TILE_SIZE - self.height, self.game.TILE_SIZE, self.game.TILE_SIZE) for p in self.tiles]
        edge_rects = [pygame.Rect(0, 0, self.game.TILE_SIZE, self.game.DISPLAY_SIZE[1]), pygame.Rect(self.game.DISPLAY_SIZE[0] - self.game.TILE_SIZE, 0, self.game.TILE_SIZE, self.game.DISPLAY_SIZE[1])]
        for i, item in sorted(enumerate(self.items), reverse=True):
            item.update(solid_rects + edge_rects, self.world_time_scale)

            if item.type == 'coin' and not self.dead:
                magnet_lvl = self.game.save_data['upgrades']['coin_magnet']
                if magnet_lvl > 0:
                    dist_x, dist_y = self.player.center[0] - item.center[0], self.player.center[1] - item.center[1]
                    dist_sq = dist_x**2 + dist_y**2
                    if dist_sq < (20 + magnet_lvl * 10)**2:
                        dist = math.sqrt(dist_sq) if dist_sq > 0 else 1
                        pull_strength = 0.05 + magnet_lvl * 0.05
                        item.velocity[0] += (dist_x / dist) * self.world_time_scale
                        item.velocity[1] += (dist_y / dist) * self.world_time_scale
            
            if item.time > 30 and item.rect.colliderect(self.player.rect):
                if item.type == 'coin':
                    self.game.sounds['coin'].play()
                    self.coins += int(1 * self.combo_multiplier)
                    self.combo_multiplier += 0.1 * (2 if 'glass_cannon' in self.active_perks else 1)
                    self.combo_timer = self.game.COMBO_DURATION
                    for _ in range(25):
                        angle, speed, physics = self.random.random() * math.pi * 2, self.random.random() * 0.4, self.random.choice([False, False, False, False, True])
                        self.sparks.append([item.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], self.random.random() * 3 + 3, 0.02, (12, 8, 2), physics, 0.1 * physics])
                else:
                    self.game.sounds['collect_item'].play()
                    for _ in range(50): self.sparks.append([item.center.copy(), [self.random.random() * 0.3 - 0.15, self.random.random() * 6 - 3], self.random.random() * 4 + 3, 0.01, (12, 8, 2), False, 0])
                    if item.type == 'shield': self.player_shielded = True; (self.game.sounds['upgrade'] if 'upgrade' in self.game.sounds else self.game.sounds['collect_item']).play()
                    else: self.current_item = item.type
                self.items.pop(i)

    def update_projectiles(self):
        for i, p in sorted(enumerate(self.projectiles), reverse=True):
            p.update(self.world_time_scale)
            proj_render_rect = p.rect.copy()
            proj_render_rect.y -= int(self.height)

            if not proj_render_rect.colliderect(self.game.display.get_rect()): self.projectiles.pop(i); continue
            
            hit_tile = False
            for j, tile_drop in sorted(enumerate(self.tile_drops), reverse=True):
                r = pygame.Rect(tile_drop[0], tile_drop[1] - self.height, self.game.TILE_SIZE, self.game.TILE_SIZE)
                if proj_render_rect.colliderect(r):
                    self.game.sounds['block_land'].play(); p.health -= 1
                    for _ in range(15):
                        angle, speed = self.random.random() * math.pi * 2, self.random.random() * 2
                        self.sparks.append([[r.centerx, r.centery], [math.cos(angle) * speed, math.sin(angle) * speed], self.random.random() * 3 + 2, 0.08, (251, 245, 239), True, 0.1])
                    self.tile_drops.pop(j)
                    if p.health <= 0:
                        hit_tile = True
                        if i < len(self.projectiles): self.projectiles.pop(i)
                    self.coins += 1; self.combo_multiplier += 0.05; self.combo_timer = self.game.COMBO_DURATION; break
            if hit_tile: continue
            
            for k, data_node_rect in sorted(enumerate(self.data_nodes), reverse=True):
                data_node_render_rect = data_node_rect.copy()
                data_node_render_rect.y -= int(self.height)
                if proj_render_rect.colliderect(data_node_render_rect):
                    self.data_nodes.pop(k)
                    if i < len(self.projectiles): self.projectiles.pop(i)
                    self.screen_shake = max(self.screen_shake, 7)
                    self.game.sounds['explosion'].play()
                    for _ in range(self.random.randint(4, 8)):
                        self.items.append(Item(self.game.animation_manager, (data_node_render_rect.centerx, data_node_render_rect.bottom), (6, 6), 'coin', self, velocity=[self.random.random() * 4 - 2, self.random.random() * 2 - 6]))
                    break

    def update_player(self):
        if not self.dead:
            for tile_pos, tile_data in self.tiles.items():
                if tile_data.get('type') == 'magnetic' and 0 < tile_pos[1] * self.game.TILE_SIZE + self.height < self.game.DISPLAY_SIZE[1]:
                    self.player.velocity[0] += max(-0.25, min(0.25, (tile_pos[0] * self.game.TILE_SIZE + self.game.TILE_SIZE // 2 - self.player.center[0]) / 80)) * self.player_time_scale

            tile_pos_below_player = (self.player.rect.midbottom[0] // self.game.TILE_SIZE, (self.player.rect.midbottom[1] + self.height) // self.game.TILE_SIZE)
            if self.player.collisions['bottom'] and tile_pos_below_player in self.tiles:
                tile_type = self.tiles[tile_pos_below_player]['type']
                if tile_type == 'conveyor_l': self.player.velocity[0] -= 0.15 * self.player_time_scale
                elif tile_type == 'conveyor_r': self.player.velocity[0] += 0.15 * self.player_time_scale
        
            tile_rects = [pygame.Rect(p[0] * self.game.TILE_SIZE, p[1] * self.game.TILE_SIZE - self.height, self.game.TILE_SIZE, self.game.TILE_SIZE) for p in self.tiles]
            edge_rects = [pygame.Rect(0, 0, self.game.TILE_SIZE, self.game.DISPLAY_SIZE[1]), pygame.Rect(self.game.TILE_SIZE * (self.game.WINDOW_TILE_SIZE[0] - 1), 0, self.game.TILE_SIZE, self.game.DISPLAY_SIZE[1])]
            
            original_speed = self.player.speed
            if 'heavy_feet' in self.active_curses: self.player.speed *= 0.85
            
            collisions = self.player.update(self.tile_drop_rects + edge_rects + tile_rects, self.player_time_scale)
            self.player.speed = original_speed

            if not collisions['bottom']:
                for side in ['left', 'right']:
                    player_side_y, player_side_x = self.player.rect.centery, self.player.rect.left - 2 if side == 'left' else self.player.rect.right + 2
                    tile_pos_side = (player_side_x // self.game.TILE_SIZE, (player_side_y + self.height) // self.game.TILE_SIZE)
                    if tile_pos_side in self.tiles and self.tiles.get(tile_pos_side, {}).get('type') == 'sticky': self.player.velocity[1] = min(self.player.velocity[1], 1.0)

            if collisions['bottom']:
                if tile_pos_below_player in self.tiles:
                    tile_type = self.tiles[tile_pos_below_player]['type']
                    if tile_type == 'fragile' and 'timer' not in self.tiles[tile_pos_below_player]['data']: self.game.sounds['block_land'].play(); self.tiles[tile_pos_below_player]['data']['timer'] = 90
                    elif tile_type == 'geyser' and self.tiles[tile_pos_below_player].get('data', {}).get('timer', 0) <= 0: self.tiles[tile_pos_below_player]['data']['timer'] = 120 # Cooldown
                    elif tile_type == 'bounce': self.player.velocity[1] = -9; self.player.jumps = self.player.jumps_max; self.game.sounds['super_jump'].play(); self.screen_shake = 10; self.combo_multiplier += 0.5; self.combo_timer = self.game.COMBO_DURATION
                    elif tile_type == 'spike': self.handle_death(); self.player.velocity = [0, -4]
                    elif tile_type == 'conduit':
                        for _ in range(4):
                            angle = self.random.random() * math.pi * 2
                            speed = self.random.random() * 1.5
                            self.sparks.append([list(self.player.rect.midbottom), [math.cos(angle) * speed, math.sin(angle) * speed - 0.5], self.random.random() * 2 + 1, 0.1, (100, 150, 255), True, 0.02])
                        self.player.focus_meter = min(self.player.FOCUS_METER_MAX, self.player.focus_meter + 1.5)

            # Update tile timers (like geyser)
            for pos, data in self.tiles.items():
                if data.get('type') == 'geyser' and data.get('data', {}).get('timer', 0) > 0:
                    data['data']['timer'] -= 1 * self.world_time_scale
                    if int(data['data']['timer']) == 90: # Erupt
                        self.game.sounds['super_jump'].play(); self.screen_shake = 10
                        for _ in range(40):
                            angle = self.random.uniform(math.pi * 1.2, math.pi * 1.8)
                            speed = self.random.uniform(1.5, 3.5)
                            self.sparks.append([[pos[0]*16 + 8, pos[1]*16 - self.height], [math.cos(angle) * speed, math.sin(angle) * speed * 2], self.random.random() * 3 + 2, 0.04, (200, 200, 255), True, 0.1])
                        p_rect = self.player.rect.copy(); p_rect.y += 2
                        geyser_render_rect = pygame.Rect(pos[0]*16, pos[1]*16 - self.height, 16, 16)
                        if p_rect.colliderect(geyser_render_rect):
                            self.player.velocity[1] = -11; self.player.jumps = self.player.jumps_max
        else:
            self.player.opacity = 80; self.player.update([], self.player_time_scale); self.player.rotation -= 16
    
    def update_sparks(self):
        for i, spark in sorted(enumerate(self.sparks), reverse=True):
            if len(spark) < 8: spark.append(False)
            if not spark[7]: spark[1][1] = min(spark[1][1] + spark[6], 3)
            spark[0][0] += spark[1][0] * self.world_time_scale
            tile_world_pos = (int(spark[0][0] // self.game.TILE_SIZE), int((spark[0][1] + self.height) // self.game.TILE_SIZE))

            if spark[5]:
                if not (self.game.TILE_SIZE <= spark[0][0] < self.game.DISPLAY_SIZE[0] - self.game.TILE_SIZE):
                     spark[0][0] -= spark[1][0] * self.world_time_scale; spark[1][0] *= -0.7
                elif tile_world_pos in self.tiles:
                    spark[0][0] -= spark[1][0] * self.world_time_scale; spark[1][0] *= -0.7
            spark[0][1] += spark[1][1] * self.world_time_scale
            if spark[5] and tile_world_pos in self.tiles:
                spark[0][1] -= spark[1][1] * self.world_time_scale; spark[1][1] *= -0.7
                if abs(spark[1][1]) < 0.2: spark[1][1] = 0; spark[7] = True
            spark[2] -= spark[3] * self.world_time_scale
            if spark[2] <= 1: self.sparks.pop(i)
    
    def update_scrolling(self):
        if self.tiles:
            try:
                highest_base_row = max(p[1] for p in self.tiles.keys()) -1
                for y in range(highest_base_row, 0, -1):
                    is_full_row = all((i + 1, y) in self.tiles for i in range(self.game.WINDOW_TILE_SIZE[0] - 2))
                    if is_full_row:
                        self.target_height = (y - self.game.WINDOW_TILE_SIZE[1] + 2) * self.game.TILE_SIZE
                        break
            except ValueError: pass
        if abs(self.height - self.target_height) > 0.01:
            self.height += (self.target_height - self.height) / 10
        if abs(self.height - self.target_height) < 0.2:
             self.height = self.target_height
             offscreen_y = self.target_height / self.game.TILE_SIZE
             to_remove = [pos for pos in self.tiles if pos[1] > offscreen_y + self.game.WINDOW_TILE_SIZE[1] + 2]
             if to_remove:
                 for pos in to_remove: del self.tiles[pos]
                 self.recalculate_stack_heights()

    def fire_projectile(self, keys):
        tile_pos_below = (self.player.rect.midbottom[0] // self.game.TILE_SIZE, (self.player.rect.midbottom[1] + self.height) // self.game.TILE_SIZE)
        player_on_prism = self.player.collisions['bottom'] and tile_pos_below in self.tiles and self.tiles.get(tile_pos_below, {}).get('type') == 'prism'

        self.game.sounds['shoot'].play(); speed = 4;
        if keys[K_UP] or keys[K_w]: vel, pos = [0, -speed], [self.player.rect.centerx, self.player.rect.top]
        elif keys[K_DOWN] or keys[K_s]: vel, pos = [0, speed], [self.player.rect.centerx, self.player.rect.bottom]
        elif self.player.flip[0]: vel, pos = [speed, 0], [self.player.rect.right, self.player.rect.centery]
        else: vel, pos = [-speed, 0], [self.player.rect.left, self.player.rect.centery]
        
        # Convert player's screen position to world position for the projectile
        pos[1] += int(self.height)
        
        # Create a muzzle flash/spark effect at the firing point
        spark_pos_screen = [pos[0], pos[1] - int(self.height)]
        for _ in range(12):
            angle = random.random() * math.pi * 2
            speed = random.random() * 1.5
            spark_vel = [math.cos(angle) * speed, math.sin(angle) * speed]
            self.sparks.append([spark_pos_screen.copy(), spark_vel, random.random() * 2 + 1, 0.1, (255, 230, 180), False, 0])

        if player_on_prism:
            self.game.sounds['upgrade'].play()
            angle, spread = math.atan2(vel[1], vel[0]), 0.4
            self.projectiles.append(Projectile(self.game.animation_manager, pos, (6, 2), 'projectile', self, velocity=vel))
            self.projectiles.append(Projectile(self.game.animation_manager, pos, (6, 2), 'projectile', self, velocity=[math.cos(angle - spread) * speed, math.sin(angle - spread) * speed]))
            self.projectiles.append(Projectile(self.game.animation_manager, pos, (6, 2), 'projectile', self, velocity=[math.cos(angle + spread) * speed, math.sin(angle + spread) * speed]))
        else:
            self.projectiles.append(Projectile(self.game.animation_manager, pos, (6, 2), 'projectile', self, velocity=vel))
        
    def render_background(self, surf):
        biome = self.game.biomes[self.current_biome_index]; surf.fill(biome['bg_color'])
        if 'far' in self.game.backgrounds and self.game.backgrounds['far']:
            scroll_y = (self.height * 0.2) % self.game.DISPLAY_SIZE[1]
            surf.blit(self.game.backgrounds['far'], (0, scroll_y)); surf.blit(self.game.backgrounds['far'], (0, scroll_y - self.game.DISPLAY_SIZE[1]))
        if 'near' in self.game.backgrounds and self.game.backgrounds['near']:
            scroll_y = (self.height * 0.4) % self.game.DISPLAY_SIZE[1]
            surf.blit(self.game.backgrounds['near'], (0, scroll_y)); surf.blit(self.game.backgrounds['near'], (0, scroll_y - self.game.DISPLAY_SIZE[1]))

    def render_plasma(self, surf):
        if self.plasma_y < self.game.DISPLAY_SIZE[1] + self.height:
            plasma_rect = pygame.Rect(0, int(self.plasma_y - self.height), self.game.DISPLAY_SIZE[0], self.game.DISPLAY_SIZE[1] - int(self.plasma_y - self.height))
            base_color, highlight_color = (255, 60, 20), (255, 150, 40)
            color = highlight_color if self.master_clock % 20 < 10 else base_color
            pygame.draw.rect(surf, color, plasma_rect)
            if self.master_clock % 4 == 0:
                pos = [self.random.randint(0, self.game.DISPLAY_SIZE[0]), self.plasma_y - self.height + 5]
                self.sparks.append([pos, [0, -self.random.random() * 0.5], self.random.random() * 2 + 1, 0.08, color, False, 0])

    def render_data_nodes(self, surf):
        for data_node_rect in self.data_nodes:
            render_pos = (data_node_rect.x, data_node_rect.y - self.height)
            if -32 < render_pos[1] < self.game.DISPLAY_SIZE[1]:
                surf.blit(self.data_node_img, render_pos)

    def render_placed_tiles(self, surf):
        for pos, data in self.tiles.items():
            blit_pos = (pos[0] * self.game.TILE_SIZE, pos[1] * self.game.TILE_SIZE - int(self.height))
            if blit_pos[1] < -self.game.TILE_SIZE or blit_pos[1] > self.game.DISPLAY_SIZE[1]: continue
                
            img_map = {'placed_tile': self.placed_tile_img, 'greed': self.greed_tile_img, 'magnetic': self.magnetic_tile_img,
                       'unstable': self.unstable_tile_img, 'sticky': self.sticky_tile_img, 'fragile': self.fragile_tile_img,
                       'bounce': self.bounce_tile_img, 'spike': self.spike_tile_img, 'prism': self.prism_tile_img, 
                       'geyser': self.geyser_tile_img, 'conduit': self.conduit_tile_img,
                       'conveyor_l': self.conveyor_l_img, 'conveyor_r': self.conveyor_r_img}
            
            img_to_blit = img_map.get(data.get('type'), self.tile_img)
            surf.blit(img_to_blit, blit_pos)

            if data['type'] in ['tile', 'placed_tile'] and (pos[0], pos[1]-1) not in self.tiles: surf.blit(self.tile_top_img, blit_pos)
            if data.get('type') == 'chest':
                surf.blit(self.chest_img, (blit_pos[0], blit_pos[1] - self.game.TILE_SIZE))
            elif data.get('type') == 'opened_chest': surf.blit(self.opened_chest_img, (blit_pos[0], blit_pos[1] - self.game.TILE_SIZE))
            
            if data.get('type') == 'geyser' and data.get('data', {}).get('timer', 0) > 90 and self.master_clock % 5 < 3:
                angle, speed = self.random.uniform(math.pi * 1.3, math.pi * 1.7), self.random.uniform(0.5, 1.2)
                self.sparks.append([[blit_pos[0]+8, blit_pos[1]+2], [math.cos(angle)*speed*0.5, math.sin(angle)*speed], self.random.uniform(1,3), 0.1, (200,200,255), False, 0])
            if data.get('type') == 'conduit' and self.master_clock % 4 == 0:
                self.sparks.append([
                    [blit_pos[0] + self.random.random() * 16, blit_pos[1] + self.random.random() * 16],
                    [0, 0], self.random.random() * 1.5, 0.1, (150, 180, 255), False, 0
                ])


    def render_falling_tiles(self, surf):
        for tile in self.tile_drops:
            pos = (tile[0], tile[1] - self.height)
            if pos[1] < -self.game.TILE_SIZE or pos[1] > self.game.DISPLAY_SIZE[1]: continue
            
            img_map = {'greed': self.greed_tile_img, 'motherlode': self.motherlode_tile_img, 'unstable': self.unstable_tile_img,
                       'magnetic': self.magnetic_tile_img, 'sticky': self.sticky_tile_img, 'fragile': self.fragile_tile_img,
                       'bounce': self.bounce_tile_img, 'spike': self.spike_tile_img, 'prism': self.prism_tile_img, 
                       'geyser': self.geyser_tile_img, 'conduit': self.conduit_tile_img,
                       'conveyor_l': self.conveyor_l_img, 'conveyor_r': self.conveyor_r_img}
            img_to_blit = img_map.get(tile[2], self.tile_img)
            surf.blit(img_to_blit, pos)
            
            if tile[2] == 'chest': surf.blit(self.ghost_chest_img, (pos[0], pos[1] - self.game.TILE_SIZE))
            if self.random.randint(1, 4) == 1:
                side = self.random.choice([-1, 1])
                self.sparks.append([[pos[0] + self.game.TILE_SIZE * (side > 0), pos[1]], [self.random.uniform(-0.05, 0.05), self.random.uniform(0, 0.5)], self.random.uniform(3,5), 0.15, (4,2,12), False, 0])

    def render_items(self, surf):
        for item in self.items:
            item.render(surf, (0, 0)) # Items positions are already in screen space

    def render_projectiles(self, surf):
        for p in self.projectiles: p.render(surf, (0, self.height))

    def render_shield_aura(self, surf):
        if self.player_shielded and not self.dead:
            # 1. Determine the pulsing size and create the new scaled image first.
            pulse = math.sin(self.master_clock / 8) * 2
            pulsing_size = (int(self.shield_aura_img.get_width() + pulse), int(self.shield_aura_img.get_height() + pulse))
            pulsing = pygame.transform.scale(self.shield_aura_img, pulsing_size)

            # 2. Now, calculate the position based on the NEW scaled image's dimensions to keep it centered.
            aura_pos = (self.player.rect.centerx - pulsing.get_width() // 2, self.player.rect.centery - pulsing.get_height() // 2)
            
            # 3. Set transparency and blit the correctly centered, pulsing aura.
            pulsing.set_alpha(150 - pulse * 10)
            surf.blit(pulsing, aura_pos, special_flags=BLEND_RGBA_ADD)
        
    def render_sparks(self, surf):
        for spark in self.sparks:
            size = int(spark[2])
            pos = (spark[0][0], spark[0][1])
            if size > 0:
                glow_size = int(size * 1.5 + 2)
                surf.blit(glow_img(glow_size, (int(spark[4][0]/2),int(spark[4][1]/2),int(spark[4][2]/2))), (pos[0]-glow_size, pos[1]-glow_size), special_flags=BLEND_RGBA_ADD)
                surf.blit(glow_img(size, spark[4]), (pos[0]-size, pos[1]-size), special_flags=BLEND_RGBA_ADD)
    
    def render_borders(self, surf):
        scroll_offset = self.height % self.game.TILE_SIZE
        for i in range(self.game.WINDOW_TILE_SIZE[1] + 2):
            y_pos = i * self.game.TILE_SIZE - scroll_offset
            surf.blit(self.edge_tile_img, (0, y_pos))
            surf.blit(self.edge_tile_img, (self.game.TILE_SIZE * (self.game.WINDOW_TILE_SIZE[0] - 1), y_pos))

    def render_hud(self, surface):
        # --- Top-Left HUD (Coins Only) ---
        x_offset = 6
        surface.blit(self.coin_icon, (x_offset, 5))
        x_offset += self.coin_icon.get_width() + 4
        self.game.black_font.render(str(self.coins), surface, (x_offset + 1, 8))
        self.game.white_font.render(str(self.coins), surface, (x_offset, 7))

        # --- Combo Meter ---
        if self.combo_multiplier > 1.0:
            text = f"x{self.combo_multiplier:.1f}"
            w = self.game.white_font.width(text, 2)
            x, y = self.game.DISPLAY_SIZE[0] // 2 - w // 2, 4
            color = (255, 255, 255) if self.master_clock % 20 > 10 else (255, 150, 40)
            combo_font = Font(self.game.get_path('data', 'fonts', 'small_font.png'), color)
            self.game.black_font.render(text, surface, (x + 1, y + 1), scale=2)
            combo_font.render(text, surface, (x, y), scale=2)
            bar_w = (self.combo_timer / self.game.COMBO_DURATION) * 60
            bar_x = self.game.DISPLAY_SIZE[0] // 2 - 30
            pygame.draw.rect(surface, (0, 0, 1), [bar_x, 21, 60, 4])
            pygame.draw.rect(surface, (251, 245, 239), [bar_x, 20, bar_w, 4])

        # --- Top-Right HUD (Item & Focus Ring) ---
        item_slot_center = (self.game.DISPLAY_SIZE[0] - 22, 18)
        focus_bg_radius = 13
        focus_radius = 12
        focus_pct = self.player.focus_meter / self.player.FOCUS_METER_MAX
        
        # Draw the solid background circle
        pygame.draw.circle(surface, (211, 148, 81), item_slot_center, focus_bg_radius)
        
        if self.player.is_charging_dash:
            focus_color = (255, 255, 255) if self.master_clock % 10 < 5 else (255, 150, 40)
        else:
            focus_color = (80, 150, 255) if self.player.focus_meter >= self.player.FOCUS_DASH_COST else (100, 60, 20)
        
        # Draw the dark inner ring for the gauge track
        pygame.draw.circle(surface, (10, 20, 40), item_slot_center, focus_radius, 3)
        
        if focus_pct > 0:
            start_angle = math.pi / 2
            end_angle = start_angle - (2 * math.pi * focus_pct)
            arc_rect = pygame.Rect(item_slot_center[0] - focus_radius, item_slot_center[1] - focus_radius, focus_radius * 2, focus_radius * 2)
            pygame.draw.arc(surface, focus_color, arc_rect, end_angle, start_angle, 3)
        
        # Blit item icon
        if self.current_item:
            icon = self.game.item_icons[self.current_item]
            icon_pos = (item_slot_center[0] - icon.get_width() // 2, item_slot_center[1] - icon.get_height() // 2)
            surface.blit(icon, icon_pos)

        # --- Directive ---
        if self.directive:
            prop_y = self.game.DISPLAY_SIZE[1] - 20 
            prop_text = self.directive.get('flavor_text', "Directive...")
            if self.directive.get('completed', False):
                prop_text = "Directive Complete!"
                color = (255, 230, 90) if self.master_clock % 20 > 10 else (255, 255, 255)
                prop_font = Font(self.game.get_path('data', 'fonts', 'small_font.png'), color)
                w = prop_font.width(prop_text)
                prop_font.render(prop_text, surface, (self.game.DISPLAY_SIZE[0] // 2 - w // 2, prop_y))
            else:
                progress = f"({int(self.directive_progress)}/{self.directive.get('value', '?')})"
                w_text = self.game.white_font.width(prop_text)
                w_prog = self.game.white_font.width(progress)
                self.game.white_font.render(prop_text, surface, (self.game.DISPLAY_SIZE[0] // 2 - (w_text + w_prog + 5) // 2, prop_y))
                self.game.white_font.render(progress, surface, (self.game.DISPLAY_SIZE[0] // 2 - (w_text + w_prog + 5) // 2 + w_text + 5, prop_y))

        # --- Perk Icons (Panel Removed) ---
        if self.active_perks:
            x_off = 6
            y_pos = self.game.DISPLAY_SIZE[1] - 18
            for key in sorted(list(self.active_perks)):
                if key in self.game.perk_icons:
                    icon = self.game.perk_icons[key]
                    surface.blit(icon, (x_off, y_pos))
                    x_off += icon.get_width() + 2