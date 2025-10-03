from app import app, db
from flask import render_template, request, redirect, url_for, flash
from app.models import User, Book, Message
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy import or_
import re

from app.decorators import seller_required

@app.route('/')
@login_required
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        contact = request.form['contact']
        password = request.form['password']
        password_confirm = request.form.get('password_confirm', '')
        role = request.form['role']

        # Basic validation
        if not name or not email or not password or not password_confirm:
            flash('Please fill out all required fields.')
            return redirect(url_for('register'))

        if password != password_confirm:
            flash('Passwords do not match.')
            return redirect(url_for('register'))

        # Email format check
        email_regex = r"[^@]+@[^@]+\.[^@]+"
        if not re.match(email_regex, email):
            flash('Invalid email address.')
            return redirect(url_for('register'))

        # Password strength (8 chars min, with number)
        if len(password) < 8 or not re.search(r'\d', password):
            flash('Password must be at least 8 characters long and contain a number.')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered.')
            return redirect(url_for('register'))

        user = User(name=name, email=email, contact=contact, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user is None or not user.check_password(request.form['password']):
            flash('Invalid credentials')
            return redirect(url_for('login'))
        login_user(user)
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.')
    return redirect(url_for('login'))

@app.route('/books', methods=['GET'])
def books():
    query = Book.query
    title = request.args.get('title', '').strip()
    author = request.args.get('author', '').strip()
    min_price = request.args.get('min_price', '').strip()
    max_price = request.args.get('max_price', '').strip()

    if title:
        query = query.filter(Book.title.ilike(f'%{title}%'))
    if author:
        query = query.filter(Book.author.ilike(f'%{author}%'))
    try:
        if min_price:
            query = query.filter(Book.price >= float(min_price))
        if max_price:
            query = query.filter(Book.price <= float(max_price))
    except ValueError:
        flash('Price filters must be valid numbers.')

    books = query.all()
    return render_template('books.html', books=books, title=title, author=author, min_price=min_price, max_price=max_price)

@app.route('/books/add', methods=['GET', 'POST'])
@login_required
@seller_required
def add_book():
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        description = request.form.get('description')
        condition = request.form.get('condition')
        price = request.form.get('price')
        image_url = request.form.get('image_url')
        if not title or not price:
            flash('Please provide both title and price.')
            return redirect(url_for('add_book'))
        try:
            price_val = float(price)
        except ValueError:
            flash('Price must be a number.')
            return redirect(url_for('add_book'))
        new_book = Book(
            title=title, author=author, description=description,
            condition=condition, price=price_val,
            image_url=image_url, seller_id=current_user.id)
        db.session.add(new_book)
        db.session.commit()
        flash('Book added successfully!')
        return redirect(url_for('books'))
    return render_template('add_book.html')

@app.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
@seller_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    if book.seller_id != current_user.id:
        flash('You are not authorized to edit this book.')
        return redirect(url_for('books'))
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        description = request.form.get('description')
        condition = request.form.get('condition')
        price = request.form.get('price')
        image_url = request.form.get('image_url')

        if not title or not price:
            flash('Title and price are required.')
            return redirect(url_for('edit_book', book_id=book.id))
        try:
            price_val = float(price)
        except ValueError:
            flash('Price must be a number.')
            return redirect(url_for('edit_book', book_id=book.id))

        book.title = title
        book.author = author
        book.description = description
        book.condition = condition
        book.price = price_val
        book.image_url = image_url

        db.session.commit()
        flash('Book updated successfully.')
        return redirect(url_for('books'))
    return render_template('edit_book.html', book=book)

@app.route('/books/delete/<int:book_id>', methods=['POST'])
@login_required
@seller_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    if book.seller_id != current_user.id:
        flash('You are not authorized to delete this book.')
        return redirect(url_for('books'))
    db.session.delete(book)
    db.session.commit()
    flash('Book deleted successfully.')
    return redirect(url_for('books'))

@app.route('/messages/<int:user_id>', methods=['GET', 'POST'])
@login_required
def messages(user_id):
    other_user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        message_text = request.form['message'].strip()
        if message_text:
            msg = Message(sender_id=current_user.id, receiver_id=other_user.id, message_text=message_text)
            db.session.add(msg)
            db.session.commit()
            flash('Message sent.')
        return redirect(url_for('messages', user_id=other_user.id))
    conversation = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == other_user.id)) |
        ((Message.sender_id == other_user.id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()
    return render_template('messages.html', conversation=conversation, other_user=other_user)

@app.route('/profile')
@login_required
def profile():
    user_books = []
    if current_user.role == 'seller':
        user_books = Book.query.filter_by(seller_id=current_user.id).all()
    return render_template('profile.html', user=current_user, books=user_books)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        contact = request.form.get('contact', '').strip()
        if not name:
            flash('Name cannot be empty.')
            return redirect(url_for('edit_profile'))
        current_user.name = name
        current_user.contact = contact
        db.session.commit()
        flash('Profile updated successfully.')
        return redirect(url_for('profile'))
    return render_template('edit_profile.html', user=current_user)

# Error handlers
@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500
