
import pygame, sys
from .core_funcs import *
from .clip import clip

def load_font_img(path, font_color):
    font_img = swap_color(pygame.image.load(path).convert(), (255, 0, 0), font_color)
    last_x, letters, letter_spacing = 0, [], []
    for x in range(font_img.get_width()):
        if font_img.get_at((x, 0))[0] == 127:
            letters.append(clip(font_img, last_x, 0, x - last_x, font_img.get_height()))
            letter_spacing.append(x - last_x)
            last_x = x + 1
    for letter in letters: letter.set_colorkey((0,0,0))
    return letters, letter_spacing, font_img.get_height()

class Font():
    def __init__(self, path, color):
        self.color = color
        self.letters, self.letter_spacing, self.line_height = load_font_img(path, color)
        # --- FIX: Reverted font_order to match the font file to prevent crashes on unsupported characters ---
        self.font_order = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z','a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','.','-',',',':','+','\'','!','?','0','1','2','3','4','5','6','7','8','9','(',')','/','_','=','\\','[',']','*','"','<','>']
        self.space_width = self.letter_spacing[0]
        self.base_spacing, self.line_spacing = 1, 2

    def width(self, text, scale=1):
        text_width = 0
        for char in text:
            if char == ' ': text_width += (self.space_width + self.base_spacing) * scale
            elif char in self.font_order: text_width += (self.letter_spacing[self.font_order.index(char)] + self.base_spacing) * scale
        return text_width

    def render(self, text, surf, loc, line_width=0, scale=1):
        x_offset, y_offset = 0, 0
        
        # --- FIX: Improved Line Wrapping Logic ---
        if line_width > 0:
            words = text.split(' ')
            new_text = ""
            current_w = 0
            for word in words:
                word_w = self.width(word)
                if current_w + word_w > line_width:
                    new_text += '\n' + word + ' '
                    current_w = word_w + self.width(' ')
                else:
                    new_text += word + ' '
                    current_w += word_w + self.width(' ')
            text = new_text

        for char in text:
            # --- FIX: Silently skip characters that are not in the font sheet ---
            if char in self.font_order:
                letter_img = self.letters[self.font_order.index(char)]
                if scale != 1: letter_img = pygame.transform.scale(letter_img, (int(letter_img.get_width()*scale), int(letter_img.get_height()*scale)))
                surf.blit(letter_img, (loc[0] + x_offset, loc[1] + y_offset))
                x_offset += (self.letter_spacing[self.font_order.index(char)] + self.base_spacing) * scale
            elif char == ' ': x_offset += (self.space_width + self.base_spacing) * scale
            elif char == '\n': y_offset += (self.line_spacing + self.line_height) * scale; x_offset = 0