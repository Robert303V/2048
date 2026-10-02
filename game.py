import numpy as np
import random


def compute_transitions(grid, direction):
    """
    Computes precise tile trajectory coordinates for smooth slide animations.
    Returns a list of dicts: {'from': (r, c), 'to': (r, c), 'val': int, 'merged': bool}
    """
    transitions = []
    if direction == 'left':
        for r in range(4):
            tiles = [(c, int(grid[r, c])) for c in range(4) if grid[r, c] != 0]
            target = 0
            i = 0
            while i < len(tiles):
                if i + 1 < len(tiles) and tiles[i][1] == tiles[i + 1][1]:
                    transitions.append({'from': (r, tiles[i][0]), 'to': (r, target), 'val': tiles[i][1], 'merged': True})
                    transitions.append({'from': (r, tiles[i + 1][0]), 'to': (r, target), 'val': tiles[i + 1][1], 'merged': True})
                    target += 1
                    i += 2
                else:
                    transitions.append({'from': (r, tiles[i][0]), 'to': (r, target), 'val': tiles[i][1], 'merged': False})
                    target += 1
                    i += 1
    elif direction == 'right':
        for r in range(4):
            tiles = [(c, int(grid[r, c])) for c in range(3, -1, -1) if grid[r, c] != 0]
            target = 3
            i = 0
            while i < len(tiles):
                if i + 1 < len(tiles) and tiles[i][1] == tiles[i + 1][1]:
                    transitions.append({'from': (r, tiles[i][0]), 'to': (r, target), 'val': tiles[i][1], 'merged': True})
                    transitions.append({'from': (r, tiles[i + 1][0]), 'to': (r, target), 'val': tiles[i + 1][1], 'merged': True})
                    target -= 1
                    i += 2
                else:
                    transitions.append({'from': (r, tiles[i][0]), 'to': (r, target), 'val': tiles[i][1], 'merged': False})
                    target -= 1
                    i += 1
    elif direction == 'up':
        for c in range(4):
            tiles = [(r, int(grid[r, c])) for r in range(4) if grid[r, c] != 0]
            target = 0
            i = 0
            while i < len(tiles):
                if i + 1 < len(tiles) and tiles[i][1] == tiles[i + 1][1]:
                    transitions.append({'from': (tiles[i][0], c), 'to': (target, c), 'val': tiles[i][1], 'merged': True})
                    transitions.append({'from': (tiles[i + 1][0], c), 'to': (target, c), 'val': tiles[i + 1][1], 'merged': True})
                    target += 1
                    i += 2
                else:
                    transitions.append({'from': (tiles[i][0], c), 'to': (target, c), 'val': tiles[i][1], 'merged': False})
                    target += 1
                    i += 1
    elif direction == 'down':
        for c in range(4):
            tiles = [(r, int(grid[r, c])) for r in range(3, -1, -1) if grid[r, c] != 0]
            target = 3
            i = 0
            while i < len(tiles):
                if i + 1 < len(tiles) and tiles[i][1] == tiles[i + 1][1]:
                    transitions.append({'from': (tiles[i][0], c), 'to': (target, c), 'val': tiles[i][1], 'merged': True})
                    transitions.append({'from': (tiles[i + 1][0], c), 'to': (target, c), 'val': tiles[i + 1][1], 'merged': True})
                    target -= 1
                    i += 2
                else:
                    transitions.append({'from': (tiles[i][0], c), 'to': (target, c), 'val': tiles[i][1], 'merged': False})
                    target -= 1
                    i += 1
    return transitions


