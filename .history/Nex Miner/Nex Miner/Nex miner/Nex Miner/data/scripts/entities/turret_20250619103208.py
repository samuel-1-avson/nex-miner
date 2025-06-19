# data/scripts/entities/turret.py
import math
import random 
from ..entity import Entity
from .turret_projectile import TurretProjectile
from ..core_funcs import get_line # <<< NEW IMPORT

class Turret(Entity):
    def __init__(self, assets, pos, size, type, state, parent_tile_pos):
        super().__init__(assets, pos, size, type)
        self.state = state
        self.parent_tile_pos = parent_tile_pos # The tile it's sitting on
        
        # Turret Attributes
        self.health = 3
        self.action = 'idle'
        self.fire_cooldown = random.randint(30, 90) # Stagger initial shots
        self.FIRE_RATE = 150 # Time between shots
        self.TARGET_RANGE_Y = 64 # Vertical range to start firing
        
    def update(self, player_rect_world, time_scale=1.0):
        super().update(1/60, time_scale)

        # Face the player
        if player_rect_world.centerx > self.center[0]:
            self.flip[0] = True
        else:
            self.flip[0] = False
            
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1 * time_scale
        else:
            # Check if player is roughly level with the turret and in front of it
            if abs(player_rect_world.centery - self.center[1]) < self.TARGET_RANGE_Y:
                if (self.flip[0] and player_rect_world.centerx > self.center[0]) or \
                   (not self.flip[0] and player_rect_world.centerx < self.center[0]):
                    
                    # --- LINE OF SIGHT CHECK ---
                    start_pos_grid = (int(self.center[0] // self.state.game.TILE_SIZE), int(self.center[1] // self.state.game.TILE_SIZE))
                    end_pos_grid = (int(player_rect_world.centerx // self.state.game.TILE_SIZE), int(player_rect_world.centery // self.state.game.TILE_SIZE))
                    
                    los_clear = True
                    # Get all grid cells between turret and player
                    line_to_player = get_line(start_pos_grid, end_pos_grid)
                    
                    # Check if any of these cells contains a solid tile
                    for pos in line_to_player:
                        if pos in self.state.tiles:
                            los_clear = False
                            break
                            
                    if los_clear:
                        self.fire()

    def fire(self):
        if self.fire_cooldown > 0:
            return
        self.fire_cooldown = self.FIRE_RATE
        
        if 'shoot' in self.state.game.sounds:
            self.state.game.sounds['shoot'].play()
        elif 'jump' in self.state.game.sounds: # Fallback sound
             self.state.game.sounds['jump'].play()

        # Create a projectile in world coordinates
        direction = 1 if self.flip[0] else -1
        vel = [2 * direction, 0]
        pos = list(self.center)
        
        self.state.turret_projectiles.append(
            TurretProjectile(self.assets, pos, (5, 3), 'turret_projectile', self.state, velocity=vel)
        )

    def take_damage(self, amount):
        self.health -= amount
        return self.health <= 0 # Returns True if destroyed