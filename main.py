from data import process, query_llm
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

vector_store = None


@app.route('/')
def index():
    return render_template('index.html')

@app.route("/health")
def health():
    return "ok", 200

@app.route('/save_url', methods=['POST'])
def save_url():
    data = request.get_json(force=True, silent=True) or {}
    url  = (data.get('url') or '').strip()

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    # Basic URL sanity check
    if not url.startswith(('http://', 'https://')):
        return jsonify({'error': 'Invalid URL. Must start with http:// or https://'}), 400

    global vector_store
    try:
        vector_store = process(url)
        print(f"[INFO] URL loaded: {url}")
        return jsonify({'message': 'Data fetched successfully'})
    except Exception as e:
        print(f"[ERROR] Failed to process URL: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/ask', methods=['POST'])
def ask():
    data     = request.get_json(force=True, silent=True) or {}
    question = (data.get('question') or '').strip()

    if not question:
        return jsonify({'error': 'No question provided'}), 400

    try:
        answer = query_llm(vector_store, question)
        return jsonify({'question': question, 'response': answer})
    except Exception as e:
        print(f"[ERROR] query_llm failed: {e}")
        return jsonify({'response': f'An error occurred: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True)