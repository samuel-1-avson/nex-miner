--- START OF FILE Cavyn Source/Cavyn Source/Cavyn Source/data/scripts/entities/bat.py ---
# data/scripts/entities/bat.py
import math
import random
from ..entity import Entity

class Bat(Entity):
    def __init__(self, assets, pos, size, state):
        super().__init__(assets, pos, size, 'bat', state)
        self.state = state
        self.speed = 0.5 + random.random() * 0.3
        self.set_action('fly')

    def update(self, player_pos, time_scale=1.0):
        super().update(1/60, time_scale)

        # Simple homing behavior towards the player
        angle = math.atan2(player_pos[1] - self.center[1], player_pos[0] - self.center[0])
        
        velocity = [math.cos(angle) * self.speed, math.sin(angle) * self.speed]
        
        self.pos[0] += velocity[0] * time_scale
        self.pos[1] += velocity[1] * time_scale
        
        # Set flip based on horizontal velocity
        if velocity[0] > 0.1:
            self.flip[0] = True
        elif velocity[0] < -0.1:
            self.flip[0] = False

    def on_death(self):
        """Create death particles and sound effect."""
        self.state.game.sounds['explosion'].play()
        for _ in range(30):
            angle = random.random() * math.pi * 2
            speed = random.random() * 2.5
            self.state.sparks.append([list(self.center), [math.cos(angle) * speed, math.sin(angle) * speed], random.uniform(2, 4), 0.1, (80, 20, 100), True, 0.05])
---