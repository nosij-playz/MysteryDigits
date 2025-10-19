import os
import sqlite3
from datetime import datetime
from config import Config

class GameManager:
    def __init__(self):
        self.db_path = Config.DATABASE_PATH
        self.init_database()
        self._apply_migrations()

    def _apply_migrations(self):
        """Apply any pending database migrations"""
        from migrations import run_migrations
        run_migrations()

    def init_database(self):
        """Initialize the database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Game sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                score INTEGER NOT NULL,
                level_reached INTEGER NOT NULL,
                dynamic_level INTEGER,
                total_correct INTEGER NOT NULL,
                total_attempts INTEGER NOT NULL,
                accuracy REAL NOT NULL,
                hints_used INTEGER NOT NULL,
                current_streak INTEGER NOT NULL DEFAULT 0,
                best_streak INTEGER NOT NULL DEFAULT 0,
                achievement_points INTEGER NOT NULL DEFAULT 0,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                duration_seconds INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Player stats table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_stats (
                player_name TEXT PRIMARY KEY,
                total_games INTEGER DEFAULT 0,
                total_score INTEGER DEFAULT 0,
                best_score INTEGER DEFAULT 0,
                best_level INTEGER DEFAULT 0,
                total_correct INTEGER DEFAULT 0,
                total_attempts INTEGER DEFAULT 0,
                total_hints_used INTEGER DEFAULT 0,
                total_play_time INTEGER DEFAULT 0,
                current_streak INTEGER DEFAULT 0,
                best_streak INTEGER DEFAULT 0,
                achievement_points INTEGER DEFAULT 0,
                avg_time_per_game INTEGER DEFAULT 0,
                first_played TIMESTAMP,
                last_played TIMESTAMP
            )
        ''')

        # Difficulty settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS difficulty_settings (
                difficulty TEXT PRIMARY KEY,
                max_digits INTEGER NOT NULL,
                distortion REAL NOT NULL,
                base_lives INTEGER NOT NULL,
                base_hints INTEGER NOT NULL,
                point_multiplier REAL NOT NULL
            )
        ''')

        # Default difficulties
        default_difficulties = [
            ('easy', 4, 0.2, 3, 3, 1.0),
            ('medium', 5, 0.4, 2, 2, 1.5),
            ('hard', 6, 0.6, 1, 1, 2.0),
            ('dynamic', 3, 0.1, 3, 5, 1.2)
        ]

        cursor.executemany('''
            INSERT OR REPLACE INTO difficulty_settings 
            (difficulty, max_digits, distortion, base_lives, base_hints, point_multiplier)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', default_difficulties)

        conn.commit()
        conn.close()

    # ------------------ Difficulty Config ------------------

    def get_difficulty_config(self, difficulty):
        """Get difficulty settings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT max_digits, distortion, base_lives, base_hints, point_multiplier
                FROM difficulty_settings 
                WHERE difficulty = ?
            ''', (difficulty,))
            result = cursor.fetchone()
            if result:
                return {
                    'max_digits': result[0],
                    'distortion': result[1],
                    'base_lives': result[2],
                    'base_hints': result[3],
                    'point_multiplier': result[4]
                }
            # Default fallback
            return {
                'max_digits': 4,
                'distortion': 0.3,
                'base_lives': 3,
                'base_hints': 3,
                'point_multiplier': 1.0
            }
        finally:
            conn.close()

    def get_lives(self, difficulty):
        config = self.get_difficulty_config(difficulty)
        return config['base_lives']

    def get_max_hints(self, difficulty):
        config = self.get_difficulty_config(difficulty)
        return config['base_hints']

    # ------------------ Game Scoring ------------------

    def calculate_score(self, difficulty, correct, time_taken, streak, hints_used, level):
        """Calculate score with bonuses and penalties"""
        if not correct:
            return 0, {}

        config = self.get_difficulty_config(difficulty)
        base_multiplier = config['point_multiplier']

        base_score = 100 * base_multiplier
        bonuses = {}

        # Time bonus
        par_time = 30 - (level * 0.5)
        if time_taken < par_time:
            time_bonus = int((par_time - time_taken) * 10)
            bonuses['time'] = time_bonus
            base_score += time_bonus

        # Streak bonus
        if streak > 1:
            streak_bonus = int(25 * (1 + (streak * 0.1)))
            bonuses['streak'] = streak_bonus
            base_score += streak_bonus

        # Level bonus for dynamic mode
        if difficulty == 'dynamic' and level > 1:
            level_bonus = level * 50
            bonuses['level'] = level_bonus
            base_score += level_bonus

        # Hint penalty
        if hints_used > 0:
            hint_penalty = hints_used * 50
            bonuses['hints'] = -hint_penalty
            base_score = max(0, base_score - hint_penalty)

        # Perfect speed bonus
        if time_taken < 5:
            speed_bonus = 200
            bonuses['speed'] = speed_bonus
            base_score += speed_bonus

        return int(base_score), bonuses

    # ------------------ Game Session ------------------

    def save_game_session(self, game_stats):
        """Save a completed game session and update player stats"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            duration = int((game_stats['end_time'] - game_stats['start_time']).total_seconds())

            # Save game session
            cursor.execute('''
                INSERT INTO game_sessions 
                (player_name, difficulty, score, level_reached, total_correct,
                 total_attempts, accuracy, hints_used, current_streak, best_streak,
                 achievement_points, start_time, end_time, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                game_stats['player_name'], game_stats['difficulty'],
                game_stats['score'], game_stats['level'],
                game_stats['total_correct'], game_stats['total_attempts'],
                game_stats['accuracy'], game_stats['hints_used'],
                game_stats['current_streak'], game_stats['best_streak'],
                game_stats['achievement_points'],
                game_stats['start_time'], game_stats['end_time'],
                duration
            ))

            # Update player stats
            cursor.execute('''
                INSERT INTO player_stats 
                (player_name, total_games, total_score, best_score,
                 best_level, total_correct, total_attempts,
                 total_hints_used, total_play_time, current_streak,
                 best_streak, achievement_points, avg_time_per_game,
                 first_played, last_played)
                VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(player_name) DO UPDATE SET
                    total_games = total_games + 1,
                    total_score = total_score + ?,
                    best_score = CASE WHEN ? > best_score THEN ? ELSE best_score END,
                    best_level = CASE WHEN ? > best_level THEN ? ELSE best_level END,
                    total_correct = total_correct + ?,
                    total_attempts = total_attempts + ?,
                    total_hints_used = total_hints_used + ?,
                    total_play_time = total_play_time + ?,
                    current_streak = ?,
                    best_streak = CASE WHEN ? > best_streak THEN ? ELSE best_streak END,
                    achievement_points = achievement_points + ?,
                    avg_time_per_game = (avg_time_per_game * total_games + ?) / (total_games + 1),
                    last_played = CURRENT_TIMESTAMP
            ''', (
                game_stats['player_name'], game_stats['score'], game_stats['score'],
                game_stats['level'], game_stats['total_correct'],
                game_stats['total_attempts'], game_stats['hints_used'],
                duration, game_stats['current_streak'],
                game_stats['best_streak'], game_stats['achievement_points'],
                duration,
                # For UPDATE
                game_stats['score'],
                game_stats['score'], game_stats['score'],
                game_stats['level'], game_stats['level'],
                game_stats['total_correct'], game_stats['total_attempts'],
                game_stats['hints_used'], duration,
                game_stats['current_streak'],
                game_stats['best_streak'], game_stats['best_streak'],
                game_stats['achievement_points'], duration
            ))

            # Check achievements
            new_achievements = self.check_achievements(game_stats['player_name'], game_stats)
            conn.commit()
            return True, new_achievements

        except Exception as e:
            print(f"Error saving game session: {e}")
            conn.rollback()
            return False, []
        finally:
            conn.close()

    # ------------------ Achievements ------------------

    def check_achievements(self, player_name, game_stats):
        """Check and unlock achievements"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        new_achievements = []

        try:
            # Fetch unearned achievements
            cursor.execute('''
                SELECT id, name, description, icon_name, condition_type, condition_value, points 
                FROM achievements
                WHERE id NOT IN (
                    SELECT achievement_id 
                    FROM player_achievements
                    WHERE player_name = ?
                )
            ''', (player_name,))

            for achievement in cursor.fetchall():
                achieved = False
                id, name, desc, icon, cond_type, cond_value, points = achievement

                # Conditions
                if cond_type == 'games_played' and game_stats.get('total_games', 0) >= cond_value:
                    achieved = True
                elif cond_type == 'perfect_accuracy' and game_stats['accuracy'] >= 100:
                    achieved = True
                elif cond_type == 'streak' and game_stats['streak'] >= cond_value:
                    achieved = True
                elif cond_type == 'speed' and game_stats['time'] <= cond_value:
                    achieved = True
                elif cond_type == 'play_time' and game_stats.get('total_play_time', 0) >= cond_value:
                    achieved = True
                elif cond_type == 'dynamic_level' and game_stats['level'] >= cond_value:
                    achieved = True
                elif cond_type == 'no_hints' and game_stats['hints_used'] == 0:
                    achieved = True
                elif cond_type == 'score' and game_stats['score'] >= cond_value:
                    achieved = True

                if achieved:
                    cursor.execute('''
                        INSERT INTO player_achievements (player_name, achievement_id, unlocked_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                    ''', (player_name, id))

                    cursor.execute('''
                        UPDATE player_stats 
                        SET achievement_points = achievement_points + ?
                        WHERE player_name = ?
                    ''', (points, player_name))

                    new_achievements.append({
                        'name': name,
                        'description': desc,
                        'icon': icon,
                        'points': points
                    })

            conn.commit()
            return new_achievements

        except Exception as e:
            print(f"Error checking achievements: {e}")
            conn.rollback()
            return []
        finally:
            conn.close()

    # ------------------ Player Stats ------------------

    def get_player_stats(self, player_name):
        """Fetch full stats for a player"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM player_stats WHERE player_name = ?', (player_name,))
            player_row = cursor.fetchone()
            if not player_row:
                return None

            # Recent games
            cursor.execute('''
                SELECT difficulty, score, level_reached, dynamic_level, accuracy, created_at
                FROM game_sessions
                WHERE player_name = ?
                ORDER BY created_at DESC
                LIMIT 20
            ''', (player_name,))

            recent_games = [{
                'difficulty': row[0],
                'score': row[1],
                'level': row[2],
                'dynamic_level': row[3],
                'accuracy': row[4],
                'played_at': row[5]
            } for row in cursor.fetchall()]

            stats = dict(zip([col[0] for col in cursor.description], player_row))
            stats['recent_games'] = recent_games
            return stats

        finally:
            conn.close()
