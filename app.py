import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from flask import Flask, request, render_template, url_for, redirect, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from fpdf import FPDF  # Use fpdf2 for creating the ticket
from functools import wraps
import os
import sqlite3

from flask_migrate import Migrate
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Flask app configurations
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'zimzam4848@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'ylly efhl trzy ercc'  # Replace with your email password
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@gmail.com'
app.secret_key = 'mysecretkey'
app.config['UPLOAD_FOLDER'] = 'static/uploads'


# Initialize extensions
db = SQLAlchemy(app)
mail = Mail(app)
migrate = Migrate(app, db)

# Admin credentials (for simplicity)
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "adminpassword"

# User model for user accounts
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(100))

    def __init__(self, email, password, name):
        self.name = name
        self.email = email
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Movie model for movie details
class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    language = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    duration = db.Column(db.String(50), nullable=False)
    image_filename = db.Column(db.String(100), nullable=False)
    trailer = db.Column(db.String(255), nullable=True)  # New field for trailer link

    # Relationship with Booking
    bookings = db.relationship('Booking', backref='movie', lazy=True)

    def __init__(self, name, language, price, duration, image_filename, trailer=None):
        self.name = name
        self.language = language
        self.price = price
        self.duration = duration
        self.image_filename = image_filename
        self.trailer = trailer

    def __repr__(self):
        return f'<Movie {self.name}>'

# Booking model to store booking details
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    tickets = db.Column(db.Integer, nullable=False)
    seat_numbers = db.Column(db.String(100), nullable=False)
    show_time = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)

    def __init__(self, movie_id, customer_name, tickets, seat_numbers, show_time, price):
        self.movie_id = movie_id
        self.customer_name = customer_name
        self.tickets = tickets
        self.seat_numbers = seat_numbers
        self.show_time = show_time
        self.price = price

    def __repr__(self):
        return f'<Booking {self.id} for {self.customer_name}>'
    
