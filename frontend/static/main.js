function handleEnter(event) {
    const userInput = document.getElementById('user-input');

    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault(); // Prevent default new line
        sendMessage(); // Trigger message sending
    } else if (event.key === 'Enter') {
        userInput.style.height = 'auto'; // Reset height for recalculation
        userInput.style.height = `${userInput.scrollHeight}px`; // Adjust height to content
    }
}

function renderResponse(text) {
    // Sanitize the entire text first
    const sanitizedText = DOMPurify.sanitize(text);

    // Process code blocks
    return sanitizedText.replace(/```(\w+)?\s*[\n\r]+([\s\S]*?)```/g, (match, language, code) => {
        return renderCodeBlock(language || 'plaintext', code.trim());
    });
}

function renderCodeBlock(language, code) {
    const normalizedLanguage = language.toLowerCase() === 'terraform' ? 'hcl' : language.toLowerCase();
    const sanitizedLanguage = DOMPurify.sanitize(normalizedLanguage, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] });
    const sanitizedCode = DOMPurify.sanitize(code, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] });
    return `<pre><code class="language-${sanitizedLanguage}">${sanitizedCode}</code></pre>`;
}

// Dynamically add user and bot messages
function sendMessage() {
    const userInput = document.getElementById('user-input');
    const chatWindow = document.getElementById('chat-window');
    const message = userInput.value.trim();

    if (!message) return; // Do nothing if the input is empty

    // Disable the input box while the bot is responding
    userInput.disabled = true;

    // Sanitize user input
    const sanitizedMessage = DOMPurify.sanitize(message);

    // Add user message to the chat window
    const userMessage = document.createElement('div');
    userMessage.className = 'message user-message';
    userMessage.textContent = sanitizedMessage;
    chatWindow.appendChild(userMessage);

    userInput.value = ''; // Clear the input box
    userInput.style.height = 'auto'; // Reset textarea height
    chatWindow.scrollTop = chatWindow.scrollHeight; // Scroll to the bottom

    // Display bot typing indicator
    const botMessage = document.createElement('div');
    botMessage.className = 'message bot-message loading-indicator';
    botMessage.textContent = 'Typing...';
    chatWindow.appendChild(botMessage);

    chatWindow.scrollTop = chatWindow.scrollHeight; // Ensure the latest message is visible

    // Send the query to the backend
    fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: message })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        // Remove the shimmer effect by replacing the class
        botMessage.classList.remove('loading-indicator');
        botMessage.classList.add('bot-message'); // Ensure the proper class for bot messages
        
        // Render the response (sanitization occurs inside renderResponse)
        const formattedResponse = renderResponse(data.response);
        botMessage.innerHTML = formattedResponse;

        // Apply syntax highlighting to the new content
        Prism.highlightAllUnder(botMessage);

        // Enable code copying for all code blocks
        enableCodeCopying();

        // Scroll to the bottom after rendering the response
        chatWindow.scrollTop = chatWindow.scrollHeight;
    })
    .catch(error => {
        console.error('Error in fetch operation:', error);
        botMessage.classList.remove('loading-indicator');
        botMessage.classList.add('bot-message');
        botMessage.textContent = `Error: ${error.message || 'Something went wrong. Please try again later.'}`;
    })    
    .finally(() => {
        // Re-enable the input box after the bot has responded
        userInput.disabled = false;
        userInput.focus(); // Bring the focus back to the input box
    });
}

function startNewConversation() {
    document.getElementById('chat-window').innerHTML = '';
    fetch('/new_conversation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });
}

function enableCodeCopying() {
    const chatWindow = document.getElementById('chat-window');
    const codeBlocks = chatWindow.querySelectorAll('pre:not(.copy-enabled)');

    codeBlocks.forEach(block => {
        block.classList.add('copy-enabled');
        const copyButton = document.createElement('button');
        copyButton.className = 'copy-button';
        copyButton.textContent = 'Copy';

        copyButton.addEventListener('click', () => {
            const codeElement = block.querySelector('code');
            const codeText = codeElement ? codeElement.innerText : '';

            navigator.clipboard.writeText(codeText).then(() => {
                copyButton.textContent = 'Copied!';
                setTimeout(() => (copyButton.textContent = 'Copy'), 2000);
            }).catch(err => {
                console.error('Failed to copy text: ', err);
            });
        });

        block.appendChild(copyButton);
    });
}


// Add event listeners
document.addEventListener('DOMContentLoaded', () => {
    const newChatButton = document.getElementById('new-chat-btn');
    const sendButton = document.getElementById('send-button');
    const userInput = document.getElementById('user-input');

    if (newChatButton) {
        newChatButton.addEventListener('click', startNewConversation);
    }

    if (sendButton) {
        sendButton.addEventListener('click', sendMessage);
    }

    if (userInput) {
        userInput.addEventListener('keydown', handleEnter);

        // Add auto-resizing with max-height restriction
        userInput.addEventListener('input', () => {
            userInput.style.height = 'auto'; // Reset height to calculate scrollHeight
            if (userInput.scrollHeight <= 150) { // Match max-height from CSS
                userInput.style.height = `${userInput.scrollHeight}px`; // Adjust height
            } else {
                userInput.style.height = '150px'; // Restrict to max height
            }
        });
    }
});
