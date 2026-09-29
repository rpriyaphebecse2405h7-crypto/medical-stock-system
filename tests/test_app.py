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

    def test_billing_requires_login(self):
        """Test billing route redirects unauthenticated users to login."""
        response = self.client.get('/billing', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please login to access billing', response.data)

    @patch('app.mysql')
    def test_billing_get_authenticated(self, mock_mysql):
        """Test GET request to /billing renders available medicines for logged-in user."""
        with self.client.session_transaction() as sess:
            sess['username'] = 'priya'
            sess['role'] = 'Staff'

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (1, 'Amoxicillin 500mg', 'Antibiotic', 'BATCH-001', 50, 15.00, '2027-12-31')
        ]
        mock_mysql.connection.cursor.return_value = mock_cursor

        response = self.client.get('/billing')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Medicine Billing & Dispensing', response.data)
        self.assertIn(b'Amoxicillin 500mg', response.data)

    @patch('app.mysql')
    def test_billing_post_success(self, mock_mysql):
        """Test successful medicine sale, stock decrement, and sales record insertion."""
        with self.client.session_transaction() as sess:
            sess['username'] = 'priya'
            sess['role'] = 'Staff'

        from datetime import date, timedelta
        future_date = date.today() + timedelta(days=180)

        mock_cursor = MagicMock()
        # id, name, batch_number, quantity, price, expiry_date
        mock_cursor.fetchone.return_value = (1, 'Paracetamol', 'BATCH-P1', 100, 5.00, future_date)
        mock_cursor.lastrowid = 42
        mock_mysql.connection.cursor.return_value = mock_cursor

        response = self.client.post('/billing', data={
            'medicine_id': '1',
            'customer_name': 'Rahul Sharma',
            'quantity': '10'
        }, follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/receipt/42', response.headers['Location'])
        # Verify UPDATE was called to decrement quantity
        update_calls = [c for c in mock_cursor.execute.call_args_list if 'UPDATE medicines' in str(c)]
        self.assertTrue(len(update_calls) > 0)
        # Verify INSERT was called to record sale
        insert_calls = [c for c in mock_cursor.execute.call_args_list if 'INSERT INTO sales' in str(c)]
        self.assertTrue(len(insert_calls) > 0)

    @patch('app.mysql')
    def test_billing_post_insufficient_stock(self, mock_mysql):
        """Test billing prevents overselling when requested quantity exceeds stock."""
        with self.client.session_transaction() as sess:
            sess['username'] = 'priya'
            sess['role'] = 'Staff'

        from datetime import date, timedelta
        future_date = date.today() + timedelta(days=180)

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1, 'Paracetamol', 'BATCH-P1', 5, 5.00, future_date)
        mock_mysql.connection.cursor.return_value = mock_cursor

        response = self.client.post('/billing', data={
            'medicine_id': '1',
            'customer_name': 'Rahul Sharma',
            'quantity': '20'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Insufficient stock for Paracetamol', response.data)

    @patch('app.mysql')
    def test_billing_post_expired_medicine(self, mock_mysql):
        """Test billing blocks sale of expired medicines."""
        with self.client.session_transaction() as sess:
            sess['username'] = 'priya'
            sess['role'] = 'Staff'

        from datetime import date, timedelta
        past_date = date.today() - timedelta(days=10)

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1, 'Expired Syrup', 'BATCH-EX1', 50, 20.00, past_date)
        mock_mysql.connection.cursor.return_value = mock_cursor

        response = self.client.post('/billing', data={
            'medicine_id': '1',
            'customer_name': 'Customer',
            'quantity': '1'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Medicine has expired', response.data)

    @patch('app.mysql')
    def test_receipt_view(self, mock_mysql):
        """Test receipt invoice page renders details properly."""
        with self.client.session_transaction() as sess:
            sess['username'] = 'priya'
            sess['role'] = 'Staff'

        mock_cursor = MagicMock()
        # s.id, m.name, m.batch_number, s.customer_name, s.quantity_sold, s.total_amount, s.sale_date, m.category
        mock_cursor.fetchone.return_value = (
            42, 'Amoxicillin 500mg', 'BATCH-001', 'Rahul Sharma', 2, 30.00, '2026-09-29', 'Antibiotic'
        )
        mock_mysql.connection.cursor.return_value = mock_cursor

        response = self.client.get('/receipt/42')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'#INV-00042', response.data)
        self.assertIn(b'Rahul Sharma', response.data)
        self.assertIn(b'Amoxicillin 500mg', response.data)

    @patch('app.mysql')
    def test_sales_history_view(self, mock_mysql):
        """Test sales history audit log page renders records."""
        with self.client.session_transaction() as sess:
            sess['username'] = 'priya'
            sess['role'] = 'Staff'

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (42, 'Amoxicillin 500mg', 'BATCH-001', 'Rahul Sharma', 2, 30.00, '2026-09-29')
        ]
        mock_cursor.fetchone.return_value = (1, 30.00)  # total_sales, total_revenue
        mock_mysql.connection.cursor.return_value = mock_cursor

        response = self.client.get('/sales')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sales & Dispensing History', response.data)
        self.assertIn(b'Amoxicillin 500mg', response.data)

    @patch('app.mysql')
    def test_admin_dashboard_with_sales_metrics(self, mock_mysql):
        """Test admin dashboard renders KPI cards including sales revenue and invoices."""
        with self.client.session_transaction() as sess:
            sess['username'] = 'admin'
            sess['role'] = 'Admin'

        mock_cursor = MagicMock()
        # total_medicines, total_suppliers, expired_count, low_stock
        mock_cursor.fetchone.side_effect = [(15,), (4,), (2,), (3,), (10, 1500.50)]
        mock_cursor.fetchall.return_value = []
        mock_mysql.connection.cursor.return_value = mock_cursor

        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Medicine Stock Dashboard', response.data)
        self.assertIn(b'Total Invoices', response.data)
        self.assertIn(b'Sales Revenue', response.data)

    @patch('app.mysql')
    def test_staff_dashboard_with_sales_metrics(self, mock_mysql):
        """Test staff dashboard renders properly with sales metrics."""
        with self.client.session_transaction() as sess:
            sess['username'] = 'priya'
            sess['role'] = 'Staff'

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [(10,), (1,), (2,), (5, 750.00)]
        mock_cursor.fetchall.return_value = []
        mock_mysql.connection.cursor.return_value = mock_cursor

        response = self.client.get('/staff_dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Staff Dashboard', response.data)
        self.assertIn(b'Total Invoices', response.data)

    @patch('app.mysql')
    def test_medicines_listing(self, mock_mysql):
        """Test medicines listing renders existing medicines."""
        with self.client.session_transaction() as sess:
            sess['username'] = 'priya'
            sess['role'] = 'Staff'

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (1, 'Paracetamol', 'Analgesic', 'BATCH-01', 1, '2025-01-01', '2027-01-01', 50, 10.00)
        ]
        mock_mysql.connection.cursor.return_value = mock_cursor

        response = self.client.get('/medicines')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Paracetamol', response.data)

    @patch('app.mysql')
    def test_suppliers_listing(self, mock_mysql):
        """Test suppliers listing renders."""
        with self.client.session_transaction() as sess:
            sess['username'] = 'priya'
            sess['role'] = 'Staff'

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (1, 'PharmaCorp', '9876543210', '123 Health Ave')
        ]
        mock_mysql.connection.cursor.return_value = mock_cursor

        response = self.client.get('/suppliers')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'PharmaCorp', response.data)


if __name__ == '__main__':
    unittest.main()