def init_db():
    conn = sqlite3.connect('bookings.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS bookings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 movie TEXT,
                 customer TEXT,
                 seats INTEGER,
                 seat_numbers TEXT,
                 price REAL)''')
    conn.commit()
    conn.close()

init_db()


# Create the database and tables
with app.app_context():
    db.create_all()
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/index')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/allmov')
def allmov():
    movies = Movie.query.all()
    return render_template('allmov.html', movies=movies)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/edit_movies', methods=['GET', 'POST'])
def edit_movies():
    if request.method == 'POST':
        movie_name = request.form['movie_name']
        language = request.form['language']
        price = request.form['price']
        duration = request.form['duration']
        trailer = request.form['trailer']  # Get the trailer link from the form
        image = request.files['movie_image']

        if image:
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)

            # Add the movie to the database with the trailer link
            new_movie = Movie(
                name=movie_name,
                language=language,
                price=price,
                duration=duration,
                image_filename=filename,
                trailer=trailer  # Store the trailer link in the database
            )
            db.session.add(new_movie)
            db.session.commit()

            flash("Movie added successfully!", "success")
            return redirect(url_for('admin_movies'))
    
    return render_template('edit_movies.html')

def get_movie_by_id(movie_id):
    return Movie.query.get(movie_id)

@app.route('/mov1')
def mov1():
    return render_template('mov1.html')  

@app.route('/movie/<int:movie_id>')
def movie_details(movie_id):
    movie = get_movie_by_id(movie_id)
    if movie is None:
        flash("Movie not found!", "danger")
        return redirect(url_for('allmov'))
    return render_template('mov2.html', movie=movie)

@app.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    movie_id = request.args.get('movie_id')

    if not movie_id:
        flash("Movie not found!", "danger")
        return redirect(url_for('allmov'))
    
    movie = Movie.query.get(movie_id)
    if not movie:
        flash("Movie not found!", "danger")
        return redirect(url_for('allmov'))
    
    # Fetch reserved seats from the bookings_details table
    conn_details = sqlite3.connect('bookings_details.db')
    c_details = conn_details.cursor()
    c_details.execute("SELECT seats FROM booking_details")
    bookings = c_details.fetchall()
    conn_details.close()

    # Parse the seat numbers from the bookings
    reserved_seats = []
    for booking in bookings:
        seat_numbers = booking[0].split(",")  # Assuming seats are stored as comma-separated values
        reserved_seats.extend(map(int, seat_numbers))
    
    # Pass the reserved seats to the template
    return render_template('book.html', movie=movie, reserved_seats=reserved_seats)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user:
            flash("Email already registered!", "danger")
        else:
            new_user = User(name=name, email=email, password=password)
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    next_url = request.args.get('next')

    if request.method == 'POST':
        role = request.form['role']
        email = request.form['email']
        password = request.form['password']

        if role == 'admin':
            if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
                session['user_id'] = 'admin'
                flash("Logged in as admin!", "success")
                return redirect(next_url or url_for('admin_index'))
            else:
                flash("Invalid admin credentials.", "danger")
                return render_template('login.html', error="Invalid admin credentials")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash("Logged in successfully!", "success")
            return redirect(next_url or url_for('index'))
        else:
            flash("Invalid email or password", "danger")
            return render_template('login.html', error="Invalid email or password")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/admin')
def admin_panel():
    return render_template('admin_index.html')

@app.route('/users')
def users():
    if 'user_id' not in session:
        flash("Please log in to access this page.", "warning")
        return redirect(url_for('login'))

    users = User.query.all()
    return render_template('users.html', users=users)


@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if request.method == 'GET':
        # Handle GET request to render the payment page
        movie_id = request.args.get('movieId')
        if not movie_id:
            flash("Movie not found!", "danger")
            return redirect(url_for('allmov'))

        # Retrieve movie details from the database
        movie = Movie.query.get(movie_id)
        if not movie:
            flash("Movie not found!", "danger")
            return redirect(url_for('allmov'))

        name = request.args.get('name')
        seat_count = request.args.get('seatCount')
        seats = request.args.get('seats')

        return render_template('payment.html', 
                               movie=movie,
                               name=name,
                               seat_count=seat_count,
                               seats=seats)

    elif request.method == 'POST':
        # Handle POST request to process payment
        data = request.json
        name = data.get('name')
        seats = data.get('seats')
        seat_count = int(data.get('seatCount'))
        movie_name = data.get('movieName')
        movie_language = data.get('movieLanguage')
        price_per_seat = float(data.get('pricePerSeat'))
        total_price = float(data.get('totalPrice'))
        email = data.get('email')

        # Insert booking into the primary database
        conn = sqlite3.connect('bookings.db')
        c = conn.cursor()
        c.execute("INSERT INTO bookings (movie, customer, seats, seat_numbers, price) VALUES (?, ?, ?, ?, ?)",
                  (movie_name, name, seat_count, seats, total_price))
        booking_id = c.lastrowid
        conn.commit()
        conn.close()

        # Insert booking into the secondary database
        conn_details = sqlite3.connect('bookings_details.db')
        c_details = conn_details.cursor()

        # Ensure the table exists in the secondary database
        c_details.execute("""
            CREATE TABLE IF NOT EXISTS booking_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                seats TEXT,
                seat_count INTEGER,
                movie_name TEXT,
                movie_language TEXT,
                price_per_seat REAL,
                total_price REAL,
                email TEXT
            )
        """)

        # Insert booking details into the secondary database
        c_details.execute("INSERT INTO booking_details (name, seats, seat_count, movie_name, movie_language, price_per_seat, total_price, email) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                          (name, seats, seat_count, movie_name, movie_language, price_per_seat, total_price, email))
        conn_details.commit()
        conn_details.close()

        # Generate PDF ticket
        pdf_file = generate_pdf(booking_id, movie_name, movie_language, name, seats, seat_count, total_price)

        # Send email with ticket PDF attached
        try:
            send_email(name, email, pdf_file)
            message = "Booking confirmed and ticket sent to your email!"
        except Exception as e:
            message = f"Booking confirmed, but email sending failed: {e}"

        # Redirect to index.html after successful payment
        return jsonify({"message": message, "redirect_url": url_for('index')})




def generate_pdf(booking_id, movie, language, customer, seats, seat_count, total_price):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Booking Confirmation", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Booking ID: {booking_id}", ln=True)
    pdf.cell(200, 10, txt=f"Movie: {movie} ({language})", ln=True)
    pdf.cell(200, 10, txt=f"Customer: {customer}", ln=True)
    pdf.cell(200, 10, txt=f"Seats: {seats} (Count: {seat_count})", ln=True)
    pdf.cell(200, 10, txt=f"Total Price: ${total_price:.2f}", ln=True)
    pdf_file = f"{booking_id}_ticket.pdf"
    pdf.output(pdf_file)
    return pdf_file


def send_email(customer, email, pdf_file):
    msg = MIMEMultipart()
    msg['Subject'] = 'Your Movie Ticket'
    msg['From'] = 'zimzam@example.com'
    msg['To'] = email

    body = MIMEText(f"Dear {customer},\n\nThank you for your booking! Please find your ticket attached.\n\nBest regards,\nThe Movie Theater Team")
    msg.attach(body)

    with open(pdf_file, 'rb') as f:
        part = MIMEApplication(f.read(), _subtype="pdf")
        part.add_header('Content-Disposition', 'attachment', filename=pdf_file)
        msg.attach(part)

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login('zimzam4848@gmail.com', 'ylly efhl trzy ercc')
        server.send_message(msg)



@app.route('/mov2')
def mov2():
    movies = Movie.query.all()
    return render_template('mov2.html', movies=movies)

@app.route('/user_movies', methods=['GET', 'POST'])
def user_movies():
    if request.method == 'POST':
        # Ensure only admins can add movies
        if 'user_id' not in session or session['user_id'] != 'admin':
            flash("Only admins can add movies.", "danger")
            return redirect(url_for('user_movies'))
        
        name = request.form['name']
        language = request.form['language']
        price = request.form['price']
        duration = request.form['duration']
        image = request.files['image']
        
        if image:
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            movie = Movie(name=name, language=language, price=price, duration=duration, image_filename=filename)
            db.session.add(movie)
            db.session.commit()
            flash("Movie added successfully!", "success")
            return redirect(url_for('user_movies'))
    
    movies = Movie.query.all()
    return render_template('user_movies.html', movies=movies)



@app.route('/admin/movies', methods=['GET'])
def admin_movies():
    # Fetch all movies for admin view
    movies = Movie.query.all()
    return render_template('admin_movies.html', movies=movies)

@app.route('/delete_movie/<int:movie_id>', methods=['POST'])
def delete_movie(movie_id):
    # Find the movie by ID
    movie = Movie.query.get_or_404(movie_id)

    # Delete the movie's image file from the server
    if movie.image_filename:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], movie.image_filename))
        except FileNotFoundError:
            pass

    # Delete the movie from the database
    db.session.delete(movie)
    db.session.commit()

    flash("Movie deleted successfully!", "success")
    return redirect(url_for('admin_movies'))

@app.route('/admin_index')
def admin_index():
    # Count total users and movies from SQLAlchemy models
    total_users = User.query.count()
    total_movies = Movie.query.count()

    # Count total bookings from the SQLite database
    conn_details = sqlite3.connect('bookings_details.db')
    c_details = conn_details.cursor()
    c_details.execute("SELECT COUNT(*) FROM booking_details")
    total_bookings = c_details.fetchone()[0]
    conn_details.close()

    return render_template('admin_index.html', total_users=total_users, total_bookings=total_bookings, total_movies=total_movies)


@app.route('/all_bookings', methods=['GET'])
def all_bookings():
    # Connect to the secondary database
    conn_details = sqlite3.connect('bookings_details.db')
    c_details = conn_details.cursor()
    
    # Fetch all bookings
    c_details.execute("SELECT * FROM booking_details")
    bookings = c_details.fetchall()
    conn_details.close()
    
    # Render the template and pass booking data
    return render_template('all_bookings.html', bookings=bookings)

@app.route('/delete_booking/<int:booking_id>', methods=['POST'])
def delete_booking(booking_id):
    # Connect to the secondary database
    conn_details = sqlite3.connect('bookings_details.db')
    c_details = conn_details.cursor()
    
    # Delete the booking by ID
    c_details.execute("DELETE FROM booking_details WHERE id = ?", (booking_id,))
    conn_details.commit()
    
    # Reset IDs to be sequential
    c_details.execute("""
        CREATE TEMP TABLE temp_table AS
        SELECT * FROM booking_details;
    """)
    c_details.execute("DELETE FROM booking_details;")
    c_details.execute("""
        INSERT INTO booking_details (id, name, seats, seat_count, movie_name, movie_language, price_per_seat, total_price, email)
        SELECT ROW_NUMBER() OVER (ORDER BY id) AS id, name, seats, seat_count, movie_name, movie_language, price_per_seat, total_price, email
        FROM temp_table;
    """)
    c_details.execute("DROP TABLE temp_table;")
    conn_details.commit()
    
    # Update the AUTOINCREMENT value based on the highest ID in the table
    c_details.execute("""
        UPDATE sqlite_sequence SET seq = (SELECT MAX(id) FROM booking_details) WHERE name = 'booking_details';
    """)
    conn_details.commit()
    
    # Close the database connection
    conn_details.close()
    
    flash("Booking deleted and IDs updated successfully!", "success")
    return redirect(url_for('all_bookings'))



if __name__ == '__main__':
    app.run(debug=True)