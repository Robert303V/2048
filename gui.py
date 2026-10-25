import pygame
import time
import re
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
        self.leaderboard_y = 72
        self.leaderboard_h = 74
        self.grid_y = 198

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

        # New All-Time Record Modal State
        self.record_modal_active = False
        self.modal_record_type = 'human'
        self.modal_record_score = 0
        self.modal_input_text = ""
        self.modal_save_rect = pygame.Rect(0, 0, 0, 0)
        self.modal_skip_rect = pygame.Rect(0, 0, 0, 0)

        # Top Action Buttons (Row: y=154, h=35)
        btn_y = 154
        btn_h = 35
        self.bot_btn_rect = pygame.Rect(self.grid_x, btn_y, 110, btn_h)
        self.ai_btn_rect = self.bot_btn_rect  # Backward compatibility alias
        self.step_btn_rect = pygame.Rect(self.grid_x + 118, btn_y, 65, btn_h)
        self.undo_btn_rect = pygame.Rect(self.grid_x + 191, btn_y, 65, btn_h)
        self.speed_btn_rect = pygame.Rect(self.grid_x + 264, btn_y, 75, btn_h)
        self.reset_btn_rect = pygame.Rect(self.grid_x + 347, btn_y, 53, btn_h)

        # Footer Buttons Row (y=666, h=28) - cleanly separated from shortcuts hint
        footer_btn_y = 666
        footer_btn_h = 28
        self.theme_btn_rect = pygame.Rect(self.grid_x, footer_btn_y, 96, footer_btn_h)
        self.sound_btn_rect = pygame.Rect(self.grid_x + 102, footer_btn_y, 88, footer_btn_h)
        self.mode_tag_rect = pygame.Rect(self.grid_x + 196, footer_btn_y, 112, footer_btn_h)

    @property
    def theme(self):
        return THEMES[self.current_theme_name]

    def toggle_theme(self):
        self.current_theme_name = 'Dark' if self.current_theme_name == 'Classic' else 'Classic'

    def trigger_milestone(self, tile_value):
        self.banner_text = f"🎉 {tile_value} Unlocked! Keep Going!"
        self.banner_end_time = time.time() + 3.0
        self.sound.play_milestone()

    def open_record_modal(self, record_type, score):
        """Opens the New All-Time Record modal overlay for player name entry."""
        self.record_modal_active = True
        self.modal_record_type = record_type
        self.modal_record_score = score
        self.modal_input_text = ""
        self.sound.play_milestone()

    def submit_record_modal(self, raw_name=None):
        """Saves the sanitized player name for the new all-time record and closes the modal."""
        if not self.record_modal_active:
            return
        name_to_save = self.modal_input_text if raw_name is None else raw_name
        default_name = "Bot Master" if self.modal_record_type == 'bot' else "Champion"
        final_name = name_to_save.strip() if name_to_save and name_to_save.strip() else default_name
        self.stats.set_record_holder(self.modal_record_type, final_name)
        self.record_modal_active = False
        self.modal_input_text = ""

    def handle_modal_key(self, event):
        """Processes keyboard input while the New All-Time Record modal is open."""
        if not self.record_modal_active:
            return False
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.submit_record_modal(self.modal_input_text)
        elif event.key == pygame.K_ESCAPE:
            self.submit_record_modal("Anonymous")
        elif event.key == pygame.K_BACKSPACE:
            self.modal_input_text = self.modal_input_text[:-1]
        else:
            ch = event.unicode
            if ch and len(self.modal_input_text) < 16 and re.match(r'^[a-zA-Z0-9 _-]$', ch):
                self.modal_input_text += ch
        return True

    def handle_modal_click(self, pos):
        """Processes mouse clicks while the New All-Time Record modal is open."""
        if not self.record_modal_active:
            return False
        if self.modal_save_rect.collidepoint(pos):
            self.submit_record_modal(self.modal_input_text)
        elif self.modal_skip_rect.collidepoint(pos):
            self.submit_record_modal("Anonymous")
        return True

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
        self.screen.blit(title_surf, (self.grid_x, 12))

        sub_surf = FONT_TINY.render("EXPECTIMAX BOT", True, th['sub_color'])
        self.screen.blit(sub_surf, (self.grid_x + 3, 52))

        # Score & Best Boxes
        box_w = 95
        box_h = 50
        box_y = 14

        # 1. Current Score Box
        score_rect = pygame.Rect(WIDTH - self.grid_x - (box_w * 2 + 10), box_y, box_w, box_h)
        pygame.draw.rect(self.screen, th['header_box'], score_rect, border_radius=6)
        lbl_s = FONT_TINY.render("SCORE", True, th['header_text_lbl'])
        lbl_s_rect = lbl_s.get_rect(center=(score_rect.centerx, score_rect.top + 14))
        self.screen.blit(lbl_s, lbl_s_rect)
        val_s = FONT_MEDIUM.render(f"{self.game.score:,}", True, th['header_text_val'])
        val_s_rect = val_s.get_rect(center=(score_rect.centerx, score_rect.top + 34))
        self.screen.blit(val_s, val_s_rect)

        # 2. Best Score Box
        best_rect = pygame.Rect(WIDTH - self.grid_x - box_w, box_y, box_w, box_h)
        pygame.draw.rect(self.screen, th['header_box'], best_rect, border_radius=6)
        lbl_b = FONT_TINY.render("BEST", True, th['header_text_lbl'])
        lbl_b_rect = lbl_b.get_rect(center=(best_rect.centerx, best_rect.top + 14))
        self.screen.blit(lbl_b, lbl_b_rect)
        val_b = FONT_MEDIUM.render(f"{self.stats.high_score:,}", True, th['header_text_val'])
        val_b_rect = val_b.get_rect(center=(best_rect.centerx, best_rect.top + 34))
        self.screen.blit(val_b, val_b_rect)

    def draw_leaderboard_card(self):
        """Renders the 4-Category Leaderboard Card (All-Time & Session for Human & Bot)."""
        th = self.theme
        card_rect = pygame.Rect(self.grid_x, self.leaderboard_y, GRID_WIDTH, self.leaderboard_h)
        pygame.draw.rect(self.screen, th['card_bg'], card_rect, border_radius=8)
        pygame.draw.rect(self.screen, th['card_border'], card_rect, width=1, border_radius=8)

        # Top Section Header: All-Time Records
        hdr_lbl = FONT_MICRO.render("ALL-TIME RECORDS", True, th['title_color'])
        self.screen.blit(hdr_lbl, (card_rect.left + 10, card_rect.top + 6))

        status_lbl = FONT_MICRO.render("● Saved", True, th['live_dot'])
        self.screen.blit(status_lbl, status_lbl.get_rect(right=card_rect.right - 10, top=card_rect.top + 6))

        # Two All-Time Record Pills (Human & Bot)
        pill_y = card_rect.top + 22
        pill_w = (GRID_WIDTH - 28) // 2
        pill_h = 24

        # 1. All-Time Human Pill
        h_pill = pygame.Rect(card_rect.left + 10, pill_y, pill_w, pill_h)
        pygame.draw.rect(self.screen, th['pill_bg'], h_pill, border_radius=5)

        h_badge = pygame.Rect(h_pill.left + 4, h_pill.top + 4, 44, 16)
        pygame.draw.rect(self.screen, th['badge_human'], h_badge, border_radius=3)
        hb_txt = FONT_MICRO.render("HUMAN", True, SCORE_TEXT_COLOR)
        self.screen.blit(hb_txt, hb_txt.get_rect(center=h_badge.center))

        h_name_str = self.stats.all_time_human_name[:11]
        hn_txt = FONT_MICRO.render(h_name_str, True, th['title_color'])
        self.screen.blit(hn_txt, hn_txt.get_rect(left=h_badge.right + 5, centery=h_pill.centery))

        hs_txt = FONT_TINY.render(f"{self.stats.all_time_human_score:,}", True, th['title_color'])
        self.screen.blit(hs_txt, hs_txt.get_rect(right=h_pill.right - 6, centery=h_pill.centery))

        # 2. All-Time Bot Pill
        b_pill = pygame.Rect(h_pill.right + 8, pill_y, pill_w, pill_h)
        pygame.draw.rect(self.screen, th['pill_bg'], b_pill, border_radius=5)

        b_badge = pygame.Rect(b_pill.left + 4, b_pill.top + 4, 32, 16)
        pygame.draw.rect(self.screen, th['badge_bot'], b_badge, border_radius=3)
        bb_txt = FONT_MICRO.render("BOT", True, SCORE_TEXT_COLOR)
        self.screen.blit(bb_txt, bb_txt.get_rect(center=b_badge.center))

        b_name_str = self.stats.all_time_bot_name[:12]
        bn_txt = FONT_MICRO.render(b_name_str, True, th['title_color'])
        self.screen.blit(bn_txt, bn_txt.get_rect(left=b_badge.right + 5, centery=b_pill.centery))

        bs_txt = FONT_TINY.render(f"{self.stats.all_time_bot_score:,}", True, th['title_color'])
        self.screen.blit(bs_txt, bs_txt.get_rect(right=b_pill.right - 6, centery=b_pill.centery))

        # Divider line
        div_y = card_rect.top + 50
        pygame.draw.line(self.screen, th['card_border'], (card_rect.left + 10, div_y), (card_rect.right - 10, div_y), 1)

        # Bottom Section: Session Records
        sess_y = card_rect.top + 61
        sh_lbl = FONT_MICRO.render("Session Human Best:", True, th['sub_color'])
        self.screen.blit(sh_lbl, sh_lbl.get_rect(left=h_pill.left + 2, centery=sess_y))
        sh_val = FONT_TINY.render(f"{self.stats.session_human_score:,}", True, th['title_color'])
        self.screen.blit(sh_val, sh_val.get_rect(right=h_pill.right - 4, centery=sess_y))

        sb_lbl = FONT_MICRO.render("Session Bot Best:", True, th['sub_color'])
        self.screen.blit(sb_lbl, sb_lbl.get_rect(left=b_pill.left + 2, centery=sess_y))
        sb_val = FONT_TINY.render(f"{self.stats.session_bot_score:,}", True, th['title_color'])
        self.screen.blit(sb_val, sb_val.get_rect(right=b_pill.right - 4, centery=sess_y))

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
        stats_y = self.grid_y + GRID_HEIGHT + 10
        card_w = (GRID_WIDTH - 24) // 4
        card_h = 48

        # 4 Metric Cards: Moves, Max Tile, Empty Cells, Last Move
        metrics = [
            ("MOVES", f"{self.game.moves:,}"),
            ("MAX TILE", f"{self.game.max_tile:,}"),
            ("EMPTY", f"{len(self.game.get_empty_cells())}/16"),
            ("LAST MOVE", self.game.last_move.upper() if self.game.last_move else "-"),
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

        # Footer Row 1: Action Buttons (Theme, Sound, Mode Tag, Lifetime Games counter)
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

        # Run Mode Tag (Pure Human vs Bot Assisted)
        pygame.draw.rect(self.screen, th['card_bg'], self.mode_tag_rect, border_radius=5)
        pygame.draw.rect(self.screen, th['card_border'], self.mode_tag_rect, width=1, border_radius=5)
        mode_str = "Bot Assisted" if self.game.used_bot else "Pure Human"
        mode_col = th['btn_bot_active'] if self.game.used_bot else th['sub_color']
        mode_lbl = FONT_TINY.render(mode_str, True, mode_col)
        self.screen.blit(mode_lbl, mode_lbl.get_rect(center=self.mode_tag_rect.center))

        # Total games played indicator (right aligned on button row)
        games_txt = f"Games: {self.stats.games_played}"
        games_surf = FONT_TINY.render(games_txt, True, th['sub_color'])
        self.screen.blit(games_surf, games_surf.get_rect(right=self.grid_x + GRID_WIDTH, centery=self.sound_btn_rect.centery))

        # Footer Row 2 & 3: Complete Keyboard & Mouse Controls Legend
        hint_line1 = "Arrows: Move  •  Space: Run/Pause Bot  •  N: Step (1 Move)  •  U: Undo"
        hint_line2 = "S: Speed (Normal/Fast/Turbo)  •  R: Reset  •  T: Theme  •  M: Sound"
        h1_surf = FONT_MICRO.render(hint_line1, True, th['sub_color'])
        h2_surf = FONT_MICRO.render(hint_line2, True, th['sub_color'])
        self.screen.blit(h1_surf, h1_surf.get_rect(center=(WIDTH // 2, 712)))
        self.screen.blit(h2_surf, h2_surf.get_rect(center=(WIDTH // 2, 730)))

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

            mode_label = "Bot Assisted" if self.game.used_bot else "Pure Human"
            score_txt = f"Score: {self.game.score:,} | Max: {self.game.max_tile:,} ({mode_label})"
            t_sc = FONT_SMALL.render(score_txt, True, th['sub_color'])
            self.screen.blit(t_sc, t_sc.get_rect(center=(WIDTH // 2, self.grid_y + GRID_HEIGHT // 2 + 10)))

            t_restart = FONT_SMALL.render("Press 'R' to Restart  |  'U' to Undo", True, th['title_color'])
            self.screen.blit(t_restart, t_restart.get_rect(center=(WIDTH // 2, self.grid_y + GRID_HEIGHT // 2 + 45)))

    def draw_record_modal(self):
        """Renders the New All-Time Record modal overlay with sanitized text input."""
        if not self.record_modal_active:
            return
        th = self.theme

        # Full-screen semi-transparent backdrop
        backdrop = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        backdrop.fill(th['modal_overlay'])
        self.screen.blit(backdrop, (0, 0))

        # Modal card container
        mw, mh = 370, 250
        mx = (WIDTH - mw) // 2
        my = (HEIGHT - mh) // 2
        modal_rect = pygame.Rect(mx, my, mw, mh)
        pygame.draw.rect(self.screen, th['bg'], modal_rect, border_radius=12)
        pygame.draw.rect(self.screen, th['banner_bg'], modal_rect, width=2, border_radius=12)

        # Title & Category
        title_s = FONT_MEDIUM.render("NEW ALL-TIME RECORD!", True, th['title_color'])
        self.screen.blit(title_s, title_s.get_rect(center=(modal_rect.centerx, my + 32)))

        cat_str = "Bot-Assisted Category" if self.modal_record_type == 'bot' else "Pure Human Category"
        cat_col = th['badge_bot'] if self.modal_record_type == 'bot' else th['badge_human']
        cat_s = FONT_TINY.render(cat_str, True, cat_col)
        self.screen.blit(cat_s, cat_s.get_rect(center=(modal_rect.centerx, my + 58)))

        # Score Display
        score_s = FONT_BIG.render(f"{self.modal_record_score:,}", True, th['btn_bot_active'])
        self.screen.blit(score_s, score_s.get_rect(center=(modal_rect.centerx, my + 92)))

        # Instruction
        inst_s = FONT_TINY.render("Enter your name for the high scores board:", True, th['title_color'])
        self.screen.blit(inst_s, inst_s.get_rect(center=(modal_rect.centerx, my + 126)))

        # Input field + Save button row
        inp_x = mx + 24
        inp_y = my + 144
        inp_w = 236
        inp_h = 36
        inp_rect = pygame.Rect(inp_x, inp_y, inp_w, inp_h)
        pygame.draw.rect(self.screen, th['grid_bg'], inp_rect, border_radius=6)
        pygame.draw.rect(self.screen, th['btn_bot_active'], inp_rect, width=2, border_radius=6)

        cursor = "|" if int(time.time() * 2) % 2 == 0 else ""
        if self.modal_input_text:
            inp_txt = FONT_SMALL.render(self.modal_input_text + cursor, True, th['title_color'])
        else:
            placeholder = cursor if cursor else "Your Name"
            col = th['title_color'] if cursor else th['sub_color']
            inp_txt = FONT_SMALL.render(placeholder, True, col)
        self.screen.blit(inp_txt, inp_txt.get_rect(left=inp_rect.left + 10, centery=inp_rect.centery))

        # Save Button
        self.modal_save_rect = pygame.Rect(inp_rect.right + 8, inp_y, 78, inp_h)
        pygame.draw.rect(self.screen, th['btn_bot_active'], self.modal_save_rect, border_radius=6)
        save_s = FONT_SMALL.render("Save", True, SCORE_TEXT_COLOR)
        self.screen.blit(save_s, save_s.get_rect(center=self.modal_save_rect.center))

        # Skip (Anonymous) Button
        self.modal_skip_rect = pygame.Rect(modal_rect.centerx - 80, my + 190, 160, 24)
        skip_s = FONT_TINY.render("Skip (Enter / Esc)", True, th['sub_color'])
        self.screen.blit(skip_s, skip_s.get_rect(center=self.modal_skip_rect.center))

        # Security Note
        sec_s = FONT_MICRO.render("Alphanumeric, spaces, underscores, and hyphens only (max 16 chars).", True, th['sub_color'])
        self.screen.blit(sec_s, sec_s.get_rect(center=(modal_rect.centerx, my + 226)))

    def update_display(self, is_bot_running, speed_mode):
        self.draw_board()
        self.draw_header()
        self.draw_leaderboard_card()
        self.draw_buttons(is_bot_running, speed_mode)
        self.draw_stats_bar()
        self.draw_milestone_banner()
        self.draw_game_over()
        self.draw_record_modal()
        pygame.display.flip()
