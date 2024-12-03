import { TextEncoder, TextDecoder } from 'util';
import DOMPurify from 'dompurify';
import fetchMock from 'jest-fetch-mock';
import { marked } from 'marked';
import Prism from 'prismjs';

global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;
global.DOMPurify = DOMPurify;

// Enable fetch mocks
fetchMock.enableMocks();

// Assign `marked` to global scope
global.marked = marked;

// Assign `Prism` to global scope
global.Prism = Prism;
