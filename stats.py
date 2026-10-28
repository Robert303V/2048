import json
import os
import time
import tempfile
import re

STATS_FILE = os.path.join(os.path.dirname(__file__), 'stats.json')
BACKUP_FILE = os.path.join(os.path.dirname(__file__), 'stats.json.bak')


def sanitize_name(input_str, default="Player"):
    """Strictly sanitizes player name: alphanumeric, spaces, underscores, hyphens only. Max 16 chars."""
    if not isinstance(input_str, str):
        return default
    # Remove control chars and non-printable unicode
    clean = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', input_str)
    # Whitelist characters
    clean = re.sub(r'[^a-zA-Z0-9 _-]', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    clean = clean[:16]
    return clean if clean else default


class GameStats:
    """
    Manages permanent high score records across 4 categories:
    1. Session Best (Bot / Assisted)
    2. Session Best (Human Only)
    3. All-Time Record (Bot / Assisted) + Player Name
    4. All-Time Record (Human Only) + Player Name
    """
    def __init__(self):
        # 1. Session Bests
        self.session_human_score = 0
        self.session_bot_score = 0

        # 2. All-Time Records
        self.all_time_human_score = 18440
        self.all_time_human_name = "Grandmaster"
        self.all_time_bot_score = 61356
        self.all_time_bot_name = "Expectimax Bot"

        # General records
        self.highest_tile = 4096
        self.games_played = 0
        self.total_moves = 0

        self._last_save_time = 0
        self._dirty = False
        self.last_celebration = None
        self.load()
        self.start_new_run()

    def start_new_run(self):
        """Snapshots the all-time records at the start of a run for mid-game celebration and end-of-game modal checks."""
        self.initial_human_best = self.all_time_human_score
        self.initial_bot_best = self.all_time_bot_score
        self.passed_human_celebrated = False
        self.passed_bot_celebrated = False
        self.last_celebration = None

    def on_bot_used(self, current_score=0):
        """Handles mid-run transition from Pure Human to Bot-Assisted mode."""
        if self.all_time_human_score > self.initial_human_best:
            self.all_time_human_score = self.initial_human_best
        if current_score > self.session_bot_score:
            self.session_bot_score = current_score
        if current_score > self.all_time_bot_score:
            self.all_time_bot_score = current_score
        self.save(force=False)

    @property
    def high_score(self):
        return max(self.all_time_bot_score, self.all_time_human_score)

    def load(self):
        """Loads records with fallback to backup file if primary file is corrupted."""
        for path in [STATS_FILE, BACKUP_FILE]:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                        self.all_time_bot_score = max(self.all_time_bot_score, data.get('all_time_bot_score', data.get('high_score', 61356)))
                        self.all_time_bot_name = sanitize_name(data.get('all_time_bot_name', 'Expectimax Bot'), 'Expectimax Bot')

                        self.all_time_human_score = max(self.all_time_human_score, data.get('all_time_human_score', 18440))
                        self.all_time_human_name = sanitize_name(data.get('all_time_human_name', 'Grandmaster'), 'Grandmaster')

                        self.highest_tile = max(self.highest_tile, data.get('highest_tile', 4096))
                        self.games_played = max(self.games_played, data.get('games_played', 0))
                        self.total_moves = max(self.total_moves, data.get('total_moves', 0))
                        break
                except Exception:
                    continue

    def save(self, force=False):
        """Atomically saves stats to disk with tempfile swap and dual backup."""
        now = time.time()
        if not force and (now - self._last_save_time < 1.0):
            self._dirty = True
            return

        payload = {
            'all_time_bot_score': int(self.all_time_bot_score),
            'all_time_bot_name': self.all_time_bot_name,
            'all_time_human_score': int(self.all_time_human_score),
            'all_time_human_name': self.all_time_human_name,
            'high_score': int(self.high_score),
            'highest_tile': int(self.highest_tile),
            'games_played': int(self.games_played),
            'total_moves': int(self.total_moves),
        }

        dir_name = os.path.dirname(STATS_FILE)
        try:
            fd, tmp_path = tempfile.mkstemp(prefix='stats_', suffix='.tmp', dir=dir_name)
            with os.fdopen(fd, 'w') as f:
                json.dump(payload, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            if os.path.exists(STATS_FILE):
                try:
                    with open(STATS_FILE, 'r') as sf:
                        json.load(sf)
                    with open(STATS_FILE, 'r') as sf, open(BACKUP_FILE, 'w') as bf:
                        bf.write(sf.read())
                except Exception:
                    pass

            os.replace(tmp_path, STATS_FILE)
            self._last_save_time = now
            self._dirty = False
        except Exception:
            pass

    def update(self, current_score, max_tile, used_bot, record_prompt_shown=True, player_name=None, is_game_over=False):
        """
        Updates score across appropriate session and all-time categories.
        Sets self.last_celebration when a high-score threshold is crossed mid-run without stopping play.
        Returns a record_break dict ONLY at the end of the run (when is_game_over is True and record_prompt_shown is False).
        """
        changed = False
        record_break = None
        self.last_celebration = None

        if used_bot:
            if current_score > self.session_bot_score:
                self.session_bot_score = current_score
            if current_score > self.all_time_bot_score:
                self.all_time_bot_score = current_score
                if player_name:
                    self.all_time_bot_name = sanitize_name(player_name, "Bot Master")
                changed = True

            if not self.passed_human_celebrated and current_score > self.initial_human_best:
                self.passed_human_celebrated = True
                self.last_celebration = {
                    'type': 'passed_human',
                    'score': current_score,
                    'prev_best': self.initial_human_best,
                    'prev_name': self.all_time_human_name,
                    'banner': f"🔥 Passed Human High Score ({self.initial_human_best:,})!",
                }

            if not self.passed_bot_celebrated and current_score > self.initial_bot_best:
                self.passed_bot_celebrated = True
                self.last_celebration = {
                    'type': 'new_bot_record',
                    'score': current_score,
                    'prev_best': self.initial_bot_best,
                    'prev_name': self.all_time_bot_name,
                    'banner': "🏆 NEW ALL-TIME BOT RECORD!",
                }

            if is_game_over and not record_prompt_shown and current_score > self.initial_bot_best:
                record_break = {
                    'type': 'bot',
                    'score': current_score,
                    'prev_best': self.initial_bot_best,
                    'prev_name': self.all_time_bot_name,
                }
        else:
            if current_score > self.session_human_score:
                self.session_human_score = current_score
            if current_score > self.all_time_human_score:
                self.all_time_human_score = current_score
                if player_name:
                    self.all_time_human_name = sanitize_name(player_name, "Champion")
                changed = True

            if not self.passed_human_celebrated and current_score > self.initial_human_best:
                self.passed_human_celebrated = True
                self.last_celebration = {
                    'type': 'new_human_record',
                    'score': current_score,
                    'prev_best': self.initial_human_best,
                    'prev_name': self.all_time_human_name,
                    'banner': "🏆 NEW HUMAN HIGH SCORE!",
                }

            if not self.passed_bot_celebrated and current_score > self.initial_bot_best:
                self.passed_bot_celebrated = True
                self.last_celebration = {
                    'type': 'passed_overall',
                    'score': current_score,
                    'prev_best': self.initial_bot_best,
                    'prev_name': self.all_time_bot_name,
                    'banner': "👑 NEW OVERALL ALL-TIME RECORD!",
                }

            if is_game_over and not record_prompt_shown and current_score > self.initial_human_best:
                record_break = {
                    'type': 'human',
                    'score': current_score,
                    'prev_best': self.initial_human_best,
                    'prev_name': self.all_time_human_name,
                }

        if max_tile > self.highest_tile:
            self.highest_tile = max_tile
            changed = True

        if changed or record_break:
            self.save(force=bool(record_break or is_game_over))

        return record_break

    def set_record_holder(self, record_type, raw_name):
        """Sets and persists the sanitized player name for an all-time record."""
        if record_type == 'bot':
            self.all_time_bot_name = sanitize_name(raw_name, "Bot Master")
        else:
            self.all_time_human_name = sanitize_name(raw_name, "Champion")
        self.save(force=True)

    def flush(self):
        if self._dirty:
            self.save(force=True)

    def increment_moves(self, count=1):
        self.total_moves += count
        self.save(force=False)

    def increment_games(self):
        self.games_played += 1
        self.save(force=True)
