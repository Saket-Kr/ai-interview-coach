/**
 * Countdown timer display.
 */
class InterviewTimer {
    constructor(displayId, durationMinutes) {
        this.display = document.getElementById(displayId);
        this.totalSeconds = durationMinutes * 60;
        this.remainingSeconds = this.totalSeconds;
        this.interval = null;
        this.running = false;
    }

    start() {
        if (this.running) return;
        this.running = true;
        this.interval = setInterval(() => {
            this.remainingSeconds = Math.max(0, this.remainingSeconds - 1);
            this._render();
            if (this.remainingSeconds <= 0) {
                this.stop();
            }
        }, 1000);
    }

    stop() {
        this.running = false;
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
    }

    sync(remainingSeconds) {
        this.remainingSeconds = Math.max(0, Math.round(remainingSeconds));
        this._render();
    }

    _render() {
        const mins = Math.floor(this.remainingSeconds / 60);
        const secs = this.remainingSeconds % 60;
        this.display.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;

        // Color coding
        const pct = this.remainingSeconds / this.totalSeconds;
        if (pct <= 0.05) {
            this.display.style.color = '#f44336';
        } else if (pct <= 0.15) {
            this.display.style.color = '#ff9800';
        } else {
            this.display.style.color = '';
        }
    }
}
