
# Cavyn Source/data/scripts/anim_loader.py

import os, json
import pygame

COLORKEY = (0, 0, 0)

def load_img(path, colorkey):
    img = pygame.image.load(path).convert()
    img.set_colorkey(colorkey)
    return img

class AnimationData:
    def __init__(self, path, colorkey=None):
        self.id = os.path.basename(path) # More robust way to get the final part of a path
        self.image_list = []

        # Iterate through files in the animation directory (path is now absolute)
        for img_filename in os.listdir(path):
            if img_filename.endswith('.png'):
                full_img_path = os.path.join(path, img_filename)
                # --- FIX: More robust frame number parsing ---
                # Avoids errors if filenames are like "frame_1.png" or just "1.png"
                try:
                    frame_number = int(os.path.splitext(os.path.basename(img_filename))[0].split('_')[-1])
                    self.image_list.append([frame_number, load_img(full_img_path, colorkey)])
                except (ValueError, IndexError):
                    print(f"Warning: Could not parse frame number from '{img_filename}' in '{path}'. Skipping file.")


        # Construct the full, absolute path to the config file
        config_path = os.path.join(path, 'config.json')
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            # Create a default config if not found
            self.config = {
                'frames': [5 for _ in range(len(self.image_list))],
                'loop': True,
                'speed': 1.0,
                'centered': False,
                'paused': False,
                'outline': None,
                'offset': [0, 0],
            }
            # Write the default config back to the correct absolute path
            with open(config_path, 'w') as f:
                json.dump(self.config, f)
        
        # Sort and process the loaded images
        self.image_list.sort()
        self.image_list = [v[1] for v in self.image_list]
        self.frame_surfs = []
        total = 0
        for i, frame in enumerate(self.config['frames']):
            total += frame
            if i < len(self.image_list): # Safety check
                self.frame_surfs.append([total, self.image_list[i]])

    @property
    def duration(self):
        return sum(self.config['frames'])

class Animation:
    def __init__(self, animation_data):
        self.data = animation_data
        self.frame = 0
        self.paused = self.data.config['paused']
        self.img = None # Initialize img attribute
        self.calc_img()
        self.rotation = 0
        self.just_looped = False

    def render(self, surf, pos, offset=(0, 0)):
        if not self.img: return # Safety check
        
        img = self.img
        rot_offset = [0, 0]
        if self.rotation:
            orig_size = self.img.get_size()
            img = pygame.transform.rotate(self.img, self.rotation)
            if not self.data.config['centered']:
                rot_offset = [(img.get_width() - orig_size[0]) // 2, (img.get_height() - orig_size[1]) // 2]
        
        if self.data.config.get('outline'): # Use .get for safety
             # Assuming you have an outline function elsewhere
            pass
        
        render_pos_x = pos[0] - offset[0]
        render_pos_y = pos[1] - offset[1]
        
        if self.data.config.get('centered'):
            surf.blit(img, (render_pos_x - img.get_width() // 2, render_pos_y - img.get_height() // 2))
        else:
            surf.blit(img, (render_pos_x - rot_offset[0], render_pos_y - rot_offset[1]))

    def calc_img(self):
        if not self.data.frame_surfs:
            self.img = pygame.Surface((1,1), pygame.SRCALPHA) # Fallback if no frames loaded
            return
            
        for frame_data in self.data.frame_surfs:
            if frame_data[0] > self.frame:
                self.img = frame_data[1]
                return
        # If frame is beyond the last frame's duration, use the last image
        self.img = self.data.frame_surfs[-1][1]

    def play(self, dt=1/60, time_scale=1.0): # Using dt is better than assuming 60fps
        self.just_looped = False
        if not self.paused:
            # Animation speed calculation should be frame-rate independent
            self.frame += dt * 60 * self.data.config.get('speed', 1.0) * time_scale
        
        if self.data.config.get('loop', False):
            # MODIFIED: Prevent infinite loop on animations with 0 duration.
            if self.data.duration > 0:
                while self.frame >= self.data.duration:
                    self.frame -= self.data.duration
                    self.just_looped = True
            else:
                self.frame = 0 # If duration is 0, just reset the frame
        else:
            # Clamp frame to max duration if not looping
            self.frame = min(self.frame, self.data.duration - 0.01)

        self.calc_img()

    def rewind(self):
        self.frame = 0
        self.calc_img() # Recalculate image after rewind

    def set_speed(self, speed):
        self.data.config['speed'] = speed

    def set_frame_index(self, index):
        # Set frame to the start time of the chosen index
        if 0 <= index < len(self.data.frame_surfs):
            if index == 0:
                self.frame = 0
            else:
                 # Start time of frame `i` is the end time of frame `i-1`
                self.frame = self.data.frame_surfs[index - 1][0]
            self.calc_img()

    def pause(self):
        self.paused = True

    def unpause(self):
        self.paused = False

class AnimationManager:
    # Now accepts the base path to the animations directory during initialization
    def __init__(self, anim_base_path):
        self.animations = {}
        if not os.path.exists(anim_base_path):
            print(f"Animation directory not found at {anim_base_path}")
            return
        
        for anim_dir_name in os.listdir(anim_base_path):
            # Construct the full, absolute path for each animation
            full_path = os.path.join(anim_base_path, anim_dir_name)
            if os.path.isdir(full_path):
                self.animations[anim_dir_name] = AnimationData(full_path, COLORKEY)

    def new(self, anim_id):
        if anim_id in self.animations:
            return Animation(self.animations[anim_id])
        else:
            print(f"Warning: Animation '{anim_id}' not found.")
            # Create an empty, dummy AnimationData if the path does not exist
            # This is safer and prevents crashes down the line
            dummy_path = self.animations.get('player_idle').id if 'player_idle' in self.animations else list(self.animations.keys())[0] if self.animations else '.'
            if dummy_path != '.':
                return Animation(self.animations[dummy_path])
            else:
                return None
