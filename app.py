from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from models import db, User, GameSession
import random
import os
from datetime import datetime, timedelta
from image_generator import ImageGenerator
from config import Config

app = Flask(__name__)
# Load settings from Config (which reads env vars if set)
app.config.from_object(Config)
# Ensure SQLAlchemy track modifications default is explicit
app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)
# Secret key override (already in Config) – keep for backward compatibility
app.secret_key = app.config.get('SECRET_KEY', 'your-secret-key-here-change-in-production')

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Initialize image generator
image_gen = ImageGenerator()


def get_generated_image_path(filename: str) -> str:
    """Return absolute filesystem path for a generated image filename."""
    return os.path.join(app.root_path, 'static', 'images', 'generated', filename)


def ensure_image_for_state(game_state):
    """Ensure the game_state has a valid current_image file; regenerate if missing."""
    # If there's no image or the file does not exist on disk, regenerate it
    if not getattr(game_state, 'current_image', None):
        game_state.current_image = image_gen.generate_image(number=game_state.current_number,
                                                            difficulty=game_state.difficulty)
        return

    image_path = get_generated_image_path(game_state.current_image)
    if not os.path.exists(image_path):
        # Regenerate into the correct static directory
        game_state.current_image = image_gen.generate_image(number=game_state.current_number,
                                                            difficulty=game_state.difficulty)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class GameState:
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.score = 0
        self.lives = 3
        self.difficulty = "easy"
        self.current_number = None
        self.current_image = None
        self.questions_answered = 0
        self.correct_answers = 0
        self.start_time = datetime.now()
    
    def generate_new_number(self):
        """Generate a new number based on difficulty"""
        digit_ranges = {
            'easy': (1, 3),
            'medium': (2, 4), 
            'hard': (3, 5),
            'expert': (4, 6)
        }
        
        min_digits, max_digits = digit_ranges[self.difficulty]
        num_digits = random.randint(min_digits, max_digits)
        
        if num_digits > 1:
            first_digit = random.randint(1, 9)
            other_digits = ''.join(str(random.randint(0, 9)) for _ in range(num_digits - 1))
            self.current_number = str(first_digit) + other_digits
        else:
            self.current_number = str(random.randint(0, 9))
        
        return self.current_number
    
    def update_difficulty(self):
        """Update difficulty based on score"""
        if self.score >= 50:
            self.difficulty = "expert"
        elif self.score >= 25:
            self.difficulty = "hard"
        elif self.score >= 10:
            self.difficulty = "medium"
        else:
            self.difficulty = "easy"

def get_game_state():
    if 'game_state' not in session:
        session['game_state'] = GameState().__dict__
    
    game_dict = session['game_state']
    game_state = GameState()
    game_state.__dict__.update(game_dict)
    
    # Convert string back to datetime
    if isinstance(game_state.start_time, str):
        game_state.start_time = datetime.fromisoformat(game_state.start_time)
    
    return game_state

def save_game_state(game_state):
    # Convert datetime to string for session storage
    game_state_dict = game_state.__dict__.copy()
    game_state_dict['start_time'] = game_state.start_time.isoformat()
    session['game_state'] = game_state_dict
    session.modified = True

def save_game_session(game_state):
    """Save completed game session to database"""
    if current_user.is_authenticated:
        duration = (datetime.now() - game_state.start_time).total_seconds()
        
        game_session = GameSession(
            user_id=current_user.id,
            final_score=game_state.score,
            questions_answered=game_state.questions_answered,
            correct_answers=game_state.correct_answers,
            max_difficulty=game_state.difficulty,
            duration=int(duration)
        )
        
        db.session.add(game_session)
        db.session.commit()

