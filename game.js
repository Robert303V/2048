// 2048 Game Engine for Web Deployment
// Features 4 High Score Categories, Bot Usage Tracking, and Sanitized Global Records

function sanitizePlayerName(input, defaultName = 'Player') {
    if (typeof input !== 'string') return defaultName;
    // 1. Remove all control characters, null bytes, and unicode direction overrides
    let clean = input.replace(/[\u0000-\u001F\u007F-\u009F\u200B-\u200F\u2028-\u202E\uFEFF]/g, '');
    // 2. Strictly whitelist alphanumeric, spaces, underscores, and hyphens only (blocks <, >, ', ", /, etc.)
    clean = clean.replace(/[^a-zA-Z0-9 _-]/g, '');
    // 3. Collapse multiple whitespace and trim
    clean = clean.replace(/\s+/g, ' ').trim();
    // 4. Strict length limit (max 16 characters)
    clean = clean.substring(0, 16);
    return clean.length > 0 ? clean : defaultName;
}

const GLOBAL_KV_BUCKET = '2048_master_v1_records';
const GLOBAL_API_BASE = `https://kvdb.io/`;

class GameEngine {
    constructor() {
        this.size = 4;
        this.history = [];

        // 1. Session Bests (Initialized to 0 per session)
        this.sessionHumanBest = 0;
        this.sessionBotBest = 0;

        // 2. All-Time Global Bests (Persisted locally & synced globally)
        this.allTimeHumanBest = parseInt(localStorage.getItem('2048_alltime_human_score') || '18440', 10);
        this.allTimeHumanName = sanitizePlayerName(localStorage.getItem('2048_alltime_human_name') || 'Grandmaster', 'Grandmaster');

        this.allTimeBotBest = parseInt(localStorage.getItem('2048_alltime_bot_score') || '61356', 10);
        this.allTimeBotName = sanitizePlayerName(localStorage.getItem('2048_alltime_bot_name') || 'Expectimax Bot', 'Expectimax Bot');

        this.gamesPlayed = parseInt(localStorage.getItem('2048_games_played') || '13', 10);

        this.usedBotInGame = false;
        this.recordPromptShownForCurrentGame = false;

        this.reset(false);
        this.syncGlobalScores();
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
        this.usedBotInGame = false;
        this.recordPromptShownForCurrentGame = false;

        // Baseline thresholds at the start of the run
        this.initialHumanBest = this.allTimeHumanBest;
        this.initialBotBest = this.allTimeBotBest;
        this.passedHumanBestCelebrated = false;
        this.passedBotBestCelebrated = false;

        if (incrementGames) {
            this.gamesPlayed++;
            localStorage.setItem('2048_games_played', this.gamesPlayed);
        }

        this.addNewTile();
        this.addNewTile();
    }

