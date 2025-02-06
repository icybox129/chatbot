/*
 * Jest Setup File
 * ===============
 * This file runs before the Jest test suites, and is used to:
 * - Populate globals like TextEncoder, TextDecoder (if not provided natively)
 * - Enable mock fetch
 * - Add Marked and Prism to the global scope so they behave as if in the browser
 */

import { TextEncoder, TextDecoder } from 'util';
import DOMPurify from 'dompurify';
import fetchMock from 'jest-fetch-mock';
import { marked } from 'marked';
import Prism from 'prismjs';

// Provide polyfills for text encoding/decoding
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

// Assign DOMPurify to global
global.DOMPurify = DOMPurify;

// Enable fetch mocks for all tests
fetchMock.enableMocks();

// Make 'marked' globally available for Markdown parsing
global.marked = marked;

// Make 'Prism' globally available for syntax highlighting
global.Prism = Prism;
