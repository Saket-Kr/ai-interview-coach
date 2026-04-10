/**
 * Chat UI rendering — append messages to the chat container.
 */
class ChatUI {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.typingIndicator = null;
    }

    addMessage(role, content) {
        this.removeTyping();
        const div = document.createElement('div');
        div.className = `chat-msg ${role}`;
        div.textContent = content;
        this.container.appendChild(div);
        this._scrollToBottom();
    }

    addSystemMessage(content) {
        this.removeTyping();
        const div = document.createElement('div');
        div.className = 'chat-msg system';
        div.textContent = content;
        this.container.appendChild(div);
        this._scrollToBottom();
    }

    showTyping() {
        if (this.typingIndicator) return;
        this.typingIndicator = document.createElement('div');
        this.typingIndicator.className = 'chat-msg interviewer typing-indicator';
        this.typingIndicator.textContent = 'Thinking...';
        this.container.appendChild(this.typingIndicator);
        this._scrollToBottom();
    }

    removeTyping() {
        if (this.typingIndicator) {
            this.typingIndicator.remove();
            this.typingIndicator = null;
        }
    }

    _scrollToBottom() {
        this.container.scrollTop = this.container.scrollHeight;
    }
}
