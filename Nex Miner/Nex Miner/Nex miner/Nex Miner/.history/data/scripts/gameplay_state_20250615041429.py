# Cavyn Source/data/scripts/gameplay_state.py

import pygame, sys, random, math, json
from pygame.locals import *

# Core game state and entity imports
from .state import State
from .text import Font
from .entities.player import Player
from .entities.item import Item
from .entities.projectile import Projectile

# Imports for state transitions
from .game_states.pause_state import PauseState
from .game_states.perk_selection_state import PerkSelectionState
from .game_states.game_over_state import GameOverState
from .game_states.curse_selection_state import CurseSelectionState
from .core_funcs import load_img


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

def render_panel_9slice(surface, rect, panel_img, corner_size):
    surface.blit(panel_img, rect.topleft, (0, 0, corner_size, corner_size))
    surface.blit(panel_img, (rect.right - corner_size, rect.top), (panel_img.get_width() - corner_size, 0, corner_size, corner_size))
    surface.blit(panel_img, (rect.left, rect.bottom - corner_size), (0, panel_img.get_height() - corner_size, corner_size, corner_size))
    surface.blit(panel_img, (rect.right - corner_size, rect.bottom - corner_size), (panel_img.get_width() - corner_size, panel_img.get_height() - corner_size, corner_size, corner_size))
    top_edge = pygame.transform.scale(panel_img.subsurface(corner_size, 0, panel_img.get_width() - corner_size * 2, corner_size), (rect.width - corner_size * 2, corner_size))
    bottom_edge = pygame.transform.scale(panel_img.subsurface(corner_size, panel_img.get_height() - corner_size, panel_img.get_width() - corner_size * 2, corner_size), (rect.width - corner_size * 2, corner_size))
    left_edge = pygame.transform.scale(panel_img.subsurface(0, corner_size, corner_size, panel_img.get_height() - corner_size * 2), (corner_size, rect.height - corner_size * 2))
    right_edge = pygame.transform.scale(panel_img.subsurface(panel_img.get_width() - corner_size, corner_size, corner_size, panel_img.get_height() - corner_size * 2), (corner_size, rect.height - corner_size * 2))
    surface.blit(top_edge, (rect.left + corner_size, rect.top))
    surface.blit(bottom_edge, (rect.left + corner_size, rect.bottom - corner_size))
    surface.blit(left_edge, (rect.left, rect.top + corner_size))
    surface.blit(right_edge, (rect.right - corner_size, rect.top + corner_size))
    center = pygame.transform.scale(panel_img.subsurface(corner_size, corner_size, panel_img.get_width() - corner_size * 2, panel_img.get_height() - corner_size * 2), (rect.width - corner_size * 2, rect.height - corner_size * 2))
    surface.blit(center, (rect.left + corner_size, rect.top + corner_size))


# =========================================================================
# === MAIN GAMEPLAY STATE CLASS ===
# =========================================================================

