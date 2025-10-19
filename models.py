from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationship with game sessions
    game_sessions = db.relationship('GameSession', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_stats(self):
        """Get user game statistics"""
        sessions = GameSession.query.filter_by(user_id=self.id).all()
        total_score = sum(session.final_score for session in sessions)
        total_games = len(sessions)
        avg_score = total_score / total_games if total_games > 0 else 0
        
        return {
            'total_games': total_games,
            'total_score': total_score,
            'avg_score': round(avg_score, 2),
            'last_played': sessions[-1].created_at if sessions else None
        }

class GameSession(db.Model):
    __tablename__ = 'game_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    final_score = db.Column(db.Integer, default=0)
    questions_answered = db.Column(db.Integer, default=0)
    correct_answers = db.Column(db.Integer, default=0)
    max_difficulty = db.Column(db.String(20), default='easy')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    duration = db.Column(db.Integer, default=0)  # in seconds
    
    def accuracy(self):
        return round((self.correct_answers / self.questions_answered) * 100, 2) if self.questions_answered > 0 else 0