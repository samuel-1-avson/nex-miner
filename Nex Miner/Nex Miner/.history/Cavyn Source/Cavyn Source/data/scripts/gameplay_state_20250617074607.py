
# Cavyn Source/data/scripts/gameplay_state.py

import pygame, sys, random, math, json
from pygame.locals import *

# Core game state and entity imports
from .state import State
from .text import Font
from .entities.player import Player
from .entities.item import Item
from .entities.projectile import Projectile
from .entities.bat import Bat # NEW: Import the Bat entity

# Imports for state transitions and utilities
from .game_states.pause_state import PauseState
from .game_states.perk_selection_state import PerkSelectionState
from .game_states.curse_selection_state import CurseSelectionState
from .core_funcs import load_img
from .ui_utils import glow_img, render_panel_9slice # CORRECTED IMPORT: No longer defined in this file

# Late import to prevent circular dependency
GameOverState = None


# =========================================================================
# === MAIN GAMEPLAY STATE CLASS ===
# =========================================================================

class GameplayState(State):
    def __init__(self, game, mode="classic", challenge_config=None, start_biome_index=0):
        super().__init__(game)
        
        # Late import pattern to resolve circular dependency
        global GameOverState
        if GameOverState is None:
            from .game_states.game_over_state import GameOverState

        self.mode = mode
        self.challenge_config = challenge_config
        self.start_biome_index = start_biome_index
        self.lava_y = self.game.DISPLAY_SIZE[1] + 50
        self.special_entity_timer = 0
        self.crystals = []
        self.enemies = []
        self.load_state_assets()
        self.reset()

    def load_state_assets(self):
        """Loads assets specific to the gameplay state using robust paths."""
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
        
        # Load assets for new biome mechanics
        try:
            self.prism_tile_img = load_img(self.game.get_path('data', 'images', 'prism_tile.png'))
            self.geyser_tile_img = load_img(self.game.get_path('data', 'images', 'geyser_tile.png'))
            self.crystal_img = load_img(self.game.get_path('data', 'images', 'crystal.png'))
            self.conduit_tile_img = load_img(self.game.get_path('data', 'images', 'tile_conduit.png'))
        except pygame.error as e:
            print(f"WARNING: Could not load new biome asset. Did you add it to data/images/? Error: {e}")
            self.prism_tile_img = pygame.Surface((16, 16)); self.prism_tile_img.fill((255, 0, 255))
            self.geyser_tile_img = pygame.Surface((16, 16)); self.geyser_tile_img.fill((255, 0, 255))
            self.crystal_img = pygame.Surface((16, 24)); self.crystal_img.fill((255, 0, 255))
            self.conduit_tile_img = pygame.Surface((16, 16)); self.conduit_tile_img.fill((0, 255, 255))
        
        self.perk_icons = {}
        for perk_name in self.game.perks.keys():
            try:
                icon_path = self.game.get_path('data', 'images', 'perk_icons', f'{perk_name}.png')
                self.perk_icons[perk_name] = load_img(icon_path)
            except pygame.error:
                # Icon doesn't exist, will be skipped during render
                pass

    def enter_state(self):
        super().enter_state()
        if self.mode == "classic" and self.perks_gained_this_run > 0 and self.perks_gained_this_run % 2 == 0:
            if self.perks_gained_this_run != self.last_curse_check:
                self.last_curse_check = self.perks_gained_this_run
                
                available_curses = list(set(self.game.curses.keys()) - self.active_curses)
                if available_curses:
                    curses_to_offer = random.sample(available_curses, k=min(3, len(available_curses)))
                    background_surf = self.game.display.copy()
                    self.render(background_surf)
                    self.game.push_state(CurseSelectionState(self.game, self, curses_to_offer, background_surf))

    def reset(self):
        self.game.save_data['stats']['runs_started'] += 1
        selected_char_key = self.game.save_data['characters']['selected']
        character_data = self.game.characters.get(selected_char_key, self.game.characters['cavyn'])
        
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
        self.ghosts = []
        self.enemies = []
        self.freeze_timer, self.game_timer, self.master_clock = 0, 0, 0
        self.height, self.target_height = 0, 0
        self.coins = 0
        self.invincibility_timer = 0
        
        self.current_item = None
        if self.game.save_data['upgrades'].get('starting_item', 0) > 0:
            possible_items = ['cube', 'jump', 'bomb', 'shield', 'freeze', 'hourglass']
            self.current_item = random.choice(possible_items)
            if self.current_item not in self.game.save_data['compendium']['items']:
                self.game.save_data['compendium']['items'].append(self.current_item)

        if 'starting_item' in character_data['mods']:
            self.current_item = character_data['mods']['starting_item']

        self.tile_coin_drop_chance = 0
        self.player_shielded = False
        equipped_artifact_key = self.game.save_data['artifacts']['equipped']
        if equipped_artifact_key:
            artifact_mod = self.game.artifacts[equipped_artifact_key]['mod']
            if artifact_mod['type'] == 'start_with_shield': self.player_shielded = True
            if artifact_mod['type'] == 'focus_cost_multiplier': self.player.FOCUS_DASH_COST *= artifact_mod['value']
            if artifact_mod['type'] == 'tile_coin_drop_chance': self.tile_coin_drop_chance = artifact_mod['value']
        
        self.prophecy = self.game.save_data.get('active_prophecy')
        self.prophecy_progress = 0
        if self.prophecy:
            self.prophecy['completed'] = False
            self.prophecy = json.loads(json.dumps(self.prophecy)) # Deep copy
            if 'fortune_finder' in self.active_perks:
                self.prophecy['value'] = int(self.prophecy['value'] * 0.75)
        self.game.save_data['active_prophecy'] = None
        
        self.item_used = False
        self.curse_reroll_available = self.game.save_data['upgrades'].get('curse_reroll', 0) > 0
        
        self.time_meter, self.time_scale, self.slowing_time = self.game.time_meter_max, 1.0, False
        self.screen_shake = 0
        self.combo_shield_used = False
        self.last_perk_score = 0
        self.combo_timer = 0
        self.last_curse_check = 0
        self.perks_gained_this_run = 0

        # Game Mode Setup
        if self.mode == "challenge":
            self.player.pos[1] = 13 * 16 # Adjust player start for challenges
            self.tiles = {tuple(pos): {'type': tile_type, 'data': {}} for pos, tile_type in self.challenge_config['start_layout']}
            self.tile_drops = []
            for t in self.challenge_config.get('falling_tiles', []):
                 self.tile_drops.append([(self.game.WINDOW_TILE_SIZE[0] // 2) * self.game.TILE_SIZE, -self.height - self.game.TILE_SIZE, t])
            self.spawn_timer_base, self.disabled_tiles, self.active_curses, self.combo_multiplier = 999999, set(), set(), 1.0
        elif self.mode == "zen":
            self.spawn_timer_base, self.disabled_tiles, self.active_curses, self.combo_multiplier = 80, {'spike', 'unstable'}, set(), 1.0
            pygame.mixer.music.set_volume(0.3 * self.game.save_data['settings'].get('music_volume', 1.0))
        elif self.mode == "hardcore":
            self.spawn_timer_base, self.disabled_tiles, self.combo_multiplier = 25, set(), 1.5
            curses_pool = list(self.game.curses.keys())
            self.active_curses = {random.choice(curses_pool)} if curses_pool else set()
        else: # Classic
            self.spawn_timer_base, self.disabled_tiles, self.active_curses, self.combo_multiplier = 45, set(), set(), 1.0

        if self.mode != "challenge":
            for i in range(self.game.WINDOW_TILE_SIZE[0] - 2): self.tiles[(i + 1, self.game.WINDOW_TILE_SIZE[1] - 1)] = {'type': 'tile', 'data': {}}
            self.tiles[(1, self.game.WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
            self.tiles[(self.game.WINDOW_TILE_SIZE[0] - 2, self.game.WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}

        self.lava_y, self.crystals, self.special_entity_timer = self.game.DISPLAY_SIZE[1] + 50, [], 0
            
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
                self.update_biome(); self.update_combo_meter(); self.update_perk_offering(); self.update_prophecy()
                self.update_tile_spawning(); self.update_ambient_hazards(); self.update_special_entities()
        if self.screen_shake > 0: self.screen_shake -= 0.5 * self.time_scale
        if self.freeze_timer > 0: self.freeze_timer -= 1 * self.time_scale
        if self.invincibility_timer > 0: self.invincibility_timer -= 1 * self.time_scale
        self.update_enemies()
        self.update_ghosts(); self.update_falling_tiles(); self.update_placed_tiles()
        self.update_tile_interactions(); self.update_items(); self.update_projectiles()
        self.update_player(); self.update_sparks(); self.update_scrolling()
        if self.mode == 'challenge': self.check_challenge_conditions()
        
    def check_challenge_conditions(self):
        if self.dead: return
        win_con = self.challenge_config['win_condition']
        lose_con = self.challenge_config.get('lose_condition')
        
        if lose_con:
            if lose_con['type'] == 'max_place' and len(self.tile_drops) > lose_con['value']:
                self.handle_death()
                return 
        
        if win_con['type'] == 'reach_y':
            goal_pos = None
            for pos, tile_type in self.challenge_config['start_layout']:
                if tile_type == 'goal': goal_pos = tuple(pos); break
            
            if goal_pos:
                goal_rect = pygame.Rect(goal_pos[0]*16, goal_pos[1]*16-self.height, 16, 16)
                if self.player.rect.colliderect(goal_rect):
                    self.handle_challenge_win()

    def handle_challenge_win(self):
        if not self.dead:
            self.dead = True 
            if self.game.sounds.get('upgrade'): self.game.sounds['upgrade'].play()
            self.game.pop_state()

    def render(self, surface):
        self.render_background(surface)
        if self.freeze_timer > 0:
            freeze_overlay = pygame.Surface(self.game.DISPLAY_SIZE, pygame.SRCALPHA)
            alpha = 60 + math.sin(self.master_clock / 5) * 10
            freeze_overlay.fill((170, 200, 255, alpha)); surface.blit(freeze_overlay, (0, 0))
        
        self.render_challenge_goal(surface)
        self.render_lava(surface); self.render_crystals(surface); self.render_ghosts(surface)
        self.render_placed_tiles(surface); self.render_falling_tiles(surface)
        for enemy in self.enemies:
            enemy.render(surface, (0, -self.height)) 
        self.render_items(surface); self.render_projectiles(surface)
        self.render_shield_aura(surface)

        if not (self.invincibility_timer > 0 and self.master_clock % 6 < 3):
            self.player.render(surface, (0, -int(self.height)))
            
        self.render_sparks(surface); self.render_borders(surface); self.render_hud(surface)
        
    def render_challenge_goal(self, surface):
        if self.mode == 'challenge':
            for pos, tile_type in self.challenge_config['start_layout']:
                if tile_type == 'goal':
                    goal_pos = (pos[0] * self.game.TILE_SIZE, pos[1] * self.game.TILE_SIZE - int(self.height))
                    goal_icon = self.game.item_icons['jump']
                    alpha = 128 + math.sin(self.master_clock / 20) * 127
                    goal_icon.set_alpha(int(alpha))
                    surface.blit(goal_icon, goal_pos, special_flags=BLEND_RGBA_ADD)
                    goal_icon.set_alpha(255) # Reset alpha

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
                angle, speed = random.random() * math.pi * 2, random.random() * 2
                self.sparks.append([self.player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.uniform(2, 4), 0.05, (170, 200, 255), True, 0.05])
            return

        self.dead = True
        self.game.save_data['stats']['total_coins'] += self.coins
        self.game.sounds['death'].play() if 'death' in self.game.sounds else None
        self.screen_shake = 20
        
        for i in range(120):
            angle, speed, physics = random.random() * math.pi * 2, random.random() * 2, random.choice([False, True])
            self.sparks.append([self.player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.04, (18, 2, 2), physics, 0.1 * physics])
            
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
        if self.mode != "zen" and self.current_biome_index + 1 < len(self.game.biomes) and self.coins >= self.game.biomes[self.current_biome_index + 1]['score_req']:
            next_biome_index += 1
        if next_biome_index != self.current_biome_index:
            self.current_biome_index = next_biome_index;
            self.game.load_biome_bgs(self.game.biomes[self.current_biome_index])
            new_biome_name = self.game.biomes[self.current_biome_index]['name']
            if new_biome_name not in self.game.save_data['biomes_unlocked']:
                self.game.save_data['biomes_unlocked'].append(new_biome_name)
                self.game.write_save(self.game.save_data)
            self.game.sounds['warp'].play(); self.screen_shake = 15; self.lava_y = self.game.DISPLAY_SIZE[1] + 50; self.crystals = []
            
    def update_ambient_hazards(self):
        if self.mode == 'challenge': return
        if 'ambient_hazard' in self.game.biomes[self.current_biome_index]:
            hazard = self.game.biomes[self.current_biome_index]['ambient_hazard']
            if hazard['type'] == 'rising_lava': 
                self.lava_y -= hazard['speed'] * self.time_scale
                if self.player.pos[1] > self.lava_y: self.handle_death()

    def update_special_entities(self):
        if self.mode == 'challenge': return
        entity_config = self.game.biomes[self.current_biome_index].get('special_entities')
        self.special_entity_timer += 1 * self.time_scale

        if entity_config:
            if self.special_entity_timer > entity_config.get('spawn_rate', 9999):
                if entity_config['type'] == 'crystal':
                    valid_cols = [i for i, h in enumerate(self.stack_heights) if h > 4]
                    if valid_cols:
                        x_pos = (random.choice(valid_cols) + 1) * self.game.TILE_SIZE
                        self.crystals.append(pygame.Rect(x_pos, -self.height - 24, 16, 24))
        
        # Enemy Spawning (Example logic, can be refined in biomes.json)
        if self.special_entity_timer > 300: # Every ~5 seconds
            self.special_entity_timer = 0
            if self.current_biome_index > 0 and len(self.enemies) < 3: # Only spawn bats after the first biome for now
                spawn_side = -10 if random.random() < 0.5 else self.game.DISPLAY_SIZE[0] + 10
                spawn_y = random.randint(20, self.game.DISPLAY_SIZE[1] - 50)
                # Note: enemy Y position must be in world-space, so we subtract scroll (height)
                self.enemies.append(Bat(self.game.animation_manager, [spawn_side, spawn_y - self.height], (8, 8), self))
        
        for i, crystal_rect in sorted(enumerate(self.crystals), reverse=True):
            crystal_screen_rect = pygame.Rect(crystal_rect.x, crystal_rect.y - self.height, crystal_rect.width, crystal_rect.height)
            if self.player.dash_timer > 0 and self.player.rect.colliderect(crystal_screen_rect):
                self.crystals.pop(i)
                self.coins += 5 * int(self.combo_multiplier)
                self.combo_multiplier += 0.5 * (2 if 'glass_cannon' in self.active_perks else 1)
                self.combo_timer = self.game.COMBO_DURATION
                self.game.sounds['explosion'].play(); self.screen_shake = max(self.screen_shake, 6)
                for k in range(20):
                    angle, speed = random.random() * math.pi * 2, random.random() * 2.5
                    self.sparks.append([list(crystal_screen_rect.center), [math.cos(angle) * speed, math.sin(angle) * speed], random.uniform(2, 5), 0.08, (200, 220, 255), True, 0.1])
                continue

            if self.freeze_timer <= 0: crystal_rect.y += 1.6 * self.time_scale
            if self.player.rect.colliderect(crystal_screen_rect): self.crystals.pop(i); self.handle_death()
            
            check_pos = (int(crystal_rect.centerx // self.game.TILE_SIZE), int(math.floor(crystal_rect.bottom / self.game.TILE_SIZE)))
            if check_pos in self.tiles:
                self.crystals.pop(i); self.screen_shake = max(self.screen_shake, 7); self.game.sounds['explosion'].play()
                for k in range(random.randint(4, 8)):
                    self.items.append(Item(self.game.animation_manager, (crystal_rect.centerx, crystal_rect.bottom), (6, 6), 'coin', self, velocity=[random.random() * 4 - 2, random.random() * 2 - 6]))
                    
    def update_enemies(self):
        player_real_pos = (self.player.center[0], self.player.center[1] + self.height)
        for i, enemy in sorted(enumerate(self.enemies), reverse=True):
            # Pass player's real position (world space) to enemy AI
            enemy.update(player_real_pos, self.time_scale if self.freeze_timer <= 0 else 0)

            # Get the enemy's on-screen rectangle for collision with player/UI elements
            enemy_screen_rect = enemy.rect.copy()
            enemy_screen_rect.y -= self.height

            if self.player.dash_timer > 0 and self.player.rect.colliderect(enemy_screen_rect):
                enemy.on_death()
                self.enemies.pop(i)
                self.combo_multiplier += 0.4
                self.combo_timer = self.game.COMBO_DURATION
                self.coins += 3
                continue

            if self.player.rect.colliderect(enemy_screen_rect):
                self.handle_death()
                continue
            
            for j, p in sorted(enumerate(self.projectiles), reverse=True):
                # Projectile positions are already in screen space
                projectile_screen_rect = pygame.Rect(p.pos[0], p.pos[1] - self.height, p.size[0], p.size[1])
                if projectile_screen_rect.colliderect(enemy_screen_rect):
                    enemy.on_death()
                    self.enemies.pop(i)
                    if j < len(self.projectiles): self.projectiles.pop(j)
                    break
                    
            # Check if off-screen to cull
            if enemy.pos[0] < -20 or enemy.pos[0] > self.game.DISPLAY_SIZE[0] + 20:
                self.enemies.pop(i)

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
            combo_drain_multiplier = 1.5 if 'short_fuse' in self.active_curses else 1
            self.combo_timer -= (2 if 'glass_cannon' in self.active_perks else 1) * self.time_scale * combo_drain_multiplier
            
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
                        angle, speed = random.random() * math.pi * 2, random.random() * 2
                        self.sparks.append([[self.game.DISPLAY_SIZE[0] // 2, 10], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 2 + 1, 0.05, (255, 200, 50), True, 0.05])
                else:
                    self.combo_multiplier = 1.0
                    for i in range(20):
                        angle, speed = random.random() * math.pi * 2, random.random() * 1.5
                        self.sparks.append([[self.game.DISPLAY_SIZE[0] // 2, 10], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 2 + 1, 0.05, (251, 245, 239), True, 0.05])

    def update_perk_offering(self):
        if self.mode in ['zen', 'challenge']: return
        score_interval = 75 if self.mode != "hardcore" else 60
        if self.coins > 0 and self.coins // score_interval > self.last_perk_score // score_interval:
            self.last_perk_score = self.coins
            available_perks = [p for p in self.game.perks.keys() if p not in self.active_perks]
            if available_perks:
                perks_to_offer = random.sample(available_perks, k=min(3, len(available_perks)))
                background_surf = self.game.display.copy()
                self.render(background_surf)
                self.game.push_state(PerkSelectionState(self.game, perks_to_offer, background_surf))
                self.game.sounds['warp'].play()

    def update_prophecy(self):
        if not self.prophecy or self.prophecy.get('completed'):
            return
        
        if self.prophecy['objective_type'] == 'collect_coins': self.prophecy_progress = self.coins
        elif self.prophecy['objective_type'] == 'reach_combo': self.prophecy_progress = self.combo_multiplier

        if self.prophecy_progress >= self.prophecy['value']:
            self.prophecy['completed'] = True
            self.game.sounds['prophecy_complete'].play()
            if self.prophecy['reward_type'] == 'coins': self.coins += self.prophecy['reward_value']
            elif self.prophecy['reward_type'] == 'item': self.current_item = self.prophecy['reward_value']
            
    def update_tile_spawning(self):
        if self.master_clock < 180 or self.mode == "challenge": return
        self.game_timer += self.time_scale
        current_spawn_rate = 10 + self.spawn_timer_base * (20000 - min(20000, self.master_clock)) / 20000
        if self.game_timer > current_spawn_rate:
            self.game_timer = 0
            valid_columns = [i for i in range(len(self.stack_heights)) if self.stack_heights[i] > 4]
            if not valid_columns: return
            choices = [col for col in valid_columns if col != self.last_place] if len(valid_columns) > 1 and self.last_place in valid_columns else valid_columns
            chosen_col_index = random.choice(choices)
            self.last_place = chosen_col_index
            biome = self.game.biomes[self.current_biome_index]
            final_tile_type = 'tile' 
            elite_roll = random.randint(1, 100)
            if elite_roll <= 2 and 'motherlode' in biome['available_tiles']: final_tile_type = 'motherlode'
            elif elite_roll <= 5 and 'unstable' in biome['available_tiles']: final_tile_type = 'unstable'
            else:
                spawn_weights = {'tile': 70, 'fragile': 8, 'bounce': 5, 'chest': 3, 'spike': 2, 'greed': 2}
                for special, chance in biome.get('special_spawn_rate', {}).items(): spawn_weights[special] = spawn_weights.get(special, 0) + chance
                available_choices = {k: v for k, v in spawn_weights.items() if k in biome['available_tiles'] and k not in self.disabled_tiles}
                if available_choices: final_tile_type = random.choices(list(available_choices.keys()), list(available_choices.values()), k=1)[0]
            if final_tile_type == 'greed' and 'high_stakes' in self.active_curses: final_tile_type = 'spike'
            self.tile_drops.append([(chosen_col_index + 1) * self.game.TILE_SIZE, -self.height - self.game.TILE_SIZE, final_tile_type])

    def update_falling_tiles(self):
        tile_drop_rects = []
        for i, tile in sorted(enumerate(self.tile_drops), reverse=True):
            if self.freeze_timer <= 0:
                tile[1] += (1.8 if tile[2] == 'motherlode' else 1.4) * self.time_scale
            r_screen = pygame.Rect(tile[0], tile[1] - self.height, self.game.TILE_SIZE, self.game.TILE_SIZE); tile_drop_rects.append(r_screen)
            if self.player.dash_timer > 0 and r_screen.colliderect(self.player.rect):
                self.tile_drops.pop(i)
                if 'brittle_blocks' not in self.active_curses:
                    self.coins += 2 * int(self.combo_multiplier)
                if self.prophecy and not self.prophecy.get('completed') and self.prophecy['objective_type'] == 'destroy_tiles_dash': self.prophecy_progress += 1
                self.combo_multiplier += 0.3 * (2 if 'glass_cannon' in self.active_perks else 1); self.combo_timer = self.game.COMBO_DURATION
                self.game.sounds['explosion'].play() if 'explosion' in self.game.sounds else self.game.sounds['block_land'].play()
                self.screen_shake = max(self.screen_shake, 6)
                for k in range(15):
                    angle, speed = random.random() * math.pi * 2, random.random() * 2.5
                    self.sparks.append([list(r_screen.center), [math.cos(angle) * speed, math.sin(angle) * speed], random.uniform(2, 5), 0.08, (251, 245, 239), True, 0.1])
                continue
            if r_screen.colliderect(self.player.rect): self.handle_death()
            check_pos = (int((tile[0] + self.game.TILE_SIZE//2) // self.game.TILE_SIZE), int(math.floor((tile[1] + self.game.TILE_SIZE) / self.game.TILE_SIZE)))
            if check_pos in self.tiles:
                self.tile_drops.pop(i)
                place_pos = (check_pos[0], check_pos[1] - 1)
                if place_pos[1] < 0: continue
                if tile[2] == 'motherlode':
                    self.game.sounds['chest_open'].play(); self.screen_shake = max(self.screen_shake, 8)
                    coins_mult = 2 if 'greedy' in self.active_perks else 1
                    for k in range(random.randint(8, 15) * coins_mult): self.items.append(Item(self.game.animation_manager, (place_pos[0] * 16 + 5, place_pos[1] * 16 + 5), (6, 6), 'coin', self, velocity=[random.random() * 6 - 3, random.random() * 2 - 8]))
                    self.tiles[place_pos] = {'type': 'chest', 'data': {}}
                else:
                    self.tiles[place_pos] = {'type': tile[2], 'data': {}}
                    if tile[2] == 'unstable': self.tiles[place_pos]['data']['timer'] = 180
                    self.game.sounds['block_land'].play()
                if random.random() < self.tile_coin_drop_chance: self.items.append(Item(self.game.animation_manager, (place_pos[0] * 16 + 5, place_pos[1] * 16 + 5), (6, 6), 'coin', self, velocity=[random.random() * 2 - 1, random.random() * -2]))
                self.recalculate_stack_heights()
                continue
        self.tile_drop_rects = tile_drop_rects
        
    def update_placed_tiles(self):
        to_remove = []
        for tile_pos, tile_data in self.tiles.items():
            player_on_tile_rect = pygame.Rect(tile_pos[0]*16, tile_pos[1]*16-self.height-2, 16, 18)
            player_on_tile = self.player.rect.colliderect(player_on_tile_rect)
            if tile_data['type'] == 'unstable' and 'timer' in tile_data['data']:
                tile_data['data']['timer'] -= 1 * self.time_scale
                if random.randint(1, 8) == 1: self.sparks.append([[(tile_pos[0]+0.5)*16, (tile_pos[1]+0.5)*16-self.height], [random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5)], random.uniform(2, 4), 0.1, (255, 100, 20), False, 0])
                if tile_data['data']['timer'] <= 0:
                    if tile_pos not in to_remove: to_remove.append(tile_pos)
            if tile_data['type'] == 'fragile' and 'timer' in tile_data['data']:
                tile_data['data']['timer'] -= 1 * self.time_scale
                if tile_data['data']['timer'] <= 0:
                    if tile_pos not in to_remove: to_remove.append(tile_pos)
        if to_remove:
            for p in to_remove:
                if p in self.tiles: del self.tiles[p]
                if random.random() < self.tile_coin_drop_chance: self.items.append(Item(self.game.animation_manager, (p[0]*16+5, p[1]*16+5), (6, 6), 'coin', self, velocity=[random.random() * 2 - 1, random.random() * -2]))
            self.recalculate_stack_heights()

    def update_tile_interactions(self):
        if self.dead: return
        for pos, data in list(self.tiles.items()):
            if data['type'] == 'chest':
                chest_rect_screen = pygame.Rect(pos[0]*16, pos[1]*16 - self.height, 16, 16)
                if chest_rect_screen.colliderect(self.player.rect):
                    self.game.sounds['chest_open'].play(); self.combo_multiplier += 1.0; self.combo_timer = self.game.COMBO_DURATION
                    self.tiles[pos]['type'] = 'opened_chest'
                    self.player.jumps = min(self.player.jumps + 1, self.player.jumps_max)
                    self.player.velocity[1] = -3.5
                    item_luck = 3 + self.game.save_data['upgrades']['item_luck']
                    if random.randint(1, 5) < item_luck:
                        item_type = random.choice(['warp', 'cube', 'jump', 'bomb', 'freeze', 'shield', 'hourglass'])
                        self.items.append(Item(self.game.animation_manager, (pos[0]*16+5, pos[1]*16+5), (6,6), item_type, self, velocity=[random.random()*5-2.5, random.random()*2-5]))
                    else:
                        coins_mult = 2 if 'greedy' in self.active_perks else 1
                        for _ in range(random.randint(2,6)*coins_mult): self.items.append(Item(self.game.animation_manager, (pos[0]*16+5, pos[1]*16+5), (6,6), 'coin', self, velocity=[random.random()*5-2.5, random.random()*2-7]))
                    
    def update_items(self):
        solid_rects = [pygame.Rect(p[0] * 16, p[1] * 16, 16, 16) for p in self.tiles]
        for i, item in sorted(enumerate(self.items), reverse=True):
            item.update(solid_rects, self.time_scale)
            item_rect_screen = item.rect.copy()
            item_rect_screen.y -= self.height
            if item.time > 30 and item_rect_screen.colliderect(self.player.rect):
                if item.type == 'coin':
                    self.game.sounds['coin'].play()
                    self.coins += int(1 * self.combo_multiplier)
                else: self.current_item = item.type
                self.items.pop(i)

    def update_projectiles(self):
        for i, p in sorted(enumerate(self.projectiles), reverse=True):
            p.update(self.time_scale)
            if not p.rect.colliderect(self.game.display.get_rect()): self.projectiles.pop(i); continue
            projectile_screen_rect = pygame.Rect(p.pos[0], p.pos[1]-self.height, p.size[0], p.size[1])
            hit = False
            for j, tile_drop in sorted(enumerate(self.tile_drops), reverse=True):
                if projectile_screen_rect.colliderect(pygame.Rect(tile_drop[0], tile_drop[1]-self.height, 16, 16)):
                    self.game.sounds['block_land'].play(); p.health -= 1; self.tile_drops.pop(j)
                    if p.health <= 0: hit = True; self.projectiles.pop(i)
                    self.coins += 1; break
            if hit: continue
            
    def update_player(self):
        if not self.dead:
            tile_rects = [pygame.Rect(p[0]*16, p[1]*16-self.height, 16, 16) for p in self.tiles]
            edge_rects = [pygame.Rect(0, 0, 16, self.game.DISPLAY_SIZE[1]), pygame.Rect(16 * (self.game.WINDOW_TILE_SIZE[0] - 1), 0, 16, self.game.DISPLAY_SIZE[1])]
            original_speed = self.player.speed
            if 'heavy_feet' in self.active_curses: self.player.speed *= 0.85
            collisions = self.player.update(self.tile_drop_rects + edge_rects + tile_rects, self.time_scale)
            self.player.speed = original_speed
            if collisions['bottom']:
                tile_pos_below = (self.player.rect.midbottom[0] // 16, (self.player.rect.midbottom[1] + self.height) // 16)
                if tile_pos_below in self.tiles:
                    tile_type = self.tiles[tile_pos_below]['type']
                    if tile_type == 'fragile': self.tiles[tile_pos_below]['data']['timer'] = 90
                    elif tile_type == 'bounce': self.player.velocity[1] = -9; self.game.sounds['super_jump'].play()
                    elif tile_type == 'spike': self.handle_death()
        else: self.player.update([], self.time_scale); self.player.rotation -= 16
    
    def update_sparks(self):
        for i, spark in sorted(enumerate(self.sparks), reverse=True):
            spark[0][0] += spark[1][0] * self.time_scale
            spark[0][1] += spark[1][1] * self.time_scale
            spark[2] -= spark[3] * self.time_scale
            if spark[2] <= 1: self.sparks.pop(i)
    
    def update_scrolling(self):
        if self.tiles and self.mode != 'challenge':
            try:
                highest_base_row = max(p[1] for p in self.tiles.keys()) - 1
                is_full = all((i + 1, highest_base_row) in self.tiles for i in range(self.game.WINDOW_TILE_SIZE[0] - 2))
                if is_full:
                    self.target_height = (highest_base_row - self.game.WINDOW_TILE_SIZE[1] + 2) * self.game.TILE_SIZE
            except ValueError: pass
        self.height += (self.target_height - self.height) * 0.1
        if abs(self.height-self.target_height) < 0.1: self.height = self.target_height
        offscreen_y = self.target_height/16 + self.game.WINDOW_TILE_SIZE[1] + 2
        to_remove = [pos for pos in self.tiles if pos[1] > offscreen_y]
        if to_remove:
            for pos in to_remove: del self.tiles[pos]
            self.recalculate_stack_heights()

    def fire_projectile(self, keys):
        self.game.sounds['jump'].play(); speed = 4
        if keys[K_UP] or keys[K_w]: vel, pos = [0, -speed], self.player.rect.midtop
        elif keys[K_DOWN] or keys[K_s]: vel, pos = [0, speed], self.player.rect.midbottom
        else: vel, pos = [speed if self.player.flip[0] else -speed, 0], self.player.rect.center
        pos_world = [pos[0], pos[1] + self.height]
        self.projectiles.append(Projectile(self.game.animation_manager, pos_world, (6, 2), 'projectile', self, velocity=vel))

    def use_item(self):
        if 'butter_fingers' in self.active_curses and random.random() < 0.5: self.current_item = None; return
        item = self.current_item
        if item == 'warp': self.player.pos[1] = min(p[1] for p in self.tiles) * 16 - self.height - 32
        elif item == 'jump': self.player.jumps = self.player.jumps_max + 1; self.player.velocity[1] = -8
        elif item == 'cube':
            px = int(self.player.center[0] // 16); py = int(self.player.center[1] // 16)
            for y in range(py + 1, self.game.WINDOW_TILE_SIZE[1]): self.tiles[(px, y)] = {'type':'placed_tile', 'data':{}}
            self.recalculate_stack_heights()
        self.current_item = None
        
    def render_background(self, surf):
        biome = self.game.biomes[self.current_biome_index]; surf.fill(biome['bg_color'])
        if 'far' in self.game.backgrounds and self.game.backgrounds['far']:
            scroll_y = (self.height * 0.2) % self.game.DISPLAY_SIZE[1]
            surf.blit(self.game.backgrounds['far'], (0, scroll_y)); surf.blit(self.game.backgrounds['far'], (0, scroll_y - self.game.DISPLAY_SIZE[1]))
        if 'near' in self.game.backgrounds and self.game.backgrounds['near']:
            scroll_y = (self.height * 0.4) % self.game.DISPLAY_SIZE[1]
            surf.blit(self.game.backgrounds['near'], (0, scroll_y)); surf.blit(self.game.backgrounds['near'], (0, scroll_y - self.game.DISPLAY_SIZE[1]))

    def render_lava(self, surf):
        if self.lava_y < self.game.DISPLAY_SIZE[1] + self.height:
            lava_rect = pygame.Rect(0, int(self.lava_y - self.height), self.game.DISPLAY_SIZE[0], self.game.DISPLAY_SIZE[1] - int(self.lava_y - self.height))
            pygame.draw.rect(surf, (255, 60, 20), lava_rect)

    def render_crystals(self, surf):
        for crystal_rect in self.crystals:
            render_pos = (crystal_rect.x, crystal_rect.y - self.height)
            surf.blit(self.crystal_img, render_pos)

    def render_placed_tiles(self, surf):
        for pos, data in self.tiles.items():
            blit_pos = (pos[0] * 16, pos[1] * 16 - int(self.height))
            if blit_pos[1] < -16 or blit_pos[1] > self.game.DISPLAY_SIZE[1]: continue
            img_map = {'placed_tile':self.placed_tile_img, 'chest':self.chest_img, 'opened_chest':self.opened_chest_img, 'fragile': self.fragile_tile_img, 'spike': self.spike_tile_img, 'greed': self.greed_tile_img, 'bounce': self.bounce_tile_img}
            img = img_map.get(data.get('type'), self.tile_img)
            surf.blit(img, blit_pos)

    def render_falling_tiles(self, surf):
        for tile in self.tile_drops:
            pos = (tile[0], tile[1] - self.height)
            if pos[1] < -16 or pos[1] > self.game.DISPLAY_SIZE[1]: continue
            img_map = {'chest': self.ghost_chest_img, 'fragile': self.fragile_tile_img, 'spike': self.spike_tile_img, 'greed': self.greed_tile_img, 'bounce': self.bounce_tile_img, 'motherlode':self.motherlode_tile_img}
            surf.blit(img_map.get(tile[2], self.tile_img), pos)

    def render_items(self, surf):
        for item in self.items: item.render(surf, (0, self.height))

    def render_projectiles(self, surf):
        for p in self.projectiles: p.render(surf, (0, self.height))

    def render_shield_aura(self, surf):
        if self.player_shielded and not self.dead:
            aura_pos = (self.player.rect.centerx - self.shield_aura_img.get_width()//2, self.player.rect.centery - self.shield_aura_img.get_height()//2)
            pulse = math.sin(self.master_clock / 8) * 2
            pulsing = pygame.transform.scale(self.shield_aura_img, (int(self.shield_aura_img.get_width() + pulse), int(self.shield_aura_img.get_height() + pulse)))
            pulsing.set_alpha(150 - pulse * 10); surf.blit(pulsing, aura_pos, special_flags=BLEND_RGBA_ADD)
        
    def render_sparks(self, surf):
        for spark in self.sparks:
            size = int(spark[2])
            pos = (spark[0][0], spark[0][1]) # Sparks are already in screen-space
            if size > 0: surf.blit(glow_img(size, spark[4]), (pos[0]-size, pos[1]-size), special_flags=BLEND_RGBA_ADD)
    
    def render_borders(self, surf):
        scroll_offset = self.height % 16
        for i in range(self.game.WINDOW_TILE_SIZE[1] + 2):
            y_pos = i * 16 - scroll_offset
            surf.blit(self.edge_tile_img, (0, y_pos)); surf.blit(self.edge_tile_img, (16 * (self.game.WINDOW_TILE_SIZE[0] - 1), y_pos))

    def render_hud(self, surface):
        top_left_panel_rect = pygame.Rect(4, 4, 80, 22)
        render_panel_9slice(surface, top_left_panel_rect, self.panel_img, 8)
        surface.blit(self.coin_icon, (10, 8)); self.game.white_font.render(str(self.coins), surface, (22, 10))
        
        if self.combo_multiplier > 1.0:
            text = f"x{self.combo_multiplier:.1f}"; w = self.game.white_font.width(text, 2)
            self.game.white_font.render(text, surface, (self.game.DISPLAY_SIZE[0]//2 - w//2, 4), scale=2)

        if self.prophecy and not self.prophecy.get('completed'):
            prop_text = self.prophecy['flavor_text']
            progress = f"({int(self.prophecy_progress)}/{self.prophecy['value']})"
            full_text = f"{prop_text} {progress}"
            w_text = self.game.white_font.width(full_text)
            self.game.white_font.render(full_text, surface, (self.game.DISPLAY_SIZE[0]//2 - w_text//2, self.game.DISPLAY_SIZE[1] - 20))

        if self.active_perks:
            perk_panel_w = 6 + (len(self.active_perks) * 12)
            perk_panel_rect = pygame.Rect(4, self.game.DISPLAY_SIZE[1] - 22, perk_panel_w, 18)
            render_panel_9slice(surface, perk_panel_rect, self.panel_img, 8)
            x_off = perk_panel_rect.left + 5
            for key in sorted(list(self.active_perks)):
                if key in self.perk_icons:
                    icon = self.perk_icons[key]
                    surface.blit(icon, (x_off, perk_panel_rect.top + 4))
                    x_off += icon.get_width() + 2
