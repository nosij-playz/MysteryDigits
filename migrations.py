"""
Database migration system for Mystery Digits
"""
import sqlite3
from datetime import datetime
from config import Config


class Migration:
    def __init__(self, db_path=Config.DATABASE_PATH):
        self.db_path = db_path
        self.init_migration_table()

    # ---------------------------
    # Initialize migrations table
    # ---------------------------
    def init_migration_table(self):
        """Create migrations tracking table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    # ---------------------------
    # Helper checks
    # ---------------------------
    def has_migration(self, name):
        """Check if a migration has been applied"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM migrations WHERE name = ?', (name,))
        result = cursor.fetchone()

        conn.close()
        return result is not None

    def column_exists(self, table_name, column_name):
        """Check if a column exists in a given table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        return column_name in columns

    # ---------------------------
    # Apply individual migration
    # ---------------------------
    def apply_migration(self, name, sql_statements):
        """Apply a single migration safely"""
        if self.has_migration(name):
            print(f"Migration {name} already applied")
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            for statement in sql_statements:
                stmt = statement.strip()
                if not stmt:
                    continue

                # --- Safe skip for duplicate columns ---
                # Check for 'game_sessions' columns
                if "ALTER TABLE game_sessions ADD COLUMN achievement_points" in stmt:
                    if self.column_exists("game_sessions", "achievement_points"):
                        print("✅ Column 'achievement_points' already exists in game_sessions — skipping.")
                        continue

                # Check for 'player_stats' columns
                player_stats_columns = {
                    "achievement_points": "ALTER TABLE player_stats ADD COLUMN achievement_points",
                    "current_streak": "ALTER TABLE player_stats ADD COLUMN current_streak",
                    "best_streak": "ALTER TABLE player_stats ADD COLUMN best_streak",
                    "avg_time_per_game": "ALTER TABLE player_stats ADD COLUMN avg_time_per_game"
                }

                skip_this = False
                for col, pattern in player_stats_columns.items():
                    if pattern in stmt:
                        if self.column_exists("player_stats", col):
                            print(f"✅ Column '{col}' already exists in player_stats — skipping.")
                            skip_this = True
                        break

                if skip_this:
                    continue

                # Execute safe statement
                cursor.execute(stmt)

            # Record migration
            cursor.execute(
                'INSERT INTO migrations (name) VALUES (?)',
                (name,)
            )

            conn.commit()
            print(f"✅ Applied migration: {name}")
            return True

        except Exception as e:
            conn.rollback()
            print(f"❌ Error applying migration {name}: {str(e)}")
            raise

        finally:
            conn.close()

    # ---------------------------
    # Run all migrations
    # ---------------------------
    def run_migrations(self):
        """Run all pending migrations"""
        migrations = [
            ("01_add_achievements", [
                '''
                CREATE TABLE IF NOT EXISTS achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    icon_name TEXT NOT NULL,
                    condition_type TEXT NOT NULL,
                    condition_value INTEGER NOT NULL,
                    points INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS player_achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT NOT NULL,
                    achievement_id INTEGER NOT NULL,
                    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (achievement_id) REFERENCES achievements (id),
                    UNIQUE (player_name, achievement_id)
                )
                '''
            ]),

            ("02_enhance_game_sessions", [
                '''
                ALTER TABLE game_sessions ADD COLUMN achievement_points INTEGER NOT NULL DEFAULT 0;
                '''
            ]),

            ("03_enhance_player_stats", [
                '''
                ALTER TABLE player_stats ADD COLUMN achievement_points INTEGER NOT NULL DEFAULT 0;
                ''',
                '''
                ALTER TABLE player_stats ADD COLUMN current_streak INTEGER NOT NULL DEFAULT 0;
                ''',
                '''
                ALTER TABLE player_stats ADD COLUMN best_streak INTEGER NOT NULL DEFAULT 0;
                ''',
                '''
                ALTER TABLE player_stats ADD COLUMN avg_time_per_game INTEGER NOT NULL DEFAULT 0;
                '''
            ]),

            ("04_default_achievements", [
                '''
                INSERT OR IGNORE INTO achievements (name, description, icon_name, condition_type, condition_value, points)
                VALUES 
                    ('First Steps', 'Complete your first game', 'trophy', 'games_played', 1, 10),
                    ('Perfect Score', 'Achieve 100% accuracy in a game', 'star', 'perfect_accuracy', 1, 50),
                    ('Streak Master', 'Get a 10+ correct streak', 'fire', 'streak', 10, 30),
                    ('Speed Demon', 'Complete a level in under 30 seconds', 'bolt', 'speed', 30, 25),
                    ('Marathon Player', 'Play for over 1 hour total', 'clock', 'play_time', 3600, 40),
                    ('Expert Detective', 'Reach level 50 in dynamic mode', 'medal', 'dynamic_level', 50, 100),
                    ('Number Ninja', 'Complete 100 total games', 'ninja', 'total_games', 100, 75),
                    ('Hint Master', 'Win a game without using hints', 'lightbulb', 'no_hints', 1, 20),
                    ('Accuracy King', 'Maintain 90%+ accuracy for 5 games', 'crown', 'sustained_accuracy', 5, 60)
                '''
            ])
        ]

        for name, statements in migrations:
            try:
                self.apply_migration(name, statements)
            except Exception as e:
                print(f"❌ Migration failed: {name}")
                print(str(e))
                break


def run_migrations():
    """Run all database migrations"""
    migrator = Migration()
    migrator.run_migrations()


if __name__ == "__main__":
    run_migrations()
