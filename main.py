import math
import random
import threading
import time

# Pygame project
# In this game you will control a trash bin and catch garbage via it

# After making game add AI with machine learning

import pygame
import os


player_x = 275
player_y = 450
player_width = 100
player_height = 100
player_replacement = 5

#pygame setup
pygame.init()
screen = pygame.display.set_mode((650,550))
clock = pygame.time.Clock()
running = True
pygame.display.set_caption("Catch The Garbage")
pygame.display.set_icon(pygame.image.load("Images/trash-can.png"))
player_image = pygame.image.load(os.path.join("Images", "recycle-bin.png"))
player_image = pygame.transform.scale(player_image, (player_width, player_height))
apple_image = pygame.transform.scale(pygame.image.load("Images/apple.png"),(50,50))
banana_image = pygame.transform.scale(pygame.image.load("Images/banana.png"), (50,50))
bottle_image = pygame.transform.scale(pygame.image.load("Images/garbage-bag.png"), (50,50))
garbage_bag_image = pygame.transform.scale(pygame.image.load("Images/garbage-bag.png"), (50,50))

garbage_image_list = [apple_image, banana_image, bottle_image, garbage_bag_image]

garbage_rect_list = []

gravity = 20
points = 0




class Player(pygame.Rect):
    def __init__(self):
        pygame.Rect.__init__(self, player_x, player_y, player_width, player_height)
        self.image = player_image

player = Player()

font = pygame.font.Font(None, 36)
text = font.render(f"Points: {points}", True, (0,0,0))
text_rect = text.get_rect()
text_rect.topleft = (5,5)


def draw():
    global text
    screen.fill("white")
    #draw player
    screen.blit(player.image, player)
    for rect in garbage_rect_list:
        screen.blit(rect.selected_image, rect)
    text = font.render(f"Points: {points}", True, (0,0,0))
    screen.blit(text, text_rect)

def check_length_between_two_points(a, b, x, y):
    return round(math.sqrt((x-a)**2 + (y-b)**2))

def check_collision():
    for garbage in garbage_rect_list:
        if player.colliderect(garbage):
            #calculate positions and if valid count as collected garbage
            garbage_center_x = garbage.x + (garbage.width // 2)
            garbage_center_y = garbage.y + (garbage.height // 2)

            trash_bin_collect_point_x = player.x + (player.width // 2)
            trash_bin_collect_point_y = player.y + (player.height // 3)

            length = check_length_between_two_points(garbage_center_x, garbage_center_y, trash_bin_collect_point_x, trash_bin_collect_point_y)
            #print(length)
            if length < 20: #if closer than 20 pixels that collect
                garbage.collected()



def get_garbages_on_ground():
    i = 0
    for garbage in garbage_rect_list:
        if garbage.lock:
            i += 1

    if i > 20:
        print("so much garbage on ground")
        pygame.quit()
        quit()
    return i


def apply_gravity(list_of_items):
    for rect in list_of_items:
        if rect.lock:
            continue
        rect.vy += gravity * dt
        rect._y += rect.vy * dt
        rect.y = int(rect._y)

        if rect.bottom > screen.get_height():
            rect.bottom = screen.get_height()
            rect._y = rect.y
            rect.vy = 0.0
            rect.on_ground()


class Garbage(pygame.Rect):

    def __init__(self, x, y, width, height):
        random_x = random.randint(20,480)
        pygame.Rect.__init__(self, random_x, y, width, height)

        self.selected_image = random.choice(garbage_image_list)

        self.vy = 0.0
        self._y = float(self.y)

        self.lock = False

    def collected(self):
        global points
        garbage_rect_list.remove(self)
        points += 1

    def on_ground(self):
        self.lock = True
        grayscle_img = pygame.transform.grayscale(self.selected_image)
        self.selected_image = grayscle_img




def create_garbage():
    i = 8 #normally it's 8
    x = 2
    while True:
        log_value = math.log2(x)
        wait_time = i / log_value

        #creating garbage
        garbage_rect = Garbage(50, -50, 50, 50)
        garbage_rect_list.append(garbage_rect)

        time.sleep(wait_time)
        print(wait_time)
        x += 0.25

creating_garbage_thread = threading.Thread(target=create_garbage)
creating_garbage_thread.start()

while running:

    #handle events
    # pygame.QUIT event means the user clicked X to close your window
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False


    #handling player movement
    keys = pygame.key.get_pressed()
    if (keys[pygame.K_LEFT] or keys[pygame.K_a]) and player.x - player_replacement >= 0:  # collusion
        player.x -= player_replacement
    elif (keys[pygame.K_RIGHT] or keys[pygame.K_d]) and player.x + player_replacement <= (screen.get_width() - player_width): # collusion
        player.x += player_replacement


    #rendering game here!!!
    #make a trash bin image for character. It will only able to move at the bottom of screen, right to left.
    # and make garbage that will spawn above screen randomly. and fall to the ground.
    draw()
    check_collision()
    get_garbages_on_ground()



    # flip() the display to put your work on screen
    pygame.display.flip()

    # independent physics.
    dt = clock.tick(60) / 1000 # dt is delta time in seconds since last frame, used for framerate- also limits fps to 60

    apply_gravity(garbage_rect_list)




#when loops ends --> quit
pygame.quit()