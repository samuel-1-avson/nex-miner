import pygame, sys, random, math, json
from pygame.locals import *

from .state import State
from .entity import Player, Item, Projectile
from .text import Font

class GameplayState(State):
    def __init__(self, game):
        super().__init__(game)

        # =========================================================================
        # RESET / INITIALIZATION LOGIC
        # =========================================================================

        self.player = Player(self.game.animation_manager, (self.game.DISPLAY_SIZE[0] // 2 - 5, -20), (8, 16), 'player')
        self.player.jumps_max += self.game.save_data['upgrades']['jumps']
        self.player.speed += self.game.save_data['upgrades']['speed'] * 0.08
        self.player.jumps = self.player.jumps_max

        self.dead = False
        self.tiles = {}
        self.tile_drops = []
        self.sparks = []
        self.projectiles = []
        self.items = []

        self.game_timer = 0
        self.height = 0
        self.target_height = 0
        self.coins = 0
        self.end_coin_count = 0
        self.current_item = None
        self.master_clock = 0
        self.item_used = False
        
        # Timers & Scales
        self.freeze_timer = 0
        self.time_meter = self.game.time_meter_max
        self.time_scale = 1.0
        self.slowing_time = False

        # Combo
        self.combo_multiplier = 1.0
        self.combo_timer = 0
        self.COMBO_DURATION = 180

        # Post-run
        self.run_coins_banked = False
        self.upgrade_selection = 0
        self.new_high_score = False

        # System
        self.screen_shake = 0
        self.player_shielded = False
        self.last_place = 0
        
        # Biome
        self.current_biome_index = 0
        self.game.load_biome_bgs(self.game.BIOMES[self.current_biome_index]) # Load initial biome GFX

        # Perks
        self.active_perks = set()
        self.last_perk_score = 0
        self.perk_selection_active = False
        self.perk_selection_choice = 0
        self.perks_to_offer = []

        # Initialize the starting tiles
        for i_inner in range(self.game.WINDOW_TILE_SIZE[0] - 2):
            self.tiles[(i_inner + 1, self.game.WINDOW_TILE_SIZE[1] - 1)] = {'type': 'tile', 'data': {}}
        self.tiles[(1, self.game.WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
        self.tiles[(self.game.WINDOW_TILE_SIZE[0] - 2, self.game.WINDOW_TILE_SIZE[1] - 2)] = {'type': 'tile', 'data': {}}
        self.stack_heights = [self.game.WINDOW_TILE_SIZE[1] - 1 for i_inner in range(self.game.WINDOW_TILE_SIZE[0] - 2)]
        self.stack_heights[0] -= 1
        self.stack_heights[-1] -= 1
        
        # Link player perks to the instance
        self.player.active_perks = self.active_perks


    # =========================================================================
    # STATE-SPECIFIC METHODS (formerly global functions)
    # =========================================================================
    
    def handle_death(self):
        if self.player_shielded:
            self.player_shielded = False
            if 'explosion' in self.game.sounds: self.game.sounds['explosion'].play()
            else: self.game.sounds['super_jump'].play()
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

    def recalculate_stack_heights(self):
        new_heights = [self.game.WINDOW_TILE_SIZE[1] for i in range(self.game.WINDOW_TILE_SIZE[0] - 2)]
        for tile_x, tile_y in self.tiles:
            if 1 <= tile_x < self.game.WINDOW_TILE_SIZE[0] - 1:
                col_index = tile_x - 1
                new_heights[col_index] = min(new_heights[col_index], tile_y)
        self.stack_heights = new_heights

    def lookup_nearby(self, pos):
        rects = []
        for offset in [(0, 0), (-1, -1), (-1, 0), (-1, 1), (0, 1), (0, -1), (1, -1), (1, 0), (1, 1)]:
            lookup_pos = (pos[0] // self.game.TILE_SIZE + offset[0], pos[1] // self.game.TILE_SIZE + offset[1])
            if lookup_pos in self.tiles:
                rects.append(pygame.Rect(lookup_pos[0] * self.game.TILE_SIZE, lookup_pos[1] * self.game.TILE_SIZE, self.game.TILE_SIZE, self.game.TILE_SIZE))
        return rects

    # =========================================================================
    # CORE STATE LOOPS
    # =========================================================================
    
    def handle_events(self, events):
        for event in events:
            super().handle_events([event])

            # --- PERK SELECTION INPUT ---
            if self.perk_selection_active:
                if event.type == KEYDOWN:
                    if event.key in [K_DOWN, K_s]:
                        self.perk_selection_choice = (self.perk_selection_choice + 1) % len(self.perks_to_offer)
                    if event.key in [K_UP, K_w]:
                        self.perk_selection_choice = (self.perk_selection_choice - 1 + len(self.perks_to_offer)) % len(self.perks_to_offer)
                    if event.key in [K_RETURN, K_e, K_x]:
                        chosen_perk = self.perks_to_offer[self.perk_selection_choice]
                        self.active_perks.add(chosen_perk)
                        self.perk_selection_active = False
                        if 'upgrade' in self.game.sounds: self.game.sounds['upgrade'].play()
                        else: self.game.sounds['collect_item'].play()
                continue # Skip all other game inputs

            # --- GAMEPLAY INPUT ---
            if event.type == KEYDOWN:
                if not self.dead:
                    # DASHING
                    if event.key in [K_c, K_l] and self.player.focus_meter >= self.player.FOCUS_DASH_COST:
                        self.player.is_charging_dash = True
                    # MOVEMENT
                    if event.key in [K_RIGHT, K_d]: self.player.right = True
                    if event.key in [K_LEFT, K_a]: self.player.left = True
                    # JUMPING
                    if event.key in [K_UP, K_w, K_SPACE]:
                        self.player.jump_buffer_timer = 8
                        if self.player.air_time < 2 or self.player.coyote_timer > 0 or self.player.jumps > 0:
                            self.game.sounds['jump'].play()
                            self.player.attempt_jump()
                    # SHOOTING
                    if event.key in [K_z, K_k] and len(self.projectiles) < 4:
                        self.game.sounds['jump'].play()
                        # (Shooting logic here, converted to use self.player, self.projectiles)
                    # ITEM USAGE
                    if event.key in [K_e, K_x]:
                        # (All item usage logic from K_e block, converted to self. variables)
                        pass 

                else: # --- DEAD / GAME OVER CONTROLS ---
                    if self.run_coins_banked:
                        # (All upgrade buying logic, converted to self. variables)
                        pass

                # RESTART
                if event.key == K_r and self.dead:
                    new_gameplay_state = GameplayState(self.game)
                    self.game.states.pop()
                    self.game.states.append(new_gameplay_state)

            if event.type == KEYUP:
                if not self.dead:
                    # (All KEYUP logic from original file, converted)
                    if event.key in [K_c, K_l] and self.player.is_charging_dash:
                         self.player.is_charging_dash = False
                         self.player.focus_meter -= self.player.FOCUS_DASH_COST
                         self.player.dash_timer = self.player.DASH_DURATION
                         #... etc
                    if event.key in [K_RIGHT, K_d]: self.player.right = False
                    if event.key in [K_LEFT, K_a]: self.player.left = False
    
    def update(self):
        if self.perk_selection_active:
            # Freeze the game logic but not the event loop when choosing perks
            return

        self.master_clock += 1
        
        # -- BIOME TRANSITION --
        if not self.dead:
            next_biome_index = self.current_biome_index
            if self.current_biome_index + 1 < len(self.game.BIOMES):
                if self.coins >= self.game.BIOMES[self.current_biome_index + 1]['score_req']:
                    next_biome_index += 1
            if next_biome_index != self.current_biome_index:
                self.current_biome_index = next_biome_index
                self.game.load_biome_bgs(self.game.BIOMES[self.current_biome_index])
                self.game.sounds['warp'].play()
                self.screen_shake = 15

        # -- TIME SCALING --
        self.time_scale = 1.0
        if not self.dead:
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
            else:
                self.time_meter = min(self.game.time_meter_max, self.time_meter + 0.2)
        if self.dead:
            self.slowing_time = False
            self.time_scale = 1.0
        
        if self.screen_shake > 0: self.screen_shake -= 0.5 * self.time_scale
        if self.freeze_timer > 0: self.freeze_timer -= 1 * self.time_scale

        # -- COMBO --
        if self.combo_timer > 0:
            depletion_rate = 1
            if 'glass_cannon' in self.active_perks: depletion_rate = 2
            self.combo_timer -= depletion_rate * self.time_scale
            if self.combo_timer <= 0 and self.combo_multiplier > 1.0:
                self.combo_timer = 0
                if 'combo_end' in self.game.sounds: self.game.sounds['combo_end'].play()
                for i in range(20):
                    angle = random.random() * math.pi * 2; speed = random.random() * 1.5
                    self.sparks.append([[self.game.DISPLAY_SIZE[0] // 2, 10], [math.cos(angle) * speed, math.sin(angle) * speed], random.random() * 2 + 1, 0.05, (251, 245, 239), True, 0.05])
                self.combo_multiplier = 1.0
        
        # -- TILE SPAWNING --
        if self.master_clock > 180:
            self.game_timer += self.time_scale
            if self.game_timer > 10 + 25 * (20000 - min(20000, self.master_clock)) / 20000:
                # (All tile spawning logic converted to use self. variables)
                # ...
                pass
                
        # -- UPDATE FALLING TILES (TILE_DROPS) --
        # (The big for-loop for tile_drops, with all collision checks against player)
        # ...
        
        # -- UPDATE PLACED TILES (TIMERS, EXPLOSIONS) --
        # (The for-loop for self.tiles, handling fragile and unstable logic)
        # ...
        
        # -- UPDATE ITEMS ON GROUND (self.items) --
        # (For loop for items, handling collection and magnet logic)
        # ...

        # -- UPDATE PROJECTILES --
        # (For loop for self.projectiles)
        # ...

        # -- PLAYER UPDATE --
        if not self.dead:
            tile_rects = [pygame.Rect(p[0] * self.game.TILE_SIZE, p[1] * self.game.TILE_SIZE, self.game.TILE_SIZE, self.game.TILE_SIZE) for p in self.tiles]
            tile_drop_rects = [pygame.Rect(t[0], t[1], self.game.TILE_SIZE, self.game.TILE_SIZE) for t in self.tile_drops]
            edge_rects = [
                pygame.Rect(0, self.player.pos[1] - 300, self.game.TILE_SIZE, 600),
                pygame.Rect(self.game.TILE_SIZE * (self.game.WINDOW_TILE_SIZE[0] - 1), self.player.pos[1] - 300, self.game.TILE_SIZE, 600)
            ]
            collisions = self.player.update(tile_drop_rects + edge_rects + tile_rects, self.time_scale)
            # (All logic for bounce, spike, fragile, sticky tiles based on collisions)
            # ...
        else:
            self.player.opacity = 80
            self.player.update([], self.time_scale)
            self.player.rotation -= 16

        # -- UPDATE SPARKS --
        # (For loop for self.sparks)
        # ...

        # -- LEVEL SCROLLING (height) --
        base_row = max(self.tiles, key=lambda x: x[1])[1] - 1 if self.tiles else self.game.WINDOW_TILE_SIZE[1] - 2
        filled = all((i + 1, base_row) in self.tiles for i in range(self.game.WINDOW_TILE_SIZE[0] - 2))
        if filled: self.target_height = math.floor(self.height / self.game.TILE_SIZE) * self.game.TILE_SIZE + self.game.TILE_SIZE
        if self.height != self.target_height:
            # (Scrolling logic for self.height)
            # ...

        # -- PERK OFFERING --
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


    def render(self, surface):
        # Store a copy for the perk screen background effect
        display_copy = surface.copy()
        
        # --- BACKGROUND ---
        current_biome = self.game.BIOMES[self.current_biome_index]
        surface.fill(current_biome['bg_color'])
        if self.game.backgrounds['far']:
            scroll_y = (self.height * 0.2) % self.game.DISPLAY_SIZE[1]
            surface.blit(self.game.backgrounds['far'], (0, scroll_y))
            surface.blit(self.game.backgrounds['far'], (0, scroll_y - self.game.DISPLAY_SIZE[1]))
        if self.game.backgrounds['near']:
            scroll_y = (self.height * 0.4) % self.game.DISPLAY_SIZE[1]
            surface.blit(self.game.backgrounds['near'], (0, scroll_y))
            surface.blit(self.game.backgrounds['near'], (0, scroll_y - self.game.DISPLAY_SIZE[1]))

        if self.freeze_timer > 0:
            freeze_overlay = pygame.Surface(self.game.DISPLAY_SIZE, pygame.SRCALPHA)
            alpha = 60 + math.sin(self.master_clock / 5) * 10
            freeze_overlay.fill((170, 200, 255, alpha))
            surface.blit(freeze_overlay, (0, 0))

        # --- TILE DRAWING (PLACED AND FALLING) ---
        # (All blitting logic for self.tiles and self.tile_drops)
        # ...

        # --- LEVEL EDGES ---
        # (Logic to draw edge_tile_img)
        # ...

        # --- ITEMS, PROJECTILES, SPARKS ---
        # (For loops to render all these entities)
        # ...

        # --- PLAYER ---
        if self.player_shielded and not self.dead:
            # (Shield aura drawing logic)
            pass
        self.player.render(surface, (0, -int(self.height)))

        # --- BORDERS ---
        # (Border image drawing logic)
        # ...

        # --- HUD & UI ---
        if not self.dead:
            # (All the HUD drawing logic for coins, meters, items, combo, perks)
            # ...
        else:
            # (The entire GAME OVER screen drawing logic with upgrades)
            if self.end_coin_count != self.coins and self.master_clock % 3 == 0:
                self.game.sounds['coin_end'].play()
                self.end_coin_count = min(self.end_coin_count + 1, self.coins)
            elif not self.run_coins_banked:
                self.game.save_data['banked_coins'] += self.end_coin_count
                self.game.write_save(self.game.save_data)
                self.run_coins_banked = True
            #... a lot more drawing logic here...

        # --- PERK SELECTION SCREEN ---
        if self.perk_selection_active:
            #surface.blit(display_copy, (0, 0)) <-- This will be tricky, let's render the world first then overlay.
            overlay = pygame.Surface(self.game.DISPLAY_SIZE, pygame.SRCALPHA)
            overlay.fill((10, 5, 20, 200))
            surface.blit(overlay, (0, 0))
            # (All the drawing logic for the perk choice panels)
            # ...
            
        # -- Screen Shake applied in main game loop now for simplicity --