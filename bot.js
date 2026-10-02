// 64-Bit Bitboard Expectimax Solver Engine in JavaScript
// High-performance typed-array implementation for browser deployment

(function(exports) {
    const ROW_LEFT = new Uint16Array(65536);
    const ROW_RIGHT = new Uint16Array(65536);
    const ROW_SCORE = new Uint32Array(65536);
    const ROW_MERGES = new Float32Array(65536);
    const ROW_REV = new Uint16Array(65536);

    const BASE = 2.8;
    const POWERS = new Float64Array(16);
    for (let i = 0; i < 16; i++) POWERS[i] = Math.pow(BASE, i);

    // Precompute 16-bit row transition tables
    for (let row = 0; row < 65536; row++) {
        const c0 = row & 0xF, c1 = (row >> 4) & 0xF, c2 = (row >> 8) & 0xF, c3 = (row >> 12) & 0xF;
        ROW_REV[row] = c3 | (c2 << 4) | (c1 << 8) | (c0 << 12);

        const line = [c0, c1, c2, c3].filter(x => x !== 0);
        const res = [];
        let score = 0, i = 0;
        while (i < line.length) {
            if (i + 1 < line.length && line[i] === line[i + 1]) {
                const nv = line[i] + 1;
                res.push(nv);
                score += (1 << nv);
                i += 2;
            } else {
                res.push(line[i]);
                i++;
            }
        }
        while (res.length < 4) res.push(0);
        ROW_LEFT[row] = res[0] | (res[1] << 4) | (res[2] << 8) | (res[3] << 12);
        ROW_SCORE[row] = score;

        // Pairwise merge bonuses
        let merges = 0;
        if (c0 !== 0 && c0 === c1) merges += Math.pow(c0, 1.8) * 4.0;
        if (c1 !== 0 && c1 === c2) merges += Math.pow(c1, 1.8) * 4.0;
        if (c2 !== 0 && c2 === c3) merges += Math.pow(c2, 1.8) * 4.0;
        ROW_MERGES[row] = merges;

        // Reverse for right move table
        ROW_RIGHT[row] = ROW_REV[ROW_LEFT[ROW_REV[row]]];
    }

    // 4 Monotonic snake gradient paths
    const SNAKE_A = [15, 14, 13, 12, 8, 9, 10, 11, 7, 6, 5, 4, 0, 1, 2, 3];
    const SNAKE_B = [15, 8, 7, 0, 14, 9, 6, 1, 13, 10, 5, 2, 12, 11, 4, 3];
    const SNAKE_C = [0, 1, 2, 3, 7, 6, 5, 4, 8, 9, 10, 11, 15, 14, 13, 12];
    const SNAKE_D = [0, 7, 8, 15, 1, 6, 9, 14, 2, 5, 10, 13, 3, 4, 11, 12];

    const WEIGHTS_A = new Float64Array(16);
    const WEIGHTS_B = new Float64Array(16);
    const WEIGHTS_C = new Float64Array(16);
    const WEIGHTS_D = new Float64Array(16);
    for (let i = 0; i < 16; i++) {
        WEIGHTS_A[i] = Math.pow(BASE, SNAKE_A[i]);
        WEIGHTS_B[i] = Math.pow(BASE, SNAKE_B[i]);
        WEIGHTS_C[i] = Math.pow(BASE, SNAKE_C[i]);
        WEIGHTS_D[i] = Math.pow(BASE, SNAKE_D[i]);
    }

    function transpose(r0, r1, r2, r3) {
        return [
            (r0 & 0xF) | ((r1 & 0xF) << 4) | ((r2 & 0xF) << 8) | ((r3 & 0xF) << 12),
            ((r0 >> 4) & 0xF) | (((r1 >> 4) & 0xF) << 4) | (((r2 >> 4) & 0xF) << 8) | (((r3 >> 4) & 0xF) << 12),
            ((r0 >> 8) & 0xF) | (((r1 >> 8) & 0xF) << 4) | (((r2 >> 8) & 0xF) << 8) | (((r3 >> 8) & 0xF) << 12),
            ((r0 >> 12) & 0xF) | (((r1 >> 12) & 0xF) << 4) | (((r2 >> 12) & 0xF) << 8) | (((r3 >> 12) & 0xF) << 12)
        ];
    }

    function moveBoard(b, dir) {
        const [r0, r1, r2, r3] = b;
        if (dir === 0) { // left
            const n0 = ROW_LEFT[r0], n1 = ROW_LEFT[r1], n2 = ROW_LEFT[r2], n3 = ROW_LEFT[r3];
            if (n0 === r0 && n1 === r1 && n2 === r2 && n3 === r3) return null;
            return [n0, n1, n2, n3];
        } else if (dir === 1) { // right
            const n0 = ROW_RIGHT[r0], n1 = ROW_RIGHT[r1], n2 = ROW_RIGHT[r2], n3 = ROW_RIGHT[r3];
            if (n0 === r0 && n1 === r1 && n2 === r2 && n3 === r3) return null;
            return [n0, n1, n2, n3];
        } else if (dir === 2) { // up
            const [c0, c1, c2, c3] = transpose(r0, r1, r2, r3);
            const nc0 = ROW_LEFT[c0], nc1 = ROW_LEFT[c1], nc2 = ROW_LEFT[c2], nc3 = ROW_LEFT[c3];
            if (nc0 === c0 && nc1 === c1 && nc2 === c2 && nc3 === c3) return null;
            return transpose(nc0, nc1, nc2, nc3);
        } else { // down
            const [c0, c1, c2, c3] = transpose(r0, r1, r2, r3);
            const nc0 = ROW_RIGHT[c0], nc1 = ROW_RIGHT[c1], nc2 = ROW_RIGHT[c2], nc3 = ROW_RIGHT[c3];
            if (nc0 === c0 && nc1 === c1 && nc2 === c2 && nc3 === c3) return null;
            return transpose(nc0, nc1, nc2, nc3);
        }
    }

    function evaluate(b) {
        const [r0, r1, r2, r3] = b;
        let empty = 0;
        const cells = new Uint8Array(16);
        let idx = 0;
        for (let r of b) {
            for (let s = 0; s < 16; s += 4) {
                const v = (r >> s) & 0xF;
                cells[idx++] = v;
                if (v === 0) empty++;
            }
        }
        let sA = 0, sB = 0, sC = 0, sD = 0;
        for (let i = 0; i < 16; i++) {
            const v = cells[i];
            if (v > 0) {
                const p = POWERS[v];
                sA += p * WEIGHTS_A[i];
                sB += p * WEIGHTS_B[i];
                sC += p * WEIGHTS_C[i];
                sD += p * WEIGHTS_D[i];
            }
        }
        const maxSnake = Math.max(sA, sB, sC, sD);
        const merges = ROW_MERGES[r0] + ROW_MERGES[r1] + ROW_MERGES[r2] + ROW_MERGES[r3];
        const [c0, c1, c2, c3] = transpose(r0, r1, r2, r3);
        const colMerges = ROW_MERGES[c0] + ROW_MERGES[c1] + ROW_MERGES[c2] + ROW_MERGES[c3];
        let score = maxSnake + empty * 8000 + (merges + colMerges) * 350;
        if (empty <= 1) score -= (2 - empty) * 100000;
        return score;
    }

    const transCache = new Map();

    function countEmpty(b) {
        let count = 0;
        for (let r of b) {
            for (let s = 0; s < 16; s += 4) {
                if (((r >> s) & 0xF) === 0) count++;
            }
        }
        return count;
    }

    function chanceNode(b, depth, prob, cutoff) {
        if (prob < cutoff || depth === 0) return evaluate(b);
        const emptyCells = [];
        for (let r = 0; r < 4; r++) {
            for (let c = 0; c < 4; c++) {
                if (((b[r] >> (c * 4)) & 0xF) === 0) emptyCells.push([r, c]);
            }
        }
        if (emptyCells.length === 0) return evaluate(b);
        let expected = 0;
        const invN = 1.0 / emptyCells.length;
        for (const [r, c] of emptyCells) {
            // Tile 2 (90%)
            const b2 = [b[0], b[1], b[2], b[3]];
            b2[r] |= (1 << (c * 4));
            expected += 0.9 * maxNode(b2, depth - 1, prob * 0.9 * invN, cutoff) * invN;

            // Tile 4 (10%)
            if (prob * 0.1 * invN >= cutoff) {
                const b4 = [b[0], b[1], b[2], b[3]];
                b4[r] |= (2 << (c * 4));
                expected += 0.1 * maxNode(b4, depth - 1, prob * 0.1 * invN, cutoff) * invN;
            } else {
                expected += 0.1 * evaluate(b) * invN;
            }
        }
        return expected;
    }

    function maxNode(b, depth, prob, cutoff) {
        if (depth === 0) return evaluate(b);
        const key = (BigInt(b[0]) | (BigInt(b[1]) << 16n) | (BigInt(b[2]) << 32n) | (BigInt(b[3]) << 48n) | (BigInt(depth) << 60n)).toString();
        const cached = transCache.get(key);
        if (cached !== undefined) return cached;

        let best = -1e12;
        for (let d = 0; d < 4; d++) {
            const nb = moveBoard(b, d);
            if (nb !== null) {
                const score = chanceNode(nb, depth, prob, cutoff);
                if (score > best) best = score;
            }
        }
        if (best === -1e12) best = evaluate(b);
        if (transCache.size < 400000) transCache.set(key, best);
        return best;
    }

    function gridToBitboard(grid) {
        const b = [0, 0, 0, 0];
        for (let r = 0; r < 4; r++) {
            for (let c = 0; c < 4; c++) {
                const val = grid[r][c];
                const exp = val > 0 ? Math.round(Math.log2(val)) : 0;
                b[r] |= (exp << (c * 4));
            }
        }
        return b;
    }

    function getBestMove(grid) {
        const b = gridToBitboard(grid);
        const empty = countEmpty(b);

        // Calibrated depth matching the master Python engine
        let depth = 4, cutoff = 0.0005;
        if (empty <= 2) { depth = 8; cutoff = 0.00005; }
        else if (empty <= 4) { depth = 6; cutoff = 0.0001; }
        else if (empty <= 7) { depth = 5; cutoff = 0.0002; }

        let bestDir = -1, bestScore = -1e12;
        const dirNames = ['left', 'right', 'up', 'down'];

        for (let d = 0; d < 4; d++) {
            const nb = moveBoard(b, d);
            if (nb !== null) {
                const score = chanceNode(nb, depth, 1.0, cutoff);
                if (score > bestScore) {
                    bestScore = score;
                    bestDir = d;
                }
            }
        }
        return bestDir !== -1 ? dirNames[bestDir] : null;
    }

    exports.ExpectimaxBot = {
        getBestMove: getBestMove
    };
})(typeof window !== 'undefined' ? window : globalThis);
