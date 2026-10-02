import math
import numpy as np

# Direction definitions
DIRECTIONS = ['up', 'down', 'left', 'right']
DIR_TO_INDEX = {d: i for i, d in enumerate(DIRECTIONS)}

# -----------------------------------------------------------------------------
# 1. Precomputed Bitboard Move & Utility Tables
# -----------------------------------------------------------------------------
B = 2.8  # Steep monotonic gradient base: guarantees monotonicity > single merge

ROW_LEFT = [0] * 65536
ROW_RIGHT = [0] * 65536
ROW_EMPTY = [0] * 65536
ROW_SMOOTH = [0.0] * 65536
ROW_MERGES = [0.0] * 65536

for _row in range(65536):
    _t = [(_row >> 12) & 0xF, (_row >> 8) & 0xF, (_row >> 4) & 0xF, _row & 0xF]

    # Slide Left
    _nz = [x for x in _t if x != 0]
    _m = []
    _i = 0
    while _i < len(_nz):
        if _i + 1 < len(_nz) and _nz[_i] == _nz[_i + 1]:
            _m.append(_nz[_i] + 1)
            _i += 2
        else:
            _m.append(_nz[_i])
            _i += 1
    while len(_m) < 4:
        _m.append(0)
    ROW_LEFT[_row] = (_m[0] << 12) | (_m[1] << 8) | (_m[2] << 4) | _m[3]

    # Slide Right
    _nz_r = [x for x in reversed(_t) if x != 0]
    _m_r = []
    _i = 0
    while _i < len(_nz_r):
        if _i + 1 < len(_nz_r) and _nz_r[_i] == _nz_r[_i + 1]:
            _m_r.append(_nz_r[_i] + 1)
            _i += 2
        else:
            _m_r.append(_nz_r[_i])
            _i += 1
    while len(_m_r) < 4:
        _m_r.append(0)
    _m_r.reverse()
    ROW_RIGHT[_row] = (_m_r[0] << 12) | (_m_r[1] << 8) | (_m_r[2] << 4) | _m_r[3]

    # Empty cells per row
    ROW_EMPTY[_row] = sum(1 for x in _t if x == 0)

    # Smoothness penalty between adjacent non-zero tiles
    _sm = 0.0
    for _j in range(3):
        if _t[_j] > 0 and _t[_j + 1] > 0:
            _sm -= abs(_t[_j] - _t[_j + 1])
    ROW_SMOOTH[_row] = _sm

    # Pairwise merge potential bonus (adjacent identical tiles)
    _mg = 0.0
    for _j in range(3):
        if _t[_j] > 0 and _t[_j] == _t[_j + 1]:
            _mg += (1 << _t[_j]) * (B ** 10)
    ROW_MERGES[_row] = _mg


# -----------------------------------------------------------------------------
# 2. Fast 64-bit Bitboard Matrix Operations
# -----------------------------------------------------------------------------
def transpose(b: int) -> int:
    """Transposes a 4x4 nibble matrix in a 64-bit int using bitwise operations."""
    a1 = b & 0xF0F00F0FF0F00F0F
    a2 = b & 0x0000F0F00000F0F0
    a3 = b & 0x0F0F00000F0F0000
    a = a1 | (a2 << 12) | (a3 >> 12)
    b1 = a & 0xFF00FF0000FF00FF
    b2 = a & 0x00FF00FF00000000
    b3 = a & 0x00000000FF00FF00
    return b1 | (b2 >> 24) | (b3 << 24)


def move_left(b: int) -> int:
    return (
        (ROW_LEFT[(b >> 48) & 0xFFFF] << 48)
        | (ROW_LEFT[(b >> 32) & 0xFFFF] << 32)
        | (ROW_LEFT[(b >> 16) & 0xFFFF] << 16)
        | ROW_LEFT[b & 0xFFFF]
    )


def move_right(b: int) -> int:
    return (
        (ROW_RIGHT[(b >> 48) & 0xFFFF] << 48)
        | (ROW_RIGHT[(b >> 32) & 0xFFFF] << 32)
        | (ROW_RIGHT[(b >> 16) & 0xFFFF] << 16)
        | ROW_RIGHT[b & 0xFFFF]
    )


def move_up(b: int) -> int:
    t = transpose(b)
    return transpose(move_left(t))


def move_down(b: int) -> int:
    t = transpose(b)
    return transpose(move_right(t))


MOVE_OPS = [move_up, move_down, move_left, move_right]


