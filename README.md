# 2048 Master Edition + Expectimax Bot

A full-featured **2048** game and high-performance **Expectimax Bot** playable on the web and desktop.

👉 **[Play Live on the Web](https://robert303v.github.io/2048/)**

---

## 🤖 The Expectimax Bot Engine

The automated solver uses a calibrated **64-bit Bitboard Expectimax Tree Search**:

- **Monotonic Snake Gradient Heuristic ($B = 2.8$)**: Mathematically guarantees that the highest-value tile stays securely pinned to the corner without dislocation.
- **Precomputed Bitboard Row Tables**: Evaluates over **500,000 board positions per second** via 65,536-entry precomputed move, score, and merge lookup tables.
- **Pairwise Merge Potential Bonuses**: Accurately recognizes and builds adjacent merge ladders.
- **Deep Adaptive Search (Depth 4 – 8)**: Evaluates up to 8 plies deep in endgame scenarios with cumulative chance node probability pruning ($p < 0.00005$).
- **100% 4096 Win Rate**: Consistently reaches **2048**, **4096**, and higher with scores exceeding **60,000+**.
