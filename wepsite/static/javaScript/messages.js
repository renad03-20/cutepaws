document.addEventListener('DOMContentLoaded', function() {
    const messageContainer = document.getElementById('messagesContainer');
    const messageInput = document.querySelector('input[name="message"]');
    const sendBtn = document.getElementById('sendBtn');
    const charCount = document.getElementById('charCount');
    const messageCount = document.getElementById('messageCount');
    const connectionStatus = document.getElementById('connectionStatus');
    
    let messageCounter = window.messageCount || 0;
    let currentSequence = window.currentSequence || 0;
    let pendingMessages = new Map(); // Track messages being sent
    let usePolling = false;
    let pollingInterval;
    
    // Generate client ID for messages
    function generateClientId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }

    // Get last sequence number from DOM
    function getLastSequence() {
        const lastMessage = messageContainer.querySelector('.message-wrapper:last-child');
        return lastMessage ? parseInt(lastMessage.dataset.sequence) || 0 : 0;
    }

    // Smart scroll that doesn't cause page jumps
    function scrollToBottom() {
        if (messageContainer) {
            // Check if user was near bottom before scrolling
            const isNearBottom = messageContainer.scrollTop + messageContainer.clientHeight >= messageContainer.scrollHeight - 50;
            
            if (isNearBottom) {
                // Use smooth scroll to prevent jarring jumps
                messageContainer.scrollTo({
                    top: messageContainer.scrollHeight,
                    behavior: 'smooth'
                });
            }
        }
    }

    // Add message to DOM with better scroll handling
    function addMessageToDOM(messageData, status = 'sent') {
        const existingMessage = messageContainer.querySelector(`[data-client-id="${messageData.client_id}"]`);
        if (existingMessage) {
            // Update existing message
            updateMessageStatus(existingMessage, status, messageData);
            return;
        }

        const userId = window.currentUserId || 0;
        const messageClass = messageData.sender_id === userId ? 'message-sent' : 'message-received';
        const statusClass = status === 'sending' ? 'message-sending' : '';
        
        const messageHtml = `
            <div class="message-wrapper ${statusClass}" 
                 data-message-id="${messageData.id || 'temp'}" 
                 data-sequence="${messageData.sequence_number || currentSequence + 1}"
                 data-client-id="${messageData.client_id}">
                <div class="message ${messageClass}">
                    <div class="message-bubble">
                        <div class="message-header">
                            <span class="sender-name">${messageData.sender}</span>
                            <span class="message-time">${messageData.timestamp}</span>
                            ${messageData.sender_id === userId ? `
                                <span class="read-status">
                                    <i class="read-icon ${status === 'sending' ? 'sending' : 'delivered'}" 
                                       title="${status === 'sending' ? 'Sending...' : 'Delivered'}">
                                       ${status === 'sending' ? '⏳' : '✓'}
                                    </i>
                                </span>` : ''}
                        </div>
                        <p class="message-content">${messageData.content}</p>
                        ${status === 'failed' ? '<div class="message-error">❌ Failed to send</div>' : ''}
                    </div>
                </div>
            </div>
        `;
        
        messageContainer.insertAdjacentHTML('beforeend', messageHtml);
        
        // Only scroll if this is user's own message or they were at bottom
        const wasAtBottom = messageContainer.scrollTop + messageContainer.clientHeight >= messageContainer.scrollHeight - 100;
        const isOwnMessage = messageData.sender_id === userId;
        
        if (isOwnMessage || wasAtBottom) {
            // Small delay to ensure DOM is updated
            setTimeout(() => {
                scrollToBottom();
            }, 10);
        }
        
        // Update counter
        messageCounter++;
        updateMessageCount();
        
        // Update sequence
        if (messageData.sequence_number) {
            currentSequence = Math.max(currentSequence, messageData.sequence_number);
        }
    }

    // Update message status
    function updateMessageStatus(element, status, messageData = null) {
        const readIcon = element.querySelector('.read-icon');
        const messageError = element.querySelector('.message-error');
        
        // Remove any existing error messages
        if (messageError) messageError.remove();
        
        element.classList.remove('message-sending', 'message-failed');
        
        switch (status) {
            case 'sent':
                element.classList.remove('message-sending');
                if (readIcon) {
                    readIcon.className = 'read-icon delivered';
                    readIcon.textContent = '✓';
                    readIcon.title = 'Delivered';
                }
                if (messageData && messageData.id) {
                    element.dataset.messageId = messageData.id;
                }
                break;
            case 'failed':
                element.classList.add('message-failed');
                if (readIcon) {
                    readIcon.className = 'read-icon failed';
                    readIcon.textContent = '❌';
                    readIcon.title = 'Failed';
                }
                element.querySelector('.message-bubble').insertAdjacentHTML('beforeend', 
                    '<div class="message-error">❌ Failed to send. Click to retry.</div>');
                break;
            case 'sending':
                element.classList.add('message-sending');
                if (readIcon) {
                    readIcon.className = 'read-icon sending';
                    readIcon.textContent = '⏳';
                    readIcon.title = 'Sending...';
                }
                break;
        }
    }

    function updateMessageCount() {
        if (messageCount) {
            messageCount.textContent = `${messageCounter} message${messageCounter !== 1 ? 's' : ''}`;
        }
    }

    function showToast(message, type = 'error') {
        const toast = document.getElementById(type + 'Toast');
        if (toast) {
            toast.textContent = message;
            toast.style.display = 'block';
            setTimeout(() => {
                toast.style.display = 'none';
            }, 5000);
        }
    }

    function updateConnectionStatus(connected) {
        if (connectionStatus) {
            connectionStatus.style.display = 'block';
            if (connected) {
                connectionStatus.className = 'connection-status status-connected';
                connectionStatus.textContent = '🟢 Connected';
                setTimeout(() => {
                    connectionStatus.style.display = 'none';
                }, 3000);
            } else {
                connectionStatus.className = 'connection-status status-disconnected';
                connectionStatus.textContent = '🔴 Disconnected - Using fallback';
            }
        }
    }

    // Polling fallback function with better error handling
    function pollForMessages() {
        if (!usePolling) return;
        
        fetch(window.location.href + '?poll=1', {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
            .then(res => res.text())
            .then(html => {
                const parser = new DOMParser();
                const newDoc = parser.parseFromString(html, 'text/html');
                const newContainer = newDoc.getElementById('messagesContainer');
                
                if (newContainer) {
                    const newMessages = Array.from(newContainer.querySelectorAll('.message-wrapper'));
                    const existingMessages = Array.from(messageContainer.querySelectorAll('.message-wrapper'));
                    
                    // Only add truly new messages
                    newMessages.forEach(newMsg => {
                        const clientId = newMsg.dataset.clientId;
                        const sequence = parseInt(newMsg.dataset.sequence);
                        
                        if (!messageContainer.querySelector(`[data-client-id="${clientId}"]`) && sequence > currentSequence) {
                            messageContainer.appendChild(newMsg.cloneNode(true));
                            messageCounter++;
                            currentSequence = sequence;
                        }
                    });
                    
                    updateMessageCount();
                    scrollToBottom();
                }
            })
            .catch(err => {
                console.log('Polling failed:', err);
            });
    }

    // Character counter
    if (messageInput && charCount) {
        messageInput.addEventListener('input', function() {
            const count = this.value.length;
            charCount.textContent = count;
            
            if (count > 950) {
                charCount.style.color = '#dc3545';
            } else if (count > 800) {
                charCount.style.color = '#ffc107';
            } else {
                charCount.style.color = '#6c757d';
            }
        });
    }

    // Prevent form resubmission on page refresh
    if (window.history.replaceState && window.location.search) {
        window.history.replaceState(null, null, window.location.pathname);
    }

    // Initial scroll and setup
    scrollToBottom();
    currentSequence = getLastSequence();
    
    // Auto-focus input when page loads
    if (messageInput) {
        setTimeout(() => messageInput.focus(), 500);
    }
    
    // Start polling by default, will be disabled if Socket.IO connects
    usePolling = true;
    pollingInterval = setInterval(pollForMessages, 5000);
});

// Socket.IO implementation 
let socket;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

function initializeSocket() {
    try {
        socket = io({
            transports: ['websocket', 'polling'],
            timeout: 5000,
            reconnection: true,
            reconnectionAttempts: maxReconnectAttempts,
            reconnectionDelay: 1000
        });

        const applicationId = window.applicationId || '';
        const userId = window.currentUserId || 0;
        const messageContainer = document.getElementById('messagesContainer');
        const messageInput = document.querySelector('input[name="message"]');
        const sendBtn = document.getElementById('sendBtn');

        // Connection handlers
        socket.on('connect', () => {
            console.log('Connected to server');
            updateConnectionStatus(true);
            reconnectAttempts = 0;
            
            // Disable polling when Socket.IO is working
            window.usePolling = false;
            if (window.pollingInterval) {
                clearInterval(window.pollingInterval);
                window.pollingInterval = null;
            }
            
            // Join the application room
            socket.emit('join_room', { application_id: applicationId });
            
            // Request synchronization
            socket.emit('sync_messages', {
                application_id: applicationId,
                last_sequence: window.currentSequence
            });
        });

        socket.on('disconnect', (reason) => {
            console.log('Disconnected:', reason);
            updateConnectionStatus(false);
            
            // Re-enable polling as fallback
            window.usePolling = true;
            if (!window.pollingInterval) {
                window.pollingInterval = setInterval(window.pollForMessages, 5000);
            }
        });

        socket.on('connect_error', (error) => {
            console.log('Connection error:', error);
            reconnectAttempts++;
            if (reconnectAttempts >= maxReconnectAttempts) {
                showToast('Connection failed. Using fallback mode.', 'error');
                window.usePolling = true;
                if (!window.pollingInterval) {
                    window.pollingInterval = setInterval(window.pollForMessages, 5000);
                }
            }
        });

        // Synchronization handler
        socket.on('sync_response', (data) => {
            console.log('Sync response:', data);
            
            data.missed_messages.forEach(messageData => {
                window.addMessageToDOM(messageData, 'sent');
            });
            
            if (data.current_sequence) {
                window.currentSequence = data.current_sequence;
            }
        });

        // Message handlers with focus preservation
        socket.on('new_message', (data) => {
            // Check if message already exists
            const existingMessage = messageContainer.querySelector(`[data-client-id="${data.client_id}"]`);
            
            if (!existingMessage) {
                window.addMessageToDOM(data, 'sent');
                
                // PRESERVE INPUT FOCUS when receiving messages
                const messageInput = document.querySelector('input[name="message"]');
                if (messageInput && document.activeElement === messageInput) {
                    // User was typing, maintain focus
                    setTimeout(() => messageInput.focus(), 50);
                }
                
                // Show notification for received messages
                if (data.sender_id !== userId) {
                    showToast(`New message from ${data.sender}`, 'success');
                }
            }
        });

        socket.on('message_confirmed', (data) => {
            // Remove from pending and update status
            if (window.pendingMessages.has(data.client_id)) {
                const element = messageContainer.querySelector(`[data-client-id="${data.client_id}"]`);
                if (element) {
                    window.updateMessageStatus(element, 'sent', data);
                }
                window.pendingMessages.delete(data.client_id);
            }
        });

        socket.on('message_failed', (data) => {
            // Update message status to failed
            if (data.client_id) {
                const element = messageContainer.querySelector(`[data-client-id="${data.client_id}"]`);
                if (element) {
                    window.updateMessageStatus(element, 'failed');
                    
                    // Add retry functionality
                    element.addEventListener('click', () => {
                        retryMessage(data.client_id, element);
                    });
                }
                window.pendingMessages.delete(data.client_id);
            }
            
            showToast(data.error || 'Failed to send message', 'error');
            if (sendBtn) {
                sendBtn.disabled = false;
                // MAINTAIN FOCUS on error
                if (messageInput) messageInput.focus();
            }
        });

        socket.on('error', (data) => {
            showToast(data.message || 'An error occurred', 'error');
            if (sendBtn) {
                sendBtn.disabled = false;
                // MAINTAIN FOCUS on error
                if (messageInput) messageInput.focus();
            }
        });

        socket.on('status_update', (data) => {
            console.log('Status update:', data.message);
            if (data.last_sequence !== undefined) {
                window.currentSequence = Math.max(window.currentSequence, data.last_sequence);
            }
        });

        // Retry failed message
        function retryMessage(clientId, element) {
            const content = element.querySelector('.message-content').textContent;
            const newClientId = window.generateClientId();
            
            // Update element with new client ID
            element.dataset.clientId = newClientId;
            window.updateMessageStatus(element, 'sending');
            
            // Send with new client ID
            socket.emit('send_message', {
                application_id: applicationId,
                content: content,
                client_id: newClientId
            });
            
            window.pendingMessages.set(newClientId, {
                content: content,
                timestamp: new Date()
            });
        }

        // Send message with proper UX handling
        const messageForm = document.getElementById('message-form');
        if (messageForm) {
            messageForm.addEventListener('submit', (e) => {
                e.preventDefault();
                
                if (!messageInput || !sendBtn) return;
                
                const content = messageInput.value.trim();
                if (!content) return;

                // Validate message length
                if (content.length > 1000) {
                    showToast('Message too long (max 1000 characters)', 'error');
                    messageInput.focus(); // Keep focus even on error
                    return;
                }

                // Generate client ID
                const clientId = window.generateClientId();
                
                // Show optimistic UI immediately
                const messageData = {
                    client_id: clientId,
                    sender: window.currentUserName || 'You',
                    sender_id: userId,
                    content: content,
                    timestamp: new Date().toLocaleString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        hour: 'numeric',
                        minute: '2-digit',
                        hour12: true
                    }),
                    sequence_number: window.currentSequence + 1
                };
                
                window.addMessageToDOM(messageData, 'sending');
                
                // Clear input immediately
                messageInput.value = '';
                const charCount = document.getElementById('charCount');
                if (charCount) charCount.textContent = '0';

                // KEEP INPUT FOCUSED
                messageInput.focus();
                
                // Disable send button temporarily
                sendBtn.disabled = true;
                
                if (socket && socket.connected) {
                    // Send via Socket.IO
                    socket.emit('send_message', {
                        application_id: applicationId,
                        content: content,
                        client_id: clientId
                    });
                    
                    // Track pending message
                    window.pendingMessages.set(clientId, {
                        content: content,
                        timestamp: new Date()
                    });
                    
                    // Re-enable button after short delay
                    setTimeout(() => {
                        if (sendBtn) {
                            sendBtn.disabled = false;
                            // ENSURE INPUT STAYS FOCUSED
                            messageInput.focus();
                        } 
                    }, 500);
                } else {
                    // REPLACE FORM SUBMIT WITH FETCH TO PREVENT PAGE JUMP
                    const formData = new FormData();
                    formData.append('message', content);
                    formData.append('form_id', document.querySelector('input[name="form_id"]').value);
                    formData.append('client_id', clientId);
                    
                    fetch(window.location.href, {
                        method: 'POST',
                        body: formData,
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    })
                    .then(response => {
                        if (response.ok) {
                            // Message sent successfully via HTTP
                            const element = messageContainer.querySelector(`[data-client-id="${clientId}"]`);
                            if (element) {
                                window.updateMessageStatus(element, 'sent');
                            }
                            showToast('Message sent', 'success');
                        } else {
                            throw new Error('HTTP send failed');
                        }
                    })
                    .catch(error => {
                        console.error('HTTP fallback failed:', error);
                        const element = messageContainer.querySelector(`[data-client-id="${clientId}"]`);
                        if (element) {
                            window.updateMessageStatus(element, 'failed');
                        }
                        showToast('Failed to send message', 'error');
                    })
                    .finally(() => {
                        sendBtn.disabled = false;
                        // CRITICAL: MAINTAIN FOCUS AFTER HTTP FALLBACK
                        messageInput.focus();
                    });
                }
            });
        }

        // Quick reply buttons with maintained focus
        document.querySelectorAll('.quick-reply-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const replies = {
                    "approved": "Your application has been approved! Please contact us to arrange pickup.",
                    "questions": "We need more information about your home environment before proceeding.",
                    "rejected": "We need more details about your living situation before we can approve this application."
                };
                
                if (messageInput && replies[btn.dataset.reply]) {
                    messageInput.value = replies[btn.dataset.reply];
                    messageInput.focus(); // MAINTAIN FOCUS
                    
                    // Update character counter
                    const charCount = document.getElementById('charCount');
                    if (charCount) {
                        charCount.textContent = messageInput.value.length;
                    }
                }
            });
        });

    } catch (e) {
        console.log("Socket.IO initialization failed:", e);
        showToast("Using fallback messaging mode", "error");
        updateConnectionStatus(false);
        window.usePolling = true;
    }
}