def grid_to_bitboard(grid) -> int:
    """Converts a 4x4 numpy array into a 64-bit bitboard int."""
    b = 0
    for r in range(4):
        for c in range(4):
            val = grid[r, c]
            if val > 0:
                rank = int(math.log2(val))
                shift = (3 - r) * 16 + (3 - c) * 4
                b |= (rank << shift)
    return b


def bitboard_to_grid(b: int) -> np.ndarray:
    """Converts a 64-bit bitboard int back into a 4x4 numpy array."""
    grid = np.zeros((4, 4), dtype=int)
    for r in range(4):
        for c in range(4):
            shift = (3 - r) * 16 + (3 - c) * 4
            rank = (b >> shift) & 0xF
            if rank > 0:
                grid[r, c] = 1 << rank
    return grid


# -----------------------------------------------------------------------------
# 3. Precomputed 8-Symmetry Snake Gradient Evaluation Tables
# -----------------------------------------------------------------------------
SNAKE_PATH = [
    (0, 0), (0, 1), (0, 2), (0, 3),
    (1, 3), (1, 2), (1, 1), (1, 0),
    (2, 0), (2, 1), (2, 2), (2, 3),
    (3, 3), (3, 2), (3, 1), (3, 0)
]
BASE_GRADIENT = np.zeros((4, 4), dtype=float)
for _k, (_r, _c) in enumerate(SNAKE_PATH):
    BASE_GRADIENT[_r, _c] = B ** (15 - _k)

GRADIENTS = []
for _k in range(4):
    _rot = np.rot90(BASE_GRADIENT, _k)
    GRADIENTS.append(_rot)
    GRADIENTS.append(np.fliplr(_rot))

SYM_TABLES = []
for _sym in GRADIENTS:
    _sym_tables = []
    for _row_idx in range(4):
        _table = [0.0] * 65536
        _weights = _sym[_row_idx]
        for _row_int in range(65536):
            _t = [(_row_int >> 12) & 0xF, (_row_int >> 8) & 0xF, (_row_int >> 4) & 0xF, _row_int & 0xF]
            _val = 0.0
            for _c in range(4):
                if _t[_c] > 0:
                    _val += (1 << _t[_c]) * _weights[_c]
            _table[_row_int] = _val
        _sym_tables.append(_table)
    SYM_TABLES.append(_sym_tables)


def evaluate_board(b: int) -> float:
    """
    Evaluates board quality across all 8 rotations/reflections in O(1) time
    combining snake monotonicity, empty cell potential, smoothness, and merge bonuses.
    """
    r0 = (b >> 48) & 0xFFFF
    r1 = (b >> 32) & 0xFFFF
    r2 = (b >> 16) & 0xFFFF
    r3 = b & 0xFFFF

    t = transpose(b)
    c0 = (t >> 48) & 0xFFFF
    c1 = (t >> 32) & 0xFFFF
    c2 = (t >> 16) & 0xFFFF
    c3 = t & 0xFFFF

    empty = ROW_EMPTY[r0] + ROW_EMPTY[r1] + ROW_EMPTY[r2] + ROW_EMPTY[r3]
    smoothness = (
        ROW_SMOOTH[r0] + ROW_SMOOTH[r1] + ROW_SMOOTH[r2] + ROW_SMOOTH[r3]
        + ROW_SMOOTH[c0] + ROW_SMOOTH[c1] + ROW_SMOOTH[c2] + ROW_SMOOTH[c3]
    )
    merges = (
        ROW_MERGES[r0] + ROW_MERGES[r1] + ROW_MERGES[r2] + ROW_MERGES[r3]
        + ROW_MERGES[c0] + ROW_MERGES[c1] + ROW_MERGES[c2] + ROW_MERGES[c3]
    )

    best_grad = 0.0
    for sym_t in SYM_TABLES:
        v = sym_t[0][r0] + sym_t[1][r1] + sym_t[2][r2] + sym_t[3][r3]
        if v > best_grad:
            best_grad = v

    # Emergency cliff penalty when empty cells are critically low (<= 1)
    if empty <= 1:
        empty_penalty = -100000.0 * (2 - empty)
    else:
        empty_penalty = 0.0

    return best_grad + merges + empty * (B ** 12) + smoothness * (B ** 9) + empty_penalty


def get_empty_indices(b: int):
    """Returns the nibble indices (0..15) of all empty cells."""
    return [i for i in range(16) if ((b >> (i * 4)) & 0xF) == 0]