class GameplayState(State):
    def __init__(self, game, mode="classic", challenge_config=None):
        super().__init__(game)
        self.mode = mode
        self.challenge_config = challenge_config
        self.lava_y = self.game.DISPLAY_SIZE[1] + 50 # Start lava off-screen
        self.special_entity_timer = 0
        self.crystals = []
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
        except pygame.error as e:
            print(f"WARNING: Could not load new biome asset. Did you add it to data/images/? Error: {e}")
            # Create placeholder surfaces to prevent crashes
            self.prism_tile_img = pygame.Surface((16, 16)); self.prism_tile_img.fill((255, 0, 255))
            self.geyser_tile_img = pygame.Surface((16, 16)); self.geyser_tile_img.fill((255, 0, 255))
            self.crystal_img = pygame.Surface((16, 24)); self.crystal_img.fill((255, 0, 255))
        
        self.perk_icons = {}
        for perk_name in self.game.perks.keys():
            try:
                icon_path = self.game.get_path('data', 'images', 'perk_icons', f'{perk_name}.png')
                self.perk_icons[perk_name] = load_img(icon_path)
            except pygame.error:
                print(f"Warning: Could not load icon for perk '{perk_name}'.")

    def enter_state(self):
        super().enter_state()
        if self.mode == "classic" and self.perks_gained_this_run > 0 and self.perks_gained_this_run % 2 == 0:
            if self.perks_gained_this_run != self.last_curse_check:
                self.last_curse_check = self.perks_gained_this_run
                
                available_curses = list(self.game.curses.keys() - self.active_curses)
                if available_curses:
                    curses_to_offer = random.sample(available_curses, k=min(3, len(available_curses)))
                    background_surf = self.game.display.copy()
                    self.render(background_surf)
                    self.game.push_state(CurseSelectionState(self.game, curses_to_offer, background_surf))

    def reset(self):
        selected_char_key = self.game.save_data['characters']['selected']
        character_data = self.game.characters.get(selected_char_key, self.game.characters['cavyn'])
        
        self.player = Player(self.game.animation_manager, (self.game.DISPLAY_SIZE[0] // 2 - 5, -20), (8, 16), selected_char_key, self)
        self.player.jumps_max = 2 + self.game.save_data['upgrades']['jumps']
        self.player.speed = 1.4 + self.game.save_data['upgrades']['speed'] * 0.08
        self.player.jumps = self.player.jumps_max
        
        self.active_perks = set(character_data['mods'].get('innate_perks', []))
        self.player.FOCUS_DASH_COST = character_data['mods'].get('FOCUS_DASH_COST', 50)
        
        self.dead = False
        self.tiles, self.tile_drops, self.sparks, self.projectiles, self.items = {}, [], [], [], []
        self.ghosts = []
        self.freeze_timer, self.game_timer, self.master_clock = 0, 0, 0
        self.height, self.target_height = 0, 0
        self.coins = 0
        self.current_item, self.item_used = None, False
        self.time_meter, self.time_scale, self.slowing_time = self.game.time_meter_max, 1.0, False
        
        # --- FIX: Added the missing initializations ---
        self.screen_shake = 0
        self.player_shielded = False
        # --- END FIX ---
        
        self.combo_shield_used = False
        self.last_perk_score = 0
        self.combo_timer = 0
        
        self.last_curse_check = 0
        self.perks_gained_this_run = 0

        # Mode-specific configurations
        if self.mode == "zen":
            self.spawn_timer_base = 80
            self.disabled_tiles = {'spike', 'unstable'}
            self.active_curses = set()
            self.combo_multiplier = 1.0
            pygame.mixer.music.set_volume(0.3 * self.game.save_data['settings'].get('music_volume', 1.0))
        elif self.mode == "hardcore":
            self.spawn_timer_base = 25
            self.disabled_tiles = set()
            if list(self.game.curses.keys()):
                self.active_curses = {random.choice(list(self.game.curses.keys()))}
            else:
                self.active_curses = set()
            self.combo_multiplier = 1.5
        else:  # Classic mode
            self.spawn_timer_base = 45
            self.disabled_tiles = set()
            self.active_curses = set()
            self.combo_multiplier = 1.0

        # Reset biome-specific variables
        self.lava_y = self.game.DISPLAY_SIZE[1] + 50
        self.crystals = []
        self.special_entity_timer = 0
            
        self.current_biome_index, self.last_place = 0, 0
        self.game.load_biome_bgs(self.game.biomes[self.current_biome_index])
        
        for i in range(self.game.WINDOW_TILE_SIZE[0] - 2):
            self.tiles[(i + 1, self.game.WINDOW_TILE_SIZE[1] - 1)] = {'type': 'tile', 'data': {}}
        self.tiles[(1, self.game.WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
        self.tiles[(self.game.WINDOW_TILE_SIZE[0] - 2, self.game.WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
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
                            self.game.sounds['jump'].play(); self.player.attempt_jump()
                    if event.key in [K_z, K_k] and len(self.projectiles) < 4: self.fire_projectile(pygame.key.get_pressed())
                    if event.key in [K_e, K_x] and self.current_item: self.use_item()

            if event.type == KEYUP and not self.dead:
                if event.key in [K_c, K_l] and self.player.is_charging_dash:
                    self.player.is_charging_dash = False; self.player.focus_meter -= self.player.FOCUS_DASH_COST
                    self.player.dash_timer = self.player.DASH_DURATION
                    self.game.sounds['explosion'].play() if 'explosion' in self.game.sounds else self.game.sounds['block_land'].play()
                if event.key in [K_RIGHT, K_d]: self.player.right = False
                if event.key in [K_LEFT, K_a]: self.player.left = False

    def update(self):
        self.master_clock += 1
        self.update_time_scale()
        if not self.dead:
            self.update_biome()
            self.update_combo_meter()
            self.update_perk_offering()
            self.update_tile_spawning()
            self.update_ambient_hazards()
            self.update_special_entities()

        if self.screen_shake > 0: self.screen_shake -= 0.5 * self.time_scale
        if self.freeze_timer > 0: self.freeze_timer -= 1 * self.time_scale
        
        self.update_ghosts()
        self.update_falling_tiles()
        self.update_placed_tiles()
        self.update_tile_interactions()
        self.update_items()
        self.update_projectiles()
        self.update_player()
        self.update_sparks()
        self.update_scrolling()

    def render(self, surface):
        self.render_background(surface)
        if self.freeze_timer > 0:
            freeze_overlay = pygame.Surface(self.game.DISPLAY_SIZE, pygame.SRCALPHA)
            alpha = 60 + math.sin(self.master_clock / 5) * 10
            freeze_overlay.fill((170, 200, 255, alpha)); surface.blit(freeze_overlay, (0, 0))

        self.render_lava(surface)
        self.render_crystals(surface)

        self.render_ghosts(surface)
        
        self.render_placed_tiles(surface)
        self.render_falling_tiles(surface)
        self.render_items(surface)
        self.render_projectiles(surface)
        if self.player_shielded and not self.dead: self.render_shield_aura(surface)
        self.player.render(surface, (0, -int(self.height)))
        self.render_sparks(surface)
        self.render_borders(surface)
        self.render_hud(surface)
        
    def update_ghosts(self):
        for i, ghost in sorted(enumerate(self.ghosts), reverse=True):
            ghost[2] -= 1
            if ghost[2] <= 0:
                self.ghosts.pop(i)
                
    def render_ghosts(self, surface):
        for img, pos, timer, flip in self.ghosts:
            alpha = max(0, (timer / 15) * 120)
            img.set_alpha(alpha)
            render_img = pygame.transform.flip(img, flip, False)
            surface.blit(render_img, (pos[0], pos[1] - self.height))

    def recalculate_stack_heights(self):
        new_heights = [self.game.WINDOW_TILE_SIZE[1] for i in range(self.game.WINDOW_TILE_SIZE[0] - 2)]
        for tile_x, tile_y in self.tiles:
            if 1 <= tile_x < self.game.WINDOW_TILE_SIZE[0] - 1:
                new_heights[tile_x - 1] = min(new_heights[tile_x - 1], tile_y)
        self.stack_heights = new_heights

    def handle_death(self):
        if self.mode == "zen":
            self.player.pos[1] -= 20
            self.player.velocity[1] = -5
            return
            
        if self.player.pos[1] + self.player.size[1] > self.lava_y and not self.dead:
            self.dead = True 
            self.game.sounds['death'].play()
            self.screen_shake = 20
            background_surf = self.game.display.copy()
            self.render(background_surf)
            self.game.push_state(GameOverState(self.game, self.coins, background_surf))
            return

        if self.player_shielded:
            self.player_shielded = False
            self.game.sounds['explosion'].play() if 'explosion' in self.game.sounds else self.game.sounds['super_jump'].play()
            self.screen_shake = 15
            for i in range(60):
                angle, speed = random.random() * math.pi * 2, random.random() * 2
                self.sparks.append([self.player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.uniform(2, 4), 0.05, (170, 200, 255), True, 0.05])
            return

        if self.dead: return
        self.dead = True 

        self.game.sounds['death'].play(); self.screen_shake = 20
        for i in range(380):
            angle, speed = random.random() * math.pi, random.random() * 1.5; physics = random.choice([False, True, True])
            self.sparks.append([self.player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.02, (12, 2, 2), physics, 0.1 * physics])
        
        background_surf = self.game.display.copy()
        self.render(background_surf)
        self.game.push_state(GameOverState(self.game, self.coins, background_surf))

    def update_biome(self):
        next_biome_index = self.current_biome_index
        if self.mode != "zen" and self.current_biome_index + 1 < len(self.game.biomes) and self.coins >= self.game.biomes[self.current_biome_index + 1]['score_req']:
            next_biome_index += 1
        if next_biome_index != self.current_biome_index:
            self.current_biome_index = next_biome_index
            self.game.load_biome_bgs(self.game.biomes[self.current_biome_index])
            self.game.sounds['warp'].play(); self.screen_shake = 15
            self.lava_y = self.game.DISPLAY_SIZE[1] + 50
            self.crystals = []
            
    def update_ambient_hazards(self):
        biome_config = self.game.biomes[self.current_biome_index]
        if 'ambient_hazard' in biome_config:
            hazard = biome_config['ambient_hazard']
            if hazard['type'] == 'rising_lava':
                self.lava_y -= hazard['speed'] * self.time_scale

    def update_special_entities(self):
        biome_config = self.game.biomes[self.current_biome_index]
        if 'special_entities' in biome_config:
            entity_config = biome_config['special_entities']
            self.special_entity_timer += 1 * self.time_scale
            if self.special_entity_timer > entity_config['spawn_rate']:
                self.special_entity_timer = 0
                if entity_config['type'] == 'crystal':
                    valid_cols = [i for i, h in enumerate(self.stack_heights) if h > 4]
                    if valid_cols:
                        x_pos = (random.choice(valid_cols) + 1) * self.game.TILE_SIZE
                        self.crystals.append(pygame.Rect(x_pos, -self.height - 24, 16, 24))

        for i, crystal_rect in sorted(enumerate(self.crystals), reverse=True):
            if self.freeze_timer <= 0:
                crystal_rect.y += 1.6 * self.time_scale
            
            if self.player.rect.colliderect(crystal_rect):
                self.crystals.pop(i)
                self.handle_death()
                
            check_pos = (int(crystal_rect.centerx // self.game.TILE_SIZE), int(math.floor(crystal_rect.bottom / self.game.TILE_SIZE)))
            if check_pos in self.tiles:
                self.crystals.pop(i)
                self.screen_shake = max(self.screen_shake, 7)
                self.game.sounds['explosion'].play()
                for k in range(random.randint(4, 8)):
                    self.items.append(Item(self.game.animation_manager, (crystal_rect.centerx, crystal_rect.bottom), (6, 6), 'coin', self, velocity=[random.random() * 4 - 2, random.random() * 2 - 6]))

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

    def update_tile_spawning(self):
        if self.master_clock < 180: return
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
            if elite_roll <= 2: final_tile_type = 'motherlode'
            elif elite_roll <= 5: final_tile_type = 'unstable'
            else:
                spawn_weights = {'tile': 70, 'fragile': 8, 'bounce': 5, 'chest': 3, 'spike': 2, 'greed': 2}
                for special, chance in biome.get('special_spawn_rate', {}).items():
                    spawn_weights[special] = spawn_weights.get(special, 0) + chance

                available_choices = {k: v for k, v in spawn_weights.items() if k in biome['available_tiles'] and k not in self.disabled_tiles}
                if available_choices:
                    final_tile_type = random.choices(list(available_choices.keys()), list(available_choices.values()), k=1)[0]
            
            if final_tile_type == 'greed' and 'high_stakes' in self.active_curses: final_tile_type = 'spike'
            self.tile_drops.append([(chosen_col_index + 1) * self.game.TILE_SIZE, -self.height - self.game.TILE_SIZE, final_tile_type])

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
                self.tile_drops.pop(i)
                if 'brittle_blocks' not in self.active_curses:
                    self.coins += 2
                    
                self.combo_multiplier += 0.3 * (2 if 'glass_cannon' in self.active_perks else 1)
                self.combo_timer = self.game.COMBO_DURATION
                self.game.sounds['explosion'].play() if 'explosion' in self.game.sounds else self.game.sounds['block_land'].play()
                self.screen_shake = max(self.screen_shake, 6)
                for k in range(20):
                    angle, speed = random.random() * math.pi * 2, random.random() * 2.5
                    self.sparks.append([[r.centerx, r.centery], [math.cos(angle) * speed, math.sin(angle) * speed], random.uniform(2, 5), 0.08, (251, 245, 239), True, 0.1])
                
                if 'overcharge' in self.active_perks:
                    to_remove = []
                    for k_inner, other_tile_data in enumerate(self.tile_drops):
                        if i == k_inner: continue
                        other_tile_rect = pygame.Rect(other_tile_data[0], other_tile_data[1], self.game.TILE_SIZE, self.game.TILE_SIZE)
                        if r.inflate(self.game.TILE_SIZE, self.game.TILE_SIZE).colliderect(other_tile_rect):
                            to_remove.append(k_inner)
                    for k_rem in sorted(to_remove, reverse=True):
                         other_r = pygame.Rect(self.tile_drops[k_rem][0], self.tile_drops[k_rem][1], self.game.TILE_SIZE, self.game.TILE_SIZE)
                         for p__ in range(15):
                              angle, speed = random.random() * math.pi * 2, random.random() * 2
                              self.sparks.append([[other_r.centerx, other_r.centery], [math.cos(angle) * speed, math.sin(angle) * speed], random.uniform(1, 4), 0.1, (255,100,80), True, 0.1])
                         self.tile_drops.pop(k_rem); self.coins += 1
                continue
                
            if r.colliderect(self.player.rect): self.handle_death()

            check_pos = (int((r.centerx) // self.game.TILE_SIZE), int(math.floor(r.bottom / self.game.TILE_SIZE)))
            if check_pos in self.tiles:
                self.tile_drops.pop(i)
                place_pos = (check_pos[0], check_pos[1] - 1)
                
                if tile[2] == 'motherlode':
                    self.game.sounds['chest_open'].play(); self.screen_shake = max(self.screen_shake, 8)
                    coins_mult = 2 if 'greedy' in self.active_perks else 1
                    for k in range(random.randint(8, 15) * coins_mult): self.items.append(Item(self.game.animation_manager, (place_pos[0] * self.game.TILE_SIZE + 5, (place_pos[1] -1) * self.game.TILE_SIZE + 5), (6, 6), 'coin', self, velocity=[random.random() * 6 - 3, random.random() * 2 - 8]))
                    self.tiles[place_pos] = {'type': 'chest', 'data': {}}
                
                elif self.tiles.get(check_pos, {}).get('type') == 'greed':
                    self.game.sounds['chest_open'].play(); del self.tiles[check_pos]
                    coins_mult = 2 if 'greedy' in self.active_perks else 1
                    for k in range(random.randint(5, 10) * coins_mult): self.items.append(Item(self.game.animation_manager, (place_pos[0] * self.game.TILE_SIZE + 5, place_pos[1] * self.game.TILE_SIZE + 5), (6, 6), 'coin', self, velocity=[random.random() * 5 - 2.5, random.random() * 2 - 7]))
                    self.tiles[place_pos] = {'type': tile[2], 'data': {}}
                
                else:
                    self.tiles[place_pos] = {'type': tile[2], 'data': {}}
                    if tile[2] == 'unstable': self.tiles[place_pos]['data']['timer'] = 180
                    self.game.sounds['block_land'].play()
                    if abs(self.player.pos[0] - place_pos[0] * self.game.TILE_SIZE) < 40: self.screen_shake = max(self.screen_shake, 4)
                    
                    if self.tiles.get(check_pos, {}).get('type') == 'chest':
                        self.tiles[check_pos]['type'] = 'tile'
                        if 'chest_destroy' in self.game.sounds: self.game.sounds['chest_destroy'].play()
                        for _ in range(100):
                            angle, speed = random.random() * math.pi * 2, random.random() * 2.5
                            self.sparks.append([[place_pos[0] * self.game.TILE_SIZE + self.game.TILE_SIZE // 2, (check_pos[1]-1) * self.game.TILE_SIZE + self.game.TILE_SIZE // 2], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.09, (12, 8, 2), False, 0.1])
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

    def update_tile_interactions(self):
        if self.dead: return
        for pos, data in list(self.tiles.items()):
            if data['type'] == 'chest':
                chest_pos = (pos[0]*self.game.TILE_SIZE, (pos[1]-1)*self.game.TILE_SIZE)
                r = pygame.Rect(chest_pos[0]+2, chest_pos[1]+6, self.game.TILE_SIZE-4, self.game.TILE_SIZE-6)
                if r.colliderect(self.player.rect):
                    self.game.sounds['chest_open'].play()
                    self.combo_multiplier += 1.0*(2 if 'glass_cannon' in self.active_perks else 1)
                    self.combo_timer = self.game.COMBO_DURATION
                    for _ in range(50):
                        self.sparks.append([[chest_pos[0]+8, chest_pos[1]+8 + self.height], [random.random()*2-1, random.random()-2], random.random()*3+3, 0.01, (12,8,2), True, 0.05])
                    self.tiles[pos]['type'] = 'opened_chest'
                    self.player.jumps = min(self.player.jumps + 1, self.player.jumps_max)
                    self.player.attempt_jump()
                    self.player.velocity[1] = -3.5
                    
                    item_luck = 3 + self.game.save_data['upgrades']['item_luck']
                    if random.randint(1, 5) < item_luck:
                        item_type = random.choice(['warp', 'cube', 'jump', 'bomb', 'freeze', 'shield', 'hourglass'])
                        self.items.append(Item(self.game.animation_manager, (pos[0]*self.game.TILE_SIZE+5, (pos[1]-1)*self.game.TILE_SIZE+5), (6,6), item_type, self, velocity=[random.random()*5-2.5, random.random()*2-5]))
                    else:
                        coins_mult = 2 if 'greedy' in self.active_perks else 1
                        for _ in range(random.randint(2,6)*coins_mult):
                            self.items.append(Item(self.game.animation_manager, (pos[0]*self.game.TILE_SIZE+5, (pos[1]-1)*self.game.TILE_SIZE+5), (6,6), 'coin', self, velocity=[random.random()*5-2.5, random.random()*2-7]))


    def update_items(self):
        solid_rects = [pygame.Rect(p[0] * self.game.TILE_SIZE, p[1] * self.game.TILE_SIZE, self.game.TILE_SIZE, self.game.TILE_SIZE) for p in self.tiles]
        edge_rects = [pygame.Rect(0, 0, self.game.TILE_SIZE, self.game.DISPLAY_SIZE[1]), pygame.Rect(self.game.DISPLAY_SIZE[0] - self.game.TILE_SIZE, 0, self.game.TILE_SIZE, self.game.DISPLAY_SIZE[1])]
        for i, item in sorted(enumerate(self.items), reverse=True):
            item.update(solid_rects + edge_rects, self.time_scale)

            if item.type == 'coin' and not self.dead:
                magnet_lvl = self.game.save_data['upgrades']['coin_magnet']
                if magnet_lvl > 0:
                    dist_x, dist_y = self.player.center[0] - item.center[0], self.player.center[1] - item.center[1]
                    dist_sq = dist_x**2 + dist_y**2
                    if dist_sq < (20 + magnet_lvl * 10)**2:
                        dist = math.sqrt(dist_sq) if dist_sq > 0 else 1
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
                        hit_tile = True
                        if i < len(self.projectiles): self.projectiles.pop(i)
                    self.coins += 1; self.combo_multiplier += 0.05; self.combo_timer = self.game.COMBO_DURATION; break
            if hit_tile: continue
            
            for k, crystal_rect in sorted(enumerate(self.crystals), reverse=True):
                if p.rect.colliderect(crystal_rect):
                    self.crystals.pop(k)
                    if i < len(self.projectiles): self.projectiles.pop(i)
                    self.screen_shake = max(self.screen_shake, 7)
                    self.game.sounds['explosion'].play()
                    for _ in range(random.randint(4, 8)):
                        self.items.append(Item(self.game.animation_manager, (crystal_rect.centerx, crystal_rect.bottom), (6, 6), 'coin', self, velocity=[random.random() * 4 - 2, random.random() * 2 - 6]))
                    break


    def update_player(self):
        if not self.dead:
            for tile_pos, tile_data in self.tiles.items():
                if tile_data.get('type') == 'magnetic' and 0 < tile_pos[1] * self.game.TILE_SIZE + self.height < self.game.DISPLAY_SIZE[1]:
                    self.player.velocity[0] += max(-0.25, min(0.25, (tile_pos[0] * self.game.TILE_SIZE + self.game.TILE_SIZE // 2 - self.player.center[0]) / 80)) * self.time_scale

            tile_rects = [pygame.Rect(p[0] * self.game.TILE_SIZE, p[1] * self.game.TILE_SIZE, self.game.TILE_SIZE, self.game.TILE_SIZE) for p in self.tiles]
            edge_rects = [pygame.Rect(0, 0, self.game.TILE_SIZE, self.game.DISPLAY_SIZE[1]), pygame.Rect(self.game.TILE_SIZE * (self.game.WINDOW_TILE_SIZE[0] - 1), 0, self.game.TILE_SIZE, self.game.DISPLAY_SIZE[1])]
            
            original_speed = self.player.speed
            if 'heavy_feet' in self.active_curses: self.player.speed *= 0.85
            
            collisions = self.player.update(self.tile_drop_rects + edge_rects + tile_rects, self.time_scale)
            self.player.speed = original_speed

            if not collisions['bottom']:
                for side in ['left', 'right']:
                    player_side_y, player_side_x = self.player.rect.centery, self.player.rect.left - 2 if side == 'left' else self.player.rect.right + 2
                    tile_pos_side = (player_side_x // self.game.TILE_SIZE, player_side_y // self.game.TILE_SIZE)
                    if tile_pos_side in self.tiles and self.tiles.get(tile_pos_side, {}).get('type') == 'sticky': self.player.velocity[1] = min(self.player.velocity[1], 1.0)

            if collisions['bottom']:
                tile_pos_below = (self.player.rect.midbottom[0] // self.game.TILE_SIZE, self.player.rect.midbottom[1] // self.game.TILE_SIZE)
                if tile_pos_below in self.tiles:
                    tile_type = self.tiles[tile_pos_below]['type']
                    if tile_type == 'fragile' and 'timer' not in self.tiles[tile_pos_below]['data']: self.game.sounds['block_land'].play(); self.tiles[tile_pos_below]['data']['timer'] = 90
                    elif tile_type == 'geyser' and self.tiles[tile_pos_below].get('data', {}).get('timer', 0) <= 0: self.tiles[tile_pos_below]['data']['timer'] = 120 # Cooldown
                    elif tile_type == 'bounce': self.player.velocity[1] = -9; self.player.jumps = self.player.jumps_max; self.game.sounds['super_jump'].play(); self.screen_shake = 10; self.combo_multiplier += 0.5; self.combo_timer = self.game.COMBO_DURATION
                    elif tile_type == 'spike': self.handle_death(); self.player.velocity = [0, -4]

            # Update tile timers (like geyser)
            for pos, data in self.tiles.items():
                if data.get('type') == 'geyser' and data.get('data', {}).get('timer', 0) > 0:
                    data['data']['timer'] -= 1 * self.time_scale
                    if int(data['data']['timer']) == 90: # Erupt
                        self.game.sounds['super_jump'].play(); self.screen_shake = 10
                        for _ in range(40):
                            angle = random.uniform(math.pi * 1.2, math.pi * 1.8)
                            speed = random.uniform(1.5, 3.5)
                            self.sparks.append([[pos[0]*16 + 8, pos[1]*16], [math.cos(angle) * speed, math.sin(angle) * speed * 2], random.random() * 3 + 2, 0.04, (200, 200, 255), True, 0.1])
                        p_rect = self.player.rect.copy(); p_rect.y += 2
                        if p_rect.colliderect(pygame.Rect(pos[0]*16, pos[1]*16, 16, 16)):
                            self.player.velocity[1] = -11; self.player.jumps = self.player.jumps_max
        else:
            self.player.opacity = 80; self.player.update([], self.time_scale); self.player.rotation -= 16
    
    def update_sparks(self):
        for i, spark in sorted(enumerate(self.sparks), reverse=True):
            if len(spark) < 8: spark.append(False)
            if not spark[7]: spark[1][1] = min(spark[1][1] + spark[6], 3)
            spark[0][0] += spark[1][0] * self.time_scale
            if spark[5]:
                if not (self.game.TILE_SIZE <= spark[0][0] < self.game.DISPLAY_SIZE[0] - self.game.TILE_SIZE):
                     spark[0][0] -= spark[1][0] * self.time_scale; spark[1][0] *= -0.7
                elif (int(spark[0][0] // self.game.TILE_SIZE), int(spark[0][1] // self.game.TILE_SIZE)) in self.tiles:
                    spark[0][0] -= spark[1][0] * self.time_scale; spark[1][0] *= -0.7
            spark[0][1] += spark[1][1] * self.time_scale
            if spark[5] and (int(spark[0][0] // self.game.TILE_SIZE), int(spark[0][1] // self.game.TILE_SIZE)) in self.tiles:
                spark[0][1] -= spark[1][1] * self.time_scale; spark[1][1] *= -0.7
                if abs(spark[1][1]) < 0.2: spark[1][1] = 0; spark[7] = True
            spark[2] -= spark[3] * self.time_scale
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
        tile_pos_below = (self.player.rect.midbottom[0] // self.game.TILE_SIZE, self.player.rect.midbottom[1] // self.game.TILE_SIZE)
        player_on_prism = self.player.collisions['bottom'] and tile_pos_below in self.tiles and self.tiles.get(tile_pos_below, {}).get('type') == 'prism'

        self.game.sounds['jump'].play(); speed = 4;
        if keys[K_UP] or keys[K_w]: vel, pos = [0, -speed], [self.player.rect.centerx, self.player.rect.top]
        elif keys[K_DOWN] or keys[K_s]: vel, pos = [0, speed], [self.player.rect.centerx, self.player.rect.bottom]
        elif self.player.flip[0]: vel, pos = [speed, 0], [self.player.rect.right, self.player.rect.centery]
        else: vel, pos = [-speed, 0], [self.player.rect.left, self.player.rect.centery]
        
        if player_on_prism:
            self.game.sounds['upgrade'].play()
            angle, spread = math.atan2(vel[1], vel[0]), 0.4
            self.projectiles.append(Projectile(self.game.animation_manager, pos, (6, 2), 'projectile', self, velocity=vel))
            self.projectiles.append(Projectile(self.game.animation_manager, pos, (6, 2), 'projectile', self, velocity=[math.cos(angle - spread) * speed, math.sin(angle - spread) * speed]))
            self.projectiles.append(Projectile(self.game.animation_manager, pos, (6, 2), 'projectile', self, velocity=[math.cos(angle + spread) * speed, math.sin(angle + spread) * speed]))
        else:
            self.projectiles.append(Projectile(self.game.animation_manager, pos, (6, 2), 'projectile', self, velocity=vel))

    def use_item(self):
        self.item_used = True
        item = self.current_item
        if item == 'warp':
            self.game.sounds['warp'].play(); self.screen_shake = 15
            max_point = min(enumerate(self.stack_heights), key=lambda x: x[1])
            self.player.pos = [(max_point[0] + 1) * self.game.TILE_SIZE + 4, (max_point[1] - 2) * self.game.TILE_SIZE]
            for _ in range(60):
                angle, speed = random.random() * math.pi * 2, random.random() * 1.75
                self.sparks.append([self.player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.02, (12, 8, 2), True, 0.1 * random.choice([0,1])])
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
            if 'explosion' in self.game.sounds: self.game.sounds['explosion'].play()
            self.screen_shake = 25
            to_bomb = [list(tp) for tp in self.tiles if math.sqrt((self.player.center[0]-(tp[0]*self.game.TILE_SIZE+8))**2+(self.player.center[1]-(tp[1]*self.game.TILE_SIZE+8))**2) < 4*self.game.TILE_SIZE]
            for pos in to_bomb:
                if tuple(pos) in self.tiles:
                    for _ in range(15):
                        angle, speed = random.random() * math.pi * 2, random.random() * 2
                        self.sparks.append([[pos[0]*self.game.TILE_SIZE+8, pos[1]*self.game.TILE_SIZE+8], [math.cos(angle)*speed, math.sin(angle)*speed], random.random()*4+2, 0.08, (12,2,2), True, 0.1])
                    del self.tiles[tuple(pos)]
            self.recalculate_stack_heights()
        elif item == 'freeze': self.game.sounds['warp'].play(); self.screen_shake = 10; self.freeze_timer = 360
        elif item == 'hourglass':
            if 'upgrade' in self.game.sounds: self.game.sounds['upgrade'].play()
            self.screen_shake = 8
            if self.combo_multiplier > 1.0:
                self.combo_timer = self.game.COMBO_DURATION
                for i in range(40):
                    angle, speed = random.random() * math.pi * 2, random.random() * 1.5
                    self.sparks.append([[self.game.DISPLAY_SIZE[0]//2, 12], [math.cos(angle) * speed, math.sin(angle) * speed - 0.5], random.random() * 3 + 1, 0.04, (255,220,100), True, 0.02])
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
        if self.lava_y < self.game.DISPLAY_SIZE[1]:
            lava_rect = pygame.Rect(0, int(self.lava_y), self.game.DISPLAY_SIZE[0], self.game.DISPLAY_SIZE[1] - int(self.lava_y))
            base_color, highlight_color = (255, 60, 20), (255, 150, 40)
            color = highlight_color if self.master_clock % 20 < 10 else base_color
            pygame.draw.rect(surf, color, lava_rect)
            if self.master_clock % 4 == 0:
                pos = [random.randint(0, self.game.DISPLAY_SIZE[0]), self.lava_y + 5]
                self.sparks.append([pos, [0, -random.random() * 0.5], random.random() * 2 + 1, 0.08, color, False, 0])

    def render_crystals(self, surf):
        for crystal_rect in self.crystals:
            render_pos = (crystal_rect.x, crystal_rect.y - self.height)
            if -32 < render_pos[1] < self.game.DISPLAY_SIZE[1]:
                surf.blit(self.crystal_img, render_pos)

    def render_placed_tiles(self, surf):
        for pos, data in self.tiles.items():
            blit_pos = (pos[0] * self.game.TILE_SIZE, pos[1] * self.game.TILE_SIZE - int(self.height))
            if blit_pos[1] < -self.game.TILE_SIZE or blit_pos[1] > self.game.DISPLAY_SIZE[1]: continue
                
            img_map = {'placed_tile': self.placed_tile_img, 'greed': self.greed_tile_img, 'magnetic': self.magnetic_tile_img,
                       'unstable': self.unstable_tile_img, 'sticky': self.sticky_tile_img, 'fragile': self.fragile_tile_img,
                       'bounce': self.bounce_tile_img, 'spike': self.spike_tile_img, 'prism': self.prism_tile_img, 'geyser': self.geyser_tile_img}
            
            img_to_blit = img_map.get(data.get('type'), self.tile_img)
            surf.blit(img_to_blit, blit_pos)

            if data['type'] in ['tile', 'placed_tile'] and (pos[0], pos[1]-1) not in self.tiles: surf.blit(self.tile_top_img, blit_pos)
            if data.get('type') == 'chest':
                surf.blit(self.chest_img, (blit_pos[0], blit_pos[1] - self.game.TILE_SIZE))
            elif data.get('type') == 'opened_chest': surf.blit(self.opened_chest_img, (blit_pos[0], blit_pos[1] - self.game.TILE_SIZE))
            
            if data.get('type') == 'geyser' and data.get('data', {}).get('timer', 0) > 90 and self.master_clock % 5 < 3:
                angle, speed = random.uniform(math.pi * 1.3, math.pi * 1.7), random.uniform(0.5, 1.2)
                self.sparks.append([[blit_pos[0]+8, blit_pos[1]+2], [math.cos(angle)*speed*0.5, math.sin(angle)*speed], random.uniform(1,3), 0.1, (200,200,255), False, 0])


    def render_falling_tiles(self, surf):
        for tile in self.tile_drops:
            pos = (tile[0], tile[1] - self.height)
            if pos[1] < -self.game.TILE_SIZE or pos[1] > self.game.DISPLAY_SIZE[1]: continue
            
            img_map = {'greed': self.greed_tile_img, 'motherlode': self.motherlode_tile_img, 'unstable': self.unstable_tile_img,
                       'magnetic': self.magnetic_tile_img, 'sticky': self.sticky_tile_img, 'fragile': self.fragile_tile_img,
                       'bounce': self.bounce_tile_img, 'spike': self.spike_tile_img, 'prism': self.prism_tile_img, 'geyser': self.geyser_tile_img}
            img_to_blit = img_map.get(tile[2], self.tile_img)
            surf.blit(img_to_blit, pos)
            
            if tile[2] == 'chest': surf.blit(self.ghost_chest_img, (pos[0], pos[1] - self.game.TILE_SIZE))
            if random.randint(1, 4) == 1:
                side = random.choice([-1, 1])
                self.sparks.append([[pos[0] + self.game.TILE_SIZE * (side > 0), pos[1]], [random.uniform(-0.05, 0.05), random.uniform(0, 0.5)], random.uniform(3,5), 0.15, (4,2,12), False, 0])

    def render_items(self, surf):
        for item in self.items:
            item_pos = (item.center[0], item.center[1] - self.height)
            r1, r2 = int(9+math.sin(self.master_clock/30)*3), int(5+math.sin(self.master_clock/40)*2)
            surf.blit(glow_img(r1,(12,8,2)), (item_pos[0]-r1-1, item_pos[1]-r1-2), special_flags=BLEND_RGBA_ADD)
            surf.blit(glow_img(r2,(24,16,3)), (item_pos[0]-r2-1, item_pos[1]-r2-2), special_flags=BLEND_RGBA_ADD)
            item.render(surf, (0, self.height))

    def render_projectiles(self, surf):
        for p in self.projectiles: p.render(surf, (0, self.height))

    def render_shield_aura(self, surf):
        aura_pos = (self.player.rect.centerx - self.shield_aura_img.get_width()//2, self.player.rect.centery - self.shield_aura_img.get_height()//2 - self.height)
        pulse = math.sin(self.master_clock / 8) * 2
        pulsing = pygame.transform.scale(self.shield_aura_img, (int(self.shield_aura_img.get_width() + pulse), int(self.shield_aura_img.get_height() + pulse)))
        pulsing.set_alpha(150 - pulse * 10); surf.blit(pulsing, aura_pos, special_flags=BLEND_RGBA_ADD)
        
    def render_sparks(self, surf):
        for spark in self.sparks:
            size = int(spark[2])
            pos = (spark[0][0], spark[0][1] - self.height)
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
        surf.blit(self.border_img_light, (0, -math.sin(self.master_clock/30)*4-7)); surf.blit(self.border_img, (0, -math.sin(self.master_clock/40)*7-14))
        surf.blit(pygame.transform.flip(self.border_img_light, 0, 1), (0, self.game.DISPLAY_SIZE[1]+math.sin(self.master_clock/40)*3+9-self.border_img.get_height()))
        surf.blit(pygame.transform.flip(self.border_img, 0, 1), (0, self.game.DISPLAY_SIZE[1]+math.sin(self.master_clock/30)*3+16-self.border_img.get_height()))

    def render_hud(self, surface):
        top_left_panel_rect = pygame.Rect(4, 4, 80, 22)
        render_panel_9slice(surface, top_left_panel_rect, self.panel_img, 8)
        
        surface.blit(self.coin_icon, (10, 8))
        self.game.black_font.render(str(self.coins), surface, (23, 11))
        self.game.white_font.render(str(self.coins), surface, (22, 10))

        time_meter_center = (66, 16)
        time_meter_radius = 7
        time_meter_pct = self.time_meter / self.game.time_meter_max
        
        pygame.draw.circle(surface, (10, 20, 40), time_meter_center, time_meter_radius + 1)
        
        if time_meter_pct > 0:
            start_angle = math.pi / 2
            end_angle = start_angle - (2 * math.pi * time_meter_pct)
            color = (255, 255, 100) if self.slowing_time and not self.player.is_charging_dash and self.master_clock % 10 < 5 else (80, 150, 255)
            pygame.draw.arc(surface, color, (time_meter_center[0] - time_meter_radius, time_meter_center[1] - time_meter_radius, time_meter_radius*2, time_meter_radius*2), end_angle, start_angle, time_meter_radius)
        
        hourglass_icon = self.game.item_icons['hourglass']
        surface.blit(hourglass_icon, (time_meter_center[0] - hourglass_icon.get_width()//2, time_meter_center[1] - hourglass_icon.get_height()//2))

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

        top_right_panel_rect = pygame.Rect(self.game.DISPLAY_SIZE[0] - 62, 4, 58, 40)
        render_panel_9slice(surface, top_right_panel_rect, self.panel_img, 8)
        
        item_slot_pos = (top_right_panel_rect.right - 24, top_right_panel_rect.top + 6)
        surface.blit(self.item_slot_img, item_slot_pos)
        if self.current_item:
            if (self.master_clock % 50 < 12) or (abs(self.master_clock % 50 - 20) < 3):
                surface.blit(self.item_slot_flash_img, item_slot_pos)
            surface.blit(self.game.item_icons[self.current_item], (item_slot_pos[0] + 5, item_slot_pos[1] + 5))
        
        prompt_font = Font(self.game.get_path('data', 'fonts', 'small_font.png'), (255, 230, 90))
        prompt_font.render("E/X", surface, (item_slot_pos[0] - 16, item_slot_pos[1] + 4))

        bar_x = top_right_panel_rect.left + 5
        bar_y = top_right_panel_rect.bottom - 12
        bar_w = top_right_panel_rect.width - 10
        bar_h = 6
        pygame.draw.rect(surface, (10, 20, 40), [bar_x, bar_y, bar_w, bar_h])
        if self.player.is_charging_dash:
            color = (255, 255, 255) if self.master_clock % 10 < 5 else (255, 150, 40)
        else:
            color = (255, 150, 40) if self.player.focus_meter >= self.player.FOCUS_DASH_COST else (100, 60, 20)
        fill_w = int((bar_w-2) * (self.player.focus_meter / self.player.FOCUS_METER_MAX))
        pygame.draw.rect(surface, color, [bar_x + 1, bar_y + 1, fill_w, bar_h - 2])

        if self.active_perks:
            num_perks = len(self.active_perks)
            perk_panel_w = 6 + (num_perks * 12)
            perk_panel_rect = pygame.Rect(4, self.game.DISPLAY_SIZE[1] - 22, perk_panel_w, 18)
            render_panel_9slice(surface, perk_panel_rect, self.panel_img, 8)

            x_off = perk_panel_rect.left + 5
            for key in sorted(list(self.active_perks)):
                if key in self.perk_icons:
                    icon = self.perk_icons[key]
                    surface.blit(icon, (x_off, perk_panel_rect.top + 4))
                    x_off += icon.get_width() + 2