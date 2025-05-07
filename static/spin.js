function rouletteGame() {
    return {
        deposit: 1000.00,
        demo: true,
        betAmount: 1,
        betType: null,
        betValue: null,
        winAmount: 0,
        tickets: [],
        gameCount: 146,
        gameStarted: false,
        gameEnded: false,
        currentResult: null,
        lastResult: '',
        previousGames: [9, 0, 34, 6, 14, 9],
        frequency: [
            { number: 1, count: 2 }, { number: 2, count: 13 }, { number: 3, count: 14 },
            { number: 4, count: 3 }, { number: 5, count: 15 }, { number: 6, count: 8 }
        ],
        colorStats: { red: 90, black: 104, green: 6 },
        dozenStats: { '1-12': 63, '13-24': 65, '25-36': 66 },
        hotNumbers: [34, 9, 6, 35, 33],
        coldNumbers: [10, 2, 29, 7, 1],
        timer: '00:15',
        selectionTimeLeft: 15,
        gameTimeLeft: 10, // Reduced spin time for faster cycles
        showRules: false,

        init() {
            this.resetGame(); // Initial reset to start in selection mode
        },

        updateTimer() {
            if (!this.gameStarted) {
                if (this.selectionTimeLeft > 0) {
                    this.selectionTimeLeft--;
                    this.timer = this.formatTime(this.selectionTimeLeft);
                    if (this.selectionTimeLeft === 0) {
                        this.startGame();
                    }
                }
            } else if (this.gameStarted && !this.gameEnded) {
                if (this.gameTimeLeft > 0) {
                    this.gameTimeLeft--;
                    this.timer = this.formatTime(this.gameTimeLeft);
                    if (this.gameTimeLeft === 0) {
                        this.endGame();
                    }
                }
            }
        },

        formatTime(totalSeconds) {
            const seconds = Math.floor(totalSeconds % 60);
            return `00:${seconds.toString().padStart(2, '0')}`;
        },

        getSegmentColor(number) {
            if (number === 0) return '#16a34a'; // Green for 0
            const redNumbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36];
            return redNumbers.includes(number) ? '#ef4444' : '#000000';
        },

        getColorClass(number) {
            if (number === 0) return 'bg-green-600 text-white';
            const redNumbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36];
            return redNumbers.includes(number) ? 'bg-red-500 text-white' : 'bg-black text-white';
        },

        getNumberClass(number) {
            if (number === 0) return 'green';
            const redNumbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36];
            return redNumbers.includes(number) ? 'red' : 'black';
        },

        setBet(type, value) {
            this.betType = type;
            this.betValue = value;
        },

        addTicket() {
            if (this.selectionTimeLeft <= 0 || !this.betType) return;
            this.tickets.push({
                betAmount: this.betAmount,
                betType: this.betType,
                betValue: this.betValue,
                actualWin: 0,
                isWinner: false
            });
            this.betType = null;
            this.betValue = null;
        },

        removeTicket(index) {
            this.tickets.splice(index, 1);
        },

        async startGame() {
            if (this.selectionTimeLeft > 0) return; // Ensure timer has reached 0

            this.gameStarted = true;
            this.gameEnded = false;
            this.gameTimeLeft = 10;
            this.currentResult = null;
            this.lastResult = '';
            this.timer = this.formatTime(this.gameTimeLeft);

            // 10 seconds for spinning
            this.$refs.wheel.style.animation = 'spin 10s ease-out forwards';
            await new Promise(resolve => setTimeout(resolve, 10000));
            this.$refs.wheel.style.animation = ''; // Stop animation

            // Random result (0-36)
            const result = Math.floor(Math.random() * 37);
            this.currentResult = result;
            this.lastResult = result;

            // Update game statistics
            this.gameCount++;
            this.previousGames.unshift(result);
            if (this.previousGames.length > 6) this.previousGames.pop();

            // Calculate win based on tickets
            this.winAmount = 0;
            this.tickets.forEach(ticket => {
                let win = 0;
                // ... (WIN CALCULATION LOGIC AS BEFORE) ...
                if (ticket.betType === 'color') {
                    const resultColor = result === 0 ? 'green' : this.getSegmentColor(result) === '#ef4444' ? 'red' : 'black';
                    if (resultColor === ticket.betValue) {
                        win = ticket.betAmount * (resultColor === 'green' ? 36 : 2);
                        ticket.isWinner = true;
                    }
                } else if (ticket.betType === 'number') {
                    if (parseInt(ticket.betValue) === result) {
                        win = ticket.betAmount * 36;
                        ticket.isWinner = true;
                    }
                } else if (ticket.betType === 'dozen') {
                    const dozen = result === 0 ? null : result <= 12 ? '1-12' : result <= 24 ? '13-24' : '25-36';
                    if (dozen === ticket.betValue) {
                        win = ticket.betAmount * 3;
                        ticket.isWinner = true;
                    }
                } else if (ticket.betType === 'oddEven') {
                    const isOdd = result % 2 !== 0;
                    if ((ticket.betValue === 'odd' && isOdd) || (ticket.betValue === 'even' && !isOdd && result !== 0)) {
                        win = ticket.betAmount * 2;
                        ticket.isWinner = true;
                    }
                } else if (ticket.betType === 'highLow') {
                    const isHigh = result >= 19 && result <= 36;
                    if ((ticket.betValue === 'high' && isHigh) || (ticket.betValue === 'low' && !isHigh && result !== 0)) {
                        win = ticket.betAmount * 2;
                        ticket.isWinner = true;
                    }
                } else if (ticket.betType === 'extra') {
                    if (ticket.betValue === '1-18-red') {
                        const isLow = result >= 1 && result <= 18;
                        const isRed = this.getSegmentColor(result) === '#ef4444';
                        if (isLow && isRed) {
                            win = ticket.betAmount * 3;
                            ticket.isWinner = true;
                        }
                    } else if (ticket.betValue === '19-36-red') {
                        const isHigh = result >= 19 && result <= 36;
                        const isRed = this.getSegmentColor(result) === '#ef4444';
                        if (isHigh && isRed) {
                            win = ticket.betAmount * 3;
                            ticket.isWinner = true;
                        }
                    } else if (ticket.betValue === '1-18-black') {
                        const isLow = result >= 1 && result <= 18;
                        const isBlack = this.getSegmentColor(result) === '#000000';
                        if (isLow && isBlack) {
                            win = ticket.betAmount * 3;
                            ticket.isWinner = true;
                        }
                    } else if (ticket.betValue === '19-36-black') {
                        const isHigh = result >= 19 && result <= 36;
                        const isBlack = this.getSegmentColor(result) === '#000000';
                        if (isHigh && isBlack) {
                            win = ticket.betAmount * 3;
                            ticket.isWinner = true;
                        }
                    } else if (ticket.betValue === '12-21') {
                        if (result === 12 || result === 21) {
                            win = ticket.betAmount * 18;
                            ticket.isWinner = true;
                        }
                    } else if (ticket.betValue === '13-31') {
                        if (result === 13 || result === 31) {
                            win = ticket.betAmount * 18;
                            ticket.isWinner = true;
                        }
                    } else if (ticket.betValue === '23-32') {
                        if (result === 23 || result === 32) {
                            win = ticket.betAmount * 18;
                            ticket.isWinner = true;
                        }
                    } else if (ticket.betValue === '11-22-33') {
                        if (result === 11 || result === 22 || result === 33) {
                            win = ticket.betAmount * 12;
                            ticket.isWinner = true;
                        }
                    }
                }
                ticket.actualWin = win.toFixed(2);
                this.winAmount += win;
            });

            if (!this.demo) {
                this.tickets.forEach(ticket => {
                    this.deposit -= ticket.betAmount;
                    if (ticket.isWinner) {
                        this.deposit += parseFloat(ticket.actualWin);
                    }
                });
            }

            if (this.winAmount > 0) {
                this.triggerConfetti();
            }

            this.gameEnded = true;
            this.timerInterval = setInterval(() => this.updateTimer(), 1000); // Restart timer for end phase
            setTimeout(() => this.resetGame(), 5000); // Short delay before resetting
        },

        endGame() {
            clearInterval(this.timerInterval);
            this.timerInterval = setInterval(() => this.updateTimer(), 1000); // Restart timer for end phase
            setTimeout(() => this.resetGame(), 5000); // Short delay before resetting
        },

        triggerConfetti() {
            for (let i = 0; i < 50; i++) {
                let confetti = document.createElement('div');
                confetti.className = 'confetti';
                confetti.style.left = Math.random() * 100 + 'vw';
                confetti.style.background = ['#facc15', '#3b82f6', '#ef4444', '#10b981'][Math.floor(Math.random() * 4)];
                document.body.appendChild(confetti);
                setTimeout(() => confetti.remove(), 2000);
            }
        },

        resetGame() {
            clearInterval(this.timerInterval);
            this.gameStarted = false;
            this.gameEnded = false;
            this.currentResult = null;
            this.lastResult = '';
            this.winAmount = 0;
            this.tickets = [];
            this.$refs.wheel.style.transform = 'rotate(0deg)';
            this.selectionTimeLeft = 15;
            this.gameTimeLeft = 10;
            this.timer = this.formatTime(this.selectionTimeLeft);
            this.timerInterval = setInterval(() => this.updateTimer(), 1000);
        }
    };
}