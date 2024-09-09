from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import os
from flask_migrate import Migrate

app = Flask(__name__)

uri = os.getenv("DATABASE_URL")  # or other relevant config var
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///literatus.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'hannah_arendt_is_great')

#app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///literatus.db')
#app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'hannah_arendt_is_great')

db = SQLAlchemy(app)
migrate = Migrate(app, db)

#app.config['SECRET_KEY'] = 'your-secret-key'  # Replace with a real secret key
#app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key')
#app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///literatus.db')
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///literatus.db'
#db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'



class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    profile_image = db.Column(db.String(256))
    books = db.relationship('Book', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def beloved_books(self):
        return [book for book in self.books if book.sentiment == 'beloved']

    @property
    def tolerated_books(self):
        return [book for book in self.books if book.sentiment == 'tolerated']

    @property
    def disliked_books(self):
        return [book for book in self.books if book.sentiment == 'disliked']


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    sentiment = db.Column(db.String(20), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists')
            return redirect(url_for('register'))

        profile_image = f"https://api.dicebear.com/6.x/initials/svg?seed={username}"
        new_user = User(username=username, profile_image=profile_image)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('profile'))
        flash('Invalid username or password')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/profile')
@login_required
def profile():
    beloved_books = Book.query.filter_by(user_id=current_user.id, sentiment='beloved').order_by(Book.position).all()
    tolerated_books = Book.query.filter_by(user_id=current_user.id, sentiment='tolerated').order_by(Book.position).all()
    disliked_books = Book.query.filter_by(user_id=current_user.id, sentiment='disliked').order_by(Book.position).all()

    all_books = beloved_books + tolerated_books + disliked_books
    total_books = len(all_books)

    for i, book in enumerate(all_books):
        if book.sentiment == 'beloved':
            base = 7.5
            max_rating = 10
        elif book.sentiment == 'tolerated':
            base = 4.5
            max_rating = 7
        else:  # disliked
            base = 1
            max_rating = 4

        category_books = beloved_books if book in beloved_books else \
            tolerated_books if book in tolerated_books else \
                disliked_books
        category_position = category_books.index(book)
        category_total = len(category_books)

        book.rating = base + ((max_rating - base) * (1 - (category_position / (category_total - 1 or 1))))
        book.rating = round(book.rating, 1)  # Round to one decimal place
        book.global_position = i + 1

    return render_template('profile.html', user=current_user,
                           beloved_books=beloved_books,
                           tolerated_books=tolerated_books,
                           disliked_books=disliked_books)


@app.route('/search_books')
def search_books():
    query = request.args.get('query', '')
    if query:
        url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=5"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            books = []
            for item in data.get('items', []):
                volume_info = item.get('volumeInfo', {})
                title = volume_info.get('title', 'Unknown Title')
                authors = volume_info.get('authors', ['Unknown Author'])
                books.append({"title": title, "author": authors[0]})
            return jsonify(books)
    return jsonify([])


@app.route('/add_book', methods=['POST'])
@login_required
def add_book():
    title = request.form['title']
    author = request.form['author']
    sentiment = request.form['sentiment']

    new_book = Book(title=title, author=author, sentiment=sentiment, user_id=current_user.id, position=0)
    db.session.add(new_book)
    db.session.commit()

    flash('Book added successfully!')
    return redirect(url_for('rate_new_book', book_id=new_book.id))


@app.route('/rate_new_book/<int:book_id>')
@login_required
def rate_new_book(book_id):
    new_book = db.session.get(Book, book_id)
    if not new_book:
        flash('Book not found.')
        return redirect(url_for('profile'))

    books_to_compare = Book.query.filter_by(user_id=current_user.id, sentiment=new_book.sentiment).order_by(Book.position).all()
    books_to_compare = [book for book in books_to_compare if book.id != new_book.id]

    if not books_to_compare:
        new_book.position = 1
        db.session.commit()
        flash('Book rating completed!')
        return redirect(url_for('profile'))

    session['books_to_compare'] = [book.id for book in books_to_compare]
    session['comparison_index'] = len(books_to_compare) // 2
    session['new_book_id'] = new_book.id

    compared_book = books_to_compare[session['comparison_index']]
    return render_template('rate_new_book.html', new_book=new_book, compared_book=compared_book)


@app.route('/compare_books', methods=['POST'])
@login_required
def compare_books():
    new_book_id = session.get('new_book_id')
    compared_book_id = int(request.form['compared_book_id'])
    preference = int(request.form['preference'])

    new_book = db.session.get(Book, new_book_id)
    compared_book = db.session.get(Book, compared_book_id)

    if not new_book or not compared_book:
        flash('Error: Book not found.')
        return redirect(url_for('profile'))

    books_to_compare = [db.session.get(Book, book_id) for book_id in session['books_to_compare']]
    index = session['comparison_index']

    if preference == 1:  # New book is preferred
        books_to_compare = books_to_compare[:index]
    else:  # Compared book is preferred
        books_to_compare = books_to_compare[index+1:]

    if not books_to_compare:
        # We've found the position for the new book
        insert_position = compared_book.position if preference == 1 else compared_book.position + 1
        insert_book(new_book, insert_position)
        flash('Book rating completed!')
        return redirect(url_for('profile'))

    session['books_to_compare'] = [book.id for book in books_to_compare]
    session['comparison_index'] = len(books_to_compare) // 2

    next_book = books_to_compare[session['comparison_index']]
    return render_template('rate_new_book.html', new_book=new_book, compared_book=next_book)


def insert_book(new_book, insert_position):
    books_to_update = Book.query.filter(
        Book.user_id == new_book.user_id,
        Book.sentiment == new_book.sentiment,
        Book.position >= insert_position
    ).all()

    for book in books_to_update:
        book.position += 1

    new_book.position = insert_position
    db.session.commit()


def update_ratings(user_id, sentiment):
    books = Book.query.filter_by(user_id=user_id, sentiment=sentiment).order_by(Book.position).all()
    total_books = len(books)
    for index, book in enumerate(books, start=1):
        book.rating = 10 - ((index - 1) * 9 / (total_books - 1)) if total_books > 1 else 10
    db.session.commit()


def update_category_ratings(books):
    if not books:
        return
    min_rating = min(book.rating or 5 for book in books)
    max_rating = max(book.rating or 5 for book in books)
    for book in books:
        if min_rating != max_rating:
            normalized_rating = (book.rating - min_rating) / (max_rating - min_rating)
            if book.sentiment == 'beloved':
                book.rating = 7 + (normalized_rating * 3)
            elif book.sentiment == 'tolerated':
                book.rating = 4 + (normalized_rating * 3)
            else:  # disliked
                book.rating = 1 + (normalized_rating * 3)
        else:
            if book.sentiment == 'beloved':
                book.rating = 8.5
            elif book.sentiment == 'tolerated':
                book.rating = 5.5
            else:  # disliked
                book.rating = 2.5


def binary_search_insert(books, new_book):
    left, right = 0, len(books) - 1
    while left <= right:
        mid = (left + right) // 2
        if books[mid].rating < new_book.rating:
            right = mid - 1
        else:
            left = mid + 1
    return left

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run()