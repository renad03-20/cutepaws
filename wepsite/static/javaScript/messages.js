document.addEventListener('DOMContentLoaded', function() {

    const currentUserId = window.currentUserId;
    const currentUserName = window.currentUserName;
    const applicationId = window.applicationId;

    const messageContainer = document.getElementById('messagesContainer');
    const messageInput = document.querySelector('input[name="message"]');
    const sendBtn = document.getElementById('sendBtn');
    const charCount = document.getElementById('charCount');
    const messageCountEl = document.getElementById('messageCount');
    const connectionStatus = document.getElementById('connectionStatus');
    
    // Initial state setup
    let messageCounter = window.messageCount || 0;
    let currentSequence = window.currentSequence || 0;
    let pendingMessages = new Map(); // Track messages being sent
    let usePolling = false;
    let pollingInterval;
    let isUserAtBottom = true;
    
    // Track scroll position to determine if user is at bottom
    if (messageContainer) {
        messageContainer.addEventListener('scroll', () => {
            const threshold = 50; // pixels from bottom
            isUserAtBottom = messageContainer.scrollHeight - messageContainer.scrollTop - messageContainer.clientHeight <= threshold;
        });
    }

    // --- Helper Functions ---

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
            // Use smooth scroll to prevent jarring jumps
            messageContainer.scrollTo({
                top: messageContainer.scrollHeight,
                behavior: 'smooth'
            });
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

        const messageClass = messageData.sender_id === currentUserId ? 'message-sent' : 'message-received';
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
                            ${messageData.sender_id === currentUserId ? `
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
        
        // Only scroll if user was at bottom or this is their own message
        if (isUserAtBottom || messageData.sender_id === currentUserId) {
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
        if (messageCountEl) {
            messageCountEl.textContent = `${messageCounter} message${messageCounter !== 1 ? 's' : ''}`;
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

    // Polling fallback function
    function pollForMessages() {
        if (!usePolling) return;
        
        const pollUrl = new URL(window.location.href);
        pollUrl.searchParams.set('poll', '1');
        
        fetch(pollUrl, {
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
                    
                    newMessages.forEach(newMsg => {
                        const clientId = newMsg.dataset.clientId;
                        const sequence = parseInt(newMsg.dataset.sequence);
                        
                        // Check if message is truly new and hasn't been added optimistically
                        if (!messageContainer.querySelector(`[data-client-id="${clientId}"]`) && sequence > currentSequence) {
                            messageContainer.appendChild(newMsg.cloneNode(true));
                            messageCounter++;
                            currentSequence = sequence;
                        }
                    });
                    
                    updateMessageCount();
                    
                    // Only scroll to bottom if user was at bottom
                    if (isUserAtBottom) {
                        scrollToBottom();
                    }
                }
            })
            .catch(err => {
                console.log('Polling failed:', err);
            });
    }
    
    // -----------------------------------------------------------------
    // EXPORTING HELPERS TO WINDOW SCOPE
    // -----------------------------------------------------------------
    window.addMessageToDOM = addMessageToDOM;
    window.updateMessageStatus = updateMessageStatus;
    window.generateClientId = generateClientId;
    window.pendingMessages = pendingMessages;
    window.pollForMessages = pollForMessages;
    window.currentSequence = currentSequence;
    window.pollingInterval = pollingInterval;
    window.usePolling = usePolling;

    // --- Socket.IO Implementation ---

    let socket;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;

    function initializeSocket() {
        try {
            socket = io({
                transports: ['websocket', 'polling'],
                timeout: 10000,
                reconnection: true,
                reconnectionAttempts: maxReconnectAttempts,
                reconnectionDelay: 1000
            });

            // Connection handlers
            socket.on('connect', () => {
                console.log('Socket.IO: Connected to server');
                updateConnectionStatus(true);
                reconnectAttempts = 0;
                
                // Disable manual polling when Socket.IO is working
                window.usePolling = false;
                if (window.pollingInterval) {
                    clearInterval(window.pollingInterval);
                    window.pollingInterval = null;
                }
                
                // CRITICAL: Join the application room immediately after connection
                socket.emit('join_room', { application_id: applicationId });
                console.log('Socket.IO: Joined room for application', applicationId);
                
                // Request synchronization
                socket.emit('sync_messages', {
                    application_id: applicationId,
                    last_sequence: window.currentSequence
                });
            });

            socket.on('room_joined', (data) => {
                console.log('Socket.IO: Successfully joined room:', data.room);
            });

            socket.on('disconnect', (reason) => {
                console.log('Socket.IO: Disconnected:', reason);
                updateConnectionStatus(false);
                
                // Re-enable polling as fallback
                window.usePolling = true;
                if (!window.pollingInterval) {
                    window.pollingInterval = setInterval(window.pollForMessages, 5000);
                }
            });

            socket.on('connect_error', (error) => {
                console.log('Socket.IO: Connection error:', error);
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
                console.log('Socket.IO: Received sync response with', data.missed_messages.length, 'missed messages');
                data.missed_messages.forEach(messageData => {
                    window.addMessageToDOM(messageData, 'sent');
                });
                
                if (data.current_sequence) {
                    window.currentSequence = data.current_sequence;
                }
            });

            // Message handlers - CRITICAL: Handle incoming messages properly
            socket.on('new_message', (data) => {
                console.log('Socket.IO: Received new message:', data);
                
                const existingMessage = messageContainer.querySelector(`[data-client-id="${data.client_id}"]`);
                
                if (!existingMessage) {
                    window.addMessageToDOM(data, 'sent');
                    
                    // Keep input focused if user was typing
                    if (messageInput && document.activeElement === messageInput) {
                        setTimeout(() => messageInput.focus(), 50);
                    }
                    
                    // Show notification for received messages (not your own)
                    if (data.sender_id !== currentUserId) {
                        showToast(`New message from ${data.sender}`, 'success');
                    }
                }
            });

            socket.on('message_confirmed', (data) => {
                console.log('Socket.IO: Message confirmed:', data);
                if (window.pendingMessages.has(data.client_id)) {
                    const element = messageContainer.querySelector(`[data-client-id="${data.client_id}"]`);
                    if (element) {
                        window.updateMessageStatus(element, 'sent', data);
                    }
                    window.pendingMessages.delete(data.client_id);
                }
            });

            socket.on('message_failed', (data) => {
                console.log('Socket.IO: Message failed:', data);
                if (data.client_id) {
                    const element = messageContainer.querySelector(`[data-client-id="${data.client_id}"]`);
                    if (element) {
                        window.updateMessageStatus(element, 'failed');
                        element.addEventListener('click', () => {
                            retryMessage(data.client_id, element);
                        }, { once: true });
                    }
                    window.pendingMessages.delete(data.client_id);
                }
                
                showToast(data.error || 'Failed to send message', 'error');
                if (sendBtn && messageInput) {
                    sendBtn.disabled = false;
                    messageInput.focus();
                }
            });

            socket.on('error', (data) => {
                console.log('Socket.IO: Error:', data);
                showToast(data.message || 'An error occurred', 'error');
                if (sendBtn) sendBtn.disabled = false;
            });

            // Retry failed message logic
            function retryMessage(clientId, element) {
                const content = element.querySelector('.message-content').textContent;
                const newClientId = window.generateClientId();
                
                element.dataset.clientId = newClientId;
                window.updateMessageStatus(element, 'sending');
                
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

                    if (content.length > 1000) {
                        showToast('Message too long (max 1000 characters)', 'error');
                        messageInput.focus();
                        return;
                    }

                    const clientId = window.generateClientId();
                    
                    // Show optimistic UI immediately
                    const messageData = {
                        client_id: clientId,
                        sender: currentUserName || 'You',
                        sender_id: currentUserId,
                        content: content,
                        timestamp: new Date().toLocaleString('en-US', {
                            month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true
                        }),
                        sequence_number: window.currentSequence + 1
                    };
                    
                    window.addMessageToDOM(messageData, 'sending');
                    
                    // Clear input immediately but maintain focus
                    messageInput.value = '';
                    if (charCount) charCount.textContent = '0';
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
                                messageInput.focus();
                            }
                        }, 500);
                    } else {
                        // HTTP Fallback (AJAX) - NO PAGE RELOAD
                        const formData = new FormData();
                        formData.append('message', content);
                        formData.append('client_id', clientId);
                        
                        // Get form_id if it exists
                        const formIdInput = document.querySelector('input[name="form_id"]');
                        if (formIdInput) {
                            formData.append('form_id', formIdInput.value);
                        }
                        
                        fetch(messageForm.action, {
                            method: 'POST',
                            body: formData,
                            headers: {
                                'X-Requested-With': 'XMLHttpRequest'
                            }
                        })
                        .then(response => {
                            if (response.ok) {
                                return response.json();
                            }
                            throw new Error('HTTP send failed');
                        })
                        .then(data => {
                            // Message sent successfully via HTTP
                            const element = messageContainer.querySelector(`[data-client-id="${clientId}"]`);
                            if (element) {
                                window.updateMessageStatus(element, 'sent');
                            }
                            showToast('Message sent via fallback', 'success');
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
                            messageInput.focus();
                        });
                    }
                });
            }

        } catch (e) {
            console.error("Socket.IO initialization failed:", e);
            showToast("Using fallback messaging mode", "error");
            updateConnectionStatus(false);
            window.usePolling = true;
        }
    }

    // --- Initial Setup ---
    
    // Initial scroll and setup
    scrollToBottom();
    currentSequence = getLastSequence();
    
    // Auto-focus input when page loads
    if (messageInput) {
        setTimeout(() => {
            messageInput.focus();
            console.log('Auto-focused message input');
        }, 500);
    }

    // Start polling by default, will be disabled if Socket.IO connects
    window.usePolling = true;
    window.pollingInterval = setInterval(pollForMessages, 5000);
    
    // Initialize socket connection
    initializeSocket();

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
            messageInput.focus();
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
});