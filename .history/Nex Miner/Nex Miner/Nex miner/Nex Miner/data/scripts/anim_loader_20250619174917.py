import os, json
import pygame

COLORKEY = (0, 0, 0)

def load_img(path, colorkey):
    img = pygame.image.load(path).convert()
    img.set_colorkey(colorkey)
    return img

class AnimationData:
    def __init__(self, path, colorkey=None):
        self.id = os.path.basename(path) 
        self.image_list = []

        for img_filename in os.listdir(path):
            if img_filename.endswith('.png'):
                full_img_path = os.path.join(path, img_filename)
                # --- FIX: More robust frame number parsing ---
                try:
                    # Tries to get number from "frame_1.png", "1.png", etc.
                    frame_number = int(os.path.splitext(os.path.basename(img_filename))[0].split('_')[-1])
                    self.image_list.append([frame_number, load_img(full_img_path, colorkey)])
                except (ValueError, IndexError):
                    print(f"Warning: Could not parse frame number from '{img_filename}' in '{path}'. Skipping file.")

        config_path = os.path.join(path, 'config.json')
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            # --- FIX: Create a default config if it doesn't exist ---
            self.config = {
                'frames': [5 for _ in range(len(self.image_list))], 'loop': True,
                'speed': 1.0, 'centered': False, 'paused': False,
                'outline': None, 'offset': [0, 0],
            }
            with open(config_path, 'w') as f:
                json.dump(self.config, f)
        
        self.image_list.sort()
        self.image_list = [v[1] for v in self.image_list]
        self.frame_surfs = []
        total = 0
        for i, frame in enumerate(self.config['frames']):
            total += frame
            if i < len(self.image_list): 
                self.frame_surfs.append([total, self.image_list[i]])

    @property
    def duration(self):
        return sum(self.config['frames'])

class Animation:
    def __init__(self, animation_data):
        self.data = animation_data
        self.frame = 0
        self.paused = self.data.config['paused']
        self.img = None
        self.calc_img()
        self.rotation = 0
        self.just_looped = False

    def render(self, surf, pos, offset=(0, 0)):
        if not self.img: return
        img = self.img
        if self.rotation:
            img = pygame.transform.rotate(self.img, self.rotation)
        render_pos = (pos[0] - offset[0], pos[1] - offset[1])
        if self.data.config.get('centered'):
            surf.blit(img, (render_pos[0] - img.get_width() // 2, render_pos[1] - img.get_height() // 2))
        else:
            surf.blit(img, render_pos)

    def calc_img(self):
        if not self.data.frame_surfs:
            self.img = pygame.Surface((1,1), pygame.SRCALPHA)
            return
        for frame_data in self.data.frame_surfs:
            if frame_data[0] > self.frame:
                self.img = frame_data[1]
                return
        self.img = self.data.frame_surfs[-1][1]

    def play(self, dt=1/60, time_scale=1.0):
        self.just_looped = False
        if not self.paused:
            self.frame += dt * 60 * self.data.config.get('speed', 1.0) * time_scale
        
        if self.data.config.get('loop', False):
            # --- FIX: Prevent infinite loop on 0-duration animations ---
            if self.data.duration > 0:
                while self.frame >= self.data.duration:
                    self.frame -= self.data.duration
                    self.just_looped = True
            else:
                self.frame = 0 # If duration is 0, just reset
        else:
            self.frame = min(self.frame, self.data.duration - 0.01)
        self.calc_img()
        
    def rewind(self):
        self.frame = 0; self.calc_img()

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
            full_path = os.path.join(anim_base_path, anim_dir_name)
            if os.path.isdir(full_path):
                self.animations[anim_dir_name] = AnimationData(full_path, COLORKEY)

    def new(self, anim_id):
        if anim_id in self.animations:
            return Animation(self.animations[anim_id])
        else:
            print(f"Warning: Animation '{anim_id}' not found.")
            # --- FIX: Prevent crash on missing animation ---
            # Fallback to player_idle or first available animation
            fallback_key = 'player_idle' if 'player_idle' in self.animations else (list(self.animations.keys())[0] if self.animations else None)
            if fallback_key:
                return Animation(self.animations[fallback_key])
            else:
                return None # Should not happen if assets are present