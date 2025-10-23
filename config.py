"""
Configuration settings for Mystery Digits
"""
import os
from datetime import timedelta

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    
    # Database configuration
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATABASE_PATH = os.path.join(BASE_DIR, 'mystery_digits.db')
    # SQLAlchemy database URI. Prefer environment-provided DATABASE_URL, then MYSQL_URI,
    # then individual MYSQL_* vars; fall back to a local SQLite file for development.
    # Build DB URI only when explicitly requested or when environment provides it.
    # Use environment variables if present; otherwise default to SQLite for local dev.
    _env_db = os.environ.get('DATABASE_URL') or os.environ.get('MYSQL_URI')

    if not _env_db:
        # If explicit individual MYSQL_* vars are present, build a URI (PyMySQL driver)
        if os.environ.get('MYSQL_USER') and os.environ.get('MYSQL_PASSWORD') and os.environ.get('MYSQL_HOST') and os.environ.get('MYSQL_PORT') and os.environ.get('MYSQL_DB'):
            _env_db = (
                f"mysql+pymysql://{os.environ.get('MYSQL_USER')}:{os.environ.get('MYSQL_PASSWORD')}@"
                f"{os.environ.get('MYSQL_HOST')}:{os.environ.get('MYSQL_PORT')}/{os.environ.get('MYSQL_DB')}"
            )

    # If USE_MYSQL env var is set to a truthy value, allow fallback to the provided MySQL URI.
    # This prevents the app from trying to contact the remote MySQL by default during local dev.
    USE_MYSQL = os.environ.get('USE_MYSQL', '').lower() in ('1', 'true', 'yes')

    if not _env_db and USE_MYSQL:
        # Only use the hardcoded remote MySQL URI if explicitly opted-in via USE_MYSQL
        _env_db = "mysql+pymysql://avnadmin:AVNS_Mw0V9t_g2KU5YDz6A_j@mysql-36242816-albinosiby1-4d7c.i.aivencloud.com:14436/defaultdb"

    SQLALCHEMY_DATABASE_URI = _env_db or f"sqlite:///{DATABASE_PATH}"
    
    # Game configuration
    DIFFICULTY_LEVELS = {
        'easy': {
            'min_digits': 1,
            'max_digits': 3,
            'time_limit': 60,
            'hints_allowed': 3,
            'points_multiplier': 1
        },
        'medium': {
            'min_digits': 2,
            'max_digits': 4,
            'time_limit': 45,
            'hints_allowed': 2,
            'points_multiplier': 2
        },
        'hard': {
            'min_digits': 3,
            'max_digits': 5,
            'time_limit': 30,
            'hints_allowed': 1,
            'points_multiplier': 3
        },
        'expert': {
            'min_digits': 4,
            'max_digits': 6,
            'time_limit': 20,
            'hints_allowed': 0,
            'points_multiplier': 4
        }
    }
    
    # Dynamic mode configuration
    DYNAMIC_MODE = {
        'initial_level': 1,
        'level_up_threshold': 3,  # Consecutive correct answers to level up
        'level_down_threshold': 2,  # Consecutive wrong answers to level down
        'max_level': 100,
        'base_points': 100,  # Base points for each correct answer
        'streak_multiplier': 0.1,  # Additional multiplier per streak
        'time_bonus_threshold': 10,  # Seconds under time limit for bonus
        'time_bonus_points': 50  # Points awarded for beating time threshold
    }
    
    # Achievement configuration
    ACHIEVEMENT_CONFIG = {
        'streak_thresholds': [5, 10, 20, 50],
        'accuracy_thresholds': [70, 80, 90, 95, 100],
        'speed_thresholds': [60, 45, 30, 20, 10],
        'games_thresholds': [1, 10, 50, 100, 500],
        'level_thresholds': [10, 25, 50, 75, 100]
    }
    
    # Image generation settings
    IMAGE_CONFIG = {
        'width': 400,
        'height': 200,
        'font_size': 60,
        'font_path': os.path.join(BASE_DIR, 'static', 'fonts', 'digital.ttf'),
        'bg_color': (255, 255, 255),
        'text_color': (0, 0, 0),
        'noise_density': 0.1,
        'line_count': 5
    }
    
    # Cache configuration
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Admin configuration
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'change-me-in-production'
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_TYPE = 'filesystem'
    
    # Development configuration
    DEBUG = os.environ.get('FLASK_ENV') == 'development'