def admin_required(func):
    """Decorator to require admin privileges"""
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('play'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

# Authentication Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('play'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('play'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('play'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('play'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match', 'error')
        elif User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
        elif User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            
            # First user becomes admin
            if User.query.count() == 0:
                user.is_admin = True
            
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# Game Routes
@app.route('/play')
@login_required
def play():
    game_state = get_game_state()
    
    if game_state.current_number is None:
        game_state.generate_new_number()
        game_state.current_image = image_gen.generate_image(
            number=game_state.current_number,
            difficulty=game_state.difficulty
        )
        save_game_state(game_state)
    
    if random.random() < 0.1:
        image_gen.cleanup_old_images()
    
    # Ensure the referenced image file exists and regenerate if missing (handles stale sessions)
    ensure_image_for_state(game_state)
    save_game_state(game_state)

    return render_template('play.html', 
                         image_url=url_for('static', filename=f"images/generated/{game_state.current_image}"),
                         score=game_state.score,
                         lives=game_state.lives,
                         difficulty=game_state.difficulty.capitalize(),
                         questions_answered=game_state.questions_answered)

@app.route('/check_answer', methods=['POST'])
@login_required
def check_answer():
    game_state = get_game_state()
    user_guess = request.form.get('guess', '').strip()
    correct_answer = game_state.current_number
    
    is_correct = user_guess == correct_answer
    
    if is_correct:
        points = {'easy': 1, 'medium': 2, 'hard': 3, 'expert': 5}
        game_state.score += points[game_state.difficulty]
        game_state.questions_answered += 1
        game_state.correct_answers += 1
        message = f"Correct! +{points[game_state.difficulty]} points"
    else:
        game_state.lives -= 1
        game_state.questions_answered += 1
        message = f"Wrong! The number was {correct_answer}"
    
    old_difficulty = game_state.difficulty
    game_state.update_difficulty()
    
    game_state.generate_new_number()
    game_state.current_image = image_gen.generate_image(
        number=game_state.current_number,
        difficulty=game_state.difficulty
    )
    
    save_game_state(game_state)
    # Ensure file exists (regen if something went wrong while storing session values)
    ensure_image_for_state(game_state)
    save_game_state(game_state)
    
    if game_state.lives <= 0:
        save_game_session(game_state)
        return redirect(url_for('game_over'))
    
    return render_template('play.html',
                         image_url=url_for('static', filename=f"images/generated/{game_state.current_image}"),
                         score=game_state.score,
                         lives=game_state.lives,
                         difficulty=game_state.difficulty.capitalize(),
                         questions_answered=game_state.questions_answered,
                         message=message,
                         was_correct=is_correct)

@app.route('/game_over')
@login_required
def game_over():
    game_state = get_game_state()
    final_score = game_state.score
    
    save_game_session(game_state)
    game_state.reset()
    save_game_state(game_state)
    
    return render_template('game_over.html', final_score=final_score)

@app.route('/restart')
@login_required
def restart():
    game_state = get_game_state()
    game_state.reset()
    save_game_state(game_state)
    return redirect(url_for('play'))

# User Profile Routes
@app.route('/profile')
@login_required
def profile():
    stats = current_user.get_stats()
    recent_games = GameSession.query.filter_by(user_id=current_user.id)\
                                   .order_by(GameSession.created_at.desc())\
                                   .limit(10).all()
    return render_template('user/profile.html', stats=stats, recent_games=recent_games)

# Admin Routes (Keep them in app.py for now)
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    # Admin statistics
    total_users = User.query.count()
    total_games = GameSession.query.count()
    total_score = db.session.query(db.func.sum(GameSession.final_score)).scalar() or 0
    avg_score = db.session.query(db.func.avg(GameSession.final_score)).scalar() or 0
    
    # Recent activity
    recent_games = GameSession.query.join(User)\
                                   .order_by(GameSession.created_at.desc())\
                                   .limit(10).all()
    
    # Daily stats
    today = datetime.utcnow().date()
    daily_games = GameSession.query.filter(
        db.func.date(GameSession.created_at) == today
    ).count()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_games=total_games,
                         total_score=total_score,
                         avg_score=round(avg_score, 2),
                         daily_games=daily_games,
                         recent_games=recent_games)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    """User management"""
    users = User.query.all()
    users_with_stats = []
    
    for user in users:
        stats = user.get_stats()
        users_with_stats.append({
            'user': user,
            'stats': stats
        })
    
    return render_template('admin/users.html', users=users_with_stats)

@app.route('/admin/game-stats')
@login_required
@admin_required
def admin_game_stats():
    """Game statistics"""
    # Overall statistics
    total_sessions = GameSession.query.count()
    total_questions = db.session.query(db.func.sum(GameSession.questions_answered)).scalar() or 0
    total_correct = db.session.query(db.func.sum(GameSession.correct_answers)).scalar() or 0
    overall_accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0
    
    # Difficulty distribution
    difficulty_stats = db.session.query(
        GameSession.max_difficulty,
        db.func.count(GameSession.id),
        db.func.avg(GameSession.final_score)
    ).group_by(GameSession.max_difficulty).all()
    
    # Recent sessions with user info
    recent_sessions = GameSession.query.join(User)\
                                      .order_by(GameSession.created_at.desc())\
                                      .limit(20).all()
    
    return render_template('admin/game_stats.html',
                         total_sessions=total_sessions,
                         total_questions=total_questions,
                         total_correct=total_correct,
                         overall_accuracy=round(overall_accuracy, 2),
                         difficulty_stats=difficulty_stats,
                         recent_sessions=recent_sessions)

# API Routes
@app.route('/api/game_data')
@login_required
def api_game_data():
    game_state = get_game_state()
    return jsonify({
        'score': game_state.score,
        'lives': game_state.lives,
        'difficulty': game_state.difficulty,
        'questions_answered': game_state.questions_answered
    })

@app.route('/api/user_stats')
@login_required
def api_user_stats():
    stats = current_user.get_stats()
    return jsonify(stats)

# Initialize database
def init_db():
    with app.app_context():
        db.create_all()
        
        # Create admin user if none exists
        if not User.query.filter_by(is_admin=True).first():
            admin = User(
                username='admin',
                email='admin@mysterydigits.com',
                is_admin=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Admin user created: username='admin', password='admin123'")

if __name__ == '__main__':
    # Ensure directories exist
    os.makedirs('static/images/generated', exist_ok=True)
    os.makedirs('templates/admin', exist_ok=True)
    os.makedirs('templates/user', exist_ok=True)
    
    # Initialize database
    init_db()
    
    app.run(debug=True, host='0.0.0.0', port=5000)