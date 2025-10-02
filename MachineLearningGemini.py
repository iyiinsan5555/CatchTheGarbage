import math
import random
import numpy as np
import time
import json
import os  # Import os for checking file existence

# ------------------------------------------------
# ENVIRONMENT & GAME CONSTANTS
# ------------------------------------------------
SCREEN_WIDTH = 650
SCREEN_HEIGHT = 550

PLAYER_WIDTH = 100
PLAYER_HEIGHT = 100
PLAYER_REPLACEMENT = 15  # MUCH FASTER PLAYER SPEED for accelerated learning

GRAVITY = 20
COLLECT_DISTANCE = 20
GARBAGE_ON_GROUND_LIMIT = 20

# Fixed timestep for physics (crucial for headless simulation)
FIXED_DT = 0.01

# Garbage Spawning Variables
GARBAGE_SPAWN_INTERVAL = 8.0  # Starting interval (seconds)
GARBAGE_SPAWN_RATE_MODIFIER = 0.25  # Rate of difficulty increase

# ------------------------------------------------
# Q-LEARNING AI SETTINGS
# ------------------------------------------------
ACTION_SPACE = 3  # 0: Left, 1: No Move, 2: Right

# State Space Simplification (10 relative horizontal bins, 3 vertical bins)
STATE_RELATIVE_X_BINS = 10
STATE_Y_BINS = 3
Q_TABLE_SHAPE = (STATE_RELATIVE_X_BINS, STATE_Y_BINS, ACTION_SPACE)

# Hyperparameters (Aggressive settings for learning)
LEARNING_RATE = 0.35
DISCOUNT_FACTOR = 0.95
INITIAL_EPSILON = 1.0
EPSILON_DECAY = 0.99999
MIN_EPSILON = 0.01

# Boosted Rewards/Penalties
REWARD_COLLECT = 150
PENALTY_GROUND = -75
PENALTY_GAME_OVER = -1500

# File paths for saving/loading
Q_TABLE_FILE = 'catch_garbage_q_table.npy'
METADATA_FILE = 'ai_metadata.json'  # To store epsilon and other variables

# Initialize Q-Table and Epsilon
Q_TABLE = np.zeros(Q_TABLE_SHAPE)
GLOBAL_EPSILON = INITIAL_EPSILON


# ------------------------------------------------
# CHECKPOINTING FUNCTIONS
# ------------------------------------------------

def load_checkpoint():
    """Loads the Q-table and epsilon value if they exist."""
    global Q_TABLE, GLOBAL_EPSILON, INITIAL_EPSILON

    # 1. Load Q-Table
    if os.path.exists(Q_TABLE_FILE):
        try:
            Q_TABLE = np.load(Q_TABLE_FILE)
            print(f"Loaded Q-table from {Q_TABLE_FILE}. Shape: {Q_TABLE.shape}")
        except Exception as e:
            print(f"Error loading Q-table: {e}. Starting with fresh Q-table.")
            Q_TABLE = np.zeros(Q_TABLE_SHAPE)
    else:
        print("Starting fresh training session (Q-table file not found).")
        Q_TABLE = np.zeros(Q_TABLE_SHAPE)

    # 2. Load Metadata (Epsilon)
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'r') as f:
                metadata = json.load(f)
            # Ensure the loaded epsilon is not lower than the minimum
            GLOBAL_EPSILON = max(MIN_EPSILON, metadata.get('epsilon', INITIAL_EPSILON))
            print(f"Loaded Epsilon: {GLOBAL_EPSILON:.6f}. Resuming exploration.")
        except Exception as e:
            print(f"Error loading metadata: {e}. Using initial Epsilon: {INITIAL_EPSILON}")
            GLOBAL_EPSILON = INITIAL_EPSILON
    else:
        GLOBAL_EPSILON = INITIAL_EPSILON


def save_checkpoint(final_epsilon):
    """Saves the current Q-table and the last epsilon value."""
    # 1. Save Q-Table
    np.save(Q_TABLE_FILE, Q_TABLE)

    # 2. Save Metadata (Epsilon)
    metadata = {'epsilon': final_epsilon}
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f)

    print(f"\nSaved Q-table to {Q_TABLE_FILE} and metadata to {METADATA_FILE}.")


# ------------------------------------------------
# SIMULATION CLASSES (Simplified, no Pygame dependency)
# ------------------------------------------------

class Player:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    @property
    def centerx(self):
        return self.x + self.width / 2