// Initialize socket connection
initializeSocket();

// Cleanup pending messages older than 30 seconds
setInterval(() => {
    const now = new Date();
    for (const [clientId, messageInfo] of window.pendingMessages.entries()) {
        if (now - messageInfo.timestamp > 30000) {
            const element = document.querySelector(`[data-client-id="${clientId}"]`);
            if (element) {
                window.updateMessageStatus(element, 'failed');
            }
            window.pendingMessages.delete(clientId);
        }
    }
}, 10000);

// Keyboard shortcuts with better focus handling
document.addEventListener('keydown', function(e) {
    const messageInput = document.querySelector('input[name="message"]');
    
    // Ctrl/Cmd + Enter to send message
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && messageInput && messageInput.value.trim()) {
        e.preventDefault();
        const form = document.getElementById('message-form');
        if (form) {
            const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
            form.dispatchEvent(submitEvent);
        }
    }
    
    // Escape to clear input but maintain focus
    if (e.key === 'Escape' && messageInput) {
        messageInput.value = '';
        const charCount = document.getElementById('charCount');
        if (charCount) charCount.textContent = '0';
        messageInput.focus(); // KEEP FOCUS AFTER CLEARING
    }
});

// Prevent accidental page refresh
window.addEventListener('beforeunload', function(e) {
    if (window.pendingMessages && window.pendingMessages.size > 0) {
        e.preventDefault();
        e.returnValue = 'You have messages being sent. Are you sure you want to leave?';
        return e.returnValue;
    }
});

// Handle visibility changes to maintain focus
document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
        const messageInput = document.querySelector('input[name="message"]');
        if (messageInput) {
            setTimeout(() => messageInput.focus(), 100);
        }
    }
});