/**
 * @jest-environment jsdom
 */

const { JSDOM } = require('jsdom');
const createDOMPurify = require('dompurify');

// Create a JSDOM window
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
    // Reset modules to ensure a fresh module import
    jest.resetModules();

    // Set up the DOM structure for the tests
    document.body.innerHTML = `
      <div id="chat-window"></div>
      <textarea id="user-input"></textarea>
      <button id="send-button">Send</button>
      <button id="new-chat-btn">New Chat</button>
    `;

    // Mock fetch
    fetch.resetMocks();
    fetch.mockResponse(JSON.stringify({ response: 'Test response', sources: [] }));

    // Mock navigator.clipboard.writeText
    Object.assign(navigator, {
      clipboard: {
        writeText: jest.fn().mockResolvedValue(),
      },
    });

    // Mock DOMPurify
    // global.DOMPurify = {
    //   sanitize: jest.fn((input) => input),
    // };

    // Import the module and extract functions
    const main = require('../frontend/static/main.js');
    handleEnter = main.handleEnter;
    renderResponse = main.renderResponse;
    sendMessage = main.sendMessage;
    startNewConversation = main.startNewConversation;
    enableCodeCopying = main.enableCodeCopying;
    initialize = main.initialize;

    // Manually call initialize() if needed
    initialize();
  });

  test('handleEnter() prevents default behavior and sends a message on Enter key without Shift', async () => {
    // Query DOM elements
    const userInput = document.getElementById('user-input');
    const chatWindow = document.getElementById('chat-window');
  
    // Assertions to ensure DOM elements exist
    expect(userInput).not.toBeNull();
    expect(chatWindow).not.toBeNull();
  
    // Set up the test scenario
    const event = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: false });
    const spy = jest.spyOn(event, 'preventDefault');
  
    userInput.value = 'Test message';
  
    // Call the function to test
    handleEnter(event);
  
    // Wait for all asynchronous code to complete
    await Promise.resolve();
  
    // Assertions
    expect(spy).toHaveBeenCalled(); // Ensure preventDefault is called
    expect(userInput.value).toBe(''); // Ensure input is cleared
  
    // Verify user message is added to chat window
    const userMessages = chatWindow.querySelectorAll('.message.user-message');
    expect(userMessages.length).toBe(1);
    expect(userMessages[0].textContent).toBe('Test message');
  
    // Verify bot message is added to chat window
    const botMessages = chatWindow.querySelectorAll('.message.bot-message');
    expect(botMessages.length).toBe(1);
    expect(botMessages[0].innerHTML).toContain('Typing...'); // Depending on how the response is rendered
  });
  
  test('renderResponse() returns formatted HTML with text and sources', () => {
    const text = '# Heading\nThis is a **bold** text.';
    const sources = ['Source 1', 'Source 2'];
  
    const result = renderResponse(text, sources);
  
    expect(result).toContain('<h1>Heading</h1>');
    expect(result).toContain('<p>This is a <strong>bold</strong> text.</p>');
    expect(result).toContain('<div class="sources-section">');
    expect(result).toContain('<h4>Sources:</h4>');
    expect(result).toContain('<li>Source 1</li>');
    expect(result).toContain('<li>Source 2</li>');
  });
  
  // test('renderResponse() returns formatted HTML with text only when no sources provided', () => {
  //   const text = 'Plain text without sources.';
  
  //   const result = renderResponse(text);
  
  //   expect(result).toContain('<p>Plain text without sources.</p>');
  //   expect(result).not.toContain('Sources:');
  // });

  test('renderResponse() sanitizes malicious input', () => {
    const text = '<script>alert("XSS")</script>';
  
    const result = renderResponse(text);
  
    expect(result).not.toContain('<script>');
    expect(result).toContain('<div></div>');
  });

  test('sendMessage() adds user message and bot response to chat window', async () => {
    const userInput = document.getElementById('user-input');
    const chatWindow = document.getElementById('chat-window');
  
    userInput.value = 'Hello, bot!';
    fetch.mockResponseOnce(JSON.stringify({ response: 'Hello, human!', sources: [] }));
  
    // Call sendMessage but do not await yet
    const sendPromise = sendMessage();
  
    // User message should be added immediately
    const userMessages = chatWindow.querySelectorAll('.message.user-message');
    expect(userMessages.length).toBe(1);
    expect(userMessages[0].textContent).toBe('Hello, bot!');
  
    // Typing indicator should be displayed before fetch completes
    const typingIndicator = chatWindow.querySelector('.loading-indicator');
    expect(typingIndicator).not.toBeNull();
    expect(typingIndicator.textContent).toBe('Typing...');
  
    // Now await the sendMessage promise to let fetch resolve
    await sendPromise;
  
    // Typing indicator should have been replaced with bot response
    const botMessages = chatWindow.querySelectorAll('.message.bot-message');
    expect(botMessages.length).toBe(1);
    const botMessageText = botMessages[0].textContent.trim();
    expect(botMessageText).toBe('Hello, human!');
  });

  test('sendMessage() handles fetch error gracefully', async () => {
    // Mock console.error
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    const userInput = document.getElementById('user-input');
    const chatWindow = document.getElementById('chat-window');

    userInput.value = 'This will cause an error';
    fetch.mockRejectOnce(new Error('Network error'));

    // Call sendMessage and capture the returned promise
    const sendPromise = sendMessage();

    // Optionally check for typing indicator
    const typingIndicator = chatWindow.querySelector('.loading-indicator');
    expect(typingIndicator).not.toBeNull();
    expect(typingIndicator.textContent).toBe('Typing...');

    // Await the promise to ensure all async operations complete
    await sendPromise;

    // Error message should be displayed
    const botMessages = chatWindow.querySelectorAll('.message.bot-message');
    expect(botMessages.length).toBe(1);
    expect(botMessages[0].textContent).toContain('Error: Network error');

    // Optionally, assert that console.error was called
    expect(consoleErrorSpy).toHaveBeenCalledWith('Error in fetch operation:', expect.any(Error));

    // Restore console.error
    consoleErrorSpy.mockRestore();
});

  test('sendMessage() does nothing when input is empty', () => {
    const userInput = document.getElementById('user-input');
    const chatWindow = document.getElementById('chat-window');
  
    userInput.value = '   '; // Input is whitespace
  
    sendMessage();
  
    // No messages should be added
    const messages = chatWindow.querySelectorAll('.message');
    expect(messages.length).toBe(0);
  
    // fetch should not be called
    expect(fetch).not.toHaveBeenCalled();
  });
  
  test(`startNewConversation() clears chat window and sends requests`, () => {
    const chatWindow = document.getElementById('chat-window');
    chatWindow.innerHTML = '<div class="message>Old message</div>';

    fetch.mockResponse(JSON.stringify({ message: 'New conversation started'}));

    startNewConversation();

    // Chat window should be cleared
    expect(chatWindow.innerHTML).toBe('');

    // fetch should be called with  correct parameters
    expect(fetch).toHaveBeenCalledWith('/new_conversation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json'},
    });
  });

  test('enableCodeCopying() adds copy buttons to code blocks', () => {
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
    const chatWindow = document.getElementById('chat-window');
    chatWindow.innerHTML = `
      <pre><code class="copy-enabled">console.log('Hello, world!');</code></pre>
    `;
  
    enableCodeCopying();
  
    const copyButtons = chatWindow.querySelectorAll('.copy-button');
    expect(copyButtons.length).toBe(0);
  });

  test('Copy button copies code to clipboard', async () => {
    const chatWindow = document.getElementById('chat-window');
    chatWindow.innerHTML = `
      <pre><code>console.log('Copy');</code></pre>
    `;
  
    enableCodeCopying();
  
    const copyButton = chatWindow.querySelector('.copy-button');
    copyButton.click();
  
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("console.log('Copy');");
  
    // Await the promise returned by the mocked clipboard writeText
    await navigator.clipboard.writeText.mock.results[0].value;
  
    expect(copyButton.textContent).toBe('Copied!');
  });

  test('Event listeners are attached on DOMContentLoaded', () => {
    // Reset modules to ensure fresh module import
    jest.resetModules();

    // Spy on document.addEventListener
    const addEventListenerSpy = jest.spyOn(document, 'addEventListener');

    // Mock DOMPurify if used within the module
    global.DOMPurify = {
      sanitize: jest.fn((input) => input),
    };

    // Import the module after setting up the spy
    const main = require('../frontend/static/main.js');
    const { initialize } = main;

    // Assert that addEventListener was called with the correct arguments
    expect(addEventListenerSpy).toHaveBeenCalledWith('DOMContentLoaded', initialize);
  });

  test('sendMessage() re-enables input after receiving response', async () => {
    const userInput = document.getElementById('user-input');
  
    userInput.value = 'Test message';
    fetch.mockResponseOnce(JSON.stringify({ response: 'Response', sources: [] }));
  
    // Capture the promise returned by sendMessage
    const sendPromise = sendMessage();
  
    // Await the promise to ensure all asynchronous operations complete
    await sendPromise;
  
    // Now make your assertions
    expect(userInput.disabled).toBe(false);
    expect(document.activeElement).toBe(userInput);
  });
  
});