class GameBoard:
    def __init__(self):
        self.grid_size = 4
        self.win_tile = 2048
        self.reset()

    def reset(self):
        self.grid = np.zeros((self.grid_size, self.grid_size), dtype=int)
        self.score = 0
        self.moves = 0
        self.game_over = False
        self.last_move = None
        self.history = []
        self.milestones_reached = set()
        self.just_unlocked_milestone = None
        self.highest_tile_merged = 0
        self.last_transitions = []
        self.last_spawn = None
        self.add_new_tile()
        self.add_new_tile()

    def add_new_tile(self):
        empty_cells = self.get_empty_cells()
        if empty_cells:
            row, col = random.choice(empty_cells)
            val = 2 if random.random() < 0.9 else 4
            self.grid[row, col] = val
            self.last_spawn = (row, col, val)

    def get_empty_cells(self):
        return list(zip(*np.where(self.grid == 0)))

    def _slide_and_merge_row(self, row):
        new_row = [i for i in row if i != 0]
        score_add = 0
        highest_merged = 0
        # Merge
        for i in range(len(new_row) - 1):
            if new_row[i] != 0 and new_row[i] == new_row[i + 1]:
                new_row[i] *= 2
                score_add += new_row[i]
                if new_row[i] > highest_merged:
                    highest_merged = new_row[i]
                new_row[i + 1] = 0
        # Slide again
        new_row = [i for i in new_row if i != 0]
        # Pad with zeros
        new_row += [0] * (self.grid_size - len(new_row))
        return new_row, score_add, highest_merged

    def move(self, direction):
        if self.game_over:
            return False

        original_grid = self.grid.copy()
        original_score = self.score
        original_moves = self.moves
        original_last_move = self.last_move
        original_milestones = set(self.milestones_reached)

        move_made = False
        move_score = 0
        max_merged = 0
        self.just_unlocked_milestone = None
        self.highest_tile_merged = 0

        # Calculate exact tile transitions for smooth visual sliding
        transitions = compute_transitions(self.grid, direction)

        if direction == 'up':
            rotated_grid = np.rot90(self.grid)
            new_grid = []
            for row in rotated_grid:
                new_row, score_add, m_merged = self._slide_and_merge_row(row)
                new_grid.append(new_row)
                move_score += score_add
                if m_merged > max_merged: max_merged = m_merged
            self.grid = np.rot90(np.array(new_grid), k=-1)

        elif direction == 'down':
            rotated_grid = np.rot90(self.grid, k=-1)
            new_grid = []
            for row in rotated_grid:
                new_row, score_add, m_merged = self._slide_and_merge_row(row)
                new_grid.append(new_row)
                move_score += score_add
                if m_merged > max_merged: max_merged = m_merged
            self.grid = np.rot90(np.array(new_grid))

        elif direction == 'left':
            new_grid = []
            for row in self.grid:
                new_row, score_add, m_merged = self._slide_and_merge_row(row)
                new_grid.append(new_row)
                move_score += score_add
                if m_merged > max_merged: max_merged = m_merged
            self.grid = np.array(new_grid)

        elif direction == 'right':
            reversed_grid = np.fliplr(self.grid)
            new_grid = []
            for row in reversed_grid:
                new_row, score_add, m_merged = self._slide_and_merge_row(row)
                new_grid.append(new_row)
                move_score += score_add
                if m_merged > max_merged: max_merged = m_merged
            self.grid = np.fliplr(np.array(new_grid))

        else:
            return False

        if not np.array_equal(original_grid, self.grid):
            # Save history for undo
            self.history.append((original_grid, original_score, original_moves, original_last_move, original_milestones))
            if len(self.history) > 60:
                self.history.pop(0)

            self.add_new_tile()
            self.score += move_score
            self.moves += 1
            self.last_move = direction
            self.highest_tile_merged = max_merged
            self.last_transitions = transitions
            move_made = True

            # Check milestones (2048, 4096, 8192, 16384)
            current_max = np.max(self.grid)
            for m in [2048, 4096, 8192, 16384]:
                if current_max >= m and m not in self.milestones_reached:
                    self.milestones_reached.add(m)
                    self.just_unlocked_milestone = m
        else:
            self.last_transitions = []

        if not self.can_move():
            self.game_over = True

        return move_made

    def undo(self):
        """Restores the previous board state, score, and moves."""
        if not self.history:
            return False
        prev_grid, prev_score, prev_moves, prev_last_move, prev_milestones = self.history.pop()
        self.grid = prev_grid
        self.score = prev_score
        self.moves = prev_moves
        self.last_move = prev_last_move
        self.milestones_reached = prev_milestones
        self.game_over = False
        self.just_unlocked_milestone = None
        self.highest_tile_merged = 0
        self.last_transitions = []
        self.last_spawn = None
        return True

    def can_move(self):
        if self.get_empty_cells():
            return True
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                if c + 1 < self.grid_size and self.grid[r, c] == self.grid[r, c + 1]:
                    return True
                if r + 1 < self.grid_size and self.grid[r, c] == self.grid[r + 1, c]:
                    return True
        return False

    def is_game_over(self):
        return self.game_over

    def get_state(self):
        return self.grid

    @property
    def max_tile(self):
        return int(np.max(self.grid))
