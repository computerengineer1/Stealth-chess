import os

class Config:
    """Centralized configuration for the Chess Overlay Bot."""

    # --- Engine Settings ---
    # Default Stockfish path. User MUST update this if different.
    STOCKFISH_PATH = r"stockfish-windows-x86-64-avx2.exe" # Change this if necessary
    ENGINE_THREADS = 2
    ENGINE_HASH = 64
    ENGINE_SKILL_LEVEL = 15  # ~2000 ELO Humanized
    ENGINE_DEPTH = 10        # Perfect balance of speed for bullet and strength
    
    # --- Humanization & Practice Settings ---
    # Options: "bullet" (ultra-fast helper), "blitz" (moderate helper), "rapid" (relaxed training helper)
    GAME_MODE = "bullet"
    RANDOMIZE_MOVES = True  # Occasionally suggest the 2nd best move if it's very close in score
    SHOW_ARROWS = True      # Render board arrows overlay

    # --- Screen Capture Settings ---
    MONITOR_INDEX = 1  # 1 is typically the primary monitor in mss
    TARGET_FPS = 10    # 10 FPS is sufficient for a turn-based game
    
    # Manual Calibration. Run python calibrate.py to get these values.
    # Set this to a tuple e.g. (100, 200, 800, 800) to bypass auto-detection.
    MANUAL_BOARD_BBOX = (283, 191, 801, 801)
    
    # --- Vision Settings ---
    # Note: Traditional CV templates matching is deprecated in favor of direct DOM reader.


    # --- UI & Overlay Settings ---
    # Adjust these if your Windows DPI scaling causes the arrows to misalign with the board
    OVERLAY_SCALE_FACTOR = 1.25  # Changed to 1.25 based on the arrow drift in your screenshot
    OVERLAY_OFFSET_X = 0         # Nudge arrows left/right (in pixels)
    OVERLAY_OFFSET_Y = 0         # Nudge arrows up/down (in pixels)
    
    # PyQt colors (R, G, B, Alpha/Opacity)
    COLOR_BEST_MOVE = (0, 255, 0, 180)     # Green
    COLOR_SECOND_MOVE = (255, 255, 0, 150) # Yellow
    COLOR_THIRD_MOVE = (255, 165, 0, 150)  # Orange

    # --- Hotkeys ---
    HOTKEY_TOGGLE = "ctrl+shift+h"
    HOTKEY_EXIT = "ctrl+shift+q"
    HOTKEY_STEALTH = "ctrl+shift+s"

    # --- Licensing Settings ---
    # Remote verification API. Set to None to use local test keys ('TEST-KEY-MONTHLY' or 'TEST-KEY-LIFETIME').
    LICENSE_API_URL = "https://gist.githubusercontent.com/computerengineer1/c6b0466a666549755c0c149fbff7dbdd/raw/db.txt"

    # --- Stealth Display Settings ---
    # When True, the PyQt overlay is hidden from screen capture/recording/streaming (Default: True)
    STEALTH_DISPLAY = True


