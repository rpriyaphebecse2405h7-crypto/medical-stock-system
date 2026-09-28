import os
import unittest
from unittest.mock import MagicMock, patch
from app import app
from config import Config


class MedicineStockSystemTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test client and test environment."""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def test_config_defaults(self):
        """Verify configuration object loads with expected keys."""
        self.assertTrue(hasattr(Config, 'SECRET_KEY'))
        self.assertTrue(hasattr(Config, 'MYSQL_HOST'))
        self.assertTrue(hasattr(Config, 'MYSQL_USER'))
        self.assertTrue(hasattr(Config, 'MYSQL_PASSWORD'))
        self.assertTrue(hasattr(Config, 'MYSQL_DB'))
        self.assertTrue(hasattr(Config, 'MYSQL_PORT'))

    def test_login_page_get(self):
        """Test GET request to login page renders successfully."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)

    def test_logout_redirects_to_login(self):
        """Test logging out clears session and redirects to login."""
        with self.client.session_transaction() as sess:
            sess['username'] = 'testuser'
            sess['role'] = 'Admin'

        response = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Logged Out Successfully', response.data)

    @patch('app.mysql')
    def test_login_post_invalid_credentials(self, mock_mysql):
        """Test invalid credentials display proper flash error."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_mysql.connection.cursor.return_value = mock_cursor

        response = self.client.post('/', data={
            'username': 'nonexistent_user',
            'password': 'wrongpassword'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid Username or Password', response.data)

    def test_reports_route_requires_db(self):
        """Verify /reports endpoint exists."""
        with patch('app.mysql') as mock_mysql:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_mysql.connection.cursor.return_value = mock_cursor

            response = self.client.get('/reports')
            self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
