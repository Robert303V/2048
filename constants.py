import pygame

# --- Window & Layout Dimensions ---
WIDTH, HEIGHT = 500, 750
GRID_WIDTH, GRID_HEIGHT = 400, 400
CELL_SIZE = GRID_WIDTH / 4
CELL_PADDING = 9

# --- Tile Palette ---
CELL_COLORS = {
    0: (196, 182, 168),      # Deeper recessed stone for empty cell sockets
    2: (246, 240, 232),      # Clean, bright porcelain ivory
    4: (242, 206, 142),      # Warm golden custard / soft honey amber (clearly distinct from 2)
    8: (242, 177, 121),
    16: (245, 149, 99),
    32: (246, 124, 95),
    64: (246, 94, 59),
    128: (237, 207, 114),
    256: (237, 204, 97),
    512: (237, 200, 80),
    1024: (237, 197, 63),
    2048: (237, 194, 46),
    4096: (158, 209, 142),
    8192: (115, 186, 155),
    16384: (90, 163, 168),
    32768: (85, 126, 172),
    65536: (77, 90, 166),
}

# --- Visual Themes ---
THEMES = {
    'Classic': {
        'bg': (187, 173, 160),
        'grid_bg': (205, 193, 180),
        'slot_bg': (196, 182, 168),
        'header_box': (143, 122, 102),
        'header_text_lbl': (238, 228, 218),
        'header_text_val': (255, 255, 255),
        'card_bg': (198, 184, 171),
        'card_border': (176, 163, 150),
        'pill_bg': (188, 174, 161),
        'title_color': (119, 110, 101),
        'sub_color': (140, 130, 120),
        'btn_ai_active': (237, 142, 70),
        'btn_ai_idle': (143, 122, 102),
        'btn_bot_active': (237, 142, 70),
        'btn_bot_idle': (143, 122, 102),
        'btn_general': (155, 140, 125),
        'badge_human': (74, 133, 5),
        'badge_bot': (217, 106, 34),
        'live_dot': (56, 142, 60),
        'text_dark': (119, 110, 101),
        'text_light': (249, 246, 242),
        'banner_bg': (237, 194, 46),
        'banner_text': (255, 255, 255),
        'game_over_overlay': (238, 228, 218, 190),
        'modal_overlay': (20, 18, 16, 175),
    },
    'Dark': {
        'bg': (26, 28, 36),
        'grid_bg': (40, 44, 56),
        'slot_bg': (48, 54, 68),
        'header_box': (50, 56, 72),
        'header_text_lbl': (175, 182, 198),
        'header_text_val': (255, 255, 255),
        'card_bg': (34, 38, 48),
        'card_border': (52, 58, 74),
        'pill_bg': (42, 47, 60),
        'title_color': (245, 247, 252),
        'sub_color': (150, 158, 178),
        'btn_ai_active': (235, 125, 55),
        'btn_ai_idle': (60, 68, 88),
        'btn_bot_active': (235, 125, 55),
        'btn_bot_idle': (60, 68, 88),
        'btn_general': (50, 56, 72),
        'badge_human': (61, 122, 4),
        'badge_bot': (197, 88, 24),
        'live_dot': (76, 175, 80),
        'text_dark': (30, 32, 40),
        'text_light': (249, 246, 242),
        'banner_bg': (158, 209, 142),
        'banner_text': (25, 45, 25),
        'game_over_overlay': (20, 22, 28, 210),
        'modal_overlay': (10, 12, 18, 195),
    },
}

TEXT_COLOR_LIGHT = (249, 246, 242)
TEXT_COLOR_DARK = (119, 110, 101)
SCORE_TEXT_COLOR = (255, 255, 255)
GRID_SIZE = 4
WIN_TILE = 2048

# --- Fonts Setup ---
pygame.font.init()
try:
    FONT_PATH = pygame.font.match_font('arial')
except Exception:
    FONT_PATH = None

FONT_HUGE = pygame.font.Font(FONT_PATH, 44) if FONT_PATH else pygame.font.Font(None, 44)
FONT_BIG = pygame.font.Font(FONT_PATH, 36) if FONT_PATH else pygame.font.Font(None, 36)
FONT_MEDIUM = pygame.font.Font(FONT_PATH, 26) if FONT_PATH else pygame.font.Font(None, 26)
FONT_SMALL = pygame.font.Font(FONT_PATH, 19) if FONT_PATH else pygame.font.Font(None, 19)
FONT_TINY = pygame.font.Font(FONT_PATH, 14) if FONT_PATH else pygame.font.Font(None, 14)
FONT_MICRO = pygame.font.Font(FONT_PATH, 11) if FONT_PATH else pygame.font.Font(None, 11)
