"""
Flask Application for the Chatbot
==================================

This application serves as the backend for the AI chatbot. It handles user 
queries, manages session history, and communicates with the query processing module.

Routes:
- `/`: Serves the home page.
- `/api/query`: Processes user queries and returns responses.
- `/new_conversation`: Resets the conversation history.

Dependencies:
- Flask
- Flask-Session
- Cachelib
"""

import os
from flask import Flask, request, jsonify, render_template, session
from flask_session import Session
from cachelib.file import FileSystemCache
from backend.query_data import main

# ─────────────────────────────────────────────────────────────────────────────
# Flask Application Setup
# ─────────────────────────────────────────────────────────────────────────────

app = Flask(
    __name__,
    template_folder="frontend/templates",
    static_folder="frontend/static"
)

# Session configuration using cachelib. This stores the session data in a
# local file system cache rather than in-memory.
session_cache = FileSystemCache(
    cache_dir="./.flask_session/",
    threshold=100, # Maximum number of items before pruning
    mode=0o600 # File permissions: read/write for owner only
)

app.config.update(
    SESSION_TYPE='cachelib',
    SESSION_CACHELIB=session_cache,
    SESSION_PERMANENT=False,
    SECRET_KEY=os.urandom(24)
)

Session(app)

# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/')
def home():
    """
    Home Page Route
    Serves the main HTML template.
    """
    return render_template('index.html')

@app.route('/api/query', methods=['POST'])
def handle_query():
    """
    API Route: Handle User Query
    Receives a query from the user, processes it using the backend logic,
    and returns the AI-generated response.

    Request Body:
    - `query` (str): The user's query text.

    Response:
    - JSON containing the bot's response and sources.
    """
    data = request.get_json()
    query_text = data.get('query', '').strip()

    # Validate the input; if no query text is provided, return an error
    if not query_text:
        return jsonify({'error': 'Invalid input'}), 400

    # Retrieve or initialize conversation history from session
    history = session.get('history', [])

    # Append user query to history
    history.append({"role": "user", "content": query_text})

    # Process the query and get the bot's response
    response_data = main(query_text, history)

    # Append the bot's response to history
    history.append({"role": "assistant", "content": response_data["response"]})

    # Save updated history back to the session
    session['history'] = history

    # Return the bot's response
    return jsonify(response_data)

@app.route('/new_conversation', methods=['POST'])
def new_conversation():
    """
    API Route: Start a New Conversation
    Clears the conversation history stored in the session.

    Response:
    - JSON confirmation message.
    """
    # Remove the 'history' key from the session if it exists
    session.pop('history', None)
    return jsonify({"message": "New conversation started"})

# ─────────────────────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True)
