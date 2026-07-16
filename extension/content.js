(async function() {
    // 🛡️ Stealth DOM Reader Bypass (Anti-Cheat Invisible)
    // Creates an isolated iframe to grab unhooked, native browser functions.
    // This bypasses overrides on fetch() and setTimeout().
    const frame = document.createElement('iframe');
    frame.style.display = 'none';
    frame.src = 'about:blank';
    document.documentElement.appendChild(frame);
    
    // Grab unhooked native functions from the clean iframe
    const nativeFetch = frame.contentWindow.fetch;
    const nativeSetTimeout = frame.contentWindow.setTimeout;
    
    // Check if the local Python server is authenticated (license is active)
    async function checkAuth() {
        try {
            const response = await nativeFetch("http://127.0.0.1:5005/auth", {
                method: "GET",
                mode: "cors",
                credentials: "omit"
            });
            if (response.ok) {
                const data = await response.json();
                return data.status === "authenticated";
            }
        } catch (e) {
            // Local server offline or not running
        }
        return false;
    }

    const isAuthed = await checkAuth();
    if (!isAuthed) {
        console.log("Chess Helper: Unauthorized or App not running. Subscription key required.");
        return;
    }

    console.log("Chess Helper: License Verified. Stealth DOM Reader started.");

    // Detect which platform we are on
    const isLichess = window.location.hostname.includes("lichess.org");
    const isChessCom = window.location.hostname.includes("chess.com");

    // Caching state to minimize reflows and HTTP spam
    let cached_is_white_bottom = null;
    let framesSinceOrientationCheck = 0;
    let lastSentMatrixStr = "";
    let lastSentIsWhiteBottom = null;
    let lastSentTimeLeft = null;
    
    // ====================================================================
    //  Chess.com Board Reader
    // ====================================================================
    function readBoardChessCom() {
        let boardArray = Array(8).fill("").map(() => Array(8).fill(""));
        let pieces = document.querySelectorAll('.piece');
        if (!pieces.length) {
            let bulletSpeedDelay = Math.floor(Math.random() * 20) + 70;
            nativeSetTimeout(readBoardChessCom, bulletSpeedDelay);
            return;
        }
        
        let is_white_bottom = true;
        
        // Cache board orientation and only check every 30 iterations (~2.5s) to avoid getBoundingClientRect layout reflows
        if (cached_is_white_bottom !== null && framesSinceOrientationCheck < 30) {
            is_white_bottom = cached_is_white_bottom;
            framesSinceOrientationCheck++;
        } else {
            framesSinceOrientationCheck = 0;
            let anchorPiece = Array.from(pieces).find(p => {
                let sqClass = Array.from(p.classList).find(c => c.startsWith('square-'));
                if (sqClass) {
                    let rank = parseInt(sqClass[8]);
                    return rank <= 2 || rank >= 7; 
                }
                return false;
            });
 
            if (anchorPiece) {
                let sqClass = Array.from(anchorPiece.classList).find(c => c.startsWith('square-'));
                let rank = parseInt(sqClass[8]);
                let rect = anchorPiece.getBoundingClientRect();
                let board = anchorPiece.parentElement.getBoundingClientRect();
                let relativeY = (rect.top - board.top) / board.height;
                let expectedY_WhiteBottom = (8 - rank) / 8;
                let expectedY_BlackBottom = (rank - 1) / 8;
                is_white_bottom = Math.abs(relativeY - expectedY_WhiteBottom) < Math.abs(relativeY - expectedY_BlackBottom);
                cached_is_white_bottom = is_white_bottom;
            } else if (cached_is_white_bottom !== null) {
                is_white_bottom = cached_is_white_bottom;
            }
        }
 
        pieces.forEach(p => {
            let classes = p.className.split(' ');
            let colorType = classes.find(c => c.length === 2 && (c[0]==='w' || c[0]==='b') && ['p', 'n', 'b', 'r', 'q', 'k'].includes(c[1].toLowerCase()));
            let sqClass = classes.find(c => c.startsWith('square-'));
            if (colorType && sqClass) {
                let file = parseInt(sqClass[7]);
                let rank = parseInt(sqClass[8]);
                let r = 8 - rank;
                let c = file - 1;
                let char = colorType[1];
                if (colorType[0] === 'w') char = char.toUpperCase();
                boardArray[r][c] = char;
            }
        });
        
        // Parse remaining time from bottom (player's) clock
        let timeLeft = 300; 
        let clockEl = document.querySelector('.clock-bottom .clock-time-monospace, .clock-bottom span, .clock-bottom');
        if (!clockEl) {
            let clocks = document.querySelectorAll('.clock-component');
            if (clocks.length > 0) {
                clockEl = clocks[clocks.length - 1];
            }
        }
        if (clockEl) {
            let timeText = clockEl.textContent.trim();
            if (timeText) {
                let parts = timeText.split(':');
                if (parts.length === 2) {
                    let min = parseInt(parts[0], 10);
                    let sec = parseFloat(parts[1]);
                    if (!isNaN(min) && !isNaN(sec)) timeLeft = min * 60 + sec;
                } else if (parts.length === 3) {
                    let hr = parseInt(parts[0], 10);
                    let min = parseInt(parts[1], 10);
                    let sec = parseFloat(parts[2]);
                    if (!isNaN(hr) && !isNaN(min) && !isNaN(sec)) timeLeft = hr * 3600 + min * 60 + sec;
                } else {
                    let sec = parseFloat(timeText);
                    if (!isNaN(sec)) timeLeft = sec;
                }
            }
        }
 
        sendBoardState(boardArray, is_white_bottom, timeLeft);
        
        // Loop recursively using native setTimeout
        let bulletSpeedDelay = Math.floor(Math.random() * 20) + 70;
        nativeSetTimeout(readBoardChessCom, bulletSpeedDelay);
    }

    // ====================================================================
    //  Lichess.org Board Reader
    // ====================================================================
    function readBoardLichess() {
        let boardArray = Array(8).fill("").map(() => Array(8).fill(""));

        // Lichess renders pieces as <piece> elements inside cg-board
        const cgBoard = document.querySelector('cg-board');
        if (!cgBoard) {
            nativeSetTimeout(readBoardLichess, 200);
            return;
        }

        const pieces = cgBoard.querySelectorAll('piece');
        if (!pieces.length) {
            nativeSetTimeout(readBoardLichess, 100);
            return;
        }

        // Detect board orientation: Lichess adds class 'orientation-white' or 'orientation-black' on parent
        let is_white_bottom = true;
        if (cached_is_white_bottom !== null && framesSinceOrientationCheck < 30) {
            is_white_bottom = cached_is_white_bottom;
            framesSinceOrientationCheck++;
        } else {
            framesSinceOrientationCheck = 0;
            const boardWrap = document.querySelector('.cg-wrap');
            if (boardWrap) {
                if (boardWrap.classList.contains('orientation-black')) {
                    is_white_bottom = false;
                } else {
                    is_white_bottom = true;
                }
            }
            cached_is_white_bottom = is_white_bottom;
        }

        // Get board dimensions for coordinate calculation
        const boardRect = cgBoard.getBoundingClientRect();
        const boardWidth = boardRect.width;
        const boardHeight = boardRect.height;
        const squareWidth = boardWidth / 8;
        const squareHeight = boardHeight / 8;

        // Piece class mapping for Lichess: class contains color (white/black) and role (king/queen/rook etc.)
        const roleMap = {
            'king': 'k', 'queen': 'q', 'rook': 'r',
            'bishop': 'b', 'knight': 'n', 'pawn': 'p'
        };

        pieces.forEach(p => {
            const classes = Array.from(p.classList);
            const isWhitePiece = classes.includes('white');
            const isBlackPiece = classes.includes('black');
            if (!isWhitePiece && !isBlackPiece) return;

            // Determine piece type from class
            let pieceChar = '';
            for (const [role, char] of Object.entries(roleMap)) {
                if (classes.includes(role)) {
                    pieceChar = isWhitePiece ? char.toUpperCase() : char;
                    break;
                }
            }
            if (!pieceChar) return;

            // Get position from CSS transform: translate(Xpx, Ypx)
            const style = p.style.transform || p.getAttribute('style') || '';
            const translateMatch = style.match(/translate\(\s*([\d.]+)px\s*,\s*([\d.]+)px\s*\)/);
            if (!translateMatch) return;

            const pixelX = parseFloat(translateMatch[1]);
            const pixelY = parseFloat(translateMatch[2]);

            // Convert pixel coordinates to board col/row (0-7)
            let col = Math.round(pixelX / squareWidth);
            let row = Math.round(pixelY / squareHeight);

            // Clamp to valid range
            col = Math.max(0, Math.min(7, col));
            row = Math.max(0, Math.min(7, row));

            // Lichess renders from white's perspective by default:
            // translate(0, 0) = a8, translate(7*sq, 7*sq) = h1
            // If black bottom, the coordinates are flipped
            if (!is_white_bottom) {
                col = 7 - col;
                row = 7 - row;
            }

            boardArray[row][col] = pieceChar;
        });

        // Parse remaining time from Lichess clocks
        let timeLeft = 300;
        // Lichess clock: bottom player's clock has class 'rclock-bottom' or the 2nd .rclock
        let clockEl = document.querySelector('.rclock-bottom .time, .rclock.rclock-bottom time');
        if (!clockEl) {
            // Fallback: try to find clocks by general selectors
            const clocks = document.querySelectorAll('.rclock time, .clock');
            if (clocks.length > 0) {
                clockEl = clocks[clocks.length - 1];
            }
        }
        if (clockEl) {
            let timeText = clockEl.textContent.trim();
            if (timeText) {
                let parts = timeText.split(':');
                if (parts.length === 2) {
                    let min = parseInt(parts[0], 10);
                    let sec = parseFloat(parts[1]);
                    if (!isNaN(min) && !isNaN(sec)) timeLeft = min * 60 + sec;
                } else if (parts.length === 3) {
                    let hr = parseInt(parts[0], 10);
                    let min = parseInt(parts[1], 10);
                    let sec = parseFloat(parts[2]);
                    if (!isNaN(hr) && !isNaN(min) && !isNaN(sec)) timeLeft = hr * 3600 + min * 60 + sec;
                } else {
                    let sec = parseFloat(timeText);
                    if (!isNaN(sec)) timeLeft = sec;
                }
            }
        }

        sendBoardState(boardArray, is_white_bottom, timeLeft);

        let bulletSpeedDelay = Math.floor(Math.random() * 20) + 70;
        nativeSetTimeout(readBoardLichess, bulletSpeedDelay);
    }

    // ====================================================================
    //  Shared: Throttled POST to Python backend
    // ====================================================================
    function sendBoardState(boardArray, is_white_bottom, timeLeft) {
        let matrixStr = JSON.stringify(boardArray);
        let timeDifference = lastSentTimeLeft !== null ? Math.abs(timeLeft - lastSentTimeLeft) : 999;
        
        let shouldSend = (matrixStr !== lastSentMatrixStr) || 
                         (is_white_bottom !== lastSentIsWhiteBottom) || 
                         (timeDifference >= 1.0);
                          
        if (shouldSend) {
            lastSentMatrixStr = matrixStr;
            lastSentIsWhiteBottom = is_white_bottom;
            lastSentTimeLeft = timeLeft;
            
            // Use native fetch to bypass page hooks
            nativeFetch("http://127.0.0.1:5005", {
                method: "POST",
                mode: "cors",
                credentials: "omit",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ 
                    matrix: boardArray, 
                    is_white_bottom: is_white_bottom,
                    time_left: timeLeft 
                })
            }).catch(e => {});
        }
    }

    // Start the appropriate reader based on hostname
    if (isLichess) {
        console.log("Chess Helper: Lichess.org detected. Starting Lichess reader.");
        readBoardLichess();
    } else {
        console.log("Chess Helper: Chess.com detected. Starting Chess.com reader.");
        readBoardChessCom();
    }
})();
