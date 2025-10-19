/**
 * Mystery Digits Game Logic
 */

class GameManager {
    constructor() {
        this.gameState = {
            currentLevel: 1,
            score: 0,
            streak: 0,
            bestStreak: 0,
            hintsUsed: 0,
            startTime: null,
            timeElapsed: 0,
            totalAttempts: 0,
            correctAttempts: 0
        };
        
        this.config = {
            updateInterval: 1000, // Timer update interval in ms
            hintPenalty: 10, // Score penalty for using a hint
            streakBonus: 5, // Bonus points for maintaining a streak
            timeBonusThreshold: 10 // Seconds under par for time bonus
        };
        
        this.timer = null;
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Guess submission
        document.getElementById('guessForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitGuess();
        });
        
        // Hint button
        document.getElementById('hintButton')?.addEventListener('click', () => {
            this.useHint();
        });
        
        // New game button
        document.getElementById('newGameButton')?.addEventListener('click', () => {
            this.startNewGame();
        });
        
        // Difficulty selection
        document.querySelectorAll('.difficulty-select')?.forEach(button => {
            button.addEventListener('click', () => {
                this.setDifficulty(button.dataset.difficulty);
            });
        });
    }
    
    startNewGame() {
        this.gameState.startTime = new Date();
        this.updateTimer();
        this.timer = setInterval(() => this.updateTimer(), this.config.updateInterval);
        
        fetch('/api/new-game', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                difficulty: document.querySelector('[name="difficulty"]').value
            })
        })
        .then(response => response.json())
        .then(data => {
            this.updateGameUI(data);
        })
        .catch(error => {
            console.error('Error starting new game:', error);
            showNotification('Error starting new game', 'error');
        });
    }
    
    submitGuess() {
        const guessInput = document.getElementById('guessInput');
        const guess = guessInput.value.trim();
        
        if (!guess) return;
        
        this.gameState.totalAttempts++;
        
        fetch('/api/check-guess', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ guess })
        })
        .then(response => response.json())
        .then(data => {
            if (data.correct) {
                this.handleCorrectGuess(data);
            } else {
                this.handleIncorrectGuess(data);
            }
            this.updateGameUI(data);
            guessInput.value = '';
        })
        .catch(error => {
            console.error('Error submitting guess:', error);
            showNotification('Error submitting guess', 'error');
        });
    }
    
    handleCorrectGuess(data) {
        this.gameState.correctAttempts++;
        this.gameState.streak++;
        this.gameState.bestStreak = Math.max(this.gameState.streak, this.gameState.bestStreak);
        
        // Calculate time bonus
        const timeBonus = this.calculateTimeBonus();
        
        // Calculate streak bonus
        const streakBonus = this.gameState.streak * this.config.streakBonus;
        
        // Update total score
        this.gameState.score += data.basePoints + timeBonus + streakBonus;
        
        showNotification(`Correct! +${data.basePoints} points`, 'success');
        
        if (timeBonus > 0) {
            showNotification(`Time Bonus: +${timeBonus} points`, 'info');
        }
        if (streakBonus > 0) {
            showNotification(`Streak Bonus: +${streakBonus} points`, 'info');
        }
        
        // Check for achievements
        if (data.achievements?.length) {
            data.achievements.forEach(achievement => {
                showAchievement(achievement);
            });
        }
    }
    
    handleIncorrectGuess(data) {
        this.gameState.streak = 0;
        showNotification('Try again!', 'warning');
    }
    
    useHint() {
        if (this.gameState.hintsUsed >= 3) {
            showNotification('No more hints available', 'warning');
            return;
        }
        
        fetch('/api/get-hint', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(response => response.json())
        .then(data => {
            this.gameState.hintsUsed++;
            this.gameState.score = Math.max(0, this.gameState.score - this.config.hintPenalty);
            
            showNotification(`Hint: ${data.hint}`, 'info');
            showNotification(`-${this.config.hintPenalty} points for using a hint`, 'warning');
            
            this.updateGameUI(data);
        })
        .catch(error => {
            console.error('Error getting hint:', error);
            showNotification('Error getting hint', 'error');
        });
    }
    
    calculateTimeBonus() {
        const parTime = this.getParTimeForLevel();
        const timeTaken = (new Date() - this.gameState.startTime) / 1000;
        
        if (timeTaken < parTime - this.config.timeBonusThreshold) {
            return Math.floor((parTime - timeTaken) * 2);
        }
        return 0;
    }
    
    getParTimeForLevel() {
        // Par time decreases as level increases
        return Math.max(10, 30 - (this.gameState.currentLevel - 1) * 2);
    }
    
    updateTimer() {
        if (!this.gameState.startTime) return;
        
        const now = new Date();
        this.gameState.timeElapsed = Math.floor((now - this.gameState.startTime) / 1000);
        
        const timerDisplay = document.getElementById('timerDisplay');
        if (timerDisplay) {
            timerDisplay.textContent = this.formatTime(this.gameState.timeElapsed);
        }
    }
    
    formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
    
    updateGameUI(data) {
        // Update score display
        const scoreDisplay = document.getElementById('scoreDisplay');
        if (scoreDisplay) {
            scoreDisplay.textContent = this.gameState.score;
        }
        
        // Update streak display
        const streakDisplay = document.getElementById('streakDisplay');
        if (streakDisplay) {
            streakDisplay.textContent = this.gameState.streak;
            streakDisplay.className = this.gameState.streak > 0 ? 
                'badge bg-success' : 'badge bg-secondary';
        }
        
        // Update hints remaining
        const hintsDisplay = document.getElementById('hintsDisplay');
        if (hintsDisplay) {
            const hintsRemaining = 3 - this.gameState.hintsUsed;
            hintsDisplay.textContent = `${hintsRemaining} hint${hintsRemaining !== 1 ? 's' : ''} remaining`;
        }
        
        // Update game image if provided
        if (data.imageUrl) {
            const gameImage = document.getElementById('gameImage');
            if (gameImage) {
                gameImage.src = data.imageUrl;
            }
        }
        
        // Update level display
        const levelDisplay = document.getElementById('levelDisplay');
        if (levelDisplay) {
            levelDisplay.textContent = `Level ${this.gameState.currentLevel}`;
        }
        
        // Update accuracy
        const accuracyDisplay = document.getElementById('accuracyDisplay');
        if (accuracyDisplay) {
            const accuracy = this.gameState.totalAttempts > 0 ?
                Math.round((this.gameState.correctAttempts / this.gameState.totalAttempts) * 100) : 0;
            accuracyDisplay.textContent = `${accuracy}%`;
        }
    }
    
    setDifficulty(difficulty) {
        document.querySelectorAll('.difficulty-select').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-difficulty="${difficulty}"]`)?.classList.add('active');
        document.querySelector('[name="difficulty"]').value = difficulty;
    }
}

// Initialize game when document is ready
document.addEventListener('DOMContentLoaded', () => {
    window.gameManager = new GameManager();
});