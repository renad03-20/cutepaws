document.addEventListener('DOMContentLoaded', function() {
    const messageContainer = document.querySelector('.message-container');
    
    // Auto-scroll to bottom
    messageContainer.scrollTop = messageContainer.scrollHeight;
    
    // Optional: Poll for new messages every 5 seconds
    setInterval(() => {
        fetch(window.location.href)
            .then(res => res.text())
            .then(html => {
                const parser = new DOMParser();
                const newDoc = parser.parseFromString(html, 'text/html');
                const newMessages = newDoc.querySelector('.message-container').innerHTML;
                
                if (newMessages !== messageContainer.innerHTML) {
                    messageContainer.innerHTML = newMessages;
                    messageContainer.scrollTop = messageContainer.scrollHeight;
                }
            });
    }, 5000);
});