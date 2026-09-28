from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date


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

    cur.close()

    return render_template(
        'dashboard.html',
        total_medicines=total_medicines,
        total_suppliers=total_suppliers,
        expired_count=expired_count,
        low_stock=low_stock,
        expiring_soon=expiring_soon
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

    cur.close()

    return render_template(
        'staff_dashboard.html',
        total_medicines=total_medicines,
        expired_count=expired_count,
        low_stock=low_stock,
        expiring_soon=expiring_soon
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


if __name__ == '__main__':
    app.run(debug=True)