function handleEnter(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
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
    chatWindow.scrollTop = chatWindow.scrollHeight; // Scroll to the bottom

    // Display bot typing indicator
    const botMessage = document.createElement('div');
    botMessage.className = 'message bot-message';
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
        botMessage.textContent = `Error: ${error.message || 'Something went wrong. Please try again later.'}`;
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
    // Select all code blocks in the chat window
    const codeBlocks = document.querySelectorAll('.chat-window pre');

    codeBlocks.forEach(block => {
        // Skip if the copy button already exists
        if (block.querySelector('.copy-button')) return;

        // Create the copy button
        const copyButton = document.createElement('button');
        copyButton.className = 'copy-button';
        copyButton.textContent = 'Copy';

        // Add click event to copy only the code text
        copyButton.addEventListener('click', () => {
            const codeElement = block.querySelector('code'); // Get the <code> inside the <pre>
            const codeText = codeElement ? codeElement.innerText : ''; // Extract only the code text

            navigator.clipboard.writeText(codeText).then(() => {
                copyButton.textContent = 'Copied!'; // Temporary success message
                setTimeout(() => (copyButton.textContent = 'Copy'), 2000); // Reset button text
            }).catch(err => {
                console.error('Failed to copy text: ', err);
            });
        });

        // Add the button to the code block
        block.appendChild(copyButton);
    });
}

// Add event listeners
document.getElementById('user-input').addEventListener('keydown', handleEnter);
document.getElementById('send-button').addEventListener('click', sendMessage);
