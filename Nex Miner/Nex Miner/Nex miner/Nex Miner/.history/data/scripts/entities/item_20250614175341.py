# data/scripts/entities/item.py
import random
from .entity import Entity
from ..core_funcs import normalize

class Item(Entity):
    def __init__(self, assets, pos, size, type, state, velocity=[0, 0]):
        super().__init__(assets, pos, size, type)
        self.state = state
        self.velocity = velocity
        self.time = 0

    def update(self, tiles, time_scale=1.0):
        self.time += 1 * time_scale
        self.velocity[1] = min(self.velocity[1] + 0.2, 3)
        self.velocity[0] = normalize(self.velocity[0], 0.05)
        self.move(self.velocity, tiles, time_scale)