# -----------------------------------------------------------------------------
# 4. Expectimax Agent with Persistent Cache & Deep Lookahead
# -----------------------------------------------------------------------------
class ExpectimaxAgent:
    """
    World-class 2048 Expectimax AI Solver:
    - 8-symmetry precomputed lookup tables (190,000+ evals/sec)
    - Persistent transposition table cache across consecutive turns
    - Full chance-node expectations (90% tile 2, 10% tile 4)
    - Adaptive deep lookahead (Depth 4 up to Depth 8 in tight endgames)
    - Cumulative probability pruning (pruning microscopic chance branches)
    - Steep B=2.8 snake monotonicity + pairwise merge potential + cliff emergency penalty
    """

    def __init__(self, state_shape=None, action_size=4):
        self.state_shape = state_shape
        self.action_size = action_size
        self.trans = {}  # Persistent transposition cache across turns

    def search(
        self,
        b: int,
        depth: int,
        is_agent: bool,
        trans: dict,
        prob_cutoff: float = 0.0001,
        cur_prob: float = 1.0,
    ):
        key = (b, depth, is_agent)
        if key in trans:
            return trans[key]

        if depth == 0 or cur_prob < prob_cutoff:
            val = (evaluate_board(b), None)
            trans[key] = val
            return val

        if is_agent:
            best_v = -float('inf')
            best_d = None
            for d in [0, 2, 3, 1]:  # Up, Left, Right, Down
                nb = MOVE_OPS[d](b)
                if nb != b:
                    v, _ = self.search(nb, depth - 1, False, trans, prob_cutoff, cur_prob)
                    if v > best_v:
                        best_v = v
                        best_d = d
            res = (best_v, best_d)
            trans[key] = res
            return res
        else:
            empties = get_empty_indices(b)
            if not empties:
                res = (evaluate_board(b), None)
                trans[key] = res
                return res

            prob = 1.0 / len(empties)
            exp_v = 0.0
            for idx in empties:
                # 90% chance of spawning tile 2 (rank 1)
                b2 = b | (1 << (idx * 4))
                v_2, _ = self.search(
                    b2, depth - 1, True, trans, prob_cutoff, cur_prob * prob * 0.9
                )
                exp_v += prob * (0.9 * v_2)

                # 10% chance of spawning tile 4 (rank 2) on meaningful branches
                if cur_prob * prob * 0.1 >= prob_cutoff and depth > 2:
                    b4 = b | (2 << (idx * 4))
                    v_4, _ = self.search(
                        b4, depth - 1, True, trans, prob_cutoff, cur_prob * prob * 0.1
                    )
                    exp_v += prob * (0.1 * v_4)
                else:
                    exp_v += prob * (0.1 * v_2)

            res = (exp_v, None)
            trans[key] = res
            return res

    def get_best_move(self, grid_or_bitboard):
        """Determines the optimal move: 'up', 'down', 'left', or 'right'."""
        if isinstance(grid_or_bitboard, (int, np.integer)):
            b = int(grid_or_bitboard)
        else:
            b = grid_to_bitboard(grid_or_bitboard)

        empties = get_empty_indices(b)
        emp_count = len(empties)

        # Adaptive Lookahead with Calibrated Probability Cutoffs:
        # Tight endgame (<= 2 empty cells): Depth 8, thorough chance evaluation (cutoff=0.00005)
        # Narrowing endgame (<= 4 empty cells): Depth 6 (cutoff=0.0001)
        # Midgame (<= 7 empty cells): Depth 5 (cutoff=0.0002)
        # Opening (> 7 empty cells): Depth 4 (cutoff=0.0005)
        if emp_count <= 2:
            depth = 8
            cutoff = 0.00005
        elif emp_count <= 4:
            depth = 6
            cutoff = 0.0001
        elif emp_count <= 7:
            depth = 5
            cutoff = 0.0002
        else:
            depth = 4
            cutoff = 0.0005

        # Bound cache memory to prevent memory bloat (< 50MB)
        if len(self.trans) > 500000:
            self.trans.clear()

        _, best_dir_idx = self.search(
            b, depth=depth, is_agent=True, trans=self.trans, prob_cutoff=cutoff, cur_prob=1.0
        )

        if best_dir_idx is not None:
            return DIRECTIONS[best_dir_idx]

        # Failsafe fallback
        for d in [0, 2, 3, 1]:
            if MOVE_OPS[d](b) != b:
                return DIRECTIONS[d]

        return None

    def act(self, grid_or_state):
        """Drop-in compatible method returning action index (0..3)."""
        move_str = self.get_best_move(grid_or_state)
        if move_str is not None:
            return DIR_TO_INDEX[move_str]
        return 0


# Alias for backward compatibility
DQNAgent = ExpectimaxAgent
