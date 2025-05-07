$(document).ready(function() {
    const config = {
        endpoints: {
            currentRound: '/keno/current_round',
            placeBet: '/keno/place_bet',
            cancelBet: '/keno/cancel_bet',
            cancelTicket: '/keno/cancel_ticket',
            ticketHistory: '/keno/ticket_history'
        },
        timing: {
            MIN_BET_AMOUNT: 5,
            TOTAL_DRAW_NUMBERS: 20,
            DRAW_INTERVAL: 750,        // 0.5s per number, 10s total for 20 numbers
            INTERACTION_CUTOFF: 6000,  // 6s before selection ends
            POPUP_DURATION: 2000,      // 2s for winner popup
            SYNC_INTERVAL: 5000        // Sync every 5s
        }
    };

    let state = {
        token: null,
        demo: false,
        gameState: 'SELECT',       // SELECT, SHOWING_RESULT
        timeLeft: 0,               // Time left in current phase (ms)
        totalAmount: 0,
        betAmount: 5,
        selectedNumbers: [],
        drawnNumbers: [],
        roundNumbers: [],          // All numbers from server
        currentRoundId: null,
        tickets: [],
        totalTickets: 0,
        hasTickets: false,
        winAmount: 0,
        showWinnerPopup: false,
        showHistoryModal: false,
        timer: '00:00',
        timerClass: 'text-white text-base',
        oddType: 'kiron',
        ticketHistory: [],
        isFetchingRound: false
    };

    // Initialize the game
    async function init() {
        state.token = getQueryParam('token') || '';
        state.demo = getQueryParam('demo') === 'true';
        $('#back-link').attr('href', `/?token=${state.token}`);
        await syncWithServer();
        setupEventListeners();
        setInterval(gameLoop, 1000); // Update timer/UI every 1s
        setInterval(syncWithServer, config.timing.SYNC_INTERVAL); // Sync with server every 5s
        updateUI();
    }

    // Get URL query parameter
    function getQueryParam(param) {
        return new URLSearchParams(window.location.search).get(param);
    }

    // Main game loop (every 1s)
    function gameLoop() {
        updateTimer();
        updateUI();
    }

    // Update timer based on state
    function updateTimer() {
        state.timeLeft = Math.max(0, state.timeLeft - 1000);
        const seconds = Math.ceil(state.timeLeft / 1000);
        state.timer = `00:${seconds.toString().padStart(2, '0')}`;
        state.timerClass = state.gameState === 'SELECT' && state.timeLeft <= config.timing.INTERACTION_CUTOFF
            ? 'text-red-600 text-xl font-bold'
            : 'text-white text-base';
    }

    // Sync with server
    async function syncWithServer() {
        if (state.isFetchingRound) return;
        state.isFetchingRound = true;
        try {
            const response = await fetchRoundData();
            if (response.status === 'success') {
                updateStateFromServer(response);
                if (state.gameState === 'SHOWING_RESULT' && state.drawnNumbers.length === 0 && state.roundNumbers.length > 0) {
                    animateNumbers(state.roundNumbers);
                }
            } else {
                console.error('Sync failed:', response.message);
            }
        } catch (error) {
            console.error('Sync error:', error);
        } finally {
            state.isFetchingRound = false;
        }
    }

    // Fetch current round data
    async function fetchRoundData() {
        const response = await $.ajax({
            url: `${config.endpoints.currentRound}?token=${state.token}`,
            method: 'GET'
        });
        return response;
    }

    // Update state based on server response
    function updateStateFromServer(data) {
        const previousState = state.gameState;
        state.currentRoundId = data.round_id;
        state.totalAmount = data.balance || 0;
        state.gameState = data.round_status;
        state.timeLeft = Math.round(data.time_left * 1000); // Sync exactly with server
        state.roundNumbers = data.numbers || [];
        state.roundResults = data.results || [];
        if (state.gameState === 'SHOWING_RESULT') {
            state.selectedNumbers = [];
            updateTicketResults(data.results);
        } else {
            state.drawnNumbers = [];
        }
        if (previousState !== state.gameState) {
            console.log(`State changed to ${state.gameState}, timeLeft: ${state.timeLeft}ms`);
        }
    }

    // Animate numbers one by one
    function animateNumbers(numbers) {
        state.drawnNumbers = [];
        let index = 0;
        const interval = setInterval(() => {
            if (index < numbers.length) {
                state.drawnNumbers.push(numbers[index]);
                index++;
                updateUI();
            } else {
                clearInterval(interval);
            }
        }, config.timing.DRAW_INTERVAL);
    }

    // Event Listeners
    function setupEventListeners() {
        $('#bet-decrement').on('click', decrementBet);
        $('#bet-increment').on('click', incrementBet);
        $('#odd-type').on('change', updateOddType);
        $('#quick-pick').on('click', quickPick);
        $('#add-ticket').on('click', addTicket);
        $('#cancel-tickets').on('click', cancelTickets);
        $('#history-button').on('click', showHistoryModal);
        $('#close-history').on('click', hideHistoryModal);
        $('#history-modal').on('click', closeModalOnOverlay);
        $('#claim-win').on('click', handleWin);
        $(document).on('click', '.number-circle', selectNumberHandler);
        $(document).on('keydown', '.number-circle', selectNumberKeyHandler);
        $(document).on('click', '.cancel-ticket', cancelTicketHandler);
        $(document).on('click', '.tooltip-button', showTooltipHandler);
    }

    function decrementBet() {
        state.betAmount = Math.max(config.timing.MIN_BET_AMOUNT, state.betAmount - 1);
        updateUI();
    }

    function incrementBet() {
        state.betAmount++;
        updateUI();
    }

    function updateOddType() {
        state.oddType = $('#odd-type').val();
        updateUI();
    }

    function quickPick() {
        if (!canSelect()) return;
        state.selectedNumbers = [];
        const pickCount = Math.floor(Math.random() * 5) + 1;
        while (state.selectedNumbers.length < pickCount) {
            const num = Math.floor(Math.random() * 80) + 1;
            if (!state.selectedNumbers.includes(num)) state.selectedNumbers.push(num);
        }
        state.selectedNumbers.sort((a, b) => a - b);
        updateNumberGrid();
    }

    async function addTicket() {
        if (!canAddTicket()) return;
        const payload = {
            token: state.token,
            ticket: { numbers: [...state.selectedNumbers], stake: state.betAmount, odd_type: state.oddType },
            round_id: state.currentRoundId
        };
        try {
            const response = await $.ajax({
                url: config.endpoints.placeBet,
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify(payload)
            });
            if (response.status === 'success') {
                state.tickets.push({
                    numbers: [...state.selectedNumbers],
                    betAmount: state.betAmount,
                    multiplier: response.odds_breakdown[response.odds_breakdown.length - 1][1],
                    potentialWin: response.potential_win,
                    actualWin: 0,
                    isWinner: false,
                    oddsBreakdown: response.odds_breakdown,
                    showTooltip: false,
                    roundId: state.currentRoundId,
                    ticketId: response.ticket_id
                });
                state.totalTickets++;
                state.hasTickets = true;
                state.totalAmount = response.new_balance;
                state.selectedNumbers = [];
                await fetchTicketHistory();
                updateUI();
            } else {
                alert('Failed to place ticket: ' + response.message);
            }
        } catch (error) {
            alert('Error placing ticket: ' + error.message);
        }
    }

    function selectNumberHandler() {
        const num = parseInt($(this).text());
        selectNumber(num);
    }

    function selectNumberKeyHandler(e) {
        if (e.key === 'Enter' || e.key === 'Space') {
            const num = parseInt($(this).text());
            selectNumber(num);
        }
    }

    function cancelTicketHandler() {
        const index = $(this).data('index');
        cancelTicket(index);
    }

    function showTooltipHandler() {
        const index = $(this).data('index');
        showTooltip(index);
    }

    function showHistoryModal() {
        state.showHistoryModal = true;
        fetchTicketHistory();
    }

    function hideHistoryModal() {
        state.showHistoryModal = false;
        updateUI();
    }

    function closeModalOnOverlay(e) {
        if (e.target === $('#history-modal')[0]) {
            state.showHistoryModal = false;
            updateUI();
        }
    }

    function canSelect() {
        return state.gameState === 'SELECT' && state.timeLeft > config.timing.INTERACTION_CUTOFF;
    }

    function canAddTicket() {
        return canSelect() && state.selectedNumbers.length > 0 && state.currentRoundId;
    }

    async function cancelTicket(index) {
        if (!canSelect()) return;
        const ticket = state.tickets[index];
        if (!ticket.ticketId) return;
        try {
            const response = await $.ajax({
                url: config.endpoints.cancelTicket,
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ token: state.token, ticket_id: ticket.ticketId })
            });
            if (response.status === 'success') {
                state.tickets.splice(index, 1);
                state.totalTickets--;
                state.hasTickets = state.tickets.length > 0;
                state.totalAmount = response.new_balance;
                await fetchTicketHistory();
                updateUI();
            } else {
                alert('Failed to cancel ticket: ' + response.message);
            }
        } catch (error) {
            alert('Error canceling ticket: ' + error.message);
        }
    }

    async function cancelTickets() {
        if (!canSelect()) return;
        try {
            const response = await $.ajax({
                url: config.endpoints.cancelBet,
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ token: state.token, round_id: state.currentRoundId })
            });
            if (response.status === 'success') {
                state.tickets = state.tickets.filter(t => t.roundId !== state.currentRoundId);
                state.totalTickets = state.tickets.length;
                state.hasTickets = state.tickets.length > 0;
                state.totalAmount = response.new_balance;
                state.selectedNumbers = [];
                await fetchTicketHistory();
                updateUI();
            } else {
                alert('Failed to cancel tickets: ' + response.message);
            }
        } catch (error) {
            alert('Error canceling tickets: ' + error.message);
        }
    }

    async function fetchTicketHistory() {
        try {
            const response = await $.ajax({
                url: `${config.endpoints.ticketHistory}?token=${state.token}`,
                method: 'GET'
            });
            if (response.status === 'success' && Array.isArray(response.tickets)) {
                state.ticketHistory = response.tickets.map(ticket => ({
                    round_id: ticket.round_id,
                    numbers: ticket.numbers || [],
                    bet_amount: ticket.bet_amount || 0,
                    winnings: ticket.winnings || 0,
                    timestamp: new Date(ticket.timestamp).toLocaleString()
                }));
            } else {
                console.error('Failed to fetch ticket history:', response.message);
                state.ticketHistory = [];
            }
        } catch (error) {
            console.error('Error fetching ticket history:', error);
            state.ticketHistory = [];
        }
        updateHistoryModal();
    }

    function handleWin() {
        if (state.winAmount > 0) {
            state.showWinnerPopup = true;
            setTimeout(() => {
                state.showWinnerPopup = false;
                updateUI();
            }, config.timing.POPUP_DURATION);
        }
    }

    function showTooltip(index) {
        state.tickets.forEach((ticket, i) => {
            ticket.showTooltip = i === index ? !ticket.showTooltip : false;
        });
        updateTickets();
    }

    function selectNumber(num) {
        if (!canSelect()) return;
        if (state.selectedNumbers.includes(num)) {
            state.selectedNumbers = state.selectedNumbers.filter(n => n !== num);
        } else if (state.selectedNumbers.length < 10) {
            state.selectedNumbers.push(num);
            state.selectedNumbers.sort((a, b) => a - b);
        }
        updateNumberGrid();
    }

    function updateTicketResults(results) {
        state.winAmount = 0;
        state.tickets = state.tickets.filter(ticket => ticket.roundId === state.currentRoundId);
        state.tickets.forEach(ticket => {
            const result = results.find(r => JSON.stringify(r.numbers) === JSON.stringify(ticket.numbers));
            if (result) {
                ticket.actualWin = result.winnings || 0;
                ticket.isWinner = ticket.actualWin > 0;
                state.winAmount += ticket.actualWin;
            }
        });
        state.totalTickets = state.tickets.length;
        state.hasTickets = state.tickets.length > 0;
    }

    // UI Updates
    function updateUI() {
        $('#total-amount').text(state.demo ? '' : `${state.totalAmount.toFixed(2)} birr`);
        $('#timer').text(state.timer).attr('class', `timer ${state.timerClass}`);
        $('body').attr('class', `body ${state.gameState === 'SHOWING_RESULT' ? 'body-game-started' : ''}`);
        updateResultSection();
        updateNumberGrid();
        updateSelectionControls();
        updateTickets();
        updateWinSection();
        updateWinnerPopup();
        updateHistoryModal();
    }

    function updateResultSection() {
        $('#result-section').css('display', state.gameState === 'SHOWING_RESULT' ? 'block' : 'none');
        $('#drawn-numbers-grid').empty();
        state.drawnNumbers.forEach(num => {
            const div = `<div class="result-circle ${state.selectedNumbers.includes(num) ? 'result-circle-match text-green-400' : 'text-white'}" aria-label="Drawn number ${num}${state.selectedNumbers.includes(num) ? ' (matched)' : ''}">${num}</div>`;
            $('#drawn-numbers-grid').append(div);
        });
    }

    // function updateResultSection() {
    //     $('#result-section').css('display', state.gameState === 'SHOWING_RESULT' ? 'block' : 'none');
    //     $('#animated-number-container').attr('class', `animated-number-container ${state.isAnimating && state.drawnNumbers.length === 1 ? '' : 'hidden'}`);
    //     $('#animated-number').attr('class', `animated-number ${
    //         state.isAnimating && state.selectedNumbers.includes(state.drawnNumbers[0]) ? 'animated-number-match' :
    //         state.isAnimating ? 'animated-number-drawn' : ''
    //     }`);
    //     $('#animated-number-text').text(state.drawnNumbers[0] || '');
    //     $('#animated-number').attr('aria-label', state.drawnNumbers[0] ? `Current drawn number: ${state.drawnNumbers[0]}` : '');
    
    //     $('#drawn-numbers-grid').css('display', 'grid');
    //     $('#drawn-numbers-grid').empty();
    //     state.roundNumbers.forEach(num => {
    //         const isCurrent = state.isAnimating && state.drawnNumbers.includes(num);
    //         const div = `<div class="result-circle ${
    //             state.selectedNumbers.includes(num) ? 'result-circle-match text-green-400' :
    //             isCurrent ? 'text-yellow-400' : 'text-white'
    //         }" aria-label="Drawn number ${num}${state.selectedNumbers.includes(num) ? ' (matched)' : ''}">${num}</div>`;
    //         $('#drawn-numbers-grid').append(div);
    //     });
    // }

    function updateNumberGrid() {
        $('#number-grid').empty().attr('class', `grid grid-cols-10 mb-4 ${canSelect() ? '' : 'pointer-events-none'}`);
        for (let num = 1; num <= 80; num++) {
            const div = `<div class="number-circle ${
                state.selectedNumbers.includes(num) && !state.drawnNumbers.includes(num) ? 'number-circle-selected' :
                state.drawnNumbers.includes(num) && state.selectedNumbers.includes(num) ? 'number-circle-match-indicator text-green-400' :
                state.drawnNumbers.includes(num) ? 'number-circle-drawn-indicator text-white' :
                canSelect() ? 'hover:bg-blue-600' : ''
            }" aria-label="Number ${num}${state.selectedNumbers.includes(num) ? ' (selected)' : ''}" aria-pressed="${state.selectedNumbers.includes(num)}" role="button" tabindex="0">${num}</div>`;
            $('#number-grid').append(div);
        }
    }

    function updateSelectionControls() {
        $('#selection-controls').css('display', state.gameState === 'SELECT' ? 'flex' : 'none');
        $('#bet-amount').text(state.betAmount);
        $('#add-ticket').prop('disabled', !canAddTicket());
        $('#cancel-tickets').css('display', state.hasTickets ? 'block' : 'none');
    }

    function updateTickets() {
        $('#total-tickets').text(`Tickets: ${state.totalTickets}`);
        $('#tickets-list').empty();
        const filteredTickets = state.gameState === 'SHOWING_RESULT'
            ? state.tickets.filter(ticket => ticket.roundId === state.currentRoundId)
            : state.tickets;
        filteredTickets.forEach((ticket, index) => {
            const ticketHtml = `
                <div class="ticket flex justify-between items-center ${ticket.isWinner && state.gameState === 'SHOWING_RESULT' ? 'ticket-winner' : ''}" aria-label="Ticket ${index + 1}">
                    <div class="flex items-center space-x-2">
                        ${canSelect() ? `<button class="cancel-ticket text-white hover:text-red-600" data-index="${index}" aria-label="Remove ticket"><svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg></button>` : ''}
                        <div>
                            <p class="text-sm">Ticket ${index + 1}</p>
                            <p class="text-sm">${ticket.numbers.map(num => `<span class="ticket-number ${state.drawnNumbers.includes(num) ? 'ticket-number-match' : ''}" aria-label="Ticket number ${num}${state.drawnNumbers.includes(num) ? ' (matched)' : ''}">${num}</span>`).join('')}</p>
                            <p class="ticket-count">Total Selected: ${ticket.numbers.length}</p>
                            ${ticket.isWinner && state.gameState === 'SHOWING_RESULT' ? '<p class="text-green-400 text-sm">Winner!</p>' : ''}
                        </div>
                    </div>
                    <div class="text-right relative">
                        <div class="flex items-center space-x-1">
                            <p class="text-sm">${ticket.betAmount} x ${ticket.multiplier}</p>
                            <button class="tooltip-button text-blue-400 hover:text-blue-600 text-xs" data-index="${index}" aria-label="Show multiplier breakdown">ⓘ</button>
                        </div>
                        <p class="ticket-win">${state.gameState === 'SHOWING_RESULT' && ticket.isWinner ? ticket.actualWin + ' birr' : ticket.potentialWin + ' birr'}</p>
                        ${ticket.showTooltip ? `<div class="multiplier-tooltip" style="top: -100%; right: 0;"><p class="font-bold">Multiplier Breakdown:</p>${ticket.oddsBreakdown.map(([matches, odds]) => `<p>Match ${matches}: ${odds.toFixed(1)}x</p>`).join('')}</div>` : ''}
                    </div>
                </div>`;
            $('#tickets-list').append(ticketHtml);
        });
    }

    function updateWinSection() {
        $('#win-section').css('display', state.gameState === 'SHOWING_RESULT' ? 'block' : 'none');
        $('#claim-win').attr('class', `button w-full py-3 text-lg flex justify-between items-center px-4 ${state.winAmount > 0 ? 'button-green' : 'button-disabled'}`);
        $('#claim-win').prop('disabled', state.winAmount <= 0);
        $('#win-amount').text(`${state.winAmount.toFixed(2)} birr`);
    }

    function updateWinnerPopup() {
        $('#winner-popup').css('display', state.showWinnerPopup ? 'block' : 'none');
        $('#winner-amount').text(`${state.winAmount.toFixed(2)} birr`);
    }

    function updateHistoryModal() {
        $('#history-modal').css('display', state.showHistoryModal ? 'flex' : 'none');
        $('#history-list').empty();
        state.ticketHistory.forEach(history => {
            const div = `
                <div class="ticket">
                    <p class="text-sm">Round ID: ${history.round_id || 'N/A'}</p>
                    <p class="text-sm">Numbers: ${history.numbers.join(', ') || 'N/A'}</p>
                    <p class="text-sm">Bet Amount: ${history.bet_amount || 0} birr</p>
                    <p class="text-sm">Winnings: ${(history.winnings || 0).toFixed(2)} birr</p>
                    <p class="text-sm">Timestamp: ${history.timestamp || 'N/A'}</p>
                </div>`;
            $('#history-list').append(div);
        });
    }

    init();
});