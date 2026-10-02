// Web Audio API Procedural Sound Engine
// Zero external audio files required - pure native browser waveform synthesis

class SoundManager {
    constructor() {
        this.ctx = null;
        this.muted = localStorage.getItem('2048_muted') === 'true';
    }

    init() {
        if (!this.ctx) {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (AudioCtx) {
                this.ctx = new AudioCtx();
            }
        }
        if (this.ctx && this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
    }

    toggleMute() {
        this.muted = !this.muted;
        localStorage.setItem('2048_muted', this.muted);
        return this.muted;
    }

    playSlide() {
        if (this.muted) return;
        this.init();
        if (!this.ctx) return;

        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'sine';
        const t = this.ctx.currentTime;
        osc.frequency.setValueAtTime(180, t);
        osc.frequency.exponentialRampToValueAtTime(110, t + 0.05);

        gain.gain.setValueAtTime(0.06, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.05);

        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(t);
        osc.stop(t + 0.05);
    }

    playMerge(tileValue) {
        if (this.muted) return;
        this.init();
        if (!this.ctx) return;

        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'triangle';

        // Frequency scales smoothly with tile value
        const exponent = Math.max(1, Math.log2(tileValue || 4));
        const baseFreq = 261.63; // C4
        const freq = baseFreq * Math.pow(2, (exponent - 1) * 0.18);

        const t = this.ctx.currentTime;
        osc.frequency.setValueAtTime(freq, t);
        osc.frequency.exponentialRampToValueAtTime(freq * 1.05, t + 0.1);

        gain.gain.setValueAtTime(0.12, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.12);

        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(t);
        osc.stop(t + 0.12);
    }

    playMilestone() {
        if (this.muted) return;
        this.init();
        if (!this.ctx) return;

        // Celebratory major arpeggio
        const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6
        notes.forEach((freq, idx) => {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = 'sine';

            const t = this.ctx.currentTime + idx * 0.08;
            osc.frequency.setValueAtTime(freq, t);

            gain.gain.setValueAtTime(0.14, t);
            gain.gain.exponentialRampToValueAtTime(0.001, t + 0.25);

            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(t);
            osc.stop(t + 0.25);
        });
    }

    playGameOver() {
        if (this.muted) return;
        this.init();
        if (!this.ctx) return;

        const notes = [330.0, 311.13, 293.66, 261.63];
        notes.forEach((freq, idx) => {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = 'sine';

            const t = this.ctx.currentTime + idx * 0.12;
            osc.frequency.setValueAtTime(freq, t);

            gain.gain.setValueAtTime(0.12, t);
            gain.gain.exponentialRampToValueAtTime(0.001, t + 0.2);

            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(t);
            osc.stop(t + 0.2);
        });
    }
}

window.soundManager = new SoundManager();
