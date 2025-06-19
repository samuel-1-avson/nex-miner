
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
        self.assets = assets; self.pos = list(pos).copy(); self.size = list(size).copy()
        self.type = type; self.flip = [False, False]; self.rotation = 0; self.centered = False
        self.opacity = 255; self.scale = [1, 1]; self.active_animation = None; self.height = 0

        if self.type + '_idle' in self.assets.animations: self.set_action('idle')
        
        # --- FIX: Prevent crash on entities with no animation (e.g., items) ---
        if not self.active_animation and not hasattr(self, 'current_image'):
            self.set_image(pygame.Surface(self.size, pygame.SRCALPHA))

    @property
    def img(self):
        if not self.active_animation:
            img = self.current_image
        else:
            self.set_image(self.active_animation.img)
            img = self.current_image
            
        if self.scale != [1, 1]: img = pygame.transform.scale(img, (int(self.scale[0] * self.image_base_dimensions[0]), int(self.scale[1] * self.image_base_dimensions[1])))
        if any(self.flip): img = pygame.transform.flip(img, self.flip[0], self.flip[1])
        if self.rotation: img = pygame.transform.rotate(img, self.rotation)
        if self.opacity != 255: img = img.copy(); img.set_alpha(self.opacity)
        return img

    @property
    def rect(self):
        if not self.centered: return pygame.Rect(self.pos[0], self.pos[1], self.size[0], self.size[1])
        else: return pygame.Rect(self.pos[0] - self.size[0] // 2, self.pos[1] - self.size[1] // 2, self.size[0], self.size[1])

    @property
    def center(self):
        return [self.pos[0] + self.size[0] // 2, self.pos[1] + self.size[1] // 2] if not self.centered else self.pos.copy()

    def set_action(self, action_id, force=False):
        animation_name = self.type + '_' + action_id
        
        # --- FIX: Animation Fallback for Characters ---
        is_valid_specific_anim = animation_name in self.assets.animations and self.assets.animations[animation_name].frame_surfs
        is_player_char = hasattr(self, 'state') and hasattr(self.state, 'game') and self.type in self.state.game.characters

        if not is_valid_specific_anim and is_player_char:
            fallback_animation_name = 'player' + '_' + action_id
            if fallback_animation_name in self.assets.animations and self.assets.animations[fallback_animation_name].frame_surfs:
                 animation_name = fallback_animation_name

        if force or not self.active_animation or self.active_animation.data.id != animation_name:
            if new_anim := self.assets.new(animation_name): self.active_animation = new_anim

    def set_image(self, surf):
        if surf: self.current_image, self.image_base_dimensions = surf.copy(), list(surf.get_size())

    def move(self, motion, tiles, time_scale=1.0):
        self.pos[0] += motion[0] * time_scale; temp_rect = self.rect
        directions = {'top':False, 'left':False, 'right':False, 'bottom':False}
        for tile in collision_list(temp_rect, tiles):
            if motion[0] * time_scale > 0: temp_rect.right = tile.left; directions['right'] = True
            if motion[0] * time_scale < 0: temp_rect.left = tile.right; directions['left'] = True
            self.pos[0] = temp_rect.x;
            if self.centered: self.pos[0] += self.size[0] // 2
        
        self.pos[1] += motion[1] * time_scale; temp_rect = self.rect
        for tile in collision_list(temp_rect, tiles):
            if motion[1] * time_scale > 0: temp_rect.bottom = tile.top; directions['bottom'] = True
            if motion[1] * time_scale < 0: temp_rect.top = tile.bottom; directions['top'] = True
            self.pos[1] = temp_rect.y
            if self.centered: self.pos[1] += self.size[1] // 2
        return directions

    def render(self, surf, offset=(0, 0)):
        img_to_render = self.img
        if not img_to_render: return

        final_offset = list(offset)
        if self.active_animation:
            final_offset[0] += self.active_animation.data.config['offset'][0]
            final_offset[1] += self.active_animation.data.config['offset'][1]
        
        render_pos = (self.pos[0] - final_offset[0], self.pos[1] - final_offset[1] - self.height)
        if self.centered: render_pos = (render_pos[0] - img_to_render.get_width()//2, render_pos[1] - img_to_render.get_height()//2)
        surf.blit(img_to_render, render_pos)

    def update(self, dt, time_scale=1.0):
        if self.active_animation: self.active_animation.play(dt, time_scale)