import pygame
import numpy as np
import random
import time
import math
import sys

# --- Pygame Setup ---
pygame.init()
pygame.display.set_caption("Trained AI Player (Q-Table Demo)")
screen = pygame.display.set_mode((650, 550))
clock = pygame.time.Clock()

# --- Game Constants ---
SCREEN_WIDTH = 650
SCREEN_HEIGHT = 550
PLAYER_WIDTH = 100
PLAYER_HEIGHT = 100
PLAYER_SPEED = 15  # Matches the trained speed (PLAYER_REPLACEMENT)
GRAVITY = 20
COLLECT_DISTANCE = 20
GARBAGE_ON_GROUND_LIMIT = 20

# --- State Space Constants (MUST MATCH TRAINER) ---
STATE_RELATIVE_X_BINS = 10
STATE_Y_BINS = 3
ACTION_SPACE = 3  # 0: Left, 1: No Move, 2: Right

# --- Load Trained Q-Table ---
try:
    Q_TABLE = np.load('catch_garbage_q_table.npy')
    print("Successfully loaded trained Q-table!")
except FileNotFoundError:
    print("Warning: 'catch_garbage_q_table.npy' not found. AI will use random policy.")
    Q_TABLE = np.zeros((STATE_RELATIVE_X_BINS, STATE_Y_BINS, ACTION_SPACE))
except Exception as e:
    print(f"Error loading Q-table: {e}. AI will use random policy.")
    Q_TABLE = np.zeros((STATE_RELATIVE_X_BINS, STATE_Y_BINS, ACTION_SPACE))

# --- Images (Ensure these paths exist for Pygame) ---
try:
    player_image = pygame.transform.scale(pygame.image.load("Images/recycle-bin.png"), (PLAYER_WIDTH, PLAYER_HEIGHT))
    apple_image = pygame.transform.scale(pygame.image.load("Images/apple.png"), (50, 50))
    banana_image = pygame.transform.scale(pygame.image.load("Images/banana.png"), (50, 50))
    bottle_image = pygame.transform.scale(pygame.image.load("Images/garbage-bag.png"), (50, 50))
    garbage_bag_image = pygame.transform.scale(pygame.image.load("Images/garbage-bag.png"), (50, 50))
    garbage_image_list = [apple_image, banana_image, bottle_image, garbage_bag_image]
except pygame.error as e:
    print(f"Error loading images: {e}. Pygame requires these files to run.")
    sys.exit()


# --- Classes ---

