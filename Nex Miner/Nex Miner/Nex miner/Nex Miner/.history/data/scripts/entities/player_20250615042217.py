# data/scripts/entities/player.py
import random
import math 
from ..entity import Entity

class Player(Entity):
    def __init__(self, assets, pos, size, type, state):
        super().__init__(assets, pos, size, type)
        self.state = state
        self.velocity = [0, 0]
        self.right = False
        self.left = False
        self.speed = 1.4
        self.jumps = 2
        self.jumps_max = 2
        self.jumping = False
        self.jump_rot = 0
        self.air_time = 0
        self.coyote_timer = 0
        self.jump_buffer_timer = 0
        self.dash_timer = 0
        self.DASH_SPEED = 8
        self.DASH_DURATION = 8
        
        # Apply Focus Mastery upgrade
        focus_level = self.state.game.save_data['upgrades'].get('focus_mastery', 0)
        self.FOCUS_METER_MAX = 100 + focus_level * 15
        self.FOCUS_RECHARGE_RATE = 0.4 + focus_level * 0.05

        self.focus_meter = self.FOCUS_METER_MAX
        self.is_charging_dash = False
        self.FOCUS_DASH_COST = 50
        self.wall_contact_timer = 0
        self.is_wall_sliding = False

    def attempt_jump(self):
        ghost_img = self.img.copy()
        ghost_img.set_alpha(120)
        self.state.ghosts.append([ghost_img, self.pos.copy(), 15, self.flip[0]])

        jump_velocity = -5
        if self.is_wall_sliding:
            jump_velocity = -6.5
            self.velocity[0] = 3.5 if self.flip[0] == False else -3.5
            for i in range(20):
                angle = random.uniform(math.pi * 0.75, math.pi * 1.25)
                if self.flip[0]: angle = random.uniform(-math.pi * 0.25, math.pi * 0.25)
                speed = random.uniform(1.5, 3.5)
                self.state.sparks.append([self.center.copy(), [math.cos(angle) * speed, math.sin(angle) * speed], random.uniform(3, 6), 0.1, (251, 245, 239), True, 0.05])

        elif 'acrobat' in self.state.active_perks and self.wall_contact_timer > 0:
            jump_velocity = -6.5
            self.wall_contact_timer = 0

        if self.jumps > 0 or self.coyote_timer > 0:
            if self.jumps == self.jumps_max or self.coyote_timer > 0:
                self.velocity[1] = jump_velocity
            else:
                self.velocity[1] = -4 
                for i in range(24):
                    physics = random.choice([False, False, True])
                    direction = 1 if i % 2 else -1
                    self.state.sparks.append([[self.center[0] + random.uniform(-7, 7), self.center[1]], [direction * (random.uniform(0.05, 0.1)) + (random.uniform(-2, 2)) * physics, random.uniform(0.05, 0.1) + random.uniform(0, 2) * physics], random.uniform(3, 6), 0.04 - 0.02 * physics, (6, 4, 1), physics, 0.05 * physics])

            if self.coyote_timer <= 0: self.jumps -= 1
            self.coyote_timer = 0
            self.jumping = True
            self.jump_rot = 0

    def update(self, tiles, time_scale=1.0):
        super().update(1 / 60, time_scale)
        self.air_time += 1
        if self.coyote_timer > 0: self.coyote_timer -= 1
        if self.jump_buffer_timer > 0: self.jump_buffer_timer -= 1
        if self.dash_timer > 0: self.dash_timer -= 1 * time_scale

        if not self.is_charging_dash:
            self.focus_meter = min(self.FOCUS_METER_MAX, self.focus_meter + self.FOCUS_RECHARGE_RATE * time_scale)

        if self.dash_timer > 0:
            direction = 1 if self.flip[0] else -1
            self.velocity[0] = direction * self.DASH_SPEED
            self.state.sparks.append([[self.center[0] - direction * 6, self.center[1] + random.uniform(-3, 3)], [-direction * random.uniform(1, 2), random.uniform(-0.5, 0.5)], random.uniform(2, 5), 0.15, (200, 220, 255), False, 0])
        else: 
            target_vel_x = self.speed if self.right else -self.speed if self.left else 0
            self.velocity[0] += (target_vel_x - self.velocity[0]) * 0.3
            if abs(self.velocity[0]) < 0.1: self.velocity[0] = 0

        self.is_wall_sliding = False
        if self.dash_timer > 0:
            self.velocity[1] = 0
        else:
            if self.air_time > 2 and (self.collisions['left'] or self.collisions['right']):
                if (self.left and self.collisions['left']) or (self.right and self.collisions['right']):
                    self.is_wall_sliding = True
                    self.velocity[1] = min(self.velocity[1], 1.2)
                    if self.state.master_clock % 4 == 0:
                        direction = -1 if self.collisions['left'] else 1
                        self.state.sparks.append([[self.center[0] + direction * 4, self.center[1]], [direction * 0.5, random.uniform(-0.2, 0.2)], random.uniform(1, 3), 0.1, (180, 180, 180), False, 0])
            
            if not self.is_wall_sliding:
                gravity = 0.24 if 'feather_fall' in self.state.active_perks else 0.3
                self.velocity[1] = min(self.velocity[1] + gravity, 4)

        if not self.state.dead and self.dash_timer <= 0:
            if self.velocity[0] > 0.1: self.flip[0] = True
            if self.velocity[0] < -0.1: self.flip[0] = False

        if self.jumping:
            self.jump_rot += 16 * time_scale
            if self.jump_rot >= 360: self.jump_rot = 0; self.jumping = False
            self.rotation = -self.jump_rot if self.flip[0] else self.jump_rot
            self.scale[1] = 0.7
        else: self.scale[1] = 1

        if self.is_charging_dash: self.set_action('idle')
        elif self.dash_timer > 0: self.set_action('jump')
        elif self.is_wall_sliding: self.set_action('jump')
        elif self.air_time > 3: self.set_action('jump')
        elif abs(self.velocity[0]) > 0.1: self.set_action('run')
        else: self.set_action('idle')

        was_on_ground = self.air_time <= 1
        was_in_air_for_long = self.air_time > 5 
        
        self.collisions = self.move(self.velocity, tiles, time_scale)
        if self.collisions['left'] or self.collisions['right']: self.wall_contact_timer = 15
        if self.wall_contact_timer > 0: self.wall_contact_timer -= 1

        if self.collisions['bottom']:
            self.velocity[1] = 0
            if was_in_air_for_long:
                self.state.game.sounds['land'].play()
                for i in range(10):
                    angle = random.uniform(math.pi * 0.9, math.pi * 2.1)
                    speed = random.uniform(0.5, 1.5)
                    self.state.sparks.append([list(self.rect.midbottom), [math.cos(angle) * speed, -math.sin(angle) * speed], random.uniform(2, 4), 0.1, (180, 180, 190), True, 0.02])

            self.air_time = 0
            self.jumps = self.jumps_max
            self.jumping = False
            self.rotation = 0
            if self.jump_buffer_timer > 0:
                self.jump_buffer_timer = 0
                self.state.game.sounds['jump'].play()
                self.attempt_jump()
        elif was_on_ground: self.coyote_timer = 6
        return self.collisions