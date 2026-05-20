import unittest
import json
from app import app, books

class FlaskCRUDTestCase(unittest.TestCase):

    def setUp(self):
        """Executed before each test. Sets up a clean environment."""
        self.app = app.test_client()
        self.app.testing = True
        
        # Reset our mock database to a predictable state before every test
        self.original_books = list(books)
        books.clear()
        books.extend([
            {"id": 1, "title": "The Hobbit", "author": "J.R.R. Tolkien"},
            {"id": 2, "title": "1984", "author": "George Orwell"}
        ])

    def tearDown(self):
        """Executed after each test. Cleans up state."""
        books.clear()
        books.extend(self.original_books)

    def test_get_all_books(self):
        """Test fetching the entire book catalog."""
        response = self.app.get('/api/books')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['books']), 2)

    def test_get_single_book_success(self):
        """Test fetching an existing book by its ID."""
        response = self.app.get('/api/books/1')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['title'], "The Hobbit")

    def test_get_single_book_not_found(self):
        """Test fetching a non-existent book returns a 404 error."""
        response = self.app.get('/api/books/999')
        self.assertEqual(response.status_code, 404)

    def test_create_book(self):
        """Test adding a brand new book successfully."""
        new_payload = {"title": "Brave New World", "author": "Aldous Huxley"}
        response = self.app.post('/api/books', 
                                 data=json.dumps(new_payload), 
                                 content_type='application/json')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 201)
        self.assertEqual(data['title'], "Brave New World")
        self.assertEqual(data['id'], 3)

    def test_delete_book(self):
        """Test deleting a specific book."""
        response = self.app.delete('/api/books/1')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("deleted successfully", data['result'])
        
        # Double check it is genuinely missing from the total count now
        get_response = self.app.get('/api/books')
        get_data = json.loads(get_response.data)
        self.assertEqual(len(get_data['books']), 1)

if __name__ == '__main__':
    unittest.main()