class Player(pygame.Rect):
    def __init__(self):
        super().__init__(275, 450, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.image = player_image


class Garbage(pygame.Rect):
    def __init__(self):
        width, height = 50, 50
        random_x = random.randint(20, SCREEN_WIDTH - width - 20)
        super().__init__(random_x, -50, width, height)

        self.selected_image = random.choice(garbage_image_list)
        self.vy = 0.0
        self._y = float(self.y)
        self.lock = False  # True if it has hit the ground


# --- Game State and Utility Functions ---
player = Player()
garbage_rect_list = []
points = 0
font = pygame.font.Font(None, 36)
spawn_difficulty_rate = 2.0
spawn_interval = 8.0  # Starting interval (seconds)
spawn_modifier = 0.25


def get_state(player_obj, garbage_list):
    """Discretizes the game state (Relative X, Y Height) - MUST MATCH TRAINER."""
    falling_garbage = [g for g in garbage_list if not g.lock]

    if not falling_garbage:
        return (0, 0)

    closest_garbage = min(falling_garbage, key=lambda g: abs(player_obj.centerx - g.centerx))

    relative_x = closest_garbage.centerx - player_obj.centerx
    bin_size = SCREEN_WIDTH / STATE_RELATIVE_X_BINS

    relative_x_bin = np.clip(
        int((relative_x + SCREEN_WIDTH / 2) / bin_size),
        0, STATE_RELATIVE_X_BINS - 1
    )

    garbage_y_bin = np.clip(
        int(closest_garbage.centery / SCREEN_HEIGHT * STATE_Y_BINS),
        0, STATE_Y_BINS - 1
    )

    return (relative_x_bin, garbage_y_bin)


def select_action(state):
    """Selects the best action based on the loaded Q-Table (pure exploitation)."""
    # Epsilon is effectively 0 here, as we only exploit the learned policy
    q_values = Q_TABLE[state]
    return np.argmax(q_values)


def apply_action(action):
    """Moves the player based on the selected action."""
    if action == 0 and player.x - PLAYER_SPEED >= 0:
        player.x -= PLAYER_SPEED
    elif action == 2 and player.x + PLAYER_SPEED <= (SCREEN_WIDTH - PLAYER_WIDTH):
        player.x += PLAYER_SPEED


def check_length_between_two_points(a, b, x, y):
    return round(math.sqrt((x - a) ** 2 + (y - b) ** 2))


def check_collision_and_collect():
    global points
    for garbage in garbage_rect_list[:]:
        if garbage.lock: continue

        # Simplified collision check
        if player.colliderect(garbage):
            garbage_center_x = garbage.x + (garbage.width // 2)
            garbage_center_y = garbage.y + (garbage.height // 2)

            trash_bin_collect_point_x = player.x + (player.width // 2)
            trash_bin_collect_point_y = player.y + (player.height // 3)

            length = check_length_between_two_points(garbage_center_x, garbage_center_y, trash_bin_collect_point_x,
                                                     trash_bin_collect_point_y)

            if length < COLLECT_DISTANCE:
                garbage_rect_list.remove(garbage)
                points += 1
                return  # Only collect one per tick for simplicity


def apply_gravity(dt):
    global running
    garbage_on_ground_count = 0

    for rect in garbage_rect_list[:]:
        if rect.lock:
            garbage_on_ground_count += 1
            continue

        rect.vy += GRAVITY * dt
        rect._y += rect.vy * dt
        rect.y = int(rect._y)

        if rect.bottom > SCREEN_HEIGHT:
            rect.bottom = SCREEN_HEIGHT
            rect._y = rect.y
            rect.vy = 0.0
            rect.lock = True

    if garbage_on_ground_count > GARBAGE_ON_GROUND_LIMIT:
        return False  # Game Over

    return True  # Game Still Running


def draw():
    screen.fill((230, 230, 250))  # Light Lavender background

    # Draw Player
    screen.blit(player.image, player)

    # Draw Garbage
    for rect in garbage_rect_list:
        if rect.lock:
            # Draw ground garbage slightly grayscale to distinguish
            grayscale_img = pygame.transform.grayscale(rect.selected_image)
            screen.blit(grayscale_img, rect)
        else:
            screen.blit(rect.selected_image, rect)

    # Draw Score/Status
    status_text = f"Points: {points} | AI Mode: ON"
    text_surface = font.render(status_text, True, (0, 0, 0))
    screen.blit(text_surface, (10, 10))


# --- Main Game Loop ---
running = True
last_spawn_time = time.time()

print("\n--- Starting Visual AI Play ---")

while running:
    # Handle Quit Event
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Calculate delta time
    dt = clock.tick(60) / 1000.0  # Cap frame rate at 60 FPS

    # --- Garbage Spawning ---
    if not garbage_rect_list or time.time() - last_spawn_time > (spawn_interval / math.log2(spawn_difficulty_rate)):
        garbage_rect_list.append(Garbage())
        last_spawn_time = time.time()
        spawn_difficulty_rate += spawn_modifier

    # --- AI Action ---
    state = get_state(player, garbage_rect_list)
    action = select_action(state)
    apply_action(action)

    # --- Game Logic ---
    running = apply_gravity(dt)
    check_collision_and_collect()

    # --- Drawing ---
    draw()

    pygame.display.flip()

# Cleanup
pygame.quit()
sys.exit()
