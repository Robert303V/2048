// 2048 Game Engine for Web Deployment
// Manages board state, moves, undo history, transitions, and permanent high score

class GameEngine {
    constructor() {
        this.size = 4;
        this.history = [];
        this.highScore = parseInt(localStorage.getItem('2048_high_score') || '61356', 10);
        this.gamesPlayed = parseInt(localStorage.getItem('2048_games_played') || '13', 10);
        this.reset(false);
    }

    reset(incrementGames = true) {
        this.grid = [
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0]
        ];
        this.score = 0;
        this.moves = 0;
        this.gameOver = false;
        this.lastMove = null;
        this.history = [];
        this.milestones = new Set();
        this.justMilestone = null;

        if (incrementGames) {
            this.gamesPlayed++;
            localStorage.setItem('2048_games_played', this.gamesPlayed);
        }

        this.addNewTile();
        this.addNewTile();
    }

    getEmptyCells() {
        const cells = [];
        for (let r = 0; r < this.size; r++) {
            for (let c = 0; c < this.size; c++) {
                if (this.grid[r][c] === 0) cells.push({ r, c });
            }
        }
        return cells;
    }

    addNewTile() {
        const empty = this.getEmptyCells();
        if (empty.length > 0) {
            const spot = empty[Math.floor(Math.random() * empty.length)];
            const val = Math.random() < 0.9 ? 2 : 4;
            this.grid[spot.r][spot.c] = val;
            return { r: spot.r, c: spot.c, val };
        }
        return null;
    }

    computeTransitions(direction) {
        const transitions = [];
        if (direction === 'left') {
            for (let r = 0; r < 4; r++) {
                const tiles = [];
                for (let c = 0; c < 4; c++) if (this.grid[r][c] !== 0) tiles.push({ c, val: this.grid[r][c] });
                let target = 0, i = 0;
                while (i < tiles.length) {
                    if (i + 1 < tiles.length && tiles[i].val === tiles[i + 1].val) {
                        transitions.push({ from: { r, c: tiles[i].c }, to: { r, c: target }, val: tiles[i].val, merged: true });
                        transitions.push({ from: { r, c: tiles[i + 1].c }, to: { r, c: target }, val: tiles[i + 1].val, merged: true });
                        target++;
                        i += 2;
                    } else {
                        transitions.push({ from: { r, c: tiles[i].c }, to: { r, c: target }, val: tiles[i].val, merged: false });
                        target++;
                        i++;
                    }
                }
            }
        } else if (direction === 'right') {
            for (let r = 0; r < 4; r++) {
                const tiles = [];
                for (let c = 3; c >= 0; c--) if (this.grid[r][c] !== 0) tiles.push({ c, val: this.grid[r][c] });
                let target = 3, i = 0;
                while (i < tiles.length) {
                    if (i + 1 < tiles.length && tiles[i].val === tiles[i + 1].val) {
                        transitions.push({ from: { r, c: tiles[i].c }, to: { r, c: target }, val: tiles[i].val, merged: true });
                        transitions.push({ from: { r, c: tiles[i + 1].c }, to: { r, c: target }, val: tiles[i + 1].val, merged: true });
                        target--;
                        i += 2;
                    } else {
                        transitions.push({ from: { r, c: tiles[i].c }, to: { r, c: target }, val: tiles[i].val, merged: false });
                        target--;
                        i++;
                    }
                }
            }
        } else if (direction === 'up') {
            for (let c = 0; c < 4; c++) {
                const tiles = [];
                for (let r = 0; r < 4; r++) if (this.grid[r][c] !== 0) tiles.push({ r, val: this.grid[r][c] });
                let target = 0, i = 0;
                while (i < tiles.length) {
                    if (i + 1 < tiles.length && tiles[i].val === tiles[i + 1].val) {
                        transitions.push({ from: { r: tiles[i].r, c }, to: { r: target, c }, val: tiles[i].val, merged: true });
                        transitions.push({ from: { r: tiles[i + 1].r, c }, to: { r: target, c }, val: tiles[i + 1].val, merged: true });
                        target++;
                        i += 2;
                    } else {
                        transitions.push({ from: { r: tiles[i].r, c }, to: { r: target, c }, val: tiles[i].val, merged: false });
                        target++;
                        i++;
                    }
                }
            }
        } else if (direction === 'down') {
            for (let c = 0; c < 4; c++) {
                const tiles = [];
                for (let r = 3; r >= 0; r--) if (this.grid[r][c] !== 0) tiles.push({ r, val: this.grid[r][c] });
                let target = 3, i = 0;
                while (i < tiles.length) {
                    if (i + 1 < tiles.length && tiles[i].val === tiles[i + 1].val) {
                        transitions.push({ from: { r: tiles[i].r, c }, to: { r: target, c }, val: tiles[i].val, merged: true });
                        transitions.push({ from: { r: tiles[i + 1].r, c }, to: { r: target, c }, val: tiles[i + 1].val, merged: true });
                        target--;
                        i += 2;
                    } else {
                        transitions.push({ from: { r: tiles[i].r, c }, to: { r: target, c }, val: tiles[i].val, merged: false });
                        target--;
                        i++;
                    }
                }
            }
        }
        return transitions;
    }

    move(direction) {
        if (this.gameOver) return { moved: false };

        const transitions = this.computeTransitions(direction);
        const originalGrid = this.grid.map(row => [...row]);
        const originalScore = this.score;
        const originalMoves = this.moves;
        const originalLastMove = this.lastMove;
        const originalMilestones = new Set(this.milestones);

        // Apply slide & merge to a line
        const slideLine = (line) => {
            const nonZero = line.filter(v => v !== 0);
            const res = [];
            let scoreGain = 0;
            let highestMerge = 0;
            let i = 0;
            while (i < nonZero.length) {
                if (i + 1 < nonZero.length && nonZero[i] === nonZero[i + 1]) {
                    const mergedVal = nonZero[i] * 2;
                    res.push(mergedVal);
                    scoreGain += mergedVal;
                    if (mergedVal > highestMerge) highestMerge = mergedVal;
                    i += 2;
                } else {
                    res.push(nonZero[i]);
                    i++;
                }
            }
            while (res.length < 4) res.push(0);
            return { res, scoreGain, highestMerge };
        };

        let moveScore = 0;
        let highestMerged = 0;
        const nextGrid = [
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0]
        ];

        if (direction === 'left') {
            for (let r = 0; r < 4; r++) {
                const { res, scoreGain, highestMerge } = slideLine(this.grid[r]);
                nextGrid[r] = res;
                moveScore += scoreGain;
                if (highestMerge > highestMerged) highestMerged = highestMerge;
            }
        } else if (direction === 'right') {
            for (let r = 0; r < 4; r++) {
                const reversed = [...this.grid[r]].reverse();
                const { res, scoreGain, highestMerge } = slideLine(reversed);
                nextGrid[r] = res.reverse();
                moveScore += scoreGain;
                if (highestMerge > highestMerged) highestMerged = highestMerge;
            }
        } else if (direction === 'up') {
            for (let c = 0; c < 4; c++) {
                const col = [this.grid[0][c], this.grid[1][c], this.grid[2][c], this.grid[3][c]];
                const { res, scoreGain, highestMerge } = slideLine(col);
                for (let r = 0; r < 4; r++) nextGrid[r][c] = res[r];
                moveScore += scoreGain;
                if (highestMerge > highestMerged) highestMerged = highestMerge;
            }
        } else if (direction === 'down') {
            for (let c = 0; c < 4; c++) {
                const col = [this.grid[3][c], this.grid[2][c], this.grid[1][c], this.grid[0][c]];
                const { res, scoreGain, highestMerge } = slideLine(col);
                res.reverse();
                for (let r = 0; r < 4; r++) nextGrid[r][c] = res[r];
                moveScore += scoreGain;
                if (highestMerge > highestMerged) highestMerged = highestMerge;
            }
        } else {
            return { moved: false };
        }

        // Check if board changed
        let changed = false;
        for (let r = 0; r < 4; r++) {
            for (let c = 0; c < 4; c++) {
                if (this.grid[r][c] !== nextGrid[r][c]) {
                    changed = true;
                    break;
                }
            }
        }

        if (!changed) return { moved: false };

        // Save history for undo
        this.history.push({
            grid: originalGrid,
            score: originalScore,
            moves: originalMoves,
            lastMove: originalLastMove,
            milestones: originalMilestones
        });
        if (this.history.length > 60) this.history.shift();

        this.grid = nextGrid;
        this.score += moveScore;
        this.moves++;
        this.lastMove = direction;

        // Check and persist permanent high score
        if (this.score > this.highScore) {
            this.highScore = this.score;
            localStorage.setItem('2048_high_score', this.highScore);
        }

        const spawned = this.addNewTile();

        // Check milestones
        this.justMilestone = null;
        const currentMax = this.getMaxTile();
        for (const m of [2048, 4096, 8192, 16384]) {
            if (currentMax >= m && !this.milestones.has(m)) {
                this.milestones.add(m);
                this.justMilestone = m;
            }
        }

        if (!this.canMove()) {
            this.gameOver = true;
        }

        return {
            moved: true,
            transitions,
            spawn: spawned,
            highestMerged,
            justMilestone: this.justMilestone
        };
    }

    undo() {
        if (this.history.length === 0) return false;
        const prev = this.history.pop();
        this.grid = prev.grid;
        this.score = prev.score;
        this.moves = prev.moves;
        this.lastMove = prev.lastMove;
        this.milestones = prev.milestones;
        this.gameOver = false;
        this.justMilestone = null;
        return true;
    }

    canMove() {
        if (this.getEmptyCells().length > 0) return true;
        for (let r = 0; r < 4; r++) {
            for (let c = 0; c < 4; c++) {
                if (c + 1 < 4 && this.grid[r][c] === this.grid[r][c + 1]) return true;
                if (r + 1 < 4 && this.grid[r][c] === this.grid[r + 1][c]) return true;
            }
        }
        return false;
    }

    getMaxTile() {
        let max = 0;
        for (let r = 0; r < 4; r++) {
            for (let c = 0; c < 4; c++) {
                if (this.grid[r][c] > max) max = this.grid[r][c];
            }
        }
        return max;
    }
}

window.GameEngine = GameEngine;
