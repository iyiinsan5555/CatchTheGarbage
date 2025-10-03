# Imports
import math, random, threading, time, pygame, sys, os

# Player Settings
player_x, player_y = 275, 450
player_width, player_height = 100, 100
player_replacement = 5

# Pygame Setup
pygame.display.set_caption("Catch The Garbage")


# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((650, 550))
clock = pygame.time.Clock()

# Images

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

pygame.display.set_icon(pygame.image.load(resource_path("Images/trash-can.png")))
player_image = pygame.transform.scale(pygame.image.load(resource_path("Images/recycle-bin.png")), (player_width, player_height))
apple_image = pygame.transform.scale(pygame.image.load(resource_path("Images/apple.png")),(50,50))
banana_image = pygame.transform.scale(pygame.image.load(resource_path("Images/banana.png")), (50,50))
bottle_image = pygame.transform.scale(pygame.image.load(resource_path("Images/garbage-bag.png")), (50,50))
garbage_bag_image = pygame.transform.scale(pygame.image.load(resource_path("Images/garbage-bag.png")), (50,50))

# Lists
garbage_rect_list = []
garbage_image_list = [apple_image, banana_image, bottle_image, garbage_bag_image]

# Game Setup
gravity = 20
points = 0
collect_distance = 20

# Classes
class Player(pygame.Rect):
    def __init__(self):
        pygame.Rect.__init__(self, player_x, player_y, player_width, player_height)
        self.image = player_image

class Garbage(pygame.Rect):
    def __init__(self, x, y, width, height):
        random_x = random.randint(20,530)
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
        grayscale_img = pygame.transform.grayscale(self.selected_image)
        self.selected_image = grayscale_img


# Variables
player = Player()
running = True
text = None
text_rect = None
font = None
enable_ai = False
ai_replacement = 5

# Functions
def check_length_between_two_points(a, b, x, y):
    return round(math.sqrt((x-a)**2 + (y-b)**2))


def check_collision_with_garbage():
    for garbage in garbage_rect_list:
        if player.colliderect(garbage):
            #calculate positions and if valid count as collected garbage
            garbage_center_x = garbage.x + (garbage.width // 2)
            garbage_center_y = garbage.y + (garbage.height // 2)

            trash_bin_collect_point_x = player.x + (player.width // 2)
            trash_bin_collect_point_y = player.y + (player.height // 3)

            length = check_length_between_two_points(garbage_center_x, garbage_center_y, trash_bin_collect_point_x, trash_bin_collect_point_y)
            #print(length)
            if length < collect_distance: #if closer than 20 pixels that collect
                garbage.collected()


def handle_garbages():
    global running
    i = 0
    for garbage in garbage_rect_list:
        if garbage.lock:
            i += 1

    if i > 20:
        print("So much garbage on ground!")
        running = False
        pygame.quit()  # Later go to main menu
        sys.exit(0)


def apply_gravity(list_of_rects, dt):
    for rect in list_of_rects:
        if rect.lock:
            continue
        else:
            rect.vy += gravity * dt
            rect._y += rect.vy * dt
            rect.y = int(rect._y)

            if rect.bottom > screen.get_height():
                rect.bottom = screen.get_height()
                rect._y = rect.y
                rect.vy = 0.0
                rect.on_ground()


def creating_garbage_loop():
    global running
    i = 8  # calculation for good wait time normally 8
    x = 2
    while running:
        log_value = math.log2(x)
        wait_time = i / log_value

        # creating garbage
        garbage_rect = Garbage(50, -50, 50, 50)
        garbage_rect_list.append(garbage_rect)

        time.sleep(wait_time)
        print(f"Wait time: {wait_time}")
        x += 0.25


def handle_events(pygame_events):
    global running
    for event in pygame_events:
        if event.type == pygame.QUIT:
            running = False
            pygame.quit()
            sys.exit(0)


def handle_player_movement(pressed_keys):  # I know it's bad but I am too lazy to rewrite it.
    if not enable_ai:
        if (pressed_keys[pygame.K_LEFT] or pressed_keys[pygame.K_a]) and player.x - player_replacement >= 0:  # collusion
            player.x -= player_replacement
        elif (pressed_keys[pygame.K_RIGHT] or pressed_keys[pygame.K_d]) and player.x + player_replacement <= (screen.get_width() - player_width): # collusion
            player.x += player_replacement


def create_text_label():
    global text, text_rect, font
    font = pygame.font.Font(None, 36)
    text = font.render(f"Points: {points}", True, (255,255,255), (0,0,0))
    text_rect = text.get_rect()
    text_rect.topleft = (5,5) #setting position


def draw():
    global text, text_rect, font
    screen.fill("white")
    text = font.render(f"Points: {points}", True, (0,0,0))
    screen.blit(text, text_rect)
    screen.blit(player.image, player)

    for rect in garbage_rect_list:
        screen.blit(rect.selected_image, rect)


def ai_for_game():
# detect the closest garbage
# move player to it's above

    if enable_ai:

        closest_garbage = None
        for garbage in garbage_rect_list:  # Finding the closest garbage to ground.
            if not closest_garbage and garbage.lock == False:
                closest_garbage = garbage
            elif closest_garbage and not garbage.lock:
                if garbage.y > closest_garbage.y:
                    closest_garbage = garbage

        if closest_garbage:  # Move player to target
            target_x = closest_garbage.x - closest_garbage.width // 2

            if target_x < player.x and abs(target_x - player.x) > 10: # prevent moving so fast to right and left
                player.x -= ai_replacement
            elif target_x > player.x:
                player.x += ai_replacement






# Threads
creating_garbage_thread = threading.Thread(target=creating_garbage_loop)
creating_garbage_thread.start()

# Init Some Functions
create_text_label()

# While Loop
while running:
    handle_events(pygame.event.get())
    handle_player_movement(pygame.key.get_pressed())
    check_collision_with_garbage()
    handle_garbages()
    ai_for_game()

    draw()

    # flip() the display to put your work on screen
    pygame.display.flip()

    # for independent physics.
    dt = clock.tick(60) / 1000  # dt is delta time in seconds since last frame, used for framerate- also limits fps to 60

    apply_gravity(garbage_rect_list, dt)


pygame.quit()
sys.exit(0)