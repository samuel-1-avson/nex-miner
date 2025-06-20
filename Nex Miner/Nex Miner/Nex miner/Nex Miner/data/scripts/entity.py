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

        # Try to set an animation based on the entity's type
        if self.type + '_idle' in self.assets.animations:
            self.set_action('idle')
            
        # --- FIX: Prevent crash on entities with no animation ---
        # If no animation was set (e.g., for 'shield' or 'hourglass' items that have
        # UI icons but no world-sprite animations), we MUST initialize a fallback image.
        # This prevents a crash when render() tries to access self.current_image.
        if not self.active_animation and not hasattr(self, 'current_image'):
            # We call set_image() to properly initialize both self.current_image and
            # self.image_base_dimensions with a placeholder. A transparent surface is best.
            self.set_image(pygame.Surface(self.size, pygame.SRCALPHA))


    @property
    def img(self):
        # This branch is now safe because self.current_image is guaranteed to exist.
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
            img = img.copy() # Make a copy to avoid modifying original
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
        animation_name = self.type + '_' + action_id
        
        # --- IMPROVEMENT: Animation Fallback for Characters ---
        is_valid_specific_anim = False
        if animation_name in self.assets.animations:
            if self.assets.animations[animation_name].frame_surfs:
                is_valid_specific_anim = True
        
        # --- FIX: Make fallback logic robust for all characters ---
        # This checks if the entity is a player-like character by checking if its type exists in the game's character list.
        # This is safer than a hardcoded list and works for AI-generated characters.
        if not is_valid_specific_anim and hasattr(self, 'state') and hasattr(self.state, 'game') and self.type in self.state.game.characters:
            fallback_animation_name = 'player' + '_' + action_id
            if fallback_animation_name in self.assets.animations and self.assets.animations[fallback_animation_name].frame_surfs:
                 animation_name = fallback_animation_name

        if force or (not self.active_animation) or (self.active_animation.data.id != animation_name):
            new_anim = self.assets.new(animation_name)
            if new_anim: # Check if animation loaded successfully
                self.active_animation = new_anim


    def set_image(self, surf):
        if surf: # Prevent trying to copy a None surf
            self.current_image = surf.copy()
            self.image_base_dimensions = list(surf.get_size())

    def set_scale(self, new_scale, fit_hitbox=True):
        try:
            self.scale = new_scale.copy()
        except AttributeError:
            self.scale = [new_scale, new_scale]
        if fit_hitbox and hasattr(self, 'image_base_dimensions'):
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
        img_to_render = self.img # Get the potentially modified image from the property
        if not img_to_render: return # Final safety check

        final_offset = list(offset)
        if self.active_animation:
            final_offset[0] += self.active_animation.data.config['offset'][0]
            final_offset[1] += self.active_animation.data.config['offset'][1]
        
        render_pos = (
            (self.pos[0] - final_offset[0]) // 1,
            (self.pos[1] - final_offset[1] - self.height) // 1
        )
        
        if self.centered:
             render_pos = (render_pos[0] - img_to_render.get_width()//2, render_pos[1] - img_to_render.get_height()//2)
        
        # This is where an outline function would be called, if it existed
        # if self.active_animation and self.active_animation.data.config['outline']:
        #    outline(...)
            
        surf.blit(img_to_render, render_pos)


    def update(self, dt, time_scale=1.0):
        if self.active_animation:
            self.active_animation.play(dt, time_scale)