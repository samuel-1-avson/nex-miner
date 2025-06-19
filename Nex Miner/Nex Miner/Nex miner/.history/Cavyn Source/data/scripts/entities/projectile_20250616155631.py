# data/scripts/entities/projectile.py
from ..entity import Entity # <-- CORRECTED: from .entity to ..entity

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