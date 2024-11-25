from flask import Flask, request, jsonify, render_template, session
from flask_session import Session
from backend.query_data import main
import os

app = Flask(
    __name__,
    template_folder="frontend/templates", 
    static_folder="frontend/static"
)

# Remember to replace this with a more secure random value in prod
app.secret_key = os.urandom(24)

# Configure server-side session
app.config['SESSION_TYPE'] = 'filesystem' # For dev, use redis in prod maybe
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True

# Initialise the session
Session(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/query', methods=['POST'])
def handle_query():
    data = request.get_json()
    query_text = data.get('query', '').strip()
    if not query_text:
        return jsonify({'error': 'Invalid input'}), 400

    # Retrieve the conversation history from session or initialise it
    history = session.get('history', [])

    # Append the new user query to the history
    history.append({"role": "user", "content": query_text})

    # Call the main function with the updated history
    response_data = main(query_text, history)

    # Append the bot's response to the history
    history.append({"role": "assistant", "content": response_data["response"]})

    # Save the updated history back to the session
    session['history'] = history

    # Return the structured response to the frontend
    return jsonify(response_data)

@app.route('/new_conversation', methods=['POST'])
def new_conversation():
    session.pop('history', None)
    return jsonify({"message": "New conversation started"})

if __name__ == '__main__':
    app.run(debug=True)