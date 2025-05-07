function ludoGame() {
    return {
        deposit: {{ deposit|safe }},
        demo: {{ 'true' if demo else 'false' }},
        betAmount: 1,
        winAmount: 0,
        tickets: 0,
        playerColor: 'red',
        botColor: 'blue', // Keeping one bot for simplicity
        boardSize: 15,
        board: [],
        paths: {
            red: [
                { r: 6, c: 0 }, { r: 6, c: 1 }, { r: 6, c: 2 }, { r: 6, c: 3 }, { r: 6, c: 4 }, { r: 6, c: 5 },
                { r: 5, c: 6 }, { r: 4, c: 6 }, { r: 3, c: 6 }, { r: 2, c: 6 }, { r: 1, c: 6 }, { r: 0, c: 6 },
                { r: 0, c: 7 }, { r: 0, c: 8 }, { r: 1, c: 8 }, { r: 2, c: 8 }, { r: 3, c: 8 }, { r: 4, c: 8 },
                { r: 5, c: 8 }, { r: 6, c: 9 }, { r: 6, c: 10 }, { r: 6, c: 11 }, { r: 6, c: 12 }, { r: 6, c: 13 },
                { r: 6, c: 14 }, { r: 7, c: 14 }, { r: 8, c: 14 }, { r: 8, c: 13 }, { r: 8, c: 12 }, { r: 8, c: 11 },
                { r: 8, c: 10 }, { r: 8, c: 9 }, { r: 9, c: 8 }, { r: 10, c: 8 }, { r: 11, c: 8 }, { r: 12, c: 8 },
                { r: 13, c: 8 }, { r: 14, c: 8 }, { r: 14, c: 7 }, { r: 14, c: 6 }, { r: 13, c: 6 }, { r: 12, c: 6 },
                { r: 11, c: 6 }, { r: 10, c: 6 }, { r: 9, c: 6 }, { r: 8, c: 5 }, { r: 8, c: 4 }, { r: 8, c: 3 },
                { r: 8, c: 2 }, { r: 8, c: 1 }, { r: 8, c: 0 }, { r: 7, c: 0 }, { r: 6, c: 0 }, // Main path
                { r: 7, c: 1 }, { r: 7, c: 2 }, { r: 7, c: 3 }, { r: 7, c: 4 }, { r: 7, c: 5 }, { r: 7, c: 6 }, { r: 7, c: 7 } // Home stretch
            ],
            blue: [
                { r: 8, c: 14 }, { r: 8, c: 13 }, { r: 8, c: 12 }, { r: 8, c: 11 }, { r: 8, c: 10 }, { r: 8, c: 9 },
                { r: 9, c: 8 }, { r: 10, c: 8 }, { r: 11, c: 8 }, { r: 12, c: 8 }, { r: 13, c: 8 }, { r: 14, c: 8 },
                { r: 14, c: 7 }, { r: 14, c: 6 }, { r: 13, c: 6 }, { r: 12, c: 6 }, { r: 11, c: 6 }, { r: 10, c: 6 },
                { r: 9, c: 6 }, { r: 8, c: 5 }, { r: 8, c: 4 }, { r: 8, c: 3 }, { r: 8, c: 2 }, { r: 8, c: 1 },
                { r: 8, c: 0 }, { r: 7, c: 0 }, { r: 6, c: 0 }, { r: 6, c: 1 }, { r: 6, c: 2 }, { r: 6, c: 3 },
                { r: 6, c: 4 }, { r: 6, c: 5 }, { r: 5, c: 6 }, { r: 4, c: 6 }, { r: 3, c: 6 }, { r: 2, c: 6 },
                { r: 1, c: 6 }, { r: 0, c: 6 }, { r: 0, c: 7 }, { r: 0, c: 8 }, { r: 1, c: 8 }, { r: 2, c: 8 },
                { r: 3, c: 8 }, { r: 4, c: 8 }, { r: 5, c: 8 }, { r: 6, c: 9 }, { r: 6, c: 10 }, { r: 6, c: 11 },
                { r: 6, c: 12 }, { r: 6, c: 13 }, { r: 6, c: 14 }, { r: 7, c: 14 }, // Main path
                { r: 7, c: 13 }, { r: 7, c: 12 }, { r: 7, c: 11 }, { r: 7, c: 10 }, { r: 7, c: 9 }, { r: 7, c: 8 }, { r: 7, c: 7 } // Home stretch
            ],
            green: [
                { r: 0, c: 8 }, { r: 1, c: 8 }, { r: 2, c: 8 }, { r: 3, c: 8 }, { r: 4, c: 8 }, { r: 5, c: 8 },
                { r: 6, c: 9 }, { r: 6, c: 10 }, { r: 6, c: 11 }, { r: 6, c: 12 }, { r: 6, c: 13 }, { r: 6, c: 14 },
                { r: 7, c: 14 }, { r: 8, c: 14 }, { r: 8, c: 13 }, { r: 8, c: 12 }, { r: 8, c: 11 }, { r: 8, c: 10 },
                { r: 8, c: 9 }, { r: 9, c: 8 }, { r: 10, c: 8 }, { r: 11, c: 8 }, { r: 12, c: 8 }, { r: 13, c: 8 },
                { r: 14, c: 8 }, { r: 14, c: 7 }, { r: 14, c: 6 }, { r: 13, c: 6 }, { r: 12, c: 6 }, { r: 11, c: 6 },
                { r: 10, c: 6 }, { r: 9, c: 6 }, { r: 8, c: 5 }, { r: 8, c: 4 }, { r: 8, c: 3 }, { r: 8, c: 2 },
                { r: 8, c: 1 }, { r: 8, c: 0 }, { r: 7, c: 0 }, { r: 6, c: 0 }, { r: 6, c: 1 }, { r: 6, c: 2 },
                { r: 6, c: 3 }, { r: 6, c: 4 }, { r: 6, c: 5 }, { r: 5, c: 6 }, { r: 4, c: 6 }, { r: 3, c: 6 },
                { r: 2, c: 6 }, { r: 1, c: 6 }, { r: 0, c: 6 }, { r: 0, c: 7 }, // Main path
                { r: 1, c: 7 }, { r: 2, c: 7 }, { r: 3, c: 7 }, { r: 4, c: 7 }, { r: 5, c: 7 }, { r: 6, c: 7 }, { r: 7, c: 7 } // Home stretch
            ],
            yellow: [
                { r: 14, c: 6 }, { r: 13, c: 6 }, { r: 12, c: 6 }, { r: 11, c: 6 }, { r: 10, c: 6 }, { r: 9, c: 6 },
                { r: 8, c: 5 }, { r: 8, c: 4 }, { r: 8, c: 3 }, { r: 8, c: 2 }, { r: 8, c: 1 }, { r: 8, c: 0 },
                { r: 7, c: 0 }, { r: 6, c: 0 }, { r: 6, c: 1 }, { r: 6, c: 2 }, { r: 6, c: 3 }, { r: 6, c: 4 },
                { r: 6, c: 5 }, { r: 5, c: 6 }, { r: 4, c: 6 }, { r: 3, c: 6 }, { r: 2, c: 6 }, { r: 1, c: 6 },
                { r: 0, c: 6 }, { r: 0, c: 7 }, { r: 0, c: 8 }, { r: 1, c: 8 }, { r: 2, c: 8 }, { r: 3, c: 8 },
                { r: 4, c: 8 }, { r: 5, c: 8 }, { r: 6, c: 9 }, { r: 6, c: 10 }, { r: 6, c: 11 }, { r: 6, c: 12 },
                { r: 6, c: 13 }, { r: 6, c: 14 }, { r: 7, c: 14 }, { r: 8, c: 14 }, { r: 8, c: 13 }, { r: 8, c: 12 },
                { r: 8, c: 11 }, { r: 8, c: 10 }, { r: 8, c: 9 }, { r: 9, c: 8 }, { r: 10, c: 8 }, { r: 11, c: 8 },
                { r: 12, c: 8 }, { r: 13, c: 8 }, { r: 14, c: 8 }, { r: 14, c: 7 }, // Main path
                { r: 13, c: 7 }, { r: 12, c: 7 }, { r: 11, c: 7 }, { r: 10, c: 7 }, { r: 9, c: 7 }, { r: 8, c: 7 }, { r: 7, c: 7 } // Home stretch
            ],
        },
        playerPieces: [],
        botPieces: [],
        currentDice: null,
        rollCount: 0,
        gameStarted: false,
        isPlayerTurn: true,
        gameOver: false,
        winner: null,
        currentTime: new Date().toLocaleTimeString(),

        init() {
            this.updateTime();
            setInterval(() => this.updateTime(), 1000);
            this.tickets = this.demo ? 1 : 0;
            this.initializeBoard();
        },

        updateTime() {
            this.currentTime = new Date().toLocaleTimeString();
        },

        initializeBoard() {
            this.board = Array(this.boardSize).fill().map(() => Array(this.boardSize).fill(null));
            // Define starting and ending areas (visual only for now)
            for (let i = 0; i < 6; i++) {
                for (let j = 0; j < 6; j++) {
                    this.boardData(i, j, 'red_start');
                    this.boardData(i, this.boardSize - 6 + j, 'green_start');
                    this.boardData(this.boardSize - 6 + i, j, 'yellow_start');
                    this.boardData(this.boardSize - 6 + i, this.boardSize - 6 + j, 'blue_start');
                }
            }
            this.paths.red.forEach(p => this.boardData(p.r, p.c, 'path'));
            this.paths.blue.forEach(p => this.boardData(p.r, p.c, 'path'));
            this.paths.green.forEach(p => this.boardData(p.r, p.c, 'path'));
            this.paths.yellow.forEach(p => this.boardData(p.r, p.c, 'path'));
            this.boardData(7, 7, 'home'); // Center home
            this.boardData(1, 6, 'safe');
            this.boardData(6, 13, 'safe');
            this.boardData(13, 8, 'safe');
            this.boardData(8, 1, 'safe');
        },

        boardData(r, c, type) {
            if (this.board && this.board.length > r && this.boardData(0).length > c) {
                this.boardData(r, c) = type;
            }
        },

        startGame() {
            if (this.betAmount <= 0 && !this.demo) return;
            this.gameStarted = true;
            this.botColor = 'blue'; // Keeping it simple with one bot
            this.playerPieces = [{ id: 1, position: -1 }, { id: 2, position: -1 }]; // -1 means at home
            this.botPieces = [{ id: 1, position: -1 }, { id: 2, position: -1 }];
            this.isPlayerTurn = true;
            this.gameOver = false;
            this.winner = null;
        },

        async rollDice() {
            if (!this.isPlayerTurn || this.gameOver) return;
            this.currentDice = Math.floor(Math.random() * 6) + 1;
            this.rollCount++;
            await new Promise(resolve => setTimeout(resolve, 1000));
            const movablePlayerPieces = this.getMovablePieces(this.playerPieces, this.paths.red, this.currentDice);

            if (movablePlayerPieces.length > 0) {
                // For now, just move the first movable piece
                await this.movePiece(this.playerPieces, 'red', movablePlayerPieces, 0, this.currentDice);
            } else if (this.currentDice !== 6) {
                this.isPlayerTurn = false;
                setTimeout(() => this.botTurn(), 1500);
            }
            this.currentDice = null;
        },

        getPiecePosition(piece, path) {
            return piece.position >= 0 && piece.position < path.length ? pathData(piece.position) : null;
        },

        getPathCoords(path, index) {
            return index >= 0 && index < path.length ? pathData(index) : null;
        },

        async movePiece(pieces, color, movablePieces, pieceIndex, dice) {
            const pieceToMove = piecesData(movablePiecesData(pieceIndex));
            if (!pieceToMove) return;

            if (pieceToMove.position === -1 && dice === 6) {
                pieceToMove.position = 0;
            } else if (pieceToMove.position !== -1) {
                const newPosition = pieceToMove.position + dice;
                if (newPosition < this.pathsData(color).length) {
                    pieceToMove.position = newPosition;
                    this.checkCapture(pieceToMove, color);
                    if (dice !== 6) {
                        this.isPlayerTurn = color !== this.playerColor;
                        if (!this.isPlayerTurn) {
                            setTimeout(() => this.botTurn(), 1500);
                        }
                    } else {
                        // Player gets another turn if they roll a 6
                    }
                } else if (newPosition === this.pathsData(color).length -1 ) {
                    pieceToMove.position = newPosition;
                    this.checkWin(pieces, color);
                }
            }
        },

        checkCapture(movedPiece, movedColor) {
            const targetPosition = this.getPiecePosition(movedPiece, this.pathsData(movedColor));
            if (!targetPosition) return;

            const opponentPieces = movedColor === this.playerColor ? this.botPieces : this.playerPieces;
            const opponentColor = movedColor === this.playerColor ? this.botColor : this.playerColor;
            const isSafe = (r, c) => (r === 1 && c === 6) || (r === 6 && c === 13) || (r === 13 && c === 8) || (r === 8 && c === 1);

            opponentPieces.forEach(opponent => {
                const opponentPosition = this.getPiecePosition(opponent, this.pathsData(opponentColor));
                if (opponentPosition && opponentPosition.r === targetPosition.r && opponentPosition.c === targetPosition.c && !isSafe(targetPosition.r, targetPosition.c)) {
                    opponent.position = -1; // Send opponent piece back home
                }
            });
        },

        checkWin(pieces, color) {
            if (pieces.every(p => p.position === this.pathsData(color).length - 1)) {
                this.gameOver = true;
                this.winner = color === this.playerColor;
                this.handleGameEnd();
            }
        },

        botTurn() {
            if (this.isPlayerTurn || this.gameOver) return;
            this.currentDice = Math.floor(Math.random() * 6) + 1;
            setTimeout(async () => {
                const movableBotPieces = this.getMovablePieces(this.botPieces, this.paths.blue, this.currentDice);
                if (movableBotPieces.length > 0) {
                    await this.movePiece(this.botPieces, 'blue', movableBotPieces, 0, this.currentDice);
                } else if (this.currentDice !== 6) {
                    this.isPlayerTurn = true;
                }
                this.currentDice = null;
                if (!this.gameOver && this.currentDice !== 6) {
                    this.isPlayerTurn = true;
                } else if (!this.gameOver && this.currentDice === 6) {
                    setTimeout(() => this.botTurn(), 1000); // Bot gets another turn
                }
            }, 1000);
        },

        getMovablePieces(pieces, path, dice) {
            return pieces.map((piece, index) => index).filter(index => {
                const piece = piecesData(index);
                if (piece.position === -1 && dice === 6) return true;
                if (piece.position !== -1) {
                    const newPos = piece.position + dice;
                    return newPos < pathData.length;
                }
                return false;
            });
        },

        handleGameEnd() {
            if (!this.demo && this.winner) {
                this.winAmount = this.betAmount * 5; // Adjust payout as needed
                this.deposit += this.winAmount - this.betAmount;
                this.tickets++;
                fetch('/game_activity', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: {{ user_id|safe }},
                        game_type: 'ludo',
                        amount_won: this.winAmount,
                        amount_lost: this.betAmount,
                        is_paid: !this.demo
                    })
                });
            }
            if (this.winner) {
                this.triggerConfetti();
            }
        },

        getCellClass(row, col) {
            const boardInfo = this.boardData(row, col);
            if (boardInfo === 'path') return 'bg-green-800';
            if (boardInfo === 'home') return 'bg-yellow-600';
            if (boardInfo === 'safe') return 'bg-blue-400';
            if (boardInfo === 'red_start') return 'bg-red-600 opacity-30';
            if (boardInfo === 'blue_start') return 'bg-blue-600 opacity-30';
            if (boardInfo === 'green_start') return 'bg-green-600 opacity-30';
            if (boardInfo === 'yellow_start') return 'bg-yellow-600 opacity-30';
            if ((row + col) % 2 === 0) return 'bg-gray-700';
            return 'bg-gray-800';
        },

        getCellContent(row, col) {
            let content = '';
            this.playerPieces.forEach(piece => {
                const pos = this.getPiecePosition(piece, this.paths.red);
                if (pos && pos.r === row && pos.c === col) {
                    content += 'R' + piece.id;
                }
            });
            this.botPieces.forEach(piece => {
                const pos = this.getPiecePosition(piece, this.paths.blue);
                if (pos && pos.r === row && pos.c === col) {
                    content += 'B' + piece.id;
                }
            });
            return content;
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
            this.gameStarted = false;
            this.board = [];
            this.playerPieces = [];
            this.botPieces = [];
            this.currentDice = null;
            this.rollCount = 0;
            this.gameOver = false;
            this.winner = null;
            this.winAmount = 0;
            this.betAmount = 1;
            this.initializeBoard();
            this.isPlayerTurn = true;
        },
        // Helper functions to access data within templates
        boardData: (r, c) => this.board && this.board.length > r && this.boardData(0).length > c ? this.boardData(r, c) : null,
        pathsData: (color) => this.pathsData(color),
        piecesData: (index) => index !== undefined ? (index < this.playerPiecesData.length ? this.playerPiecesData(index) : this.botPiecesData(index - this.playerPiecesData.length)) : null,
        playerPiecesData: (index) => this.playerPiecesData(index),
        botPiecesData: (index) => this.botPiecesData(index),
        movablePiecesData: (index) => index,
    };
}