/**
 * Main interview orchestrator — wires WebSocket, audio capture, chat UI, and timer.
 *
 * Flow: interviewer asks → recording starts → candidate speaks (with pauses) →
 *       candidate clicks "Done Speaking" → audio uploaded → transcribed →
 *       displayed in chat → sent to LLM → interviewer responds → repeat
 */
(function () {
    const chat = new ChatUI('chat');
    const timer = new InterviewTimer('timer', DURATION_MINUTES);

    const micDot = document.getElementById('mic-dot');
    const micLabel = document.getElementById('mic-label');
    const doneBtn = document.getElementById('done-btn');
    const startBtn = document.getElementById('start-interview-btn');
    const endBtn = document.getElementById('end-btn');
    const overlay = document.getElementById('analysis-overlay');

    let ws = null;
    let audio = null;
    let interviewStarted = false;
    let waitingForInterviewer = false;

    function updateMicUI(state) {
        micDot.className = 'mic-dot';
        switch (state) {
            case 'idle':
                micLabel.textContent = 'Waiting for interviewer...';
                doneBtn.disabled = true;
                break;
            case 'listening':
                micDot.classList.add('listening');
                micLabel.textContent = 'Recording — thinking...';
                doneBtn.disabled = false;
                break;
            case 'speaking':
                micDot.classList.add('listening');
                micLabel.textContent = 'Recording — speaking...';
                doneBtn.disabled = false;
                break;
            case 'processing':
                micDot.classList.add('processing');
                micLabel.textContent = 'Transcribing...';
                doneBtn.disabled = true;
                break;
        }
    }

    async function handleAudioReady(blob) {
        const formData = new FormData();
        formData.append('file', blob, 'recording.webm');

        try {
            const res = await fetch(`/api/interviews/${INTERVIEW_ID}/audio`, {
                method: 'POST',
                body: formData,
            });

            if (!res.ok) {
                const err = await res.text();
                console.error('Transcription failed:', err);
                chat.addSystemMessage('Could not transcribe audio. Please try again.');
                audio.resetForNextQuestion();
                audio.startRecording();
                return;
            }

            const data = await res.json();
            chat.addMessage('candidate', data.text);
            waitingForInterviewer = true;

            // Send transcribed text to LLM via WebSocket
            ws.send(JSON.stringify({ type: 'candidate_message', text: data.text }));

        } catch (err) {
            console.error('Audio upload error:', err);
            chat.addSystemMessage('Error uploading audio. Please try again.');
            audio.resetForNextQuestion();
            audio.startRecording();
        }
    }

    function handleWSMessage(event) {
        const msg = JSON.parse(event.data);

        switch (msg.type) {
            case 'interviewer_message':
                chat.addMessage('interviewer', msg.content);
                waitingForInterviewer = false;
                // Start recording for candidate's response
                if (audio && interviewStarted) {
                    audio.resetForNextQuestion();
                    audio.startRecording();
                }
                break;

            case 'thinking':
                chat.showTyping();
                break;

            case 'timer_sync':
                timer.sync(msg.remaining_seconds);
                break;

            case 'status_change':
                if (msg.status === 'completed') {
                    if (audio) audio.destroy();
                    timer.stop();
                    doneBtn.disabled = true;
                    endBtn.disabled = true;
                    // Redirect to dashboard — analysis runs in background
                    // Dashboard will show "Analyzing" status and report when ready
                    setTimeout(() => {
                        window.location.href = '/dashboard';
                    }, 2000);
                }
                break;

            case 'error':
                chat.addSystemMessage('Error: ' + msg.message);
                break;
        }
    }

    startBtn.addEventListener('click', async () => {
        startBtn.disabled = true;
        startBtn.setAttribute('aria-busy', 'true');

        try {
            audio = new AudioCapture({
                onAudioReady: handleAudioReady,
                onStateChange: updateMicUI,
            });
            await audio.init();
        } catch (err) {
            alert('Microphone access required. Please allow mic access and try again.');
            startBtn.disabled = false;
            startBtn.removeAttribute('aria-busy');
            return;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        ws = new WebSocket(`${protocol}//${window.location.host}/ws/interview/${INTERVIEW_ID}`);

        ws.onopen = () => {
            interviewStarted = true;
            startBtn.style.display = 'none';
            timer.start();
            ws.send(JSON.stringify({ type: 'start' }));
        };

        ws.onmessage = handleWSMessage;

        ws.onclose = () => {
            if (interviewStarted && !overlay.style.display.includes('flex')) {
                chat.addSystemMessage('Connection lost. Refresh to reconnect.');
            }
        };

        ws.onerror = () => {
            chat.addSystemMessage('WebSocket error. Please refresh the page.');
        };
    });

    doneBtn.addEventListener('click', () => {
        if (audio && audio.isRecording) {
            audio.submit();
        }
    });

    endBtn.addEventListener('click', () => {
        if (!interviewStarted) return;
        if (confirm('End the interview? Your analysis will be generated.')) {
            if (audio) audio.cancel();
            ws.send(JSON.stringify({ type: 'end' }));
        }
    });
})();
