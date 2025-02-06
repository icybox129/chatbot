/**
 * main.test.js
 * ============
 * Jest test suite for the front-end logic in `main.js`.
 * Uses jsdom to simulate the browser environment and verify:
 * 1. Correct DOM updates for user and bot messages.
 * 2. fetch calls to the server endpoints.
 * 3. Code copy button functionality.
 * 4. Proper event handling (keydown, click, etc.).
 */

const { JSDOM } = require('jsdom');
const createDOMPurify = require('dompurify');

/**
 * Create a mock DOM environment for testing.
 * We also import DOMPurify for sanitizing within the test environment.
 */
const window = new JSDOM('').window;
const DOMPurify = createDOMPurify(window);

describe('main.js functions', () => {
  let handleEnter;
  let renderResponse;
  let sendMessage;
  let startNewConversation;
  let enableCodeCopying;
  let initialize;

  beforeEach(() => {
    // Reset modules to ensure each test is isolated
    jest.resetModules();

    // Set up the DOM structure for the tests
    document.body.innerHTML = `
      <div id="chat-window"></div>
      <textarea id="user-input"></textarea>
      <button id="send-button">Send</button>
      <button id="new-chat-btn">New Chat</button>
    `;

    // Mock fetch globally so we can control responses
    fetch.resetMocks();
    fetch.mockResponse(JSON.stringify({ response: 'Test response', sources: [] }));

    // Mock navigator.clipboard functionality
    Object.assign(navigator, {
      clipboard: {
        writeText: jest.fn().mockResolvedValue(),
      },
    });

    // Import main.js and deconstruct the exported functions
    const main = require('../frontend/static/main.js');
    handleEnter = main.handleEnter;
    renderResponse = main.renderResponse;
    sendMessage = main.sendMessage;
    startNewConversation = main.startNewConversation;
    enableCodeCopying = main.enableCodeCopying;
    initialize = main.initialize;

    // Call initialize() to attach event listeners if needed
    initialize();
  });

  test('handleEnter() prevents default behavior and sends a message on Enter without Shift', async () => {
    /**
     * Checks that pressing Enter triggers sending the message instead
     * of creating a new line.
     */
    const userInput = document.getElementById('user-input');
    const chatWindow = document.getElementById('chat-window');
    expect(userInput).not.toBeNull();
    expect(chatWindow).not.toBeNull();
  
    // Simulate the user typing a message
    userInput.value = 'Test message';
  
    // Create a fake keydown event
    const event = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: false });
    const spy = jest.spyOn(event, 'preventDefault');
  
    // Invoke handleEnter
    handleEnter(event);

    // Wait for asynchronous tasks in sendMessage
    await Promise.resolve();
  
    // Assertions
    expect(spy).toHaveBeenCalled();       // Check that default newline was prevented
    expect(userInput.value).toBe('');     // Input should be cleared after send
    const userMessages = chatWindow.querySelectorAll('.message.user-message');
    expect(userMessages.length).toBe(1);  // The user's message should appear in chat
    expect(userMessages[0].textContent).toBe('Test message');

    // Bot "typing..." indicator
    const botMessages = chatWindow.querySelectorAll('.message.bot-message');
    expect(botMessages.length).toBe(1);
    expect(botMessages[0].innerHTML).toContain('Typing...');
  });

  test('renderResponse() returns formatted HTML with text and sources', () => {
    /**
     * Verifies that Markdown is properly converted to HTML,
     * and that sources are appended in the correct format.
     */
    const text = '# Heading\nThis is a **bold** text.';
    const sources = ['Source 1', 'Source 2'];
  
    const result = renderResponse(text, sources);
    expect(result).toContain('<h1>Heading</h1>');
    expect(result).toContain('<strong>bold</strong>');
    expect(result).toContain('<div class="sources-section">');
    expect(result).toContain('<h4>Sources:</h4>');
    expect(result).toContain('<li>Source 1</li>');
    expect(result).toContain('<li>Source 2</li>');
  });

  test('renderResponse() sanitizes malicious input', () => {
    /**
     * Ensures that <script> tags or other potentially harmful 
     * markup are removed or neutralized.
     */
    const text = '<script>alert("XSS")</script>';
    const result = renderResponse(text);
    expect(result).not.toContain('<script>');
    expect(result).toContain('<div></div>');
  });

  test('sendMessage() adds user message and bot response to chat window', async () => {
    /**
     * Verifies that after sending the user's message:
     * - The user's message is appended immediately.
     * - A "typing..." bot placeholder is added.
     * - Finally, a response from the server is shown as the bot's message.
     */
    const userInput = document.getElementById('user-input');
    const chatWindow = document.getElementById('chat-window');
  
    userInput.value = 'Hello, bot!';
    fetch.mockResponseOnce(JSON.stringify({ response: 'Hello, human!', sources: [] }));
  
    // Trigger the send
    const sendPromise = sendMessage();
  
    // The user's message should appear right away
    const userMessages = chatWindow.querySelectorAll('.message.user-message');
    expect(userMessages.length).toBe(1);
    expect(userMessages[0].textContent).toBe('Hello, bot!');

    // A "typing..." placeholder
    const typingIndicator = chatWindow.querySelector('.loading-indicator');
    expect(typingIndicator).not.toBeNull();
    expect(typingIndicator.textContent).toBe('Typing...');

    // Wait for fetch to resolve
    await sendPromise;

    // The typing indicator should be replaced with final bot response
    const botMessages = chatWindow.querySelectorAll('.message.bot-message');
    expect(botMessages.length).toBe(1);
    expect(botMessages[0].textContent.trim()).toBe('Hello, human!');
  });

  test('sendMessage() handles fetch error gracefully', async () => {
    /**
     * Ensures the UI reports an error if fetch fails.
     */
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    const userInput = document.getElementById('user-input');
    const chatWindow = document.getElementById('chat-window');

    userInput.value = 'Trigger error';
    fetch.mockRejectOnce(new Error('Network error'));

    const sendPromise = sendMessage();

    // Check "typing..." before fetch completes
    const typingIndicator = chatWindow.querySelector('.loading-indicator');
    expect(typingIndicator).not.toBeNull();
    expect(typingIndicator.textContent).toBe('Typing...');

    await sendPromise;

    // Should display the error text
    const botMessages = chatWindow.querySelectorAll('.message.bot-message');
    expect(botMessages.length).toBe(1);
    expect(botMessages[0].textContent).toContain('Error: Network error');

    // Console error logging
    expect(consoleErrorSpy).toHaveBeenCalledWith('Error in fetch operation:', expect.any(Error));
    consoleErrorSpy.mockRestore();
  });

  test('sendMessage() does nothing when input is empty', () => {
    /**
     * Checks that pressing send with empty input 
     * does not make a fetch call or add messages to the chat.
     */
    const userInput = document.getElementById('user-input');
    const chatWindow = document.getElementById('chat-window');
    userInput.value = '   '; // Whitespace only

    sendMessage();

    // No new messages should be created
    const messages = chatWindow.querySelectorAll('.message');
    expect(messages.length).toBe(0);

    // fetch should not be called
    expect(fetch).not.toHaveBeenCalled();
  });

  test('startNewConversation() clears chat window and sends request', () => {
    /**
     * Verifies the chat window is emptied and a POST request 
     * is made to `/new_conversation` endpoint.
     */
    const chatWindow = document.getElementById('chat-window');
    chatWindow.innerHTML = '<div class="message">Old message</div>';

    fetch.mockResponse(JSON.stringify({ message: 'New conversation started'}));

    startNewConversation();

    // Chat window should be cleared
    expect(chatWindow.innerHTML).toBe('');

    // fetch should be called with correct parameters
    expect(fetch).toHaveBeenCalledWith('/new_conversation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
  });

  test('enableCodeCopying() adds copy buttons to code blocks', () => {
    /**
     * Checks that new 'Copy' buttons are added to code blocks 
     * that don't already have them.
     */
    const chatWindow = document.getElementById('chat-window');
    chatWindow.innerHTML = `
      <pre><code>console.log('Hello World');</code></pre>
    `;

    enableCodeCopying();
    const copyButtons = chatWindow.querySelectorAll('.copy-button');
    expect(copyButtons.length).toBe(1);
    expect(copyButtons[0].textContent).toBe('Copy');
  });

  test('enableCodeCopying() does not add duplicate copy buttons', () => {
    /**
     * Ensures that once a code block is marked "copy-enabled," 
     * we don't add a second copy button.
     */
    const chatWindow = document.getElementById('chat-window');
    chatWindow.innerHTML = `
      <pre><code class="copy-enabled">console.log('Hello, world!');</code></pre>
    `;
  
    enableCodeCopying();
    const copyButtons = chatWindow.querySelectorAll('.copy-button');
    expect(copyButtons.length).toBe(0);
  });

  test('Copy button copies code to clipboard', async () => {
    /**
     * Checks that clicking the 'Copy' button successfully 
     * writes the code to the clipboard, and updates the button text.
     */
    const chatWindow = document.getElementById('chat-window');
    chatWindow.innerHTML = `
      <pre><code>console.log('Copy');</code></pre>
    `;
  
    enableCodeCopying();
    const copyButton = chatWindow.querySelector('.copy-button');
    copyButton.click();
  
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("console.log('Copy');");
  
    // Wait for the promise returned by mock writeText
    await navigator.clipboard.writeText.mock.results[0].value;
  
    // Button text should become 'Copied!'
    expect(copyButton.textContent).toBe('Copied!');
  });

  test('Event listeners are attached on DOMContentLoaded', () => {
    /**
     * Ensures that `document.addEventListener('DOMContentLoaded', initialize)` is called,
     * so that the chatbot UI is correctly set up after the DOM is loaded.
     */
    jest.resetModules();
    const addEventListenerSpy = jest.spyOn(document, 'addEventListener');

    global.DOMPurify = { sanitize: jest.fn((input) => input) };

    // Re-import the module after we set up the spy
    const main = require('../frontend/static/main.js');
    const { initialize } = main;

    // Expect that the event listener was indeed registered
    expect(addEventListenerSpy).toHaveBeenCalledWith('DOMContentLoaded', initialize);
  });

  test('sendMessage() re-enables input after receiving response', async () => {
    /**
     * Confirms that the input box is disabled only while waiting
     * for the server, then re-enabled (with focus) afterward.
     */
    const userInput = document.getElementById('user-input');
    userInput.value = 'Test message';
    
    fetch.mockResponseOnce(JSON.stringify({ response: 'Response', sources: [] }));
  
    const sendPromise = sendMessage();
    await sendPromise;
  
    // After fetch completes, input should be enabled again
    expect(userInput.disabled).toBe(false);
    expect(document.activeElement).toBe(userInput);
  });
});
