# data/scripts/entities/turret_projectile.py
import math
from ..entity import Entity

class TurretProjectile(Entity):
    def __init__(self, assets, pos, size, type, state, velocity=[0, 0]):
        super().__init__(assets, pos, size, type)
        self.state = state
        self.velocity = list(velocity)
        self.time = 0

    def update(self, time_scale=1.0):
        super().update(1/60, time_scale)
        self.time += 1
        self.pos[0] += self.velocity[0] * time_scale
        self.pos[1] += self.velocity[1] * time_scale
        
        # Simple rotation effect
        self.rotation = math.sin(self.time / 6) * 10
        
        # Disappear if it goes far off-screen
        if not self.rect.colliderect(self.state.game.display.get_rect().inflate(100, 100)):
            return True # Signal for deletion
        
        return False