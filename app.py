from flask import Flask, jsonify, request, abort

app = Flask(__name__)

from prometheus_flask_exporter import PrometheusMetrics
metrics = PrometheusMetrics(app)

# In-memory database for demonstration purposes
books = [
    {"id": 1, "title": "The Hobbit", "author": "J.R.R. Tolkien"},
    {"id": 2, "title": "1984", "author": "George Orwell"}
]

# 1. READ: Get all books
@app.route('/api/books', methods=['GET'])
def get_books():
    return jsonify({"books": books}), 200

# 2. READ: Get a single book by ID
@app.route('/api/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    book = next((b for b in books if b["id"] == book_id), None)
    if book is None:
        abort(404, description="Book not found")
    return jsonify(book), 200

# 3. CREATE: Add a new book
@app.route('/api/books', methods=['POST'])
def create_book():
    if not request.json or not 'title' in request.json or not 'author' in request.json:
        abort(400, description="Missing title or author in request body")
    
    new_book = {
        "id": books[-1]["id"] + 1 if books else 1,
        "title": request.json['title'],
        "author": request.json['author']
    }
    books.append(new_book)
    return jsonify(new_book), 201

# 4. DELETE: Remove a book by ID
@app.route('/api/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    book = next((b for b in books if b["id"] == book_id), None)
    if book is None:
        abort(404, description="Book not found")
    books.remove(book)
    return jsonify({"result": "Book deleted successfully"}), 200

if __name__ == '__main__':
    app.run(debug=True)