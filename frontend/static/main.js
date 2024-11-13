document.addEventListener('DOMContentLoaded', () => {
    if (typeof hljs !== 'undefined') {
        // Register 'terraform' as an alias for 'hcl'
        hljs.registerAliases('terraform', { languageName: 'hcl' });
        hljs.highlightAll();
    } else {
        console.error('Highlight.js is not defined.');
    }
});

function handleEnter(event) {
    if (event.key === 'Enter') sendMessage();
}

function sanitizeHtml(str) {
    const temp = document.createElement('div');
    temp.textContent = str;
    return temp.innerHTML;
}

function renderResponse(text) {
    // Regex to match code blocks with or without language specifier
    return text.replace(/```(\w+)?\s*[\n\r]+([\s\S]*?)```/g, (match, language, code) => {
        return renderCodeBlock(language || 'plaintext', code.trim());
    });
}

function renderCodeBlock(language, code) {
    const normalizedLanguage = language.toLowerCase() === 'terraform' ? 'hcl' : language.toLowerCase();
    return `<pre><code class="language-${sanitizeHtml(normalizedLanguage)}">${sanitizeHtml(code)}</code></pre>`;
}


// Dynamically add user and bot messages
function sendMessage() {
    const userInput = document.getElementById('user-input');
    const chatWindow = document.getElementById('chat-window');
    const message = userInput.value.trim();

    if (!message) return; // Do nothing if the input is empty

    // Add user message to the chat window
    const userMessage = document.createElement('div');
    userMessage.className = 'message user-message';
    userMessage.textContent = message;
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
        botMessage.textContent = `Error: ${error.message || 'Unable to fetch response'}`;
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


console.log('Available languages:', hljs.listLanguages());

