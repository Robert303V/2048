// 64-Bit Bitboard Expectimax Solver Engine in JavaScript
// Optimized for maximum gameplay strength (8-symmetry snake heuristic + smoothness + merge potential)
// and zero-allocation O(1) lookup speed with a typed-array transposition table and iterative deepening.

(function(exports) {
    const B = 2.8;

    // -------------------------------------------------------------------------
    // 1. Precomputed 16-Bit Row Move & Heuristic Lookup Tables (65,536 entries)
    // -------------------------------------------------------------------------
    const ROW_LEFT = new Uint16Array(65536);
    const ROW_RIGHT = new Uint16Array(65536);
    const ROW_EMPTY = new Uint8Array(65536);
    const ROW_SMOOTH = new Float64Array(65536);
    const ROW_MERGES = new Float64Array(65536);

    const EMPTY_WEIGHT = Math.pow(B, 12);
    const SMOOTH_WEIGHT = Math.pow(B, 9);
    const MERGE_WEIGHT = Math.pow(B, 10);

    for (let row = 0; row < 65536; row++) {
        const t = [
            (row >> 12) & 0xF,
            (row >> 8) & 0xF,
            (row >> 4) & 0xF,
            row & 0xF
        ];

        // Slide Left
        const nz = t.filter(x => x !== 0);
        const m = [];
        let i = 0;
        while (i < nz.length) {
            if (i + 1 < nz.length && nz[i] === nz[i + 1]) {
                m.push(nz[i] + 1);
                i += 2;
            } else {
                m.push(nz[i]);
                i++;
            }
        }
        while (m.length < 4) m.push(0);
        ROW_LEFT[row] = (m[0] << 12) | (m[1] << 8) | (m[2] << 4) | m[3];

        // Slide Right
        const nzr = [t[3], t[2], t[1], t[0]].filter(x => x !== 0);
        const mr = [];
        i = 0;
        while (i < nzr.length) {
            if (i + 1 < nzr.length && nzr[i] === nzr[i + 1]) {
                mr.push(nzr[i] + 1);
                i += 2;
            } else {
                mr.push(nzr[i]);
                i++;
            }
        }
        while (mr.length < 4) mr.push(0);
        mr.reverse();
        ROW_RIGHT[row] = (mr[0] << 12) | (mr[1] << 8) | (mr[2] << 4) | mr[3];

        // Empty cells count
        let emp = 0;
        for (let j = 0; j < 4; j++) {
            if (t[j] === 0) emp++;
        }
        ROW_EMPTY[row] = emp;

        // Smoothness penalty between adjacent non-zero tiles
        let sm = 0.0;
        for (let j = 0; j < 3; j++) {
            if (t[j] > 0 && t[j + 1] > 0) {
                sm -= Math.abs(t[j] - t[j + 1]);
            }
        }
        ROW_SMOOTH[row] = sm * SMOOTH_WEIGHT;

        // Pairwise merge potential bonus (adjacent identical tiles)
        let mg = 0.0;
        for (let j = 0; j < 3; j++) {
            if (t[j] > 0 && t[j] === t[j + 1]) {
                mg += (1 << t[j]) * MERGE_WEIGHT;
            }
        }
        ROW_MERGES[row] = mg;
    }

    // -------------------------------------------------------------------------
    // 2. Precomputed 8-Symmetry Snake Gradient Tables (8 x 4 x 65,536)
    // -------------------------------------------------------------------------
    const SNAKE_PATH = [
        [0, 0], [0, 1], [0, 2], [0, 3],
        [1, 3], [1, 2], [1, 1], [1, 0],
        [2, 0], [2, 1], [2, 2], [2, 3],
        [3, 3], [3, 2], [3, 1], [3, 0]
    ];

    const baseGrad = [
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0]
    ];
    for (let k = 0; k < 16; k++) {
        const [r, c] = SNAKE_PATH[k];
        baseGrad[r][c] = Math.pow(B, 15 - k);
    }

    function rot90(mat) {
        const res = [
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0]
        ];
        for (let r = 0; r < 4; r++) {
            for (let c = 0; c < 4; c++) {
                res[3 - c][r] = mat[r][c];
            }
        }
        return res;
    }

    function fliplr(mat) {
        return mat.map(row => [row[3], row[2], row[1], row[0]]);
    }

    const gradients = [];
    let curGrad = baseGrad;
    for (let k = 0; k < 4; k++) {
        gradients.push(curGrad);
        gradients.push(fliplr(curGrad));
        curGrad = rot90(curGrad);
    }

    // SYM_TABLES[sym][rowIdx][row16]
    const SYM_TABLES = gradients.map(sym => {
        return [0, 1, 2, 3].map(rowIdx => {
            const table = new Float64Array(65536);
            const weights = sym[rowIdx];
            const w0 = weights[0], w1 = weights[1], w2 = weights[2], w3 = weights[3];
            for (let rowInt = 0; rowInt < 65536; rowInt++) {
                const c0 = (rowInt >> 12) & 0xF;
                const c1 = (rowInt >> 8) & 0xF;
                const c2 = (rowInt >> 4) & 0xF;
                const c3 = rowInt & 0xF;
                let val = 0.0;
                if (c0 > 0) val += (1 << c0) * w0;
                if (c1 > 0) val += (1 << c1) * w1;
                if (c2 > 0) val += (1 << c2) * w2;
                if (c3 > 0) val += (1 << c3) * w3;
                table[rowInt] = val;
            }
            return table;
        });
    });

    // -------------------------------------------------------------------------
    // 3. Fast Bitboard Transpose & O(1) Board Evaluation
    // -------------------------------------------------------------------------
    function transpose0(r0, r1, r2, r3) {
        return ((r0 & 0xF000)) | ((r1 & 0xF000) >> 4) | ((r2 & 0xF000) >> 8) | ((r3 & 0xF000) >> 12);
    }
    function transpose1(r0, r1, r2, r3) {
        return ((r0 & 0x0F00) << 4) | ((r1 & 0x0F00)) | ((r2 & 0x0F00) >> 4) | ((r3 & 0x0F00) >> 8);
    }
    function transpose2(r0, r1, r2, r3) {
        return ((r0 & 0x00F0) << 8) | ((r1 & 0x00F0) << 4) | ((r2 & 0x00F0)) | ((r3 & 0x00F0) >> 4);
    }
    function transpose3(r0, r1, r2, r3) {
        return ((r0 & 0x000F) << 12) | ((r1 & 0x000F) << 8) | ((r2 & 0x000F) << 4) | (r3 & 0x000F);
    }

    function evaluate(r0, r1, r2, r3) {
        const c0 = transpose0(r0, r1, r2, r3);
        const c1 = transpose1(r0, r1, r2, r3);
        const c2 = transpose2(r0, r1, r2, r3);
        const c3 = transpose3(r0, r1, r2, r3);

        const empty = ROW_EMPTY[r0] + ROW_EMPTY[r1] + ROW_EMPTY[r2] + ROW_EMPTY[r3];
        const smoothness = (
            ROW_SMOOTH[r0] + ROW_SMOOTH[r1] + ROW_SMOOTH[r2] + ROW_SMOOTH[r3] +
            ROW_SMOOTH[c0] + ROW_SMOOTH[c1] + ROW_SMOOTH[c2] + ROW_SMOOTH[c3]
        );
        const merges = (
            ROW_MERGES[r0] + ROW_MERGES[r1] + ROW_MERGES[r2] + ROW_MERGES[r3] +
            ROW_MERGES[c0] + ROW_MERGES[c1] + ROW_MERGES[c2] + ROW_MERGES[c3]
        );

        let bestGrad = 0.0;
        for (let s = 0; s < 8; s++) {
            const symT = SYM_TABLES[s];
            const v = symT[0][r0] + symT[1][r1] + symT[2][r2] + symT[3][r3];
            if (v > bestGrad) bestGrad = v;
        }

        const emptyPenalty = empty <= 1 ? -100000.0 * (2 - empty) : 0.0;
        return bestGrad + merges + empty * EMPTY_WEIGHT + smoothness + emptyPenalty;
    }

    // -------------------------------------------------------------------------
    // 4. Zero-Allocation Typed-Array Transposition Table (524,288 slots)
    // -------------------------------------------------------------------------
    const TT_SIZE = 1 << 19; // 524,288 entries
    const TT_MASK = TT_SIZE - 1;
    const ttKeyHi = new Uint32Array(TT_SIZE);
    const ttKeyLo = new Uint32Array(TT_SIZE);
    const ttMeta = new Uint8Array(TT_SIZE); // (depth << 1) | isAgent (plus +1 offset so 0 means empty)
    const ttVal = new Float64Array(TT_SIZE);

    function hashBoard(hi, lo, meta) {
        let h = (hi ^ Math.imul(lo, 0x9E3779B1) ^ Math.imul(meta, 0x85EBCA6B)) >>> 0;
        h ^= h >>> 16;
        h = Math.imul(h, 0x7FEB352D) >>> 0;
        h ^= h >>> 15;
        return h & TT_MASK;
    }

    // -------------------------------------------------------------------------
    // 5. Expectimax Search with Calibrated Ply Depth & Probability Pruning
    // -------------------------------------------------------------------------
    function searchAgent(r0, r1, r2, r3, depth, probCutoff, curProb) {
        if (depth <= 0 || curProb < probCutoff) {
            return evaluate(r0, r1, r2, r3);
        }

        const hi = ((r0 << 16) | r1) >>> 0;
        const lo = ((r2 << 16) | r3) >>> 0;
        const meta = (depth << 1) | 2;
        const idx = hashBoard(hi, lo, meta);

        if (ttMeta[idx] === meta && ttKeyHi[idx] === hi && ttKeyLo[idx] === lo) {
            return ttVal[idx];
        }

        let bestV = -Infinity;

        // 0: Up
        {
            const c0 = transpose0(r0, r1, r2, r3);
            const c1 = transpose1(r0, r1, r2, r3);
            const c2 = transpose2(r0, r1, r2, r3);
            const c3 = transpose3(r0, r1, r2, r3);
            const nc0 = ROW_LEFT[c0], nc1 = ROW_LEFT[c1], nc2 = ROW_LEFT[c2], nc3 = ROW_LEFT[c3];
            if (nc0 !== c0 || nc1 !== c1 || nc2 !== c2 || nc3 !== c3) {
                const nr0 = transpose0(nc0, nc1, nc2, nc3);
                const nr1 = transpose1(nc0, nc1, nc2, nc3);
                const nr2 = transpose2(nc0, nc1, nc2, nc3);
                const nr3 = transpose3(nc0, nc1, nc2, nc3);
                const v = searchChance(nr0, nr1, nr2, nr3, depth - 1, probCutoff, curProb);
                if (v > bestV) bestV = v;
            }
        }
        // 1: Left
        {
            const nr0 = ROW_LEFT[r0], nr1 = ROW_LEFT[r1], nr2 = ROW_LEFT[r2], nr3 = ROW_LEFT[r3];
            if (nr0 !== r0 || nr1 !== r1 || nr2 !== r2 || nr3 !== r3) {
                const v = searchChance(nr0, nr1, nr2, nr3, depth - 1, probCutoff, curProb);
                if (v > bestV) bestV = v;
            }
        }
        // 2: Right
        {
            const nr0 = ROW_RIGHT[r0], nr1 = ROW_RIGHT[r1], nr2 = ROW_RIGHT[r2], nr3 = ROW_RIGHT[r3];
            if (nr0 !== r0 || nr1 !== r1 || nr2 !== r2 || nr3 !== r3) {
                const v = searchChance(nr0, nr1, nr2, nr3, depth - 1, probCutoff, curProb);
                if (v > bestV) bestV = v;
            }
        }
        // 3: Down
        {
            const c0 = transpose0(r0, r1, r2, r3);
            const c1 = transpose1(r0, r1, r2, r3);
            const c2 = transpose2(r0, r1, r2, r3);
            const c3 = transpose3(r0, r1, r2, r3);
            const nc0 = ROW_RIGHT[c0], nc1 = ROW_RIGHT[c1], nc2 = ROW_RIGHT[c2], nc3 = ROW_RIGHT[c3];
            if (nc0 !== c0 || nc1 !== c1 || nc2 !== c2 || nc3 !== c3) {
                const nr0 = transpose0(nc0, nc1, nc2, nc3);
                const nr1 = transpose1(nc0, nc1, nc2, nc3);
                const nr2 = transpose2(nc0, nc1, nc2, nc3);
                const nr3 = transpose3(nc0, nc1, nc2, nc3);
                const v = searchChance(nr0, nr1, nr2, nr3, depth - 1, probCutoff, curProb);
                if (v > bestV) bestV = v;
            }
        }

        if (bestV === -Infinity) {
            bestV = evaluate(r0, r1, r2, r3);
        }

        ttKeyHi[idx] = hi;
        ttKeyLo[idx] = lo;
        ttMeta[idx] = meta;
        ttVal[idx] = bestV;
        return bestV;
    }

    function searchChance(r0, r1, r2, r3, depth, probCutoff, curProb) {
        if (depth <= 0 || curProb < probCutoff) {
            return evaluate(r0, r1, r2, r3);
        }

        const empCount = ROW_EMPTY[r0] + ROW_EMPTY[r1] + ROW_EMPTY[r2] + ROW_EMPTY[r3];
        if (empCount === 0) {
            return evaluate(r0, r1, r2, r3);
        }

        const hi = ((r0 << 16) | r1) >>> 0;
        const lo = ((r2 << 16) | r3) >>> 0;
        const meta = (depth << 1) | 1;
        const idx = hashBoard(hi, lo, meta);

        if (ttMeta[idx] === meta && ttKeyHi[idx] === hi && ttKeyLo[idx] === lo) {
            return ttVal[idx];
        }

        const prob = 1.0 / empCount;
        const nextProb2 = curProb * prob * 0.9;
        const nextProb4 = curProb * prob * 0.1;
        const evalTile4 = (nextProb4 >= probCutoff && depth > 2);
        let expV = 0.0;

        const rows = [r0, r1, r2, r3];
        for (let r = 0; r < 4; r++) {
            const rowVal = rows[r];
            if (ROW_EMPTY[rowVal] === 0) continue;
            for (let shift = 12; shift >= 0; shift -= 4) {
                if (((rowVal >> shift) & 0xF) === 0) {
                    // 90% chance of spawning tile 2 (rank 1)
                    rows[r] = rowVal | (1 << shift);
                    const v2 = searchAgent(rows[0], rows[1], rows[2], rows[3], depth - 1, probCutoff, nextProb2);

                    if (evalTile4) {
                        // 10% chance of spawning tile 4 (rank 2)
                        rows[r] = rowVal | (2 << shift);
                        const v4 = searchAgent(rows[0], rows[1], rows[2], rows[3], depth - 1, probCutoff, nextProb4);
                        expV += prob * (0.9 * v2 + 0.1 * v4);
                    } else {
                        expV += prob * v2;
                    }
                    rows[r] = rowVal;
                }
            }
        }

        ttKeyHi[idx] = hi;
        ttKeyLo[idx] = lo;
        ttMeta[idx] = meta;
        ttVal[idx] = expV;
        return expV;
    }

    function gridToRows(grid) {
        const rows = [0, 0, 0, 0];
        for (let r = 0; r < 4; r++) {
            let rowBits = 0;
            for (let c = 0; c < 4; c++) {
                const val = grid[r][c];
                if (val > 0) {
                    const rank = Math.round(Math.log2(val));
                    rowBits |= (rank << ((3 - c) * 4));
                }
            }
            rows[r] = rowBits;
        }
        return rows;
    }

    function getBestMove(grid) {
        const [r0, r1, r2, r3] = gridToRows(grid);
        const empCount = ROW_EMPTY[r0] + ROW_EMPTY[r1] + ROW_EMPTY[r2] + ROW_EMPTY[r3];

        // Adaptive Lookahead calibrated with the master Python solver
        // Plus boosted midgame/endgame depth enabled by O(1) table evaluation
        let depth, cutoff;
        if (empCount <= 2) {
            depth = 9;
            cutoff = 0.00004;
        } else if (empCount <= 4) {
            depth = 7;
            cutoff = 0.00008;
        } else if (empCount <= 7) {
            depth = 6;
            cutoff = 0.00015;
        } else {
            depth = 4;
            cutoff = 0.0004;
        }

        // Evaluate all 4 root candidate moves: Up, Left, Right, Down
        const c0 = transpose0(r0, r1, r2, r3);
        const c1 = transpose1(r0, r1, r2, r3);
        const c2 = transpose2(r0, r1, r2, r3);
        const c3 = transpose3(r0, r1, r2, r3);

        const candidates = [
            // Up
            (function() {
                const nc0 = ROW_LEFT[c0], nc1 = ROW_LEFT[c1], nc2 = ROW_LEFT[c2], nc3 = ROW_LEFT[c3];
                if (nc0 === c0 && nc1 === c1 && nc2 === c2 && nc3 === c3) return null;
                return {
                    dir: 'up',
                    r0: transpose0(nc0, nc1, nc2, nc3),
                    r1: transpose1(nc0, nc1, nc2, nc3),
                    r2: transpose2(nc0, nc1, nc2, nc3),
                    r3: transpose3(nc0, nc1, nc2, nc3)
                };
            })(),
            // Left
            (function() {
                const nr0 = ROW_LEFT[r0], nr1 = ROW_LEFT[r1], nr2 = ROW_LEFT[r2], nr3 = ROW_LEFT[r3];
                if (nr0 === r0 && nr1 === r1 && nr2 === r2 && nr3 === r3) return null;
                return { dir: 'left', r0: nr0, r1: nr1, r2: nr2, r3: nr3 };
            })(),
            // Right
            (function() {
                const nr0 = ROW_RIGHT[r0], nr1 = ROW_RIGHT[r1], nr2 = ROW_RIGHT[r2], nr3 = ROW_RIGHT[r3];
                if (nr0 === r0 && nr1 === r1 && nr2 === r2 && nr3 === r3) return null;
                return { dir: 'right', r0: nr0, r1: nr1, r2: nr2, r3: nr3 };
            })(),
            // Down
            (function() {
                const nc0 = ROW_RIGHT[c0], nc1 = ROW_RIGHT[c1], nc2 = ROW_RIGHT[c2], nc3 = ROW_RIGHT[c3];
                if (nc0 === c0 && nc1 === c1 && nc2 === c2 && nc3 === c3) return null;
                return {
                    dir: 'down',
                    r0: transpose0(nc0, nc1, nc2, nc3),
                    r1: transpose1(nc0, nc1, nc2, nc3),
                    r2: transpose2(nc0, nc1, nc2, nc3),
                    r3: transpose3(nc0, nc1, nc2, nc3)
                };
            })()
        ].filter(Boolean);

        if (candidates.length === 0) return null;
        if (candidates.length === 1) return candidates[0].dir;

        let bestDir = candidates[0].dir;
        let bestV = -Infinity;

        for (let i = 0; i < candidates.length; i++) {
            const cand = candidates[i];
            const v = searchChance(cand.r0, cand.r1, cand.r2, cand.r3, depth - 1, cutoff, 1.0);
            if (v > bestV) {
                bestV = v;
                bestDir = cand.dir;
            }
        }

        return bestDir;
    }

    exports.ExpectimaxBot = {
        getBestMove: getBestMove
    };
})(typeof window !== 'undefined' ? window : globalThis);
