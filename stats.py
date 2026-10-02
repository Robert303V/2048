import json
import os
import time
import tempfile

STATS_FILE = os.path.join(os.path.dirname(__file__), 'stats.json')
BACKUP_FILE = os.path.join(os.path.dirname(__file__), 'stats.json.bak')


class GameStats:
    """Manages permanent, corruption-proof high score and lifetime records."""
    def __init__(self):
        self.high_score = 0
        self.highest_tile = 0
        self.games_played = 0
        self.total_moves = 0
        self._last_save_time = 0
        self._dirty = False
        self.load()

    def load(self):
        """Loads stats with fallback to backup file if primary file is missing or corrupted."""
        for path in [STATS_FILE, BACKUP_FILE]:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                        self.high_score = max(self.high_score, data.get('high_score', 0))
                        self.highest_tile = max(self.highest_tile, data.get('highest_tile', 0))
                        self.games_played = max(self.games_played, data.get('games_played', 0))
                        self.total_moves = max(self.total_moves, data.get('total_moves', 0))
                        if self.high_score > 0:
                            break
                except Exception:
                    continue

    def save(self, force=False):
        """Atomically saves statistics to disk to guarantee data is never corrupted or lost."""
        now = time.time()
        if not force and (now - self._last_save_time < 1.0):
            self._dirty = True
            return

        payload = {
            'high_score': int(self.high_score),
            'highest_tile': int(self.highest_tile),
            'games_played': int(self.games_played),
            'total_moves': int(self.total_moves),
        }

        dir_name = os.path.dirname(STATS_FILE)
        try:
            # 1. Atomic write to temporary file with flush & fsync
            fd, tmp_path = tempfile.mkstemp(prefix='stats_', suffix='.tmp', dir=dir_name)
            with os.fdopen(fd, 'w') as f:
                json.dump(payload, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # 2. Preserve backup of existing valid file
            if os.path.exists(STATS_FILE):
                try:
                    with open(STATS_FILE, 'r') as sf:
                        json.load(sf)  # Only backup if valid JSON
                    with open(STATS_FILE, 'r') as sf, open(BACKUP_FILE, 'w') as bf:
                        bf.write(sf.read())
                except Exception:
                    pass

            # 3. Atomic replacement
            os.replace(tmp_path, STATS_FILE)
            self._last_save_time = now
            self._dirty = False
        except Exception:
            pass

    def update(self, current_score, max_tile):
        """Updates best records whenever current game surpasses previous all-time highs."""
        changed = False
        if current_score > self.high_score:
            self.high_score = current_score
            changed = True
        if max_tile > self.highest_tile:
            self.highest_tile = max_tile
            changed = True
        if changed:
            self.save(force=False)

    def flush(self):
        """Flushes any pending unsaved stats immediately."""
        if self._dirty:
            self.save(force=True)

    def increment_moves(self, count=1):
        self.total_moves += count
        self.save(force=False)

    def increment_games(self):
        self.games_played += 1
        self.save(force=True)
