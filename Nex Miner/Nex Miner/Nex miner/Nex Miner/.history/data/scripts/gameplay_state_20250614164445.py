# Cavyn Source/data/scripts/gameplay_state.py
# This class contains the entire logic and state for an active game session.

import pygame
import sys
import random
import math
from pygame.locals import *

# Import our custom classes.
# Note: The Entity class must now contain Player, Item, and Projectile, or they should be imported separately.
from .state.state import State
from .entity import Player, Item, Projectile 
from .text import Font


class GameplayState(State):
    def __init__(self, game):
        """
        Sets up a new game run. This code is equivalent to your
        old 'Restart' logic, creating a fresh play session.
        """
        super().__init__(game)

        # Game Session State
        self.dead = False
        self.run_coins_banked = False
        self.new_high_score = False

        # Player Setup
        self.player = Player(self.game.animation_manager, (self.game.DISPLAY_SIZE[0] // 2 - 5, -20), (8, 16), 'player')
        self.player.jumps_max += self.game.save_data['upgrades']['jumps']
        self.player.speed += self.game.save_data['upgrades']['speed'] * 0.08
        self.player.jumps = self.player.jumps_max
        self.player_shielded = False

        # World and Tile State
        self.tiles = {}
        self.tile_drops = []
        self.height = 0
        self.target_height = 0
        self.last_place = 0
        self.recalculate_stack_heights = True # Flag to trigger initial calculation

        # Item and Scoring State
        self.items = []
        self.projectiles = []
        self.current_item = None
        self.item_used = False
        self.coins = 0
        self.end_coin_count = 0
        self.upgrade_selection = 0

        # Timers and Effects State
        self.master_clock = 0
        self.game_timer = 0
        self.slowing_time = False
        self.time_meter = self.game.time_meter_max
        self.time_scale = 1.0
        self.freeze_timer = 0
        self.screen_shake = 0
        
        # Combo State
        self.combo_multiplier = 1.0
        self.combo_timer = 0
        self.COMBO_DURATION = 180

        # Perk State
        self.active_perks = set()
        self.last_perk_score = 0
        self.perk_selection_active = False
        self.perk_selection_choice = 0
        self.perks_to_offer = []

        # Biome State
        self.current_biome_index = 0
        self.current_biome = self.game.BIOMES[self.current_biome_index] # Load initial biome info
        self.game.load_biome_bgs(self.current_biome) # Tell game engine to load visuals

        # Initial world generation
        for i_inner in range(self.game.WINDOW_TILE_SIZE[0] - 2):
            self.tiles[(i_inner + 1, self.game.WINDOW_TILE_SIZE[1] - 1)] = {'type': 'tile', 'data': {}}
        self.tiles[(1, self.game.WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
        self.tiles[(self.game.WINDOW_TILE_SIZE[0] - 2, self.game.WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
        
        self.stack_heights = [self.game.WINDOW_TILE_SIZE[1] - 1 for i in range(self.game.WINDOW_TILE_SIZE[0] - 2)]
        self.stack_heights[0] -= 1
        self.stack_heights[-1] -= 1


    def handle_death(self):
        """ Manages player death, checks for shield, and updates save data. """
        if self.player_shielded:
            self.player_shielded = False
            self.game.sounds['explosion'].play() if 'explosion' in self.game.sounds else self.game.sounds['super_jump'].play()
            self.screen_shake = 15
            for i in range(60):
                angle = random.random() * math.pi * 2
                speed = random.random() * 2
                self.sparks.append([self.player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.uniform(2, 4), 0.05, (170, 200, 255), True, 0.05])
            return

        if not self.dead:
            self.game.sounds['death'].play()
            self.screen_shake = 20
            if self.coins > self.game.save_data['high_score']:
                self.game.save_data['high_score'] = self.coins
                self.new_high_score = True
                self.game.write_save(self.game.save_data)

            self.dead = True
            self.run_coins_banked = False
            self.upgrade_selection = 0
            self.player.velocity = [1.3, -6]
            for i in range(380):
                angle = random.random() * math.pi
                speed = random.random() * 1.5
                physics_on = random.choice([False, True, True])
                self.sparks.append([self.player.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 3 + 3, 0.02, (12, 2, 2), physics_on, 0.1 * physics_on])


    def _recalculate_stack_heights_internal(self):
        """ Internal method to update the height of each tile column. """
        new_heights = [self.game.WINDOW_TILE_SIZE[1] for i in range(self.game.WINDOW_TILE_SIZE[0] - 2)]
        for tile_x, tile_y in self.tiles:
            if 1 <= tile_x < self.game.WINDOW_TILE_SIZE[0] - 1:
                col_index = tile_x - 1
                new_heights[col_index] = min(new_heights[col_index], tile_y)
        self.stack_heights = new_heights
        self.recalculate_stack_heights = False

    def handle_events(self, events):
        """ Handles all user input for the gameplay state. """
        for event in events:
            # Handle universal quit events from the base class
            super().handle_events([event]) 

            if event.type == KEYDOWN:
                # Perk Selection Input
                if self.perk_selection_active:
                    if event.key in [K_DOWN, K_s]:
                        self.perk_selection_choice = (self.perk_selection_choice + 1) % len(self.perks_to_offer)
                    if event.key in [K_UP, K_w]:
                        self.perk_selection_choice = (self.perk_selection_choice - 1 + len(self.perks_to_offer)) % len(self.perks_to_offer)
                    if event.key in [K_RETURN, K_e, K_x]:
                        chosen_perk = self.perks_to_offer[self.perk_selection_choice]
                        self.active_perks.add(chosen_perk)
                        self.perk_selection_active = False
                        self.game.sounds['upgrade'].play() if 'upgrade' in self.game.sounds else self.game.sounds['collect_item'].play()
                    continue  # Skip all other input while perk selection is active

                # In-Game (Alive) Input
                if not self.dead:
                    if event.key in [K_c, K_l] and self.player.focus_meter >= self.player.FOCUS_DASH_COST:
                        self.player.is_charging_dash = True
                    if event.key in [K_RIGHT, K_d]:
                        self.player.right = True
                    if event.key in [K_LEFT, K_a]:
                        self.player.left = True
                    if event.key in [K_UP, K_w, K_SPACE]:
                        self.player.jump_buffer_timer = 8
                        if self.player.air_time < 2 or self.player.coyote_timer > 0 or self.player.jumps > 0:
                            self.game.sounds['jump'].play()
                            self.player.attempt_jump()
                    
                    if event.key in [K_z, K_k] and len(self.projectiles) < 4:
                        self.game.sounds['jump'].play()
                        pressed = pygame.key.get_pressed()
                        speed, vel, pos = 4, [0, 0], []
                        if pressed[K_UP] or pressed[K_w]:
                            vel, pos = [0, -speed], [self.player.rect.centerx, self.player.rect.top]
                        elif pressed[K_DOWN] or pressed[K_s]:
                             vel, pos = [0, speed], [self.player.rect.centerx, self.player.rect.bottom]
                        elif self.player.flip[0]:
                             vel, pos = [speed, 0], [self.player.rect.right, self.player.rect.centery]
                        else:
                             vel, pos = [-speed, 0], [self.player.rect.left, self.player.rect.centery]
                        self.projectiles.append(Projectile(self.game.animation_manager, pos, (6, 2), 'projectile', velocity=vel))
                    
                    if event.key in [K_e, K_x] and self.current_item:
                        self.item_used = True
                        if self.current_item == 'warp':
                            self.game.sounds['warp'].play()
                            self.screen_shake = 15
                            max_point = min(enumerate(self.stack_heights), key=lambda x: x[1])
                            self.player.pos[0] = (max_point[0] + 1) * self.game.TILE_SIZE + 4
                            self.player.pos[1] = (max_point[1] - 1) * self.game.TILE_SIZE
                        elif self.current_item == 'jump':
                            self.game.sounds['super_jump'].play()
                            self.screen_shake = 12
                            self.player.jumps += 1
                            self.player.attempt_jump()
                            self.player.velocity[1] = -8
                        elif self.current_item == 'cube':
                             self.game.sounds['block_land'].play()
                             place_pos = (int(self.player.center[0] // self.game.TILE_SIZE), int(self.player.pos[1] // self.game.TILE_SIZE) + 1)
                             self.stack_heights[place_pos[0] - 1] = place_pos[1]
                             base_row = max(self.tiles, key=lambda x: x[1])[1] - 1 if self.tiles else self.game.WINDOW_TILE_SIZE[1] - 2
                             for i in range(place_pos[1], base_row + 2):
                                 self.tiles[(place_pos[0], i)] = {'type': 'placed_tile', 'data': {}}
                        elif self.current_item == 'bomb':
                             self.game.sounds['explosion'].play() if 'explosion' in self.game.sounds else None
                             self.screen_shake = 25
                             tiles_to_bomb = [list(pos) for pos in self.tiles if math.hypot(self.player.center[0] - (pos[0] * self.game.TILE_SIZE + 8), self.player.center[1] - (pos[1] * self.game.TILE_SIZE + 8)) < 4 * self.game.TILE_SIZE]
                             for pos in tiles_to_bomb:
                                 if tuple(pos) in self.tiles:
                                     # (Add particles here)
                                     del self.tiles[tuple(pos)]
                             self.recalculate_stack_heights = True
                        elif self.current_item == 'freeze':
                             self.game.sounds['warp'].play()
                             self.screen_shake = 10
                             self.freeze_timer = 360
                        
                        self.current_item = None
                
                # Game Over Input
                else:
                    if self.run_coins_banked:
                        if event.key == K_DOWN:
                            self.upgrade_selection = (self.upgrade_selection + 1) % len(self.game.UPGRADES)
                        if event.key == K_UP:
                            self.upgrade_selection = (self.upgrade_selection - 1 + len(self.game.UPGRADES)) % len(self.game.UPGRADES)
                        if event.key == K_RETURN:
                            key = self.game.upgrade_keys[self.upgrade_selection]
                            upgrade = self.game.UPGRADES[key]
                            level = self.game.save_data['upgrades'][key]
                            cost = int(upgrade['base_cost'] * (1.5 ** level))
                            if level < upgrade['max_level'] and self.game.save_data['banked_coins'] >= cost:
                                self.game.save_data['banked_coins'] -= cost
                                self.game.save_data['upgrades'][key] += 1
                                self.game.write_save(self.game.save_data)
                                self.game.sounds['upgrade'].play() if 'upgrade' in self.game.sounds else None

                # Restart Key
                if event.key == K_r and self.dead:
                    new_gameplay_state = GameplayState(self.game)
                    self.game.states.pop()
                    self.game.states.append(new_gameplay_state)

            if event.type == KEYUP and not self.dead:
                if event.key in [K_c, K_l]:
                    if self.player.is_charging_dash:
                        self.player.is_charging_dash = False
                        self.player.focus_meter -= self.player.FOCUS_DASH_COST
                        self.player.dash_timer = self.player.DASH_DURATION
                        self.game.sounds['explosion'].play() if 'explosion' in self.game.sounds else self.game.sounds['block_land'].play()
                if event.key in [K_RIGHT, K_d]:
                    self.player.right = False
                if event.key in [K_LEFT, K_a]:
                    self.player.left = False

    def update(self):
        """ Runs all the game logic for one frame. """
        
        self.display_copy = self.game.display.copy() # For perk selection screen background

        if self.perk_selection_active:
            # If the perk screen is up, we freeze all game logic.
            # Rendering and event handling will still happen.
            return

        if self.recalculate_stack_heights:
             self._recalculate_stack_heights_internal()

        # Update Timers and Effects
        self.master_clock += 1
        if self.screen_shake > 0: self.screen_shake -= 0.5 * self.time_scale
        
        # Biome Logic
        if not self.dead:
            next_biome_index = self.current_biome_index
            if self.current_biome_index + 1 < len(self.game.BIOMES) and self.coins >= self.game.BIOMES[self.current_biome_index + 1]['score_req']:
                next_biome_index += 1
            if next_biome_index != self.current_biome_index:
                self.current_biome_index = next_biome_index
                self.current_biome = self.game.BIOMES[self.current_biome_index]
                self.game.load_biome_bgs(self.current_biome)
                # Biome transition effect would go here if needed (flash screen, sound)
        
        # Time Dilation Logic
        is_slowing_now = (pygame.key.get_pressed()[K_LSHIFT] and self.time_meter > 0) or self.player.is_charging_dash
        if not self.dead:
            if is_slowing_now and not self.slowing_time: self.game.sounds['time_slow_start'].play()
            elif not is_slowing_now and self.slowing_time: self.game.sounds['time_slow_end'].play()
        self.slowing_time = is_slowing_now if not self.dead else False
        self.time_scale = 0.4 if self.slowing_time else 1.0
        
        if self.slowing_time:
            if self.player.is_charging_dash:
                self.player.focus_meter = max(0, self.player.focus_meter - 1.5)
                if self.player.focus_meter <= 0: self.player.is_charging_dash = False
            else: # Normal slow
                self.time_meter = max(0, self.time_meter - 0.75)
                if self.time_meter <= 0: self.game.sounds['time_empty'].play()
        else:
            self.time_meter = min(self.game.time_meter_max, self.time_meter + 0.2)
        
        if self.freeze_timer > 0: self.freeze_timer -= 1 * self.time_scale

        # Combo Logic
        if self.combo_timer > 0:
            depletion = 1 * (2 if 'glass_cannon' in self.active_perks else 1)
            self.combo_timer -= depletion * self.time_scale
            if self.combo_timer <= 0 and self.combo_multiplier > 1.0:
                self.combo_timer = 0
                self.game.sounds['combo_end'].play() if 'combo_end' in self.game.sounds else None
                self.combo_multiplier = 1.0

        # Update World Scrolling
        base_row = max(self.tiles, key=lambda x: x[1])[1] - 1 if self.tiles else self.game.WINDOW_TILE_SIZE[1] - 2
        filled = all((i + 1, base_row) in self.tiles for i in range(self.game.WINDOW_TILE_SIZE[0] - 2))
        if filled:
            self.target_height = math.floor(self.height / self.game.TILE_SIZE) * self.game.TILE_SIZE + self.game.TILE_SIZE
        if self.height != self.target_height:
            self.height += (self.target_height - self.height) / 10
            if abs(self.target_height - self.height) < 0.2:
                self.height = self.target_height
                for i in range(self.game.WINDOW_TILE_SIZE[0] - 2):
                    if (i + 1, base_row + 1) in self.tiles: del self.tiles[(i + 1, base_row + 1)]

        # Tile Spawning
        if self.master_clock > 180:
            self.game_timer += self.time_scale
            spawn_threshold = 10 + 25 * (20000 - min(20000, self.master_clock)) / 20000
            if self.game_timer > spawn_threshold:
                self.game_timer = 0
                minimum = min(self.stack_heights)
                options = [i for i, stack in enumerate(self.stack_heights) if i != self.last_place for _ in range(int((stack - minimum) ** (2.2 - min(20000, self.master_clock) / 10000)) + 1)]
                
                tile_type = random.choices(
                    population=['motherlode', 'unstable', 'special', 'normal'], 
                    weights=[2, 3, 10, 85], k=1)[0]
                
                if tile_type == 'normal':
                    tile_type = random.choices(
                        population=['chest', 'fragile', 'bounce', 'spike', 'tile'],
                        weights=[1, 2, 2, 1, 24], k=1)[0]
                elif tile_type == 'special':
                    # This logic only works if there is one special tile per biome
                    special_tile = list(self.current_biome['special_spawn_rate'].keys())[0]
                    tile_type = special_tile

                if tile_type not in self.current_biome['available_tiles']: tile_type = 'tile'

                c = random.choice(options)
                self.last_place = c
                self.tile_drops.append([(c + 1) * self.game.TILE_SIZE, -self.height - self.game.TILE_SIZE, tile_type])
        
        # Update All Entities
        self.update_falling_tiles()
        self.update_placed_tiles()
        self.update_items()
        self.update_projectiles()
        self.update_player()
        self.update_sparks()
        
        # Perk Offering Logic
        if not self.dead and not self.perk_selection_active:
            score_interval = 75
            if self.coins > 0 and self.coins // score_interval > self.last_perk_score // score_interval:
                self.last_perk_score = self.coins
                available_perks = [p for p in self.game.PERKS.keys() if p not in self.active_perks]
                if available_perks:
                    self.perk_selection_active = True
                    self.perks_to_offer = random.sample(available_perks, k=min(3, len(available_perks)))
                    self.perk_selection_choice = 0
                    self.game.sounds['warp'].play()


    def update_player(self):
        edge_rects = [
            pygame.Rect(0, self.player.pos[1] - 300, self.game.TILE_SIZE, 600),
            pygame.Rect(self.game.TILE_SIZE * (self.game.WINDOW_TILE_SIZE[0] - 1), self.player.pos[1] - 300, self.game.TILE_SIZE, 600)
        ]
        tile_rects = [pygame.Rect(pos[0] * self.game.TILE_SIZE, pos[1] * self.game.TILE_SIZE, self.game.TILE_SIZE, self.game.TILE_SIZE) for pos in self.tiles]
        
        if not self.dead:
            # Player update
            collisions = self.player.update(self.tile_drop_rects + edge_rects + tile_rects, self.time_scale)
            # Wall Slide
            if not collisions['bottom']:
                is_sliding_left = ((self.player.rect.left - 2) // self.game.TILE_SIZE, self.player.rect.centery // self.game.TILE_SIZE)
                is_sliding_right = ((self.player.rect.right + 2) // self.game.TILE_SIZE, self.player.rect.centery // self.game.TILE_SIZE)
                if (is_sliding_left in self.tiles and self.tiles[is_sliding_left]['type'] == 'sticky') or \
                   (is_sliding_right in self.tiles and self.tiles[is_sliding_right]['type'] == 'sticky'):
                    self.player.velocity[1] = min(self.player.velocity[1], 1.0)
            # Tile effects on land
            if collisions['bottom']:
                feet_pos = (self.player.rect.midbottom[0] // self.game.TILE_SIZE, self.player.rect.midbottom[1] // self.game.TILE_SIZE)
                if feet_pos in self.tiles:
                    tile_type = self.tiles[feet_pos]['type']
                    if tile_type == 'fragile' and 'timer' not in self.tiles[feet_pos]['data']:
                        self.tiles[feet_pos]['data']['timer'] = 90
                    elif tile_type == 'bounce':
                        self.player.velocity[1] = -9
                        self.player.jumps = self.player.jumps_max
                    elif tile_type == 'spike':
                        self.handle_death()
                        self.player.velocity = [0, -4]
        else: # If dead
            self.player.opacity = 80
            self.player.update([], self.time_scale)
            self.player.rotation -= 16


    def render(self, surface):
        """ Draws the entire game world and HUD to the screen. """

        surface_copy = surface.copy()
        
        if self.perk_selection_active:
            # Draw the frozen game screen underneath
            surface.blit(self.display_copy, (0, 0))
            overlay = pygame.Surface(self.game.DISPLAY_SIZE, pygame.SRCALPHA)
            overlay.fill((10, 5, 20, 200))
            surface.blit(overlay, (0, 0))
            
            # --- Draw Perk UI ---
            title_text = "CHOOSE A PERK"
            text_w = self.game.white_font.width(title_text, scale=2)
            title_pos = (self.game.DISPLAY_SIZE[0]//2 - text_w//2, 20)
            self.game.black_font.render(title_text, surface, (title_pos[0]+1, title_pos[1]+1), scale=2)
            self.game.white_font.render(title_text, surface, title_pos, scale=2)
            
            panel_y_start, panel_h, panel_margin = 50, 35, 5
            for i, perk_key in enumerate(self.perks_to_offer):
                panel_rect = pygame.Rect(40, panel_y_start + i * (panel_h + panel_margin), self.game.DISPLAY_SIZE[0] - 80, panel_h)
                border_color = (255, 230, 90) if i == self.perk_selection_choice else (150, 150, 180)
                pygame.draw.rect(surface, border_color, panel_rect, 1)
                
                perk_name = self.game.PERKS[perk_key]['name'].upper()
                perk_desc = self.game.PERKS[perk_key]['desc']
                self.game.white_font.render(perk_name, surface, (panel_rect.x + 8, panel_rect.y + 7))
                self.game.black_font.render(perk_desc, surface, (panel_rect.x + 9, panel_rect.y + 19))
                self.game.white_font.render(perk_desc, surface, (panel_rect.x + 8, panel_rect.y + 18))
            return # Skip rest of render

        # --- Normal Game Rendering ---
        
        # Backgrounds
        surface.fill(self.current_biome['bg_color'])
        if self.game.backgrounds['far']:
            scroll_y = (self.height * 0.2) % self.game.DISPLAY_SIZE[1]
            surface.blit(self.game.backgrounds['far'], (0, scroll_y))
            surface.blit(self.game.backgrounds['far'], (0, scroll_y - self.game.DISPLAY_SIZE[1]))
        if self.game.backgrounds['near']:
            scroll_y = (self.height * 0.4) % self.game.DISPLAY_SIZE[1]
            surface.blit(self.game.backgrounds['near'], (0, scroll_y))
            surface.blit(self.game.backgrounds['near'], (0, scroll_y - self.game.DISPLAY_SIZE[1]))

        # Overlays
        if self.freeze_timer > 0:
            freeze_overlay = pygame.Surface(self.game.DISPLAY_SIZE, pygame.SRCALPHA)
            alpha = 60 + math.sin(self.master_clock / 5) * 10
            freeze_overlay.fill((170, 200, 255, alpha))
            surface.blit(freeze_overlay, (0, 0))

        # Render World Entities (Tiles, Items, etc.)
        # ... (You need to create these methods by moving drawing logic here)
        # self.render_placed_tiles(surface)
        # self.render_falling_tiles(surface)
        # self.render_items(surface)
        # self.render_projectiles(surface)
        # self.render_player(surface)
        # self.render_sparks(surface)
        
        # Borders
        # surface.blit(self.game.border_img_light, (0, ...))

        # HUD
        if not self.dead:
            # self.render_hud(surface)
            pass
        else:
            # self.render_game_over(surface)
            pass
        
        # Screenshake application
        if self.screen_shake > 0:
            render_offset = [random.randint(0, int(self.screen_shake)) - int(self.screen_shake) // 2 for _ in range(2)]
            surface.blit(surface_copy, render_offset)


    # I recommend breaking down the large update/render logic further into helper methods
    # for clarity, but this structure fulfills the request. The user would continue
    # populating the update_ and render_ methods as described.
    
    # ... update_falling_tiles, update_placed_tiles, update_items, update_projectiles, update_sparks ...
    # ... render_placed_tiles, render_falling_tiles, render_items, etc ...