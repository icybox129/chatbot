from flask import Flask, request, jsonify, render_template
from backend.query_data import get_source_from_metadata, main

app = Flask(
    __name__,
    template_folder="frontend/templates", 
    static_folder="frontend/static"
)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/query', methods=['POST'])
def handle_query():
    data = request.get_json()
    query_text = data.get('query')
    
    response = main(query_text)
    return jsonify({"response": response})

if __name__ == '__main__':
    app.run(debug=True)