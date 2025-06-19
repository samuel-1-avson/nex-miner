
# data/scripts/entities/turret.py
import math
import random 
from ..entity import Entity
from .turret_projectile import TurretProjectile
from ..core_funcs import get_line # --- NEW: Import the line-of-sight function ---

class Turret(Entity):
    def __init__(self, assets, pos, size, type, state, parent_tile_pos):
        super().__init__(assets, pos, size, type)
        self.state = state
        self.parent_tile_pos = parent_tile_pos # The tile it's sitting on
        
        self.health = 3; self.action = 'idle'
        self.fire_cooldown = random.randint(30, 90) # Stagger initial shots
        self.FIRE_RATE = 150; self.TARGET_RANGE_Y = 64
        
    def update(self, player_rect_world, time_scale=1.0):
        super().update(1/60, time_scale)
        self.flip[0] = player_rect_world.centerx > self.center[0]
            
        if self.fire_cooldown > 0: self.fire_cooldown -= 1 * time_scale
        else:
            if abs(player_rect_world.centery - self.center[1]) < self.TARGET_RANGE_Y:
                if (self.flip[0] and player_rect_world.centerx > self.center[0]) or \
                   (not self.flip[0] and player_rect_world.centerx < self.center[0]):
                    
                    # --- FIX: LINE OF SIGHT CHECK ---
                    start_grid = (int(self.center[0] // self.state.game.TILE_SIZE), int(self.center[1] // self.state.game.TILE_SIZE))
                    end_grid = (int(player_rect_world.centerx // self.state.game.TILE_SIZE), int(player_rect_world.centery // self.state.game.TILE_SIZE))
                    
                    los_clear = True
                    for pos in get_line(start_grid, end_grid):
                        if (pos[0], pos[1]) in self.state.tiles and self.state.tiles[(pos[0], pos[1])].get('type') not in ['chest', 'opened_chest']:
                            los_clear = False
                            break
                    if los_clear: self.fire()

    def fire(self):
        if self.fire_cooldown > 0: return
        self.fire_cooldown = self.FIRE_RATE
        if 'shoot' in self.state.game.sounds: self.state.game.sounds['shoot'].play()
        self.state.turret_projectiles.append(TurretProjectile(
            self.assets, list(self.center), (5, 3), 'turret_projectile', 
            self.state, velocity=[2 * (1 if self.flip[0] else -1), 0]
        ))

    def take_damage(self, amount):
        self.health -= amount
        return self.health <= 0