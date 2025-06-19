# data/scripts/entities/turret.py
import math
from ..entity import Entity
from .turret_projectile import TurretProjectile

class Turret(Entity):
    def __init__(self, assets, pos, size, type, state, parent_tile_pos):
        super().__init__(assets, pos, size, type)
        self.state = state
        self.parent_tile_pos = parent_tile_pos # The tile it's sitting on
        
        # --- Turret Attributes ---
        self.health = 3
        self.action = 'idle'
        self.fire_cooldown = 0
        self.FIRE_RATE = 150 # Time between shots
        self.TARGET_RANGE_Y = 64 # Vertical range to start firing
        
    def update(self, player_rect, time_scale=1.0):
        super().update(1/60, time_scale)

        # Face the player
        if player_rect.centerx > self.rect.centerx:
            self.flip[0] = True
        else:
            self.flip[0] = False
            
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1 * time_scale
        else:
            # Check if player is roughly level with the turret
            if abs(player_rect.centery - self.rect.centery) < self.TARGET_RANGE_Y:
                self.fire()

    def fire(self):
        # Don't fire if on cooldown
        if self.fire_cooldown > 0:
            return
            
        self.fire_cooldown = self.FIRE_RATE
        
        # Play fire sound
        if 'shoot' in self.state.game.sounds:
            self.state.game.sounds['shoot'].play()
        elif 'jump' in self.state.game.sounds:
             self.state.game.sounds['jump'].play()

        # Create a projectile
        direction = 1 if self.flip[0] else -1
        vel = [2 * direction, 0]
        pos = list(self.center)
        
        # Add a new projectile to the gameplay state's list
        self.state.turret_projectiles.append(
            TurretProjectile(self.assets, pos, (5, 3), 'turret_projectile', self.state, velocity=vel)
        )

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            return True # Indicates destruction
        return False