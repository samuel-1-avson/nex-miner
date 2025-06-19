import math

import pygame

from .core_funcs import *

def collision_list(obj, obj_list):
    hit_list = []
    for r in obj_list:
        if obj.colliderect(r):
            hit_list.append(r)
    return hit_list

class Entity:
    def __init__(self, assets, pos, size, type):
        self.assets = assets
        self.pos = list(pos).copy()
        self.size = list(size).copy()
        self.type = type
        self.flip = [False, False]
        self.rotation = 0
        self.centered = False
        self.opacity = 255
        self.scale = [1, 1]
        self.active_animation = None
        self.height = 0

        if self.type + '_idle' in self.assets.animations:
            self.set_action('idle')

    @property
    def img(self):
        if not self.active_animation:
            img = self.current_image
        else:
            self.set_image(self.active_animation.img)
            img = self.current_image
        if self.scale != [1, 1]:
            img = pygame.transform.scale(img, (int(self.scale[0] * self.image_base_dimensions[0]), int(self.scale[1] * self.image_base_dimensions[1])))
        if any(self.flip):
            img = pygame.transform.flip(img, self.flip[0], self.flip[1])
        if self.rotation:
            img = pygame.transform.rotate(img, self.rotation)
        if self.opacity != 255:
            img.set_alpha(self.opacity)
        return img

    @property
    def rect(self):
        if not self.centered:
            return pygame.Rect(self.pos[0] // 1, self.pos[1] // 1, self.size[0], self.size[1])
        else:
            return pygame.Rect((self.pos[0] - self.size[0] // 2) // 1, (self.pos[1] - self.size[1] // 2) // 1, self.size[0], self.size[1])

    @property
    def center(self):
        if self.centered:
            return self.pos.copy()
        else:
            return [self.pos[0] + self.size[0] // 2, self.pos[1] + self.size[1] // 2]

    def set_action(self, action_id, force=False):
        # --- MODIFIED to handle dynamic character sprites ---
        animation_name = self.type + '_' + action_id
        
        # Check if a character-specific animation exists (e.g., 'ninja_idle')
        # It's better to check the assets directly instead of just the name.
        if animation_name not in self.assets.animations:
            # If not, fall back to the default 'player' animation (e.g., 'player_idle')
            # The check 'player' in self.type is a bit of a hack, but works for this project structure
            if 'player' in self.type or self.type == 'ninja': # Simple check for player-like entities
                 animation_name = 'player' + '_' + action_id

        # Proceed with the original logic using the determined animation name
        if force:
            self.active_animation = self.assets.new(animation_name)
        elif (not self.active_animation) or (self.active_animation.data.id != animation_name):
            self.active_animation = self.assets.new(animation_name)

    def set_image(self, surf):
        self.current_image = surf.copy()
        self.image_base_dimensions = list(surf.get_size())

    def set_scale(self, new_scale, fit_hitbox=True):
        try:
            self.scale = new_scale.copy()
        except AttributeError:
            self.scale = [new_scale, new_scale]
        if fit_hitbox:
            self.size = [int(self.scale[0] * self.image_base_dimensions[0]), int(self.scale[1] * self.image_base_dimensions[1])]

    def get_angle(self, target):
        if isinstance(target, Entity):
            return math.atan2(target.center[1] - self.center[1], target.center[0] - self.center[0])
        else:
            return math.atan2(target[1] - self.center[1], target[0] - self.center[0])

    def get_render_angle(self, target):
        if isinstance(target, Entity):
            return math.atan2(target.center[1] - self.center[1], target.center[0] - self.center[0] - self.height)
        else:
            return math.atan2(target[1] - self.center[1], target[0] - self.center[0] - self.height)

    def get_distance(self, target):
        try:
            return math.sqrt((target.pos[0] - self.pos[0]) ** 2 + (target.pos[1] - self.pos[1]) ** 2)
        except:
            return math.sqrt((target[0] - self.pos[0]) ** 2 + (target[1] - self.pos[1]) ** 2)

    def in_range(self, target, range):
        return self.get_distance(target) <= range

    def get_visible(self):
        # TODO: implement for this project
        '''render_pos = ((self.pos[0] - offset[0]) // 1, (self.pos[1] - offset[1] - self.height) // 1)
        if not self.centered:
            render_r = pygame.Rect(*render_pos, *self.size)
        else:
            render_pos = [render_pos[0] - self.size[0], render_pos[1] - self.size[1]]
            render_r = pygame.Rect(*render_pos, *self.size)
        return self.game.camera.rect.colliderect(render_r)'''
        return True

    def move(self, motion, tiles, time_scale=1.0):
        self.pos[0] += motion[0] * time_scale
        hit_list = collision_list(self.rect, tiles)
        temp_rect = self.rect
        directions = {k : False for k in ['top', 'left', 'right', 'bottom']}
        for tile in hit_list:
            if motion[0] * time_scale > 0:
                temp_rect.right = tile.left
                self.pos[0] = temp_rect.x
                directions['right'] = True
            if motion[0] * time_scale < 0:
                temp_rect.left = tile.right
                self.pos[0] = temp_rect.x
                directions['left'] = True
            if self.centered:
                self.pos[0] += self.size[0] // 2
        self.pos[1] += motion[1] * time_scale
        hit_list = collision_list(self.rect, tiles)
        temp_rect = self.rect
        for tile in hit_list:
            if motion[1] * time_scale > 0:
                temp_rect.bottom = tile.top
                self.pos[1] = temp_rect.y
                directions['bottom'] = True
            if motion[1] * time_scale < 0:
                temp_rect.top = tile.bottom
                self.pos[1] = temp_rect.y
                directions['top'] = True
            if self.centered:
                self.pos[1] += self.size[1] // 2
        return directions

    def render(self, surf, offset=(0, 0)):
        offset = list(offset)
        if self.active_animation:
            offset[0] += self.active_animation.data.config['offset'][0]
            offset[1] += self.active_animation.data.config['offset'][1]
        if self.centered:
            offset[0] += self.img.get_width() // 2
            offset[1] += self.img.get_height() // 2
        if self.active_animation and self.active_animation.data.config['outline']:
            outline(surf, self.img, ((self.pos[0] - offset[0]) // 1, (self.pos[1] - offset[1] - self.height) // 1), self.active_animation.data.config['outline'])
        surf.blit(self.img, ((self.pos[0] - offset[0]) // 1, (self.pos[1] - offset[1] - self.height) // 1))

    def update(self, dt, time_scale=1.0):
        if self.active_animation:
            self.active_animation.play(dt, time_scale)