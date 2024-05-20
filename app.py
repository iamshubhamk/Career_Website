from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import sqlite3
import hashlib

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure key in production
DATABASE = './jobs.db'

# Initialize database connection
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Utility function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL -- 'recruiter' or 'jobseeker'
            )
        ''')

        # Create jobs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                recruiter_id INTEGER NOT NULL,
                FOREIGN KEY (recruiter_id) REFERENCES users(id)
            )
        ''')

        # Create applications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                jobseeker_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending', -- 'pending', 'accepted', 'rejected'
                FOREIGN KEY (job_id) REFERENCES jobs(id),
                FOREIGN KEY (jobseeker_id) REFERENCES users(id)
            )
        ''')

        conn.commit()
        print("Database tables created successfully.")
    except Exception as e:
        print(f"Error creating database tables: {e}")
    finally:
        conn.close()

create_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recruiter-login')
def recruiter_login():
    return render_template('recruiter_login.html')

# Route to handle recruiter login form submission
@app.route('/recruiter-login', methods=['POST'])
def recruiter_login_post():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Add your login logic here
        return redirect(url_for('recruiter_dashboard'))
    return render_template('recruiter_login.html')

# Route to serve the jobseeker login page
@app.route('/jobseeker-login')
def jobseeker_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Add your login logic here
        return redirect(url_for('jobseeker_dashboard'))
    return render_template('jobseeker_login.html')

# Route to handle jobseeker login form submission
@app.route('/jobseeker-login', methods=['POST'])
def jobseeker_login_post():
    username = request.form['username']
    password = request.form['password']
    # Add your login logic here
    return redirect(url_for('jobseeker_dashboard'))

# Placeholder route for recruiter dashboard
@app.route('/recruiter-dashboard')
def recruiter_dashboard():
    return render_template('recruiter_dashboard.html')

# Placeholder route for jobseeker dashboard
@app.route('/jobseeker-dashboard')
def jobseeker_dashboard():
    return render_template('jobseeker_dashboard.html')

# Route to create database tables (for testing or setup purposes)
@app.route('/create-db')
def create_database():
    create_db()
    return 'Database tables created successfully.'

@app.route('/register')
def register():
    return render_template('register.html')

# Endpoint to register a new user (both recruiters and job seekers)
@app.route('/register', methods=['POST'])
def register_post():
    role = request.form['role']
    username = request.form['username']
    password = request.form['password']
    conn = sqlite3.connect('jobs.db')
    c = conn.cursor()
    c.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
              (username, password, role))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# Endpoint to authenticate a user
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Missing username or password'}), 400

    hashed_password = hash_password(password)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, hashed_password))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return jsonify({'message': 'Login successful!', 'user_id': user['id'], 'role': user['role']}), 200
        else:
            return jsonify({'error': 'Invalid username or password'}), 401
    except Exception as e:
        print(e)
        return jsonify({'error': 'Failed to login'}), 500
    finally:
        conn.close()

# Endpoint to logout a user
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Endpoint to post a new job
@app.route('/post-job', methods=['POST'])
def post_job():
    if 'user_id' not in session or session['role'] != 'recruiter':
        return jsonify({'error': 'Unauthorized access'}), 401

    data = request.json
    title = data.get('title')
    description = data.get('description')
    location = data.get('location')

    if not title or not description or not location:
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO jobs (title, description, location, recruiter_id) VALUES (?, ?, ?, ?)',
                       (title, description, location, session['user_id']))
        conn.commit()
        job_id = cursor.lastrowid
        return jsonify({'message': 'Job posted successfully!', 'job_id': job_id}), 200
    except Exception as e:
        print(e)
        return jsonify({'error': 'Failed to post job'}), 500
    finally:
        conn.close()

# Endpoint to retrieve jobs for job seekers
@app.route('/jobs')
def get_jobs():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM jobs')
        jobs = cursor.fetchall()
        return jsonify([dict(job) for job in jobs]), 200
    except Exception as e:
        print(e)
        return jsonify({'error': 'Failed to retrieve jobs'}), 500
    finally:
        conn.close()

# Endpoint to apply for a job
@app.route('/apply-job/<int:job_id>', methods=['POST'])
def apply_job(job_id):
    if 'user_id' not in session or session['role'] != 'jobseeker':
        return jsonify({'error': 'Unauthorized access'}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO applications (job_id, jobseeker_id) VALUES (?, ?)',
                       (job_id, session['user_id']))
        conn.commit()
        application_id = cursor.lastrowid
        return jsonify({'message': 'Job application submitted successfully!', 'application_id': application_id}), 200
    except Exception as e:
        print(e)
        return jsonify({'error': 'Failed to submit job application'}), 500
    finally:
        conn.close()

# Endpoint to update application status
@app.route('/update-application/<int:application_id>', methods=['PUT'])
def update_application(application_id):
    if 'user_id' not in session or session['role'] != 'recruiter':
        return jsonify({'error': 'Unauthorized access'}), 401

    data = request.json
    status = data.get('status')

    if not status:
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE applications SET status = ? WHERE id = ?',
                       (status, application_id))
        conn.commit()
        return jsonify({'message': 'Application status updated successfully!'}), 200
    except Exception as e:
        print(e)
        return jsonify({'error': 'Failed to update application status'}), 500
    finally:
        conn.close()

# Start the Flask app
if __name__ == '__main__':
    app.run(debug=True)
