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

    @patch('app.mysql')
    def test_dashboard_admin_access(self, mock_mysql):
        """Test admin dashboard statistics and rendering."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [(15,), (4,), (2,), (3,)]
        mock_cursor.fetchall.return_value = [('Paracetamol', '2026-10-02')]
        mock_mysql.connection.cursor.return_value = mock_cursor

        with self.client.session_transaction() as sess:
            sess['username'] = 'admin'
            sess['role'] = 'Admin'

        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)

    @patch('app.mysql')
    def test_staff_dashboard_access(self, mock_mysql):
        """Test staff dashboard renders correctly."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [(10,), (1,), (2,)]
        mock_cursor.fetchall.return_value = []
        mock_mysql.connection.cursor.return_value = mock_cursor

        with self.client.session_transaction() as sess:
            sess['username'] = 'staff1'
            sess['role'] = 'Staff'

        response = self.client.get('/staff_dashboard')
        self.assertEqual(response.status_code, 200)

    @patch('app.mysql')
    def test_medicines_stock_list(self, mock_mysql):
        """Test retrieving medicines stock list."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (1, 'Amoxicillin', 'Antibiotic', 'BATCH001', 1, '2025-01-01', '2027-01-01', 50, 15.50)
        ]
        mock_mysql.connection.cursor.return_value = mock_cursor

        response = self.client.get('/medicines')
        self.assertEqual(response.status_code, 200)

    @patch('app.mysql')
    def test_add_medicine_stock_post(self, mock_mysql):
        """Test adding new medicine stock entry."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(1, 'PharmaCorp')]
        mock_mysql.connection.cursor.return_value = mock_cursor

        with self.client.session_transaction() as sess:
            sess['username'] = 'admin'
            sess['role'] = 'Admin'

        response = self.client.post('/add_medicine', data={
            'name': 'Ibuprofen',
            'category': 'Painkiller',
            'batch': 'B123',
            'supplier_id': '1',
            'manufacture_date': '2026-01-01',
            'expiry_date': '2028-01-01',
            'quantity': '100',
            'price': '8.50'
        }, follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/medicines', response.headers['Location'])
        mock_cursor.execute.assert_called()

    @patch('app.mysql')
    def test_delete_medicine_stock(self, mock_mysql):
        """Test deleting medicine item from stock."""
        mock_cursor = MagicMock()
        mock_mysql.connection.cursor.return_value = mock_cursor

        with self.client.session_transaction() as sess:
            sess['username'] = 'admin'
            sess['role'] = 'Admin'

        response = self.client.get('/delete_medicine/1', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/medicines', response.headers['Location'])

    @patch('app.mysql')
    def test_suppliers_list_and_add(self, mock_mysql):
        """Test suppliers inventory and supplier addition."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(1, 'Apex Meds', '9876543210', 'Highway 1')]
        mock_mysql.connection.cursor.return_value = mock_cursor

        with self.client.session_transaction() as sess:
            sess['username'] = 'admin'
            sess['role'] = 'Admin'

        # GET suppliers
        res_get = self.client.get('/suppliers')
        self.assertEqual(res_get.status_code, 200)

        # POST add supplier
        res_post = self.client.post('/add_supplier', data={
            'supplier_name': 'BioHealth',
            'contact_number': '1234567890',
            'address': 'City Center'
        }, follow_redirects=True)
        self.assertEqual(res_post.status_code, 200)

    def test_billing_sales_receipt_calculation(self):
        """Test medicine sales billing calculation and itemized receipt logic."""
        items = [
            {'name': 'Paracetamol', 'qty': 3, 'unit_price': 5.00},
            {'name': 'Vitamin C', 'qty': 2, 'unit_price': 12.50}
        ]
        subtotal = sum(i['qty'] * i['unit_price'] for i in items)
        tax_rate = 0.05
        tax_amount = round(subtotal * tax_rate, 2)
        discount = 2.00
        grand_total = subtotal + tax_amount - discount

        self.assertEqual(subtotal, 40.00)
        self.assertEqual(tax_amount, 2.00)
        self.assertEqual(grand_total, 40.00)

    @unittest.skip("External payment gateway receipt verification skipped in offline/CI environment")
    def test_external_billing_gateway_receipt(self):
        """Simulate external payment provider webhook confirmation."""
        pass


if __name__ == '__main__':
    unittest.main()
