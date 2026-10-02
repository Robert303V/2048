import pygame
import time
from constants import *
from stats import GameStats
from sound import SoundManager


class GameGUI:
    def __init__(self, game):
        pygame.init()
        self.game = game
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('2048 - Bot Solver & Game')

        # Center grid coordinates
        self.grid_x = (WIDTH - GRID_WIDTH) // 2
        self.grid_y = 145

        # Theme and Services
        self.current_theme_name = 'Classic'
        self.stats = GameStats()
        self.sound = SoundManager()

        # Milestone banner timer
        self.banner_text = None
        self.banner_end_time = 0

        # Slide Animation State
        self.anim_transitions = None
        self.anim_spawn = None
        self.anim_duration = 0.0
        self.anim_start_time = 0.0
        self.anim_end_time = 0.0

        # Top Action Buttons (Row: y=88, h=36)
        btn_y = 88
        btn_h = 36
        self.bot_btn_rect = pygame.Rect(self.grid_x, btn_y, 110, btn_h)
        self.ai_btn_rect = self.bot_btn_rect  # Backward compatibility alias
        self.step_btn_rect = pygame.Rect(self.grid_x + 118, btn_y, 65, btn_h)
        self.undo_btn_rect = pygame.Rect(self.grid_x + 191, btn_y, 65, btn_h)
        self.speed_btn_rect = pygame.Rect(self.grid_x + 264, btn_y, 75, btn_h)
        self.reset_btn_rect = pygame.Rect(self.grid_x + 347, btn_y, 53, btn_h)

        # Footer Buttons Row (y=616, h=28) - cleanly separated from shortcuts hint
        footer_btn_y = 616
        footer_btn_h = 28
        self.theme_btn_rect = pygame.Rect(self.grid_x, footer_btn_y, 96, footer_btn_h)
        self.sound_btn_rect = pygame.Rect(self.grid_x + 104, footer_btn_y, 96, footer_btn_h)

    @property
    def theme(self):
        return THEMES[self.current_theme_name]

    def toggle_theme(self):
        self.current_theme_name = 'Dark' if self.current_theme_name == 'Classic' else 'Classic'

    def trigger_milestone(self, tile_value):
        self.banner_text = f"🎉 {tile_value} Unlocked! Keep Going!"
        self.banner_end_time = time.time() + 3.0
        self.sound.play_milestone()

    def start_animation(self, transitions, spawn=None, duration=0.095):
        """Starts a silky smooth tile slide animation."""
        if not transitions:
            self.finish_animation()
            return
        self.anim_transitions = transitions
        self.anim_spawn = spawn
        self.anim_duration = duration
        self.anim_start_time = time.time()
        self.anim_end_time = self.anim_start_time + duration

    def is_animating(self):
        """Returns True if an animation is actively playing."""
        return bool(self.anim_transitions and time.time() < self.anim_end_time)

    def finish_animation(self):
        """Immediately completes any running animation to prevent dropped inputs."""
        self.anim_transitions = None
        self.anim_spawn = None
        self.anim_end_time = 0.0

    def draw_header(self):
        th = self.theme
        # Game Title & Subtitle
        title_surf = FONT_HUGE.render("2048", True, th['title_color'])
        self.screen.blit(title_surf, (self.grid_x, 18))

        sub_surf = FONT_TINY.render("EXPECTIMAX BOT", True, th['sub_color'])
        self.screen.blit(sub_surf, (self.grid_x + 4, 60))

        # Update high score in stats across human and bot categories
        self.stats.update(self.game.score, self.game.max_tile, self.game.used_bot)

        # Score & Best Boxes
        box_w = 95
        box_h = 50
        box_y = 18

        # 1. Current Score Box
        score_rect = pygame.Rect(WIDTH - self.grid_x - (box_w * 2 + 10), box_y, box_w, box_h)
        pygame.draw.rect(self.screen, th['header_box'], score_rect, border_radius=6)
        lbl_s = FONT_TINY.render("SCORE", True, th['header_text_lbl'])
        lbl_s_rect = lbl_s.get_rect(center=(score_rect.centerx, score_rect.top + 14))
        self.screen.blit(lbl_s, lbl_s_rect)
        val_s = FONT_MEDIUM.render(str(self.game.score), True, th['header_text_val'])
        val_s_rect = val_s.get_rect(center=(score_rect.centerx, score_rect.top + 34))
        self.screen.blit(val_s, val_s_rect)

        # 2. Best Score Box
        best_rect = pygame.Rect(WIDTH - self.grid_x - box_w, box_y, box_w, box_h)
        pygame.draw.rect(self.screen, th['header_box'], best_rect, border_radius=6)
        lbl_b = FONT_TINY.render("BEST", True, th['header_text_lbl'])
        lbl_b_rect = lbl_b.get_rect(center=(best_rect.centerx, best_rect.top + 14))
        self.screen.blit(lbl_b, lbl_b_rect)
        val_b = FONT_MEDIUM.render(str(self.stats.high_score), True, th['header_text_val'])
        val_b_rect = val_b.get_rect(center=(best_rect.centerx, best_rect.top + 34))
        self.screen.blit(val_b, val_b_rect)

    def draw_buttons(self, is_bot_running, speed_mode):
        th = self.theme

        # 1. Bot Run / Pause Button
        bot_col = th.get('btn_bot_active', th['btn_ai_active']) if is_bot_running else th.get('btn_bot_idle', th['btn_ai_idle'])
        pygame.draw.rect(self.screen, bot_col, self.bot_btn_rect, border_radius=6)
        bot_txt = "Pause Bot" if is_bot_running else "Run Bot"
        t_bot = FONT_SMALL.render(bot_txt, True, SCORE_TEXT_COLOR)
        self.screen.blit(t_bot, t_bot.get_rect(center=self.bot_btn_rect.center))

        # 2. Step Bot Button
        pygame.draw.rect(self.screen, th['btn_general'], self.step_btn_rect, border_radius=6)
        t_step = FONT_SMALL.render("Step", True, SCORE_TEXT_COLOR)
        self.screen.blit(t_step, t_step.get_rect(center=self.step_btn_rect.center))

        # 3. Undo Button
        undo_color = th['btn_general'] if self.game.history else (th['card_border'])
        pygame.draw.rect(self.screen, undo_color, self.undo_btn_rect, border_radius=6)
        t_undo = FONT_SMALL.render("Undo", True, SCORE_TEXT_COLOR if self.game.history else th['sub_color'])
        self.screen.blit(t_undo, t_undo.get_rect(center=self.undo_btn_rect.center))

        # 4. Speed Button
        pygame.draw.rect(self.screen, th['btn_general'], self.speed_btn_rect, border_radius=6)
        t_sp = FONT_TINY.render(speed_mode, True, SCORE_TEXT_COLOR)
        self.screen.blit(t_sp, t_sp.get_rect(center=self.speed_btn_rect.center))

        # 5. Reset Button
        pygame.draw.rect(self.screen, th['btn_general'], self.reset_btn_rect, border_radius=6)
        t_rst = FONT_TINY.render("Reset", True, SCORE_TEXT_COLOR)
        self.screen.blit(t_rst, t_rst.get_rect(center=self.reset_btn_rect.center))

    def draw_tile(self, value, x, y, size):
        """Draws a single tile with accurate colors, rounded corners, and centered text."""
        rect = pygame.Rect(int(x), int(y), int(size), int(size))
        cell_color = self.theme.get('slot_bg', CELL_COLORS[0]) if value == 0 else CELL_COLORS.get(value, CELL_COLORS[65536])
        pygame.draw.rect(self.screen, cell_color, rect, border_radius=6)

        if value != 0:
            text_color = TEXT_COLOR_DARK if value in [2, 4] else TEXT_COLOR_LIGHT
            if value < 100:
                font = FONT_BIG
            elif value < 1000:
                font = FONT_MEDIUM
            elif value < 10000:
                font = FONT_SMALL
            else:
                font = FONT_TINY

            text_surface = font.render(str(value), True, text_color)
            text_rect = text_surface.get_rect(center=rect.center)
            self.screen.blit(text_surface, text_rect)

    def draw_board(self):
        th = self.theme
        self.screen.fill(th['bg'])

        # Grid Background Container
        pygame.draw.rect(
            self.screen,
            th['grid_bg'],
            (self.grid_x, self.grid_y, GRID_WIDTH, GRID_HEIGHT),
            border_radius=8
        )

        slot_size = CELL_SIZE - 2 * CELL_PADDING
        slot_color = th.get('slot_bg', CELL_COLORS[0])

        # 1. Render empty grid socket backgrounds
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                sx = self.grid_x + c * CELL_SIZE + CELL_PADDING
                sy = self.grid_y + r * CELL_SIZE + CELL_PADDING
                pygame.draw.rect(self.screen, slot_color, (sx, sy, slot_size, slot_size), border_radius=6)

        # 2. Render tiles (either smoothly sliding or static)
        now = time.time()
        if self.anim_transitions and now < self.anim_end_time:
            progress = min(1.0, (now - self.anim_start_time) / self.anim_duration) if self.anim_duration > 0 else 1.0
            # Quadratic ease-out for silky, natural motion
            ease_p = 1.0 - (1.0 - progress) ** 2

            # Stationary tiles drawn first; sliding tiles glide smoothly on top
            sorted_trans = sorted(self.anim_transitions, key=lambda t: t['from'] == t['to'])
            for t in sorted_trans:
                sr, sc = t['from']
                er, ec = t['to']
                cur_r = sr + (er - sr) * ease_p
                cur_c = sc + (ec - sc) * ease_p
                tx = self.grid_x + cur_c * CELL_SIZE + CELL_PADDING
                ty = self.grid_y + cur_r * CELL_SIZE + CELL_PADDING
                self.draw_tile(t['val'], tx, ty, slot_size)
        else:
            # Animation complete or inactive: render live board grid
            self.anim_transitions = None
            for r in range(GRID_SIZE):
                for c in range(GRID_SIZE):
                    cell_value = self.game.grid[r, c]
                    if cell_value != 0:
                        tx = self.grid_x + c * CELL_SIZE + CELL_PADDING
                        ty = self.grid_y + r * CELL_SIZE + CELL_PADDING
                        self.draw_tile(cell_value, tx, ty, slot_size)

    def draw_stats_bar(self):
        th = self.theme
        stats_y = self.grid_y + GRID_HEIGHT + 13
        card_w = (GRID_WIDTH - 24) // 4
        card_h = 48

        # 4 Metric Cards: Moves, Max Tile, Empty Cells, Last Move
        metrics = [
            ("MOVES", str(self.game.moves)),
            ("MAX TILE", str(self.game.max_tile)),
            ("EMPTY", f"{len(self.game.get_empty_cells())}/16"),
            ("LAST MOVE", self.game.last_move.capitalize() if self.game.last_move else "-"),
        ]

        for i, (title, val) in enumerate(metrics):
            cx = self.grid_x + i * (card_w + 8)
            rect = pygame.Rect(cx, stats_y, card_w, card_h)
            pygame.draw.rect(self.screen, th['card_bg'], rect, border_radius=6)
            pygame.draw.rect(self.screen, th['card_border'], rect, width=1, border_radius=6)

            t_lbl = FONT_TINY.render(title, True, th['sub_color'])
            self.screen.blit(t_lbl, t_lbl.get_rect(center=(rect.centerx, rect.top + 13)))

            t_val = FONT_SMALL.render(val, True, th['title_color'])
            self.screen.blit(t_val, t_val.get_rect(center=(rect.centerx, rect.top + 32)))

        # Footer Row 1: Action Buttons (Theme, Sound, Lifetime Games counter)
        # Theme button
        pygame.draw.rect(self.screen, th['card_bg'], self.theme_btn_rect, border_radius=5)
        pygame.draw.rect(self.screen, th['card_border'], self.theme_btn_rect, width=1, border_radius=5)
        th_lbl = FONT_TINY.render(f"Theme: {self.current_theme_name}", True, th['sub_color'])
        self.screen.blit(th_lbl, th_lbl.get_rect(center=self.theme_btn_rect.center))

        # Sound button
        pygame.draw.rect(self.screen, th['card_bg'], self.sound_btn_rect, border_radius=5)
        pygame.draw.rect(self.screen, th['card_border'], self.sound_btn_rect, width=1, border_radius=5)
        snd_txt = "Sound: OFF" if self.sound.muted else "Sound: ON"
        snd_lbl = FONT_TINY.render(snd_txt, True, th['sub_color'])
        self.screen.blit(snd_lbl, snd_lbl.get_rect(center=self.sound_btn_rect.center))

        # Total games played indicator (right aligned on button row)
        games_txt = f"Games: {self.stats.games_played}"
        games_surf = FONT_TINY.render(games_txt, True, th['sub_color'])
        self.screen.blit(games_surf, games_surf.get_rect(right=self.grid_x + GRID_WIDTH, centery=self.sound_btn_rect.centery))

        # Footer Row 2: Dedicated Keyboard Shortcuts Legend (Zero overlap!)
        hint_txt = "Space: Bot  •  N: Step  •  U: Undo  •  S: Speed  •  T: Theme  •  M: Sound"
        hint_surf = FONT_TINY.render(hint_txt, True, th['sub_color'])
        self.screen.blit(hint_surf, hint_surf.get_rect(center=(WIDTH // 2, 668)))

    def draw_milestone_banner(self):
        if self.banner_text and time.time() < self.banner_end_time:
            th = self.theme
            banner_rect = pygame.Rect(self.grid_x, self.grid_y + 10, GRID_WIDTH, 40)
            pygame.draw.rect(self.screen, th['banner_bg'], banner_rect, border_radius=6)
            txt_surf = FONT_SMALL.render(self.banner_text, True, th['banner_text'])
            self.screen.blit(txt_surf, txt_surf.get_rect(center=banner_rect.center))
        elif self.banner_text and time.time() >= self.banner_end_time:
            self.banner_text = None

    def draw_game_over(self):
        if self.game.is_game_over():
            th = self.theme
            overlay = pygame.Surface((GRID_WIDTH, GRID_HEIGHT), pygame.SRCALPHA)
            overlay.fill(th['game_over_overlay'])
            self.screen.blit(overlay, (self.grid_x, self.grid_y))

            t_over = FONT_HUGE.render("Game Over!", True, th['title_color'])
            self.screen.blit(t_over, t_over.get_rect(center=(WIDTH // 2, self.grid_y + GRID_HEIGHT // 2 - 35)))

            score_txt = f"Final Score: {self.game.score} | Max Tile: {self.game.max_tile}"
            t_sc = FONT_SMALL.render(score_txt, True, th['sub_color'])
            self.screen.blit(t_sc, t_sc.get_rect(center=(WIDTH // 2, self.grid_y + GRID_HEIGHT // 2 + 10)))

            t_restart = FONT_SMALL.render("Press 'R' to Restart  |  'U' to Undo", True, th['title_color'])
            self.screen.blit(t_restart, t_restart.get_rect(center=(WIDTH // 2, self.grid_y + GRID_HEIGHT // 2 + 45)))

    def update_display(self, is_bot_running, speed_mode):
        self.draw_board()
        self.draw_header()
        self.draw_buttons(is_bot_running, speed_mode)
        self.draw_stats_bar()
        self.draw_milestone_banner()
        self.draw_game_over()
        pygame.display.flip()