    markBotUsed() {
        if (!this.usedBotInGame) {
            this.usedBotInGame = true;
            // If this run had temporarily raised allTimeHumanBest before switching to Bot, restore baseline human best
            if (this.allTimeHumanBest > this.initialHumanBest) {
                this.allTimeHumanBest = this.initialHumanBest;
                localStorage.setItem('2048_alltime_human_score', this.allTimeHumanBest);
            }
            if (this.score > this.sessionBotBest) {
                this.sessionBotBest = this.score;
            }
        }
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
        const originalUsedBot = this.usedBotInGame;
        const originalPassedHuman = this.passedHumanBestCelebrated;
        const originalPassedBot = this.passedBotBestCelebrated;

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
            milestones: originalMilestones,
            usedBot: originalUsedBot,
            passedHuman: originalPassedHuman,
            passedBot: originalPassedBot,
            recordPromptShown: this.recordPromptShownForCurrentGame
        });
        if (this.history.length > 60) this.history.shift();

        this.grid = nextGrid;
        this.score += moveScore;
        this.moves++;
        this.lastMove = direction;

        // Update Session Bests & Live All-Time Scores
        if (this.usedBotInGame) {
            if (this.score > this.sessionBotBest) {
                this.sessionBotBest = this.score;
            }
            if (this.score > this.allTimeBotBest) {
                this.allTimeBotBest = this.score;
                localStorage.setItem('2048_alltime_bot_score', this.allTimeBotBest);
            }
        } else {
            if (this.score > this.sessionHumanBest) {
                this.sessionHumanBest = this.score;
            }
            if (this.score > this.allTimeHumanBest) {
                this.allTimeHumanBest = this.score;
                localStorage.setItem('2048_alltime_human_score', this.allTimeHumanBest);
            }
        }

        // Check non-interrupting mid-run High Score celebrations!
        // 1. Passing the Human All-Time High Score (whether playing as Human or Bot)
        // 2. Passing the Bot / Overall All-Time High Score
        let highScoreCelebration = null;
        if (!this.passedBotBestCelebrated && this.score > this.initialBotBest) {
            this.passedBotBestCelebrated = true;
            this.passedHumanBestCelebrated = true;
            highScoreCelebration = {
                kind: 'bot_record',
                category: this.usedBotInGame ? 'bot' : 'human',
                text: this.usedBotInGame
                    ? `🏆 NEW ALL-TIME BOT RECORD! (${this.score.toLocaleString()})`
                    : `👑 NEW OVERALL ALL-TIME RECORD! (${this.score.toLocaleString()})`
            };
        } else if (!this.passedHumanBestCelebrated && this.score > this.initialHumanBest) {
            this.passedHumanBestCelebrated = true;
            highScoreCelebration = {
                kind: 'human_record',
                category: 'human',
                text: this.usedBotInGame
                    ? `🔥 Passed Human High Score! (${this.score.toLocaleString()})`
                    : `🏆 NEW HUMAN HIGH SCORE! (${this.score.toLocaleString()})`
            };
        }

        const spawned = this.addNewTile();

        // Check tile milestones
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

        // Trigger the Name Entry Modal ONLY at the end of the run (Game Over) so gameplay is never interrupted!
        let recordBreak = null;
        if (this.gameOver && !this.recordPromptShownForCurrentGame) {
            if (this.usedBotInGame && this.score > this.initialBotBest) {
                recordBreak = {
                    type: 'bot',
                    score: this.score,
                    prevBest: this.initialBotBest,
                    prevName: this.allTimeBotName
                };
            } else if (!this.usedBotInGame && this.score > this.initialHumanBest) {
                recordBreak = {
                    type: 'human',
                    score: this.score,
                    prevBest: this.initialHumanBest,
                    prevName: this.allTimeHumanName
                };
            }
        }

        return {
            moved: true,
            transitions,
            spawn: spawned,
            highestMerged,
            justMilestone: this.justMilestone,
            highScoreCelebration,
            recordBreak
        };
    }

    saveAllTimeRecord(type, rawName) {
        const sanitizedName = sanitizePlayerName(rawName, type === 'bot' ? 'Bot Master' : 'Champion');
        if (type === 'bot') {
            this.allTimeBotBest = Math.max(this.allTimeBotBest, this.score);
            this.allTimeBotName = sanitizedName;
            this.initialBotBest = this.allTimeBotBest;
            localStorage.setItem('2048_alltime_bot_score', this.allTimeBotBest);
            localStorage.setItem('2048_alltime_bot_name', this.allTimeBotName);
        } else {
            this.allTimeHumanBest = Math.max(this.allTimeHumanBest, this.score);
            this.allTimeHumanName = sanitizedName;
            this.initialHumanBest = this.allTimeHumanBest;
            localStorage.setItem('2048_alltime_human_score', this.allTimeHumanBest);
            localStorage.setItem('2048_alltime_human_name', this.allTimeHumanName);
        }
        this.recordPromptShownForCurrentGame = true;

        // Async Cloud Sync
        this.pushGlobalRecord(type, this.score, sanitizedName);
    }

    async pushGlobalRecord(type, score, name) {
        try {
            const key = type === 'bot' ? 'record_bot_v1' : 'record_human_v1';
            const payload = JSON.stringify({ score, name, updated: Date.now() });
            // Free public key-value store write
            await fetch(`${GLOBAL_API_BASE}${GLOBAL_KV_BUCKET}/${key}`, {
                method: 'PUT',
                body: payload,
                headers: { 'Content-Type': 'application/json' }
            });
        } catch (e) {
            // Silently fall back to local storage if network is offline
        }
    }

    async syncGlobalScores() {
        try {
            // Fetch human record
            const resHuman = await fetch(`${GLOBAL_API_BASE}${GLOBAL_KV_BUCKET}/record_human_v1`);
            if (resHuman.ok) {
                const data = await resHuman.json();
                if (data && typeof data.score === 'number' && data.score > this.allTimeHumanBest) {
                    this.allTimeHumanBest = data.score;
                    this.initialHumanBest = Math.max(this.initialHumanBest, data.score);
                    this.allTimeHumanName = sanitizePlayerName(data.name, 'Grandmaster');
                    localStorage.setItem('2048_alltime_human_score', this.allTimeHumanBest);
                    localStorage.setItem('2048_alltime_human_name', this.allTimeHumanName);
                }
            }

            // Fetch bot record
            const resBot = await fetch(`${GLOBAL_API_BASE}${GLOBAL_KV_BUCKET}/record_bot_v1`);
            if (resBot.ok) {
                const data = await resBot.json();
                if (data && typeof data.score === 'number' && data.score > this.allTimeBotBest) {
                    this.allTimeBotBest = data.score;
                    this.initialBotBest = Math.max(this.initialBotBest, data.score);
                    this.allTimeBotName = sanitizePlayerName(data.name, 'Expectimax Bot');
                    localStorage.setItem('2048_alltime_bot_score', this.allTimeBotBest);
                    localStorage.setItem('2048_alltime_bot_name', this.allTimeBotName);
                }
            }

            if (typeof window !== 'undefined' && window.updateLeaderboardDisplay) {
                window.updateLeaderboardDisplay();
            }
        } catch (e) {
            // Offline or unavailable, localStorage maintains integrity
        }
    }

    undo() {
        if (this.history.length === 0) return false;
        const prev = this.history.pop();
        this.grid = prev.grid;
        this.score = prev.score;
        this.moves = prev.moves;
        this.lastMove = prev.lastMove;
        this.milestones = prev.milestones;
        this.usedBotInGame = prev.usedBot;
        this.passedHumanBestCelebrated = Boolean(prev.passedHuman);
        this.passedBotBestCelebrated = Boolean(prev.passedBot);
        this.recordPromptShownForCurrentGame = Boolean(prev.recordPromptShown);
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
window.sanitizePlayerName = sanitizePlayerName;
