from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date


try:
    from flask_mysqldb import MySQL
except ImportError:
    class MySQL:
        def __init__(self, app=None):
            self.app = app
            self.connection = None


from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config.get('SECRET_KEY', 'medicine_secret_key')

mysql = MySQL(app)


def init_db():
    conn = mysql.connection
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'user'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            supplier_name VARCHAR(200) NOT NULL,
            contact_number VARCHAR(20),
            address TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            category VARCHAR(100),
            batch_number VARCHAR(100),
            supplier_id INT,
            manufacture_date DATE,
            expiry_date DATE,
            quantity INT DEFAULT 0,
            price DECIMAL(10, 2),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INT AUTO_INCREMENT PRIMARY KEY,
            medicine_id INT,
            customer_name VARCHAR(100) DEFAULT 'Walk-in Customer',
            quantity_sold INT NOT NULL,
            total_amount DECIMAL(10, 2) NOT NULL,
            sale_date DATE NOT NULL,
            FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE SET NULL
        )
    """)

    def add_column_if_missing(table, column, definition):
        cur.execute(f"""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA='medicine_stock_db' 
            AND TABLE_NAME='{table}' 
            AND COLUMN_NAME='{column}'
        """)
        exists = cur.fetchone()[0]
        if not exists:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    add_column_if_missing('sales', 'customer_name', "VARCHAR(100) DEFAULT 'Walk-in Customer'")

    conn.commit()
    cur.close()


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[2], password):
            session['username'] = user[1]
            session['role'] = user[3]
            flash('Login Successful')

            if user[3] == 'Admin':
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('staff_dashboard'))
        else:
            flash('Invalid Username or Password')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged Out Successfully')
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        existing_user = cur.fetchone()

        if existing_user:
            flash('Username already exists. Please choose another username.')
            cur.close()
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
            (username, hashed_password, role)
        )
        mysql.connection.commit()
        cur.close()

        flash('Registration Successful. Please Login.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/dashboard')  # ✅ Fixed: removed duplicate @app.route('/dashboard')
def dashboard():
    if session.get('role') != 'Admin':
        flash('Access Denied')
        return redirect(url_for('staff_dashboard'))

    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) FROM medicines")
    total_medicines = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM suppliers")
    total_suppliers = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM medicines WHERE expiry_date < CURDATE()")
    expired_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM medicines WHERE quantity < 10")
    low_stock = cur.fetchone()[0]

    cur.execute("""
        SELECT name, expiry_date FROM medicines 
        WHERE expiry_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 3 DAY)
    """)
    expiring_soon = cur.fetchall()

    cur.execute("SELECT COUNT(*), COALESCE(SUM(total_amount), 0) FROM sales")
    sales_stats = cur.fetchone()
    total_sales = sales_stats[0] if sales_stats else 0
    total_revenue = float(sales_stats[1]) if sales_stats and sales_stats[1] is not None else 0.0

    cur.close()

    return render_template(
        'dashboard.html',
        total_medicines=total_medicines,
        total_suppliers=total_suppliers,
        expired_count=expired_count,
        low_stock=low_stock,
        expiring_soon=expiring_soon,
        total_sales=total_sales,
        total_revenue=total_revenue
    )


@app.route('/staff_dashboard')
def staff_dashboard():
    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) FROM medicines")
    total_medicines = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM medicines WHERE expiry_date < CURDATE()")
    expired_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM medicines WHERE quantity < 10")
    low_stock = cur.fetchone()[0]

    cur.execute("""
        SELECT name, expiry_date FROM medicines 
        WHERE expiry_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 3 DAY)
    """)
    expiring_soon = cur.fetchall()

    cur.execute("SELECT COUNT(*), COALESCE(SUM(total_amount), 0) FROM sales")
    sales_stats = cur.fetchone()
    total_sales = sales_stats[0] if sales_stats else 0
    total_revenue = float(sales_stats[1]) if sales_stats and sales_stats[1] is not None else 0.0

    cur.close()

    return render_template(
        'staff_dashboard.html',
        total_medicines=total_medicines,
        expired_count=expired_count,
        low_stock=low_stock,
        expiring_soon=expiring_soon,
        total_sales=total_sales,
        total_revenue=total_revenue
    )


@app.route('/medicines')  # ✅ Fixed: only one definition of medicines()
def medicines():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM medicines")
    data = cur.fetchall()
    cur.close()
    return render_template('medicines.html', medicines=data, now=date.today().strftime('%Y-%m-%d'))


@app.route('/add_medicine', methods=['GET', 'POST'])
def add_medicine():
    if session.get('role') != 'Admin':
        flash('Access Denied')
        return redirect(url_for('staff_dashboard'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, supplier_name FROM suppliers")
    suppliers = cur.fetchall()

    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        batch = request.form.get('batch')
        supplier_id = request.form.get('supplier_id')
        manufacture_date = request.form.get('manufacture_date')
        expiry_date = request.form.get('expiry_date')
        quantity = request.form.get('quantity')
        price = request.form.get('price')

        if not all([name, category, batch, supplier_id,
                    manufacture_date, expiry_date, quantity, price]):
            flash('Please fill all fields')
            return redirect(url_for('add_medicine'))

        cur.execute('''
            INSERT INTO medicines
            (name, category, batch_number, supplier_id, manufacture_date, expiry_date, quantity, price)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (name, category, batch, supplier_id,
              manufacture_date, expiry_date, quantity, price))

        mysql.connection.commit()
        cur.close()
        flash('Medicine Added Successfully')
        return redirect(url_for('medicines'))

    cur.close()
    return render_template('add_medicine.html', suppliers=suppliers)


@app.route('/delete_medicine/<int:id>')
def delete_medicine(id):
    if session.get('role') != 'Admin':
        flash('Access Denied')
        return redirect(url_for('staff_dashboard'))

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM medicines WHERE id=%s", [id])
    mysql.connection.commit()
    cur.close()

    flash('Medicine Deleted Successfully')
    return redirect(url_for('medicines'))


@app.route('/suppliers')
def suppliers():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM suppliers")
    data = cur.fetchall()
    cur.close()
    return render_template('suppliers.html', suppliers=data)


@app.route('/add_supplier', methods=['GET', 'POST'])
def add_supplier():
    if session.get('role') != 'Admin':
        flash('Access Denied')
        return redirect(url_for('staff_dashboard'))

    if request.method == 'POST':
        supplier_name = request.form.get('supplier_name')
        contact_number = request.form.get('contact_number')
        address = request.form.get('address')

        if not all([supplier_name, contact_number, address]):
            flash('Please fill all fields')
            return redirect(url_for('add_supplier'))

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO suppliers (supplier_name, contact_number, address) VALUES (%s, %s, %s)",
            (supplier_name, contact_number, address)
        )
        mysql.connection.commit()
        cur.close()

        flash('Supplier Added Successfully')
        return redirect(url_for('suppliers'))

    return render_template('add_supplier.html')


@app.route('/reports')
def reports():
    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM medicines WHERE expiry_date < CURDATE()")
    expired_medicines = cur.fetchall()

    cur.execute("SELECT * FROM medicines WHERE quantity < 10")
    low_stock_medicines = cur.fetchall()

    cur.close()

    return render_template(
        'reports.html',
        expired_medicines=expired_medicines,
        low_stock_medicines=low_stock_medicines
    )


@app.route('/billing', methods=['GET', 'POST'])
def billing():
    if not session.get('username'):
        flash('Please login to access billing')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    if request.method == 'POST':
        medicine_id = request.form.get('medicine_id')
        customer_name = request.form.get('customer_name', '').strip() or 'Walk-in Customer'
        quantity_str = request.form.get('quantity')

        if not medicine_id or not quantity_str:
            flash('Please select a medicine and enter quantity')
            cur.close()
            return redirect(url_for('billing'))

        try:
            quantity_sold = int(quantity_str)
            if quantity_sold <= 0:
                raise ValueError
        except ValueError:
            flash('Please enter a valid positive quantity')
            cur.close()
            return redirect(url_for('billing'))

        cur.execute(
            "SELECT id, name, batch_number, quantity, price, expiry_date FROM medicines WHERE id = %s",
            (medicine_id,)
        )
        medicine = cur.fetchone()

        if not medicine:
            flash('Selected medicine not found')
            cur.close()
            return redirect(url_for('billing'))

        med_id, med_name, batch_no, current_stock, unit_price, expiry_date = medicine

        # Safety check 1: Expiry date
        if expiry_date and expiry_date < date.today():
            flash(f'Cannot dispense {med_name} (Batch: {batch_no}): Medicine has expired on {expiry_date}!')
            cur.close()
            return redirect(url_for('billing'))

        # Safety check 2: Sufficient stock
        if quantity_sold > current_stock:
            flash(f'Insufficient stock for {med_name}! Available: {current_stock}, Requested: {quantity_sold}')
            cur.close()
            return redirect(url_for('billing'))

        total_amount = round(float(unit_price) * quantity_sold, 2)

        # Atomic transaction: decrement stock & insert sale
        cur.execute(
            "UPDATE medicines SET quantity = quantity - %s WHERE id = %s",
            (quantity_sold, med_id)
        )
        cur.execute(
            """INSERT INTO sales (medicine_id, customer_name, quantity_sold, total_amount, sale_date)
               VALUES (%s, %s, %s, %s, CURDATE())""",
            (med_id, customer_name, quantity_sold, total_amount)
        )
        sale_id = cur.lastrowid
        mysql.connection.commit()
        cur.close()

        flash(f'Bill generated successfully! Sold {quantity_sold} units of {med_name} for ₹{total_amount:.2f}')
        return redirect(url_for('receipt', sale_id=sale_id))

    # GET request: fetch non-expired in-stock medicines
    cur.execute("""
        SELECT id, name, category, batch_number, quantity, price, expiry_date
        FROM medicines
        WHERE expiry_date >= CURDATE() AND quantity > 0
        ORDER BY name ASC
    """)
    medicines = cur.fetchall()
    cur.close()
    return render_template('billing.html', medicines=medicines)


@app.route('/receipt/<int:sale_id>')
def receipt(sale_id):
    if not session.get('username'):
        flash('Please login to view receipt')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT s.id, COALESCE(m.name, 'Deleted Medicine'), COALESCE(m.batch_number, 'N/A'),
               s.customer_name, s.quantity_sold, s.total_amount, s.sale_date, COALESCE(m.category, 'General')
        FROM sales s
        LEFT JOIN medicines m ON s.medicine_id = m.id
        WHERE s.id = %s
    """, (sale_id,))
    sale = cur.fetchone()
    cur.close()

    if not sale:
        flash('Receipt not found')
        return redirect(url_for('billing'))

    # Calculate unit price for display: total_amount / quantity_sold
    unit_price = round(float(sale[5]) / sale[4], 2) if sale[4] else 0.0

    return render_template('receipt.html', sale=sale, unit_price=unit_price)


@app.route('/sales')
def sales():
    if not session.get('username'):
        flash('Please login to view sales history')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT s.id, COALESCE(m.name, 'Deleted Medicine'), COALESCE(m.batch_number, 'N/A'),
               s.customer_name, s.quantity_sold, s.total_amount, s.sale_date
        FROM sales s
        LEFT JOIN medicines m ON s.medicine_id = m.id
        ORDER BY s.id DESC
    """)
    sales_data = cur.fetchall()

    cur.execute("SELECT COUNT(*), COALESCE(SUM(total_amount), 0) FROM sales")
    summary = cur.fetchone()
    total_sales = summary[0] if summary else 0
    total_revenue = float(summary[1]) if summary and summary[1] is not None else 0.0

    cur.close()
    return render_template(
        'sales.html',
        sales=sales_data,
        total_sales=total_sales,
        total_revenue=total_revenue
    )


if __name__ == '__main__':
    app.run(debug=True)