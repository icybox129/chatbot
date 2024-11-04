// Listen for the Enter key to submit the message
document.getElementById('query').addEventListener('keydown', function(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        submitQuery();
    }
});

function sanitizeHtml(str) {
    const temp = document.createElement('div');
    temp.textContent = str;
    return temp.innerHTML;
}

function renderCodeBlock(language, code) {
    return `<pre><code class="language-${sanitizeHtml(language)}">${sanitizeHtml(code)}</code></pre>`;
}

function renderResponse(text) {
    // Handle responses with code blocks
    if (text.includes('```')) {
        return text.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, language, code) => {
            return renderCodeBlock(language || '', code.trim());
        });
    }
    
    // Handle regular text
    return text;
}

function submitQuery() {
    const query = document.getElementById('query').value;
    if (!query) return;

    const chatWindow = document.getElementById('chat-window');
    const userMessage = document.createElement('div');
    userMessage.classList.add('message', 'user-message');
    userMessage.textContent = query;
    chatWindow.appendChild(userMessage);

    document.getElementById('query').value = '';

    const botMessage = document.createElement('div');
    botMessage.classList.add('message', 'bot-message');
    botMessage.textContent = 'Loading...';
    chatWindow.appendChild(botMessage);

    chatWindow.scrollTop = chatWindow.scrollHeight;

    fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (!data || !data.response) {
            throw new Error('Invalid response format');
        }

        try {
            const formattedResponse = renderResponse(data.response);
            botMessage.innerHTML = formattedResponse;

            // Apply syntax highlighting
            botMessage.querySelectorAll('pre code').forEach(block => {
                hljs.highlightElement(block);
            });
        } catch (error) {
            console.error('Error rendering response:', error);
            botMessage.textContent = data.response; // Fallback to plain text
        }
    })
    .catch(error => {
        console.error('Error in fetch operation:', error);
        botMessage.textContent = `Error: ${error.message || 'Unable to fetch response'}`;
    });

    setTimeout(() => {
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }, 100);
}

// Add the redirectToHomepage function here
function redirectToHomepage() {
    window.location.href = '/';
}