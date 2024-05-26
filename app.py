from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import logging

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///career_website.db'
app.config['UPLOAD_FOLDER'] = 'uploads'

# Initialize SQLAlchemy instance
db = SQLAlchemy()

# Import models after db has been initialized
from models import db, Recruiter, JobSeeker, Job, Applicant

# Bind SQLAlchemy instance to the app
db.init_app(app)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Define allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}


@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']
        
        if user_type == 'recruiter':
            user = Recruiter.query.filter_by(email=email).first()
        else:
            user = JobSeeker.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_type'] = user_type
            session['email'] = email  # Store email in session
            
            if user_type == 'recruiter':
                return redirect(url_for('recruiter_dashboard'))
            else:
                return redirect(url_for('jobseeker_dashboard'))
        
        flash('Invalid email or password')
    
    return render_template('login.html')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/application_status', methods=['GET'])
def application_status():
    if 'user_id' not in session or session['user_type'] != 'jobseeker':
        return redirect(url_for('login'))

    email = session.get('email')
    if not email:
        return "Email not found in session", 400

    applications = Applicant.query.filter_by(email=email).all()

    return render_template('application_status.html', applications=applications)


@app.route('/apply_job', methods=['POST'])
def apply_job():
    if 'user_id' not in session or session['user_type'] != 'jobseeker':
        return redirect(url_for('login'))

    try:
        job_id = request.form['job_id']
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        resume = request.files['resume']

        if resume and allowed_file(resume.filename):
            filename = secure_filename(resume.filename)
            resume.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            new_applicant = Applicant(
                job_id=job_id,
                name=name,
                email=email,
                phone=phone,
                resume=filename,
                status='application not seen'
            )
            db.session.add(new_applicant)
            db.session.commit()
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'status': 'fail', 'message': 'Invalid file type'}), 400

    except Exception as e:
        logging.error("Error during job application: %s", e)
        return jsonify({'status': 'fail', 'message': 'Internal Server Error'}), 500


@app.route('/manage_applicant/<int:applicant_id>', methods=['GET', 'POST'])
def manage_applicant(applicant_id):
    if 'user_id' not in session or session['user_type'] != 'recruiter':
        return redirect(url_for('login'))

    applicant = Applicant.query.get(applicant_id)
    if not applicant:
        return "Applicant not found."

    if request.method == 'POST':
        status = request.form['status']
        applicant.status = status
        db.session.commit()
        flash('Applicant status updated successfully.')
        return redirect(url_for('recruiter_dashboard'))

    return render_template('manage_applicant.html', applicant=applicant)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']

        new_user = User(email=email, password=password, user_type=user_type)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/recruiter_dashboard')
def recruiter_dashboard():
    if 'user_id' not in session or session['user_type'] != 'recruiter':
        return redirect(url_for('login'))
    
    jobs = Job.query.filter_by(recruiter_id=session['user_id']).all()
    return render_template('recruiter_dashboard.html', jobs=jobs)

@app.route('/post_job_form')
def post_job_form():
    if 'user_id' not in session or session['user_type'] != 'recruiter':
        return redirect(url_for('login'))
    
    return render_template('post_job_form.html')

@app.route('/post_job', methods=['POST'])
def post_job():
    if 'user_id' not in session or session['user_type'] != 'recruiter':
        return redirect(url_for('login'))
    
    title = request.form['title']
    description = request.form['description']

    new_job = Job(title=title, description=description, recruiter_id=session['user_id'])
    db.session.add(new_job)
    db.session.commit()

    flash('Job posted successfully.')
    return redirect(url_for('recruiter_dashboard'))

@app.route('/jobseeker_dashboard', methods=['GET'])
def jobseeker_dashboard():
    if 'user_id' not in session or session['user_type'] != 'jobseeker':
        return redirect(url_for('login'))

    email = session.get('email')
    if not email:
        return "Email not found in session", 400

    # Fetch jobs and check if the jobseeker has applied to them
    jobs = Job.query.all()
    applications = Applicant.query.filter_by(email=email).all()
    applied_jobs = {application.job_id: application.status for application in applications}

    job_list = []
    for job in jobs:
        job_dict = {
            'id': job.id,
            'title': job.title,
            'description': job.description,
            'applied': job.id in applied_jobs,
            'status': applied_jobs.get(job.id, '')
        }
        job_list.append(job_dict)

    return render_template('jobseeker_dashboard.html', jobs=job_list)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
