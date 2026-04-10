/**
 * Audio capture — candidate-controlled submission.
 *
 * Recording runs continuously until the candidate clicks "Done Speaking".
 * Silence detection is visual-only (mic activity indicator), not a trigger.
 * Whisper handles extracting speech from recordings that contain pauses.
 */
class AudioCapture {
    constructor({ speechThreshold = 0.015, onAudioReady, onStateChange }) {
        this.speechThreshold = speechThreshold;
        this.onAudioReady = onAudioReady;
        this.onStateChange = onStateChange || (() => {});

        this.stream = null;
        this.mediaRecorder = null;
        this.audioContext = null;
        this.analyser = null;
        this.chunks = [];
        this.isRecording = false;
        this.activityCheckInterval = null;
        this.state = 'idle'; // idle, listening, speaking, processing
    }

    async init() {
        this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.audioContext = new AudioContext();
        const source = this.audioContext.createMediaStreamSource(this.stream);
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 2048;
        source.connect(this.analyser);
        this._setState('idle');
    }

    startRecording() {
        if (!this.stream) return;
        this.chunks = [];

        this.mediaRecorder = new MediaRecorder(this.stream, {
            mimeType: this._getSupportedMimeType(),
        });
        this.mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) this.chunks.push(e.data);
        };
        this.mediaRecorder.onstop = () => {
            if (this.chunks.length > 0) {
                const blob = new Blob(this.chunks, { type: this.mediaRecorder.mimeType });
                this._setState('processing');
                if (this.onAudioReady) this.onAudioReady(blob);
            }
            this.chunks = [];
        };

        this.mediaRecorder.start(500);
        this.isRecording = true;
        this._setState('listening');

        // Visual-only: show mic activity (speaking vs silent)
        this.activityCheckInterval = setInterval(() => this._checkActivity(), 150);
    }

    submit() {
        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            clearInterval(this.activityCheckInterval);
            this.mediaRecorder.stop();
            this.isRecording = false;
        }
    }

    cancel() {
        clearInterval(this.activityCheckInterval);
        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.stop();
        }
        this.chunks = [];
        this.isRecording = false;
        this._setState('idle');
    }

    resetForNextQuestion() {
        this._setState('idle');
    }

    destroy() {
        this.cancel();
        if (this.stream) {
            this.stream.getTracks().forEach(t => t.stop());
        }
        if (this.audioContext) {
            this.audioContext.close();
        }
    }

    _checkActivity() {
        if (!this.analyser || !this.isRecording) return;

        const data = new Float32Array(this.analyser.fftSize);
        this.analyser.getFloatTimeDomainData(data);

        let sum = 0;
        for (let i = 0; i < data.length; i++) sum += data[i] * data[i];
        const rms = Math.sqrt(sum / data.length);

        // Visual feedback only — no submission logic
        if (rms >= this.speechThreshold) {
            if (this.state !== 'speaking') this._setState('speaking');
        } else {
            if (this.state !== 'listening') this._setState('listening');
        }
    }

    _setState(state) {
        this.state = state;
        this.onStateChange(state);
    }

    _getSupportedMimeType() {
        const types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
        for (const t of types) {
            if (MediaRecorder.isTypeSupported(t)) return t;
        }
        return '';
    }
}
