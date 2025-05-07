function bingoGame() {
    return {
        TOTAL_CARTELLAS_LIMIT: 100,
        MINIMUM_CARTELLAS: 5,
        AUTO_START_DELAY: 20000, // 20 seconds
        COUNTDOWN_DURATION: 10,
        DRAW_INTERVAL: 2500, // 2.5 seconds
        ANIMATION_DURATION: 1000, // 1 second
        POPUP_DURATION: 2000,

        totalAmount: 1000.00,
        demo: true,
        betAmount: 5,
        cartellaAmount: 20,
        totalPrize: 0,
        totalCartellas: 0,
        patternSelected: true,
        patternType: 'single',
        selectedCartellaNumbers: [],
        takenCartellas: [],
        currentCartella: [],
        cartellas: [],
        calledNumbers: [],
        lastFiveCalls: [],
        gameStarted: false,
        gameStarting: false,
        countdown: 10,
        hasWinner: false,
        currentCalledNumber: null,
        currentCalledNumberLetter: '',
        previousNumber: null,
        previousNumberLetter: null,
        showWinnerPopup: false,
        winningCartella: null,
        roundStartTime: null,
        predefinedCartellas: [],

        init() {
            this.generatePredefinedCartellas();
            this.roundStartTime = Date.now();
            this.checkAutoStart();
            this.updatePrize();
        },

        generatePredefinedCartellas() {
            const ranges = [
                [1, 15],   // B
                [16, 30],  // I
                [31, 45],  // N
                [46, 60],  // G
                [61, 75]   // O
            ];
            this.predefinedCartellas = [];
            for (let i = 0; i < 100; i++) {
                let cartella = [];
                for (let col = 0; col < 5; col++) {
                    let colNumbers = [];
                    for (let row = 0; row < 5; row++) {
                        if (col === 2 && row === 2) {
                            colNumbers.push('*');
                        } else {
                            let num;
                            do {
                                num = Math.floor(Math.random() * (ranges[col][1] - ranges[col][0] + 1)) + ranges[col][0];
                            } while (colNumbers.includes(num));
                            colNumbers.push(num);
                        }
                    }
                    cartella.push(colNumbers);
                }
                // Transpose to row-major
                cartella = cartella[0].map((_, i) => cartella.map(col => col[i]));
                this.predefinedCartellas.push(cartella);
            }
        },

        updatePrize() {
            const total = this.totalCartellas * this.cartellaAmount;
            this.totalPrize = total * 0.95; // 5% system cut
        },

        checkAutoStart() {
            setTimeout(() => {
                if (!this.gameStarted && this.totalCartellas < this.MINIMUM_CARTELLAS) {
                    // Simulate other users selecting cartellas
                    while (this.totalCartellas < this.MINIMUM_CARTELLAS) {
                        const nextNum = this.totalCartellas + 1;
                        if (!this.takenCartellas.includes(nextNum) && !this.selectedCartellaNumbers.includes(nextNum)) {
                            this.takenCartellas.push(nextNum);
                            this.totalCartellas++;
                        }
                    }
                    this.updatePrize();
                    this.startCountdown();
                } else if (!this.gameStarted && this.totalCartellas >= this.MINIMUM_CARTELLAS) {
                    this.startCountdown();
                }
            }, this.AUTO_START_DELAY);
        },

        startCountdown() {
            if (this.gameStarted || this.gameStarting) return;
            this.gameStarting = true;
            this.countdown = this.COUNTDOWN_DURATION;
            const countdownInterval = setInterval(() => {
                this.countdown--;
                if (this.countdown <= 0) {
                    clearInterval(countdownInterval);
                    this.gameStarting = false;
                    this.startGame();
                }
            }, 1000);
        },

        selectPattern(type) {
            this.patternType = type;
            this.cartellas = [];
            this.selectedCartellaNumbers = [];
            this.takenCartellas = [];
            this.currentCartella = [];
            this.totalCartellas = 0;
            this.updatePrize();
        },

        toggleCartellaNumber(num) {
            if (this.selectedCartellaNumbers.includes(num)) {
                this.selectedCartellaNumbers = this.selectedCartellaNumbers.filter(n => n !== num);
            } else if (this.selectedCartellaNumbers.length < 2) {
                this.selectedCartellaNumbers.push(num);
                this.selectedCartellaNumbers.sort((a, b) => a - b);
            }
            this.currentCartella = this.predefinedCartellas[num - 1] || [];
        },

        confirmCartellas() {
            if (this.selectedCartellaNumbers.length === 0 || this.totalCartellas >= this.TOTAL_CARTELLAS_LIMIT) return;
            this.selectedCartellaNumbers.forEach(num => {
                this.cartellas.push({
                    id: num,
                    grid: this.predefinedCartellas[num - 1],
                    numbers: this.predefinedCartellas[num - 1].flat().filter(n => n !== '*'),
                    markedNumbers: [],
                    patterns: [],
                    isWinner: false
                });
                this.takenCartellas.push(num);
                this.totalCartellas++;
            });
            this.updatePrize();
            this.selectedCartellaNumbers = [];
            this.currentCartella = [];
        },

        cancelCartellas() {
            this.cartellas = [];
            this.takenCartellas = [];
            this.selectedCartellaNumbers = [];
            this.currentCartella = [];
            this.totalCartellas = 0;
            this.updatePrize();
        },

        getLetter(num) {
            if (num >= 1 && num <= 15) return 'B';
            if (num >= 16 && num <= 30) return 'I';
            if (num >= 31 && num <= 45) return 'N';
            if (num >= 46 && num <= 60) return 'G';
            return 'O';
        },

        getNumber(col, row) {
            const baseNumbers = [
                [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],     // B
                [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30], // I
                [31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45], // N
                [46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60], // G
                [61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75]  // O
            ];
            return baseNumbers[col][row - 1];
        },

        toggleMark(cartella, num) {
            if (cartella.markedNumbers.includes(num)) {
                cartella.markedNumbers = cartella.markedNumbers.filter(n => n !== num);
            } else {
                cartella.markedNumbers.push(num);
            }
            if (this.calledNumbers.length >= 4) {
                this.checkPatterns(cartella);
            }
        },

        checkPatterns(cartella) {
            const patterns = [];
            // Check rows
            for (let row = 0; row < 5; row++) {
                if (cartella.grid[row].every(num => num === '*' || cartella.markedNumbers.includes(num))) {
                    patterns.push('Row ' + (row + 1));
                }
            }
            // Check columns
            for (let col = 0; col < 5; col++) {
                if (cartella.grid.every(row => row[col] === '*' || cartella.markedNumbers.includes(row[col]))) {
                    patterns.push('Column ' + ['B', 'I', 'N', 'G', 'O'][col]);
                }
            }
            // Check diagonals
            if (cartella.grid.every((row, i) => row[i] === '*' || cartella.markedNumbers.includes(row[i]))) {
                patterns.push('Diagonal TL-BR');
            }
            if (cartella.grid.every((row, i) => row[4-i] === '*' || cartella.markedNumbers.includes(row[4-i]))) {
                patterns.push('Diagonal TR-BL');
            }
            cartella.patterns = patterns;
            const requiredPatterns = this.patternType === 'single' ? 1 : 2;
            if (patterns.length >= requiredPatterns) {
                cartella.isWinner = true;
                this.hasWinner = true;
                this.winAmount = this.patternType === 'single' ? this.betAmount * 5 : this.betAmount * 10;
            }
        },

        isWinningNumber(cartella, row, col) {
            const num = cartella.grid[row][col];
            if (num === '*') return true;
            return cartella.patterns.some(pattern => {
                if (pattern.startsWith('Row')) {
                    const rowNum = parseInt(pattern.split(' ')[1]) - 1;
                    return row === rowNum;
                }
                if (pattern.startsWith('Column')) {
                    const colLetter = pattern.split(' ')[1];
                    const colIndex = ['B', 'I', 'N', 'G', 'O'].indexOf(colLetter);
                    return col === colIndex;
                }
                if (pattern === 'Diagonal TL-BR') {
                    return row === col;
                }
                if (pattern === 'Diagonal TR-BL') {
                    return row + col === 4;
                }
                return false;
            });
        },

        startGame() {
            if (this.totalCartellas < this.MINIMUM_CARTELLAS) return;
            this.gameStarted = true;
            this.calledNumbers = [];
            this.lastFiveCalls = [];
            this.previousNumber = null;
            this.previousNumberLetter = null;

            const drawNumber = () => {
                if (this.hasWinner || this.calledNumbers.length >= 75) {
                    this.showWinnerPopup = true;
                    setTimeout(() => {
                        this.resetGame();
                    }, this.POPUP_DURATION);
                    return;
                }

                // Randomly simulate a server win after a minimum of 4 draws
                if (this.calledNumbers.length >= 4 && Math.random() < 0.1) { // 10% chance per draw after 4 draws
                    let winningCartella;
                    do {
                        winningCartella = Math.floor(Math.random() * 100) + 1;
                    } while (this.cartellas.some(cartella => cartella.id === winningCartella));
                    this.winningCartella = winningCartella;
                    this.showWinnerPopup = true;
                    setTimeout(() => {
                        this.resetGame();
                    }, this.POPUP_DURATION);
                    return;
                }

                let nextNum;
                do {
                    nextNum = Math.floor(Math.random() * 75) + 1;
                } while (this.calledNumbers.includes(nextNum));

                this.currentCalledNumber = nextNum;
                this.currentCalledNumberLetter = this.getLetter(nextNum);
                setTimeout(() => {
                    this.previousNumber = this.currentCalledNumber;
                    this.previousNumberLetter = this.currentCalledNumberLetter;
                    this.calledNumbers.push(nextNum);
                    this.lastFiveCalls.unshift({ letter: this.currentCalledNumberLetter, number: this.currentCalledNumber });
                    if (this.lastFiveCalls.length > 5) this.lastFiveCalls.pop();
                    this.currentCalledNumber = null;
                    setTimeout(drawNumber, this.DRAW_INTERVAL);
                }, this.ANIMATION_DURATION);
            };

            drawNumber();
        },

        claimWin() {
            if (!this.hasWinner || this.calledNumbers.length < 4) return;
            this.showWinnerPopup = true;
            setTimeout(() => {
                this.resetGame();
            }, this.POPUP_DURATION);
        },

        resetGame() {
            this.patternSelected = true;
            this.patternType = 'single';
            this.selectedCartellaNumbers = [];
            this.takenCartellas = [];
            this.currentCartella = [];
            this.cartellas = [];
            this.calledNumbers = [];
            this.lastFiveCalls = [];
            this.gameStarted = false;
            this.gameStarting = false;
            this.countdown = 10;
            this.hasWinner = false;
            this.currentCalledNumber = null;
            this.currentCalledNumberLetter = '';
            this.previousNumber = null;
            this.previousNumberLetter = null;
            this.showWinnerPopup = false;
            this.winningCartella = null;
            this.totalCartellas = 0;
            this.winAmount = 0;
            this.roundStartTime = Date.now();
            this.checkAutoStart();
            this.updatePrize();
        },

        // Add a method to sync with the backend
        syncWithBackend() {
            fetch('/bingo/sync', {
                method: 'GET',
            })
            .then(response => response.json())
            .then(data => {
                console.log('Synced with backend:', data);
                // Update the game state based on the backend response
                this.totalCartellas = data.totalCartellas;
                this.calledNumbers = data.calledNumbers;
                this.totalPrize = data.totalPrize;
            })
            .catch(error => console.error('Error syncing with backend:', error));
        }
    };
}