document.addEventListener('DOMContentLoaded', () => {
    // 1. Get Data from HTML
    const dataDiv = document.getElementById('chat-data');
    if (!dataDiv) return; // Not on the messages page

    const applicationId = dataDiv.dataset.applicationId;
    const currentUserId = parseInt(dataDiv.dataset.userId);

    // 2. DOM Elements
    const messageContainer = document.getElementById('messages-container');
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const statusIndicator = document.getElementById('connection-status');

    // 3. Helper: Scroll to bottom
    function scrollToBottom() {
        if(messageContainer) {
            messageContainer.scrollTop = messageContainer.scrollHeight;
        }
    }
    // Initial scroll
    scrollToBottom();

    // 4. Helper: Render a message
    function appendMessage(data) {
        const isMe = (parseInt(data.sender_id) === currentUserId);
        
        const wrapper = document.createElement('div');
        wrapper.className = `d-flex mb-3 ${isMe ? 'justify-content-end' : 'justify-content-start'}`;
        
        const bgClass = isMe ? 'bg-primary text-white' : 'bg-white border';
        const textMutedClass = isMe ? 'text-light' : 'text-muted';

        wrapper.innerHTML = `
            <div class="message-box p-3 rounded ${bgClass}" style="max-width: 75%;">
                <p class="mb-1">${data.content}</p>
                <small class="${textMutedClass}">${data.timestamp || 'Just now'}</small>
            </div>
        `;
        
        messageContainer.appendChild(wrapper);
        scrollToBottom();
    }

    // 5. Initialize Socket.IO
    const socket = io();

    socket.on('connect', () => {
        console.log('Connected to server');
        if(statusIndicator) statusIndicator.style.display = 'none';
        
        // This MUST match the @socketio.on('join_application') in views.py
        socket.emit('join_application', { application_id: applicationId });
    });

    socket.on('disconnect', () => {
        console.log('Disconnected');
        if(statusIndicator) {
            statusIndicator.style.display = 'block';
            statusIndicator.textContent = 'Disconnected - Reconnecting...';
        }
    });

    // Receive message
    socket.on('new_message', (data) => {
        appendMessage(data);
    });

    socket.on('message_error', (data) => {
        alert("Error: " + data.error);
    });

    // Send message
    if (chatForm) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault(); // STOP PAGE REFRESH

            const content = messageInput.value.trim();
            if (!content) return;

            // Emit to server
            socket.emit('send_message_socket', {
                application_id: applicationId,
                content: content,
                client_id: Date.now().toString()
            });

            // Clear input
            messageInput.value = '';
            messageInput.focus();
        });
    }
});