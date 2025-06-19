#!/usr/bin/python3.4
import pygame, sys
from .core_funcs import *
from .clip import clip

def load_font_img(path, font_color):
    fg_color = (255, 0, 0)
    bg_color = (0, 0, 0)
    font_img = pygame.image.load(path).convert()
    font_img = swap_color(font_img, fg_color, font_color)
    last_x = 0
    letters = []
    letter_spacing = []
    for x in range(font_img.get_width()):
        if font_img.get_at((x, 0))[0] == 127:
            letters.append(clip(font_img, last_x, 0, x - last_x, font_img.get_height()))
            letter_spacing.append(x - last_x)
            last_x = x + 1
        x += 1
    for letter in letters:
        letter.set_colorkey(bg_color)
    return letters, letter_spacing, font_img.get_height()

class Font():
    def __init__(self, path, color):
        self.color = color
        self.letters, self.letter_spacing, self.line_height = load_font_img(path, color)
        # --- FIX: Added '%' for the settings menu volume display.
        self.font_order = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z','a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','.','-',',',':','+','\'','!','?','0','1','2','3','4','5','6','7','8','9','(',')','/','_','=','\\','[',']','*','"','<','>','%',';'] # Added '%'
        self.space_width = self.letter_spacing[0]
        self.base_spacing = 1
        self.line_spacing = 2

    def width(self, text, scale=1):
        text_width = 0
        for char in text:
            if char == ' ':
                text_width += (self.space_width + self.base_spacing) * scale
            else:
                # Add a check to prevent crashes on unsupported characters
                if char in self.font_order:
                    text_width += (self.letter_spacing[self.font_order.index(char)] + self.base_spacing) * scale
        return text_width

    def render(self, text, surf, loc, line_width=0, scale=1):
        x_offset = 0
        y_offset = 0
        
        # Line wrapping logic
        if line_width != 0:
            spaces = []
            x = 0
            for i, char in enumerate(text):
                if char == ' ':
                    spaces.append((x, i))
                    x += (self.space_width + self.base_spacing) * scale
                elif char in self.font_order: # Check if char is supported
                    x += (self.letter_spacing[self.font_order.index(char)] + self.base_spacing) * scale
            line_offset = 0
            for i, space in enumerate(spaces):
                if (space[0] - line_offset) > line_width:
                    line_offset += spaces[i - 1][0] - line_offset
                    if i != 0:
                        text = text[:spaces[i - 1][1]] + '\n' + text[spaces[i - 1][1] + 1:]
                        
        for char in text:
            # Add a check to only process characters that exist in the font
            if char in self.font_order:
                letter_img = self.letters[self.font_order.index(char)]
                letter_spacing = self.letter_spacing[self.font_order.index(char)]
                
                if scale != 1:
                    new_size = (int(letter_img.get_width() * scale), int(letter_img.get_height() * scale))
                    letter_img = pygame.transform.scale(letter_img, new_size)

                surf.blit(letter_img, (loc[0] + x_offset, loc[1] + y_offset))
                x_offset += (letter_spacing + self.base_spacing) * scale
            elif char == ' ':
                x_offset += (self.space_width + self.base_spacing) * scale
            elif char == '\n':
                y_offset += (self.line_spacing + self.line_height) * scale
                x_offset = 0
            # If the character is not supported, it will now be skipped silently.