class Garbage:
    def __init__(self, y, width, height):
        self.x = random.randint(20, SCREEN_WIDTH - width - 20)
        self.y = y
        self.width = width
        self.height = height
        self.vy = 0.0
        self._y = float(self.y)
        self.lock = False  # True if it has hit the ground

    @property
    def centerx(self):
        return self.x + self.width / 2

    @property
    def centery(self):
        return self.y + self.height / 2

    @property
    def bottom(self):
        return self.y + self.height


# ------------------------------------------------
# Q-LEARNING CORE FUNCTIONS
# ------------------------------------------------

def get_state(player_obj, garbage_list):
    """Discretizes the game state (Relative X, Y Height)."""
    falling_garbage = [g for g in garbage_list if not g.lock]

    if not falling_garbage:
        return (0, 0)

    closest_garbage = min(falling_garbage, key=lambda g: abs(player_obj.centerx - g.centerx))

    # 1. Relative X Bin (Horizontal distance)
    relative_x = closest_garbage.centerx - player_obj.centerx

    bin_size = SCREEN_WIDTH / STATE_RELATIVE_X_BINS

    relative_x_bin = np.clip(
        int((relative_x + SCREEN_WIDTH / 2) / bin_size),
        0, STATE_RELATIVE_X_BINS - 1
    )

    # 2. Y Height Bin (Vertical position: High, Mid, Low)
    garbage_y_bin = np.clip(
        int(closest_garbage.centery / SCREEN_HEIGHT * STATE_Y_BINS),
        0, STATE_Y_BINS - 1
    )

    return (relative_x_bin, garbage_y_bin)


def select_action(state):
    """Selects an action using the Epsilon-Greedy strategy."""
    if random.random() < GLOBAL_EPSILON:
        return random.choice(range(ACTION_SPACE))  # Explore
    else:
        q_values = Q_TABLE[state]
        return np.argmax(q_values)


def apply_action(player_obj, action):
    """Moves the player based on the selected action."""
    if action == 0 and player_obj.x - PLAYER_REPLACEMENT >= 0:
        player_obj.x -= PLAYER_REPLACEMENT
    elif action == 2 and player_obj.x + PLAYER_REPLACEMENT <= (SCREEN_WIDTH - PLAYER_WIDTH):
        player_obj.x += PLAYER_REPLACEMENT


def update_q_table(state, action, reward, next_state):
    """Applies the Q-learning formula."""
    old_q_value = Q_TABLE[state + (action,)]
    max_future_q = np.max(Q_TABLE[next_state])

    new_q_value = (1 - LEARNING_RATE) * old_q_value + LEARNING_RATE * (reward + DISCOUNT_FACTOR * max_future_q)

    Q_TABLE[state + (action,)] = new_q_value


# ------------------------------------------------
# SIMULATION LOOP (THE FAST RUNNER)
# ------------------------------------------------

def visualize_q_table():
    """Prints a text visualization of the Q-table's policy."""
    print("\n--- AI Learned Policy (Best Action for each State) ---")
    print("Action Key: 0=LEFT, 1=NONE, 2=RIGHT")
    print("Relative X Bins (0=Leftmost, 9=Rightmost) vs. Y Bins (0=High, 2=Low)")

    # Create the header for the relative X bins
    header = ["Y Bins ↓ |"] + [f"X={i}" for i in range(STATE_RELATIVE_X_BINS)]
    print("-" * 75)
    print("".join([f"{col:^7}" for col in header]))
    print("-" * 75)

    # Iterate through Y Bins (vertical height)
    for y_bin in range(STATE_Y_BINS):
        row = [f"Y={y_bin:^5} |"]
        # Iterate through Relative X Bins (horizontal position)
        for x_bin in range(STATE_RELATIVE_X_BINS):
            state = (x_bin, y_bin)
            best_action = np.argmax(Q_TABLE[state])
            row.append(f" {best_action:^5} |")
        print("".join(row).replace('| |', '|'))
        print("-" * 75)


