from flask import Flask, render_template, request, redirect, flash, session, url_for
import sqlite3, random, string
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def init_db():
    conn = sqlite3.connect('database.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            countrycode TEXT,
            number TEXT,
            gender TEXT,
            dob    TEXT       
                           
        )''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_url TEXT,
            shorten_url TEXT,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(id)
        )''')
    conn.close()

def shorten_url(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.route('/', methods=['GET', 'POST'])
def home():
    short_url=None

    if request.method == 'POST':
        original_url = request.form['url']
        short_id = shorten_url()
        user_id = session.get('user_id')

        conn = sqlite3.connect('database.db')
        conn.execute('INSERT INTO urls(original_url, shorten_url, user_id) VALUES (?, ?, ?)', 
                     (original_url, short_id, user_id))
        conn.commit()
        conn.close()

        short_url = request.host_url + short_id
        flash(f'SHORTENED URL: {short_url}', 'info')
        return render_template('index.html', short_url=short_url)
    return render_template('index.html')

@app.route('/<short_id>')
def redirect_url(short_id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('SELECT original_url FROM urls WHERE shorten_url = ?', (short_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return redirect(row[0])
    else:
        return 'Invalid URL', 404

@app.route('/signup', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        countrycode = request.form['cc']
        number = request.form['number']
        gender = request.form['gender']
        dob = request.form['dob']
        try:
            conn = sqlite3.connect('database.db')
            conn.execute('INSERT INTO Users(username, password,countrycode,number,gender,dob) VALUES (?, ?, ?, ?, ?, ?)', (username, password, countrycode, number, gender , dob))
            conn.commit()
            conn.close()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists!', 'danger')
    return render_template('signup.html')

@app.route('/Login-Form', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        cur.execute('SELECT id, password FROM Users WHERE username = ?', (username,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('Login-Form.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect('/')

@app.route('/Dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Login required to access dashboard.', 'warning')
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    # For future analytics (total clicks etc.)
    cur.execute('SELECT COUNT(*) FROM urls WHERE user_id = ?', (session['user_id'],))
    total_urls = cur.fetchone()[0]

    # Sample: clicks per day (replace with actual click tracking if available)
    cur.execute('''
        SELECT DATE(created_at), COUNT(*) 
        FROM urls 
        WHERE user_id = ? 
        GROUP BY DATE(created_at)
    ''', (session['user_id'],))
    click_data = cur.fetchall()
    conn.close()

    labels = [row[0] for row in click_data]
    values = [row[1] for row in click_data]

    return render_template('Dashboard.html', labels=labels, values=values , total_urls=total_urls)

# @app.route('/Dashboard')
# def dashboard():
#     if 'user_id' not in session:
#         flash('Login required to access dashboard.', 'warning')
#         return redirect('/Login-Form')

#     conn = sqlite3.connect('database.db')
#     cur = conn.cursor()
#     cur.execute('SELECT id, original_url, shorten_url, created_at FROM urls WHERE user_id = ?', (session['user_id'],))
#     urls = cur.fetchall()
#     conn.close()
#     return render_template('Dashboard.html', urls=urls)

@app.route('/delete/<int:url_id>')
def delete_url(url_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    conn.execute('DELETE FROM urls WHERE id = ? AND user_id = ?', (url_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('URL deleted successfully.', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
