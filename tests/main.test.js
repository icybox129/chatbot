/**
 * @jest-environment jsdom
 */

import { send } from 'process';
import { handleEnter, initialize, renderResponse, sendMessage, startNewConversation, enableCodeCopying } from '../frontend/static/main.js';

describe('main.js functions', () => {
    beforeEach(() => {
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
  
      // Initialize event listeners after DOM is set up
      initialize();
  
      // Dispatch DOMContentLoaded event to trigger event listeners
      document.dispatchEvent(new Event('DOMContentLoaded'));
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
  
  test('renderResponse() returns formatted HTML with text only when no sources provided', () => {
    const text = 'Plain text without sources.';
  
    const result = renderResponse(text);
  
    expect(result).toContain('<p>Plain text without sources.</p>');
    expect(result).not.toContain('Sources:');
  });

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

    await sendMessage();

    // User message should be added
    const userMessages = chatWindow.querySelectorAll('.message.user-message');
    expect(userMessages.length).toBe(1);
    expect(userMessages[0].textContent).toBe('Hello, bot!');

    // Typing indicator should be displayed
    const typingIndicator = chatWindow.querySelector('.loading-indicator');
    expect(typingIndicator).not.toBeNull();
    expect(typingIndicator.textContent).toBe('Typing...');

    // Wait for the asynchronous code to complete
    await Promise.resolve();

    // Bot response should replace the typing indicator
    const botMessages = chatWindow.querySelectorAll('.message.bot-message');
    expect(botMessages.length).toBe(1);
    expect(botMessages[0].textContent).toBe('Hello, human!');
  });
  
});