def run_episode():
    """Runs a single episode (game) to completion."""
    global GLOBAL_EPSILON

    # Reset game state
    player = Player(275, 450, PLAYER_WIDTH, PLAYER_HEIGHT)
    garbage_list = []
    points = 0
    garbage_on_ground_count = 0

    game_time = 0.0
    spawn_timer = 0.0
    spawn_difficulty_rate = 2.0  # Corresponds to initial 'x' in original log2 formula

    # Variables for Q-Learning update
    last_state = None
    last_action = None

    is_running = True

    while is_running:

        # --- Garbage Spawning ---
        spawn_timer += FIXED_DT

        log_value = math.log2(spawn_difficulty_rate)
        wait_time = GARBAGE_SPAWN_INTERVAL / log_value

        if spawn_timer >= wait_time or not garbage_list:
            garbage = Garbage(-50, 50, 50)
            garbage_list.append(garbage)
            spawn_timer = 0.0
            spawn_difficulty_rate += GARBAGE_SPAWN_RATE_MODIFIER

        # --- AI Decision Making ---
        current_state = get_state(player, garbage_list)
        action = select_action(current_state)
        apply_action(player, action)

        last_state = current_state
        last_action = action

        # --- Physics and Reward Collection ---

        reward = 0

        # 1. Apply Gravity and Check Ground Collision
        for garbage in garbage_list[:]:
            if garbage.lock: continue

            garbage._y += (garbage.vy * FIXED_DT)
            garbage.y = int(garbage._y)
            garbage.vy += (GRAVITY * FIXED_DT)

            # Check for ground collision
            if garbage.bottom >= SCREEN_HEIGHT:
                garbage.y = SCREEN_HEIGHT - garbage.height
                garbage._y = garbage.y
                garbage.vy = 0.0
                garbage.lock = True

                garbage_on_ground_count += 1
                r = PENALTY_GROUND
                reward += r

                next_state = get_state(player, garbage_list)
                update_q_table(last_state, last_action, r, next_state)

        # 2. Check for Player Collection
        for garbage in garbage_list[:]:
            if garbage.lock: continue

            player_center_x = player.centerx
            player_collect_y = player.y + player.height / 3

            dx = garbage.centerx - player_center_x
            dy = garbage.centery - player_collect_y
            length_sq = (dx ** 2 + dy ** 2)

            if length_sq < COLLECT_DISTANCE ** 2:
                garbage_list.remove(garbage)
                points += 1
                r = REWARD_COLLECT
                reward += r

                next_state = get_state(player, garbage_list)
                update_q_table(last_state, last_action, r, next_state)

        # 3. Check Game Over
        if garbage_on_ground_count > GARBAGE_ON_GROUND_LIMIT:
            is_running = False
            reward += PENALTY_GAME_OVER

            old_q_value = Q_TABLE[last_state + (last_action,)]
            new_q_value = (1 - LEARNING_RATE) * old_q_value + LEARNING_RATE * (reward + DISCOUNT_FACTOR * 0)
            Q_TABLE[last_state + (last_action,)] = new_q_value

        game_time += FIXED_DT

    # --- End of Episode ---
    # Epsilon decay occurs only once per episode
    GLOBAL_EPSILON = max(MIN_EPSILON, GLOBAL_EPSILON * EPSILON_DECAY)

    return points, game_time


def fast_training_run(max_runtime_seconds=3600):
    """Runs episodes as fast as possible for a set duration (default 1 hour)."""
    start_time = time.time()
    episode_count = 0
    total_points = 0

    # Load previous training state
    load_checkpoint()

    print("--- Starting Headless Q-Learning Simulation ---")
    print(f"Goal Runtime: {max_runtime_seconds // 60} minutes")
    print(f"Current Epsilon: {GLOBAL_EPSILON:.6f}")
    print("-" * 40)

    try:
        while time.time() - start_time < max_runtime_seconds:
            points, duration = run_episode()

            episode_count += 1
            total_points += points

            # Log progress every 100 episodes
            if episode_count % 100 == 0:
                elapsed_time = time.time() - start_time
                avg_points = total_points / episode_count

                print(
                    f"[{int(elapsed_time)}s] Episodes: {episode_count:,} | Avg Score: {avg_points:.2f} | Epsilon: {GLOBAL_EPSILON:.6f}")

    except KeyboardInterrupt:
        print("\nTraining interrupted by user.")

    print("-" * 40)
    print(f"Simulation Finished. Total time added: {int(time.time() - start_time)} seconds.")
    print(f"Total Episodes Run in this session: {episode_count:,}")

    # Calculate final average score for this session
    if episode_count > 0:
        final_avg_score = total_points / episode_count
        print(f"Session Average Score: {final_avg_score:.2f}")

    # Save the current state for continuation
    save_checkpoint(GLOBAL_EPSILON)

    # Visualize the final policy
    visualize_q_table()


if __name__ == "__main__":
    # You can change the time limit here (e.g., 3600 for 1 hour, 600 for 10 minutes)
    fast_training_run(max_runtime_seconds=1200)
