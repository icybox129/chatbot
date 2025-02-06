/**
 * main.js
 * =======
 * This file contains the front-end logic for the chatbot application,
 * including sending user queries to the Flask backend, displaying 
 * messages, and handling any client-side interactions (e.g., code copy buttons).
 */


/**
 * handleEnter
 * -----------
 * Adjusts textarea behavior when pressing Enter or Shift+Enter.
 * - Normal 'Enter' triggers sendMessage() instead of creating a new line.
 * - Shift+Enter creates a new line and adjusts the textarea's height accordingly.
 */
function handleEnter(event) {
    const userInput = document.getElementById('user-input');

    // Check if 'Enter' was pressed without Shift
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault(); // Prevent default new line
        sendMessage();          // Trigger message sending

    // If 'Enter' was pressed with Shift, auto-resize the textarea
    } else if (event.key === 'Enter') {
        userInput.style.height = 'auto'; // Reset height for recalculation
        userInput.style.height = `${userInput.scrollHeight}px`; // Adjust height to content
    }
}

/**
 * renderResponse
 * --------------
 * Takes a response string (in Markdown) plus optional sources,
 * sanitizes the content, converts it to HTML, and appends a 
 * "Sources" section if provided.
 */

function renderResponse(text, sources = []) {
    // Sanitize the raw text to remove potential malicious scripts
    const sanitizedText = DOMPurify.sanitize(text, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] });
    // Convert the sanitized markdown text into HTML
    const html = marked.parse(sanitizedText);

    // Sanitize the rendered HTML again, allowing only certain tags/attributes
    const sanitizedHtml = DOMPurify.sanitize(html, {
        ALLOWED_TAGS: ['pre', 'code', 'span', 'div', 'p', 'ul', 'ol', 'li', 'strong', 'em', 'a',
                       'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br'],
        ALLOWED_ATTR: ['class', 'href', 'target', 'rel']
    });

    // Create the main response HTML
    let responseHtml = `<div>${sanitizedHtml}</div>`;

    // If sources are provided, append them in a styled section
    if (sources.length > 0) {
        const sourcesHtml = `
            <div class="sources-section">
                <h4>Sources:</h4>
                <ul>
                    ${sources.map(source => `<li>${DOMPurify.sanitize(source)}</li>`).join('')}
                </ul>
            </div>
        `;
        responseHtml += sourcesHtml;
    }

    return responseHtml;
}

/**
 * sendMessage
 * -----------
 * Reads user input from the textarea, sends it to the server via /api/query,
 * and handles the display of both user and bot messages in the chat window.
 */
function sendMessage() {
    const userInput = document.getElementById('user-input');
    const chatWindow = document.getElementById('chat-window');
    const message = userInput.value.trim();

     // If the user hasn't typed anything, do nothing
    if (!message) return;

    // Disable the input box while the bot is responding
    userInput.disabled = true;

    // Create a temporary "bot is typing" message
    const botMessage = document.createElement('div');
    botMessage.className = 'message bot-message loading-indicator';
    botMessage.textContent = 'Typing...';

    // Add user message to the chat window
    const userMessage = document.createElement('div');
    userMessage.className = 'message user-message';
    userMessage.textContent = DOMPurify.sanitize(message);
    chatWindow.appendChild(userMessage);

    // Clear and reset the textarea
    userInput.value = '';
    userInput.style.height = 'auto';

    // Add the "typing..." placeholder message
    chatWindow.appendChild(botMessage);
    chatWindow.scrollTop = chatWindow.scrollHeight; // Scroll to bottom

    // Send the query to the backend
    return fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: message })
    })
    .then(response => {
        // Check HTTP status code
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        // Replace the typing indicator with the final bot message
        botMessage.classList.remove('loading-indicator');
        botMessage.classList.add('bot-message');

        // Extract sources if available
        const sources = data.sources || [];
        const formattedResponse = renderResponse(data.response, sources);

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

/**
 * startNewConversation
 * --------------------
 * Clears the chat window and notifies the server to reset the conversation history.
 */
function startNewConversation() {
    document.getElementById('chat-window').innerHTML = '';
    // Make a POST request to the server to clear the session history
    fetch('/new_conversation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });
}

/**
 * enableCodeCopying
 * -----------------
 * Adds a "Copy" button to each code block so users can copy code snippets.
 */
function enableCodeCopying() {
    const chatWindow = document.getElementById('chat-window');
    // Select all code blocks that do not have the 'copy-enabled' class
    const codeBlocks = chatWindow.querySelectorAll('pre code:not(.copy-enabled)');

    codeBlocks.forEach(codeElement => {
        codeElement.classList.add('copy-enabled');

        // Create a button for copying
        const copyButton = document.createElement('button');
        copyButton.className = 'copy-button';
        copyButton.textContent = 'Copy';

        // Attach click event to handle the copy
        copyButton.addEventListener('click', () => {
            const codeText = codeElement.textContent;

            navigator.clipboard.writeText(codeText).then(() => {
                copyButton.textContent = 'Copied!';
                setTimeout(() => (copyButton.textContent = 'Copy'), 2000);
            }).catch(err => {
                console.error('Failed to copy text: ', err);
            });
        });

        // Position the copy button within the pre element
        const preElement = codeElement.parentElement;
        preElement.style.position = 'relative';
        preElement.appendChild(copyButton);
    });
}

/**
 * initialize
 * ----------
 * Called when the DOM is fully loaded. Sets up button event listeners 
 * and ensures the textarea auto-resizes.
 */
function initialize() {
    const newChatButton = document.getElementById('new-chat-btn');
    const sendButton = document.getElementById('send-button');
    const userInput = document.getElementById('user-input');
  
    // When user clicks "New Chat," reset the conversation
    if (newChatButton) {
      newChatButton.addEventListener('click', startNewConversation);
    }

    // When user clicks the send button, send the message
    if (sendButton) {
      sendButton.addEventListener('click', sendMessage);
    }
  
    // Handle resizing or sending on Enter in the textarea
    if (userInput) {
      userInput.addEventListener('keydown', handleEnter);
  
      // Dynamically resize up to a max height
      userInput.addEventListener('input', () => {
        userInput.style.height = 'auto';
        if (userInput.scrollHeight <= 150) {
          userInput.style.height = `${userInput.scrollHeight}px`;
        } else {
          userInput.style.height = '150px';
        }
      });
    }
  }
  
 // Run initialize() as soon as the DOM content has loaded
  document.addEventListener('DOMContentLoaded', initialize);
  
  // Conditional export for testing
  if (typeof module !== 'undefined' && typeof module.exports !== 'undefined') {
    module.exports = {
      handleEnter,
      renderResponse,
      sendMessage,
      startNewConversation,
      enableCodeCopying,
      initialize,
    };
  }
  