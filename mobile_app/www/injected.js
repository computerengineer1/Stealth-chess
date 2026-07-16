window.injectedStealthFunction = function() {
    if (window.__stealth_assistant_running) {
        console.log("Stealth Injected Script is already running.");
        return;
    }
    window.__stealth_assistant_running = true;
    console.log("Stealth Injected Script Loaded successfully!");

    // Use native setTimeout with iOS WKWebView fallback
    // iOS WKWebView blocks cross-origin iframe contentWindow access,
    // so we gracefully fall back to the global setTimeout if needed
    let nativeSetTimeout = window.setTimeout.bind(window);
    try {
        const frame = document.createElement('iframe');
        frame.style.display = 'none';
        frame.src = 'about:blank';
        document.documentElement.appendChild(frame);
        if (frame.contentWindow && frame.contentWindow.setTimeout) {
            nativeSetTimeout = frame.contentWindow.setTimeout.bind(frame.contentWindow);
        }
    } catch (e) {
        // iOS WKWebView security restriction — use global setTimeout
        console.log("Using fallback setTimeout for iOS compatibility.");
    }

    // Caching state to throttle WebView-to-App messages
    let cachedIsWhiteBottom = null;
    let framesSinceOrientationCheck = 0;
    let lastSentMatrixStr = "";
    let lastSentIsWhiteBottom = null;
    let lastSentTimeLeft = null;

    // Detect which chess platform the WebView is on
    const isLichess = window.location.hostname.includes("lichess.org");

    // ====================================================================
    //  Lichess.org Board Scanner
    // ====================================================================
    function scanLichessBoard() {
        try {
            const cgBoard = document.querySelector('cg-board');
            if (!cgBoard) {
                nativeSetTimeout(scanLichessBoard, 200);
                return;
            }

            // Sync DOM overlay position and size in real-time
            const rect = cgBoard.getBoundingClientRect();
            const domSvg = document.getElementById("stealth-board-overlay");
            if (domSvg && domSvg.style.display !== "none") {
                domSvg.style.width = rect.width + "px";
                domSvg.style.height = rect.height + "px";
                domSvg.style.left = (window.scrollX + rect.left) + "px";
                domSvg.style.top = (window.scrollY + rect.top) + "px";
                domSvg.setAttribute("width", rect.width);
                domSvg.setAttribute("height", rect.height);
            }

            const pieces = cgBoard.querySelectorAll('piece');
            if (!pieces.length) {
                nativeSetTimeout(scanLichessBoard, 100);
                return;
            }

            let isWhiteBottom = true;

            // Cache orientation check
            if (cachedIsWhiteBottom !== null && framesSinceOrientationCheck < 30) {
                isWhiteBottom = cachedIsWhiteBottom;
                framesSinceOrientationCheck++;
            } else {
                framesSinceOrientationCheck = 0;
                const boardWrap = document.querySelector('.cg-wrap');
                if (boardWrap) {
                    isWhiteBottom = !boardWrap.classList.contains('orientation-black');
                }
                cachedIsWhiteBottom = isWhiteBottom;
            }

            // Board pixel dimensions for coordinate conversion
            const boardWidth = rect.width;
            const boardHeight = rect.height;
            const squareWidth = boardWidth / 8;
            const squareHeight = boardHeight / 8;

            const roleMap = {
                'king': 'k', 'queen': 'q', 'rook': 'r',
                'bishop': 'b', 'knight': 'n', 'pawn': 'p'
            };

            let boardArray = Array(8).fill("").map(() => Array(8).fill(""));

            pieces.forEach(p => {
                const classes = Array.from(p.classList);
                const isWhitePiece = classes.includes('white');
                const isBlackPiece = classes.includes('black');
                if (!isWhitePiece && !isBlackPiece) return;

                let pieceChar = '';
                for (const [role, char] of Object.entries(roleMap)) {
                    if (classes.includes(role)) {
                        pieceChar = isWhitePiece ? char.toUpperCase() : char;
                        break;
                    }
                }
                if (!pieceChar) return;

                const style = p.style.transform || p.getAttribute('style') || '';
                const translateMatch = style.match(/translate\(\s*([\d.]+)px\s*,\s*([\d.]+)px\s*\)/);
                if (!translateMatch) return;

                const pixelX = parseFloat(translateMatch[1]);
                const pixelY = parseFloat(translateMatch[2]);

                let col = Math.round(pixelX / squareWidth);
                let row = Math.round(pixelY / squareHeight);
                col = Math.max(0, Math.min(7, col));
                row = Math.max(0, Math.min(7, row));

                if (!isWhiteBottom) {
                    col = 7 - col;
                    row = 7 - row;
                }

                boardArray[row][col] = pieceChar;
            });

            // Parse Lichess clock
            let timeLeft = 300;
            let clockEl = document.querySelector('.rclock-bottom .time, .rclock.rclock-bottom time');
            if (!clockEl) {
                const clocks = document.querySelectorAll('.rclock time, .clock');
                if (clocks.length > 0) {
                    clockEl = clocks[clocks.length - 1];
                }
            }
            if (clockEl) {
                const timeText = clockEl.textContent.trim();
                if (timeText) {
                    const parts = timeText.split(':');
                    if (parts.length === 2) {
                        const min = parseInt(parts[0], 10);
                        const sec = parseFloat(parts[1]);
                        if (!isNaN(min) && !isNaN(sec)) timeLeft = min * 60 + sec;
                    } else if (parts.length === 3) {
                        const hr = parseInt(parts[0], 10);
                        const min = parseInt(parts[1], 10);
                        const sec = parseFloat(parts[2]);
                        if (!isNaN(hr) && !isNaN(min) && !isNaN(sec)) timeLeft = hr * 3600 + min * 60 + sec;
                    } else {
                        const sec = parseFloat(timeText);
                        if (!isNaN(sec)) timeLeft = sec;
                    }
                }
            }

            // Throttle & send
            sendBoardPayload(boardArray, isWhiteBottom, timeLeft);

        } catch (err) {
            console.error("Lichess scan loop error:", err);
            try {
                const errorPayload = { type: "ERROR", message: "LichessScan: " + err.message, stack: err.stack };
                if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.cordova_iab) {
                    window.webkit.messageHandlers.cordova_iab.postMessage(JSON.stringify(errorPayload));
                }
            } catch (postErr) {}
        }

        const delay = Math.floor(Math.random() * 20) + 70;
        nativeSetTimeout(scanLichessBoard, delay);
    }

    // ====================================================================
    //  Shared payload sender (throttles messages to parent Capacitor app)
    // ====================================================================
    function sendBoardPayload(boardArray, isWhiteBottom, timeLeft) {
        const matrixStr = JSON.stringify(boardArray);
        const timeDiff = lastSentTimeLeft !== null ? Math.abs(timeLeft - lastSentTimeLeft) : 999;
        
        const shouldSend = (matrixStr !== lastSentMatrixStr) || 
                          (isWhiteBottom !== lastSentIsWhiteBottom) || 
                          (timeDiff >= 1.0);

        if (shouldSend) {
            lastSentMatrixStr = matrixStr;
            lastSentIsWhiteBottom = isWhiteBottom;
            lastSentTimeLeft = timeLeft;

            const payload = {
                type: "BOARD_STATE",
                matrix: boardArray,
                is_white_bottom: isWhiteBottom,
                time_left: timeLeft
            };

            if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.cordova_iab) {
                window.webkit.messageHandlers.cordova_iab.postMessage(JSON.stringify(payload));
            } else if (window.parent && window.parent !== window) {
                window.parent.postMessage(payload, "*");
            }
        }
    }

    // Main Chess.com scanning loop
    function scanChessBoard() {
        try {
            const boardElement = document.querySelector('wc-chess-board, chess-board, .board');
            if (!boardElement) {
                // Keep searching if board not loaded yet
                nativeSetTimeout(scanChessBoard, 200);
                return;
            }

            // Sync DOM overlay position and size in real-time
            const rect = boardElement.getBoundingClientRect();
            const domSvg = document.getElementById("stealth-board-overlay");
            if (domSvg && domSvg.style.display !== "none") {
                domSvg.style.width = rect.width + "px";
                domSvg.style.height = rect.height + "px";
                domSvg.style.left = (window.scrollX + rect.left) + "px";
                domSvg.style.top = (window.scrollY + rect.top) + "px";
                domSvg.setAttribute("width", rect.width);
                domSvg.setAttribute("height", rect.height);
            }

            const root = boardElement.shadowRoot || boardElement;
            const pieces = root.querySelectorAll('.piece, piece');
            if (!pieces.length) {
                nativeSetTimeout(scanChessBoard, 100);
                return;
            }

            let isWhiteBottom = true;

            // Cache orientation check to prevent layout reflows on getBoundingClientRect
            if (cachedIsWhiteBottom !== null && framesSinceOrientationCheck < 30) {
                isWhiteBottom = cachedIsWhiteBottom;
                framesSinceOrientationCheck++;
            } else {
                framesSinceOrientationCheck = 0;
                // Find a piece on rank 1, 2, 7, or 8 to determine board direction
                let anchorPiece = Array.from(pieces).find(p => {
                    const sqClass = Array.from(p.classList).find(c => c.startsWith('square-'));
                    if (sqClass) {
                        const coordPart = sqClass.replace('square-', '');
                        let rank = 0;
                        if (coordPart.length === 2) {
                            rank = parseInt(coordPart[1], 10);
                        } else if (coordPart.length === 4) {
                            rank = parseInt(coordPart.substring(2, 4), 10);
                        }
                        return rank >= 1 && rank <= 8 && (rank <= 2 || rank >= 7); 
                    }
                    return false;
                });

                if (anchorPiece) {
                    const sqClass = Array.from(anchorPiece.classList).find(c => c.startsWith('square-'));
                    const coordPart = sqClass.replace('square-', '');
                    let rank = 0;
                    if (coordPart.length === 2) {
                        rank = parseInt(coordPart[1], 10);
                    } else if (coordPart.length === 4) {
                        rank = parseInt(coordPart.substring(2, 4), 10);
                    }
                    const rect = anchorPiece.getBoundingClientRect();
                    const boardRect = boardElement.getBoundingClientRect();
                    const relativeY = (rect.top - boardRect.top) / boardRect.height;
                    const expectedY_WhiteBottom = (8 - rank) / 8;
                    const expectedY_BlackBottom = (rank - 1) / 8;
                    isWhiteBottom = Math.abs(relativeY - expectedY_WhiteBottom) < Math.abs(relativeY - expectedY_BlackBottom);
                    cachedIsWhiteBottom = isWhiteBottom;
                } else if (cachedIsWhiteBottom !== null) {
                    isWhiteBottom = cachedIsWhiteBottom;
                }
            }

            // Build 8x8 Board Matrix
            let boardArray = Array(8).fill("").map(() => Array(8).fill(""));
            pieces.forEach(p => {
                const classes = Array.from(p.classList);
                const colorType = classes.find(c => c.length === 2 && (c[0] === 'w' || c[0] === 'b') && ['p', 'n', 'b', 'r', 'q', 'k'].includes(c[1].toLowerCase()));
                const sqClass = classes.find(c => c.startsWith('square-'));
                if (colorType && sqClass) {
                    const coordPart = sqClass.replace('square-', '');
                    let file = 0, rank = 0;
                    if (coordPart.length === 2) {
                        file = parseInt(coordPart[0], 10);
                        rank = parseInt(coordPart[1], 10);
                    } else if (coordPart.length === 4) {
                        file = parseInt(coordPart.substring(0, 2), 10);
                        rank = parseInt(coordPart.substring(2, 4), 10);
                    }
                    
                    if (file >= 1 && file <= 8 && rank >= 1 && rank <= 8) {
                        const r = 8 - rank;
                        const c = file - 1;
                        let char = colorType[1];
                        if (colorType[0] === 'w') char = char.toUpperCase();
                        boardArray[r][c] = char;
                    }
                }
            });

            // Parse remaining time from player's clock (bottom clock)
            let timeLeft = 300;
            let clockEl = document.querySelector('.clock-bottom .clock-time-monospace, .clock-bottom span, .clock-bottom');
            if (!clockEl) {
                const clocks = document.querySelectorAll('.clock-component');
                if (clocks.length > 0) {
                    clockEl = clocks[clocks.length - 1]; // Player's clock is typically the last one
                }
            }
            if (clockEl) {
                const timeText = clockEl.textContent.trim();
                if (timeText) {
                    const parts = timeText.split(':');
                    if (parts.length === 2) {
                        const min = parseInt(parts[0], 10);
                        const sec = parseFloat(parts[1]);
                        if (!isNaN(min) && !isNaN(sec)) timeLeft = min * 60 + sec;
                    } else if (parts.length === 3) {
                        const hr = parseInt(parts[0], 10);
                        const min = parseInt(parts[1], 10);
                        const sec = parseFloat(parts[2]);
                        if (!isNaN(hr) && !isNaN(min) && !isNaN(sec)) timeLeft = hr * 3600 + min * 60 + sec;
                    } else {
                        const sec = parseFloat(timeText);
                        if (!isNaN(sec)) timeLeft = sec;
                    }
                }
            }

            // Use shared throttled payload sender
            sendBoardPayload(boardArray, isWhiteBottom, timeLeft);
        } catch (err) {
            console.error("Stealth scan loop error:", err);
            try {
                const errorPayload = {
                    type: "ERROR",
                    message: "Scan: " + err.message,
                    stack: err.stack
                };
                if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.cordova_iab) {
                    window.webkit.messageHandlers.cordova_iab.postMessage(JSON.stringify(errorPayload));
                }
            } catch (postErr) {}
        }

        // Schedule next scan recursion (matches Py speed ~70-90ms)
        const delay = Math.floor(Math.random() * 20) + 70;
        nativeSetTimeout(scanChessBoard, delay);
    }

    // SVG Overlay Draw Logic
    window.drawStealthOverlay = function(moves, isWhiteBottom, timeLeft, showArrows, showHud, stealthScreen) {
        window.__stealth_settings_arrows = showArrows;
        window.__stealth_settings_hud = showHud;
        window.__stealth_settings_secure = (stealthScreen !== false);

        if (window.__stealth_ui_hidden) {
            showArrows = false;
            showHud = false;
        }

        try {
            const boardElement = document.querySelector('wc-chess-board, chess-board, .board');
            if (!boardElement) return;

            const rect = boardElement.getBoundingClientRect();
            const rectData = { left: rect.left, top: rect.top, width: rect.width, height: rect.height };

            // If secure stealth screen is active, route all drawing to the native secure webview
            if (window.__stealth_settings_secure) {
                // Clear any DOM overlay that was previously drawn
                const root = boardElement.shadowRoot || boardElement;
                let svg = document.getElementById("stealth-board-overlay") || root.querySelector("#stealth-board-overlay");
                if (svg) svg.style.setProperty("display", "none", "important");
                let hud = document.getElementById("stealth-hud-card");
                if (hud) hud.style.setProperty("display", "none", "important");

                // Send to native secure overlay
                if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.cordova_iab) {
                    window.webkit.messageHandlers.cordova_iab.postMessage({
                        id: "stealth_draw_overlay",
                        d: JSON.stringify({
                            moves: moves,
                            isWhiteBottom: isWhiteBottom,
                            timeLeft: timeLeft,
                            showArrows: showArrows,
                            showHud: showHud,
                            rect: rectData,
                            secretHidden: !!window.__stealth_ui_hidden
                        })
                    });
                }
                return;
            }

            // Otherwise, we draw in the Chess.com DOM (making it visible in recordings/screenshots)
            // First, clear the native secure overlay by sending a blank state
            if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.cordova_iab) {
                window.webkit.messageHandlers.cordova_iab.postMessage({
                    id: "stealth_draw_overlay",
                    d: JSON.stringify({
                        moves: [],
                        isWhiteBottom: isWhiteBottom,
                        timeLeft: timeLeft,
                        showArrows: false,
                        showHud: false,
                        rect: rectData,
                        secretHidden: true
                    })
                });
            }

            const root = boardElement.shadowRoot || boardElement;
            // Clean up any old SVG that might still be inside the shadow root of the chessboard
            const oldSvg = root.querySelector("#stealth-board-overlay");
            if (oldSvg) {
                oldSvg.remove();
            }

            // 1. Create or Find SVG element in document.body
            let svg = document.getElementById("stealth-board-overlay");
            if (!svg) {
                svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
                svg.setAttribute("id", "stealth-board-overlay");
                svg.style.position = "absolute";
                svg.style.pointerEvents = "none";

                // Add SVG Shadow / Glow filter definitions
                const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
                defs.innerHTML = `
                    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
                        <feDropShadow dx="1" dy="2" stdDeviation="2" flood-color="black" flood-opacity="0.6"/>
                    </filter>
                    <filter id="glow-teal" x="-20%" y="-20%" width="140%" height="140%">
                        <feGaussianBlur stdDeviation="3" result="blur" />
                        <feComponentTransfer in="blur" result="glow1">
                            <feFuncA type="linear" slope="0.6"/>
                        </feComponentTransfer>
                        <feMerge>
                            <feMergeNode in="glow1" />
                            <feMergeNode in="SourceGraphic" />
                        </feMerge>
                    </filter>
                `;
                svg.appendChild(defs);
                document.body.appendChild(svg);
            }

            // Always update layout properties on every call in case the board resized or moved
            svg.style.width = rect.width + "px";
            svg.style.height = rect.height + "px";
            svg.style.left = (window.scrollX + rect.left) + "px";
            svg.style.top = (window.scrollY + rect.top) + "px";
            svg.setAttribute("width", rect.width);
            svg.setAttribute("height", rect.height);
            svg.style.zIndex = "99999";

            // Clean previous arrows, highlights, and annotations
            while (svg.childNodes.length > 1) {
                svg.removeChild(svg.lastChild);
            }

            if (showArrows === false) {
                svg.style.display = "none";
                drawGameHud(moves, timeLeft, showHud);
                return;
            } else {
                svg.style.display = "block";
            }

            // Helper calculations
            const sqW = rect.width / 8;
            const sqH = rect.height / 8;

            function sqToCoords(sq) {
                const colChar = sq[0];
                const rankChar = sq[1];
                let col = colChar.charCodeAt(0) - 97;
                let row = 8 - parseInt(rankChar, 10);
                if (!isWhiteBottom) {
                    col = 7 - col;
                    row = 7 - row;
                }
                const x = col * sqW + sqW / 2;
                const y = row * sqH + sqH / 2;
                return { x, y, col, row };
            }

            // Parse moves and compare evaluations
            let parsedScores = [];
            let bestScoreVal = 0.0;

            moves.forEach((m, idx) => {
                let val = 0.0;
                let isMate = false;
                if (m.score.includes("M")) {
                    isMate = true;
                    val = m.score.includes("-") ? -1000.0 : 1000.0;
                } else {
                    val = parseFloat(m.score) || 0.0;
                }
                parsedScores.push({ val, isMate });
            });

            if (parsedScores.length > 0) {
                bestScoreVal = parsedScores[0].val;
            }

            // Render moves in reverse order so best move paints on top
            for (let idx = moves.length - 1; idx >= 0; idx--) {
                const m = moves[idx];
                const moveUci = m.move;
                if (moveUci.length < 4) continue;

                const scoreVal = parsedScores[idx].val;
                const isMate = parsedScores[idx].isMate;

                // Classify move quality & colors
                let color = "rgba(240, 150, 20, 0.7)";
                let strokeWidth = idx === 0 ? 5.5 : 3.5;
                let markerSize = idx === 0 ? 17 : 13;

                if (isMate) {
                    color = "rgba(138, 43, 226, 0.8)";
                } else if (idx === 0) {
                    if (scoreVal >= 3.5) {
                        color = "rgba(27, 172, 166, 0.85)";
                    } else {
                        color = "rgba(38, 187, 92, 0.85)";
                    }
                } else {
                    const diff = Math.abs(bestScoreVal - scoreVal);
                    if (diff >= 2.0) {
                        color = "rgba(235, 60, 60, 0.85)";
                    } else if (diff >= 1.0) {
                        color = "rgba(240, 100, 40, 0.75)";
                    } else if (diff <= 0.35) {
                        color = "rgba(149, 183, 33, 0.8)";
                    }
                }

                const fromSq = moveUci.substring(0, 2);
                const toSq = moveUci.substring(2, 4);
                const fromC = sqToCoords(fromSq);
                const toC = sqToCoords(toSq);

                // A. Draw square highlights
                const startHighlight = document.createElementNS("http://www.w3.org/2000/svg", "rect");
                startHighlight.setAttribute("x", (fromC.col * sqW + 3).toString());
                startHighlight.setAttribute("y", (fromC.row * sqH + 3).toString());
                startHighlight.setAttribute("width", (sqW - 6).toString());
                startHighlight.setAttribute("height", (sqH - 6).toString());
                startHighlight.setAttribute("rx", "6");
                startHighlight.setAttribute("fill", color);
                startHighlight.setAttribute("fill-opacity", idx === 0 ? "0.15" : "0.08");
                startHighlight.setAttribute("stroke", color);
                startHighlight.setAttribute("stroke-width", idx === 0 ? "2" : "1.2");
                svg.appendChild(startHighlight);

                const endHighlight = document.createElementNS("http://www.w3.org/2000/svg", "rect");
                endHighlight.setAttribute("x", (toC.col * sqW + 3).toString());
                endHighlight.setAttribute("y", (toC.row * sqH + 3).toString());
                endHighlight.setAttribute("width", (sqW - 6).toString());
                endHighlight.setAttribute("height", (sqH - 6).toString());
                endHighlight.setAttribute("rx", "6");
                endHighlight.setAttribute("fill", color);
                endHighlight.setAttribute("fill-opacity", idx === 0 ? "0.15" : "0.08");
                endHighlight.setAttribute("stroke", color);
                endHighlight.setAttribute("stroke-width", idx === 0 ? "2" : "1.2");
                svg.appendChild(endHighlight);

                // B. Draw arrows
                const dx = toC.x - fromC.x;
                const dy = toC.y - fromC.y;
                const length = Math.hypot(dx, dy);
                if (length < 1) continue;

                const ux = dx / length;
                const uy = dy / length;
                const paddingStart = 10;
                const paddingEnd = 24;
                const startX = fromC.x + ux * paddingStart;
                const startY = fromC.y + uy * paddingStart;
                const endX = fromC.x + ux * (length - paddingEnd);
                const endY = fromC.y + uy * (length - paddingEnd);

                // Shadow shaft
                const shadowLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
                shadowLine.setAttribute("x1", startX.toString());
                shadowLine.setAttribute("y1", startY.toString());
                shadowLine.setAttribute("x2", endX.toString());
                shadowLine.setAttribute("y2", endY.toString());
                shadowLine.setAttribute("stroke", "black");
                shadowLine.setAttribute("stroke-opacity", "0.4");
                shadowLine.setAttribute("stroke-width", (strokeWidth + 3.5).toString());
                shadowLine.setAttribute("stroke-linecap", "round");
                svg.appendChild(shadowLine);

                // Main arrow shaft
                const mainLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
                mainLine.setAttribute("x1", startX.toString());
                mainLine.setAttribute("y1", startY.toString());
                mainLine.setAttribute("x2", endX.toString());
                mainLine.setAttribute("y2", endY.toString());
                mainLine.setAttribute("stroke", color);
                mainLine.setAttribute("stroke-width", strokeWidth.toString());
                mainLine.setAttribute("stroke-linecap", "round");
                svg.appendChild(mainLine);

                // Arrow Head Triangle
                const p1x = endX;
                const p1y = endY;
                const p2x = endX - ux * markerSize + (-uy) * (markerSize * 0.65);
                const p2y = endY - uy * markerSize + ux * (markerSize * 0.65);
                const p3x = endX - ux * markerSize - (-uy) * (markerSize * 0.65);
                const p3y = endY - uy * markerSize - ux * (markerSize * 0.65);

                const arrowHeadShadow = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
                arrowHeadShadow.setAttribute("points", `${p1x+1},${p1y+1.5} ${p2x+1},${p2y+1.5} ${p3x+1},${p3y+1.5}`);
                arrowHeadShadow.setAttribute("fill", "black");
                arrowHeadShadow.setAttribute("fill-opacity", "0.4");
                svg.appendChild(arrowHeadShadow);

                const arrowHead = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
                arrowHead.setAttribute("points", `${p1x},${p1y} ${p2x},${p2y} ${p3x},${p3y}`);
                arrowHead.setAttribute("fill", color);
                svg.appendChild(arrowHead);

                // Draw start dot node
                const startDot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                startDot.setAttribute("cx", startX.toString());
                startDot.setAttribute("cy", startY.toString());
                startDot.setAttribute("r", (strokeWidth * 1.1).toString());
                startDot.setAttribute("fill", color);
                startDot.setAttribute("stroke", "white");
                startDot.setAttribute("stroke-width", "1");
                svg.appendChild(startDot);
            }

            // 2. Render In-Game HUD Dashboard
            drawGameHud(moves, timeLeft, showHud);
        } catch (err) {
            console.error("Stealth overlay draw error:", err);
            try {
                const errorPayload = {
                    type: "ERROR",
                    message: "Draw Overlay: " + err.message,
                    stack: err.stack
                };
                if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.cordova_iab) {
                    window.webkit.messageHandlers.cordova_iab.postMessage(JSON.stringify(errorPayload));
                }
            } catch (postErr) {}
        }
    };

    // HTML Mobile HUD Overlay
    function drawGameHud(moves, timeLeft, showHud) {
        let hud = document.getElementById("stealth-hud-card");
        if (showHud === false) {
            if (hud) hud.style.setProperty("display", "none", "important");
            return;
        } else {
            if (hud) hud.style.setProperty("display", "flex", "important");
        }
        if (!hud) {
            hud = document.createElement("div");
            hud.setAttribute("id", "stealth-hud-card");
            Object.assign(hud.style, {
                position: "fixed",
                bottom: "12px",
                left: "12px",
                right: "12px",
                backgroundColor: "rgba(15, 15, 20, 0.9)",
                border: "1.5px solid rgba(27, 172, 166, 0.8)",
                borderRadius: "12px",
                padding: "10px 14px",
                color: "#ffffff",
                fontFamily: "'Segoe UI', Arial, sans-serif",
                fontSize: "12px",
                zIndex: "999999",
                boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
                display: "flex",
                flexDirection: "column",
                gap: "8px",
                backdropFilter: "blur(8px)",
                webkitBackdropFilter: "blur(8px)"
            });
            document.body.appendChild(hud);
        }

        // Adjust HUD border based on remaining time
        let borderColor = "rgba(27, 172, 166, 0.8)";
        let timeColor = "#2ecc71";
        let timeState = "SAFE";

        if (timeLeft <= 15) {
            borderColor = "rgba(235, 60, 60, 0.9)";
            timeColor = "#ff4f4f";
            timeState = "PANIC!";
        } else if (timeLeft <= 60) {
            borderColor = "rgba(240, 150, 20, 0.85)";
            timeColor = "#f39c12";
            timeState = "WARNING";
        }
        hud.style.borderColor = borderColor;

        // Best move evaluation score
        let bestScore = "0.00";
        if (moves.length > 0) {
            bestScore = moves[0].score;
        }
        let scoreVal = parseFloat(bestScore) || 0.0;
        let isMate = bestScore.includes("M");

        // Vertical white/black power bar calculation
        let barRatio = 50;
        if (isMate) {
            barRatio = bestScore.includes("-") ? 5 : 95;
        } else {
            let clamped = Math.max(-5.0, Math.min(5.0, scoreVal));
            barRatio = ((clamped + 5.0) / 10.0) * 100;
        }

        // Format Clock
        const m = Math.floor(timeLeft / 60);
        const s = Math.floor(timeLeft % 60);
        const clockStr = `${m.toString().padStart(2,'0')}:${s.toString().padStart(2,'0')}`;

        // Construct HTML content inside HUD
        let candidateRowsHtml = "";
        moves.forEach((item, index) => {
            let badgeText = "GOOD";
            let badgeBg = "rgba(240, 150, 20, 0.15)";
            let badgeColor = "#f39c12";

            if (item.score.includes("M")) {
                badgeText = "MATE";
                badgeBg = "rgba(138, 43, 226, 0.2)";
                badgeColor = "#9b59b6";
            } else if (index === 0) {
                if (scoreVal >= 3.5) {
                    badgeText = "BRILLIANT";
                    badgeBg = "rgba(27, 172, 166, 0.2)";
                    badgeColor = "#1abc9c";
                } else {
                    badgeText = "BEST";
                    badgeBg = "rgba(46, 187, 92, 0.2)";
                    badgeColor = "#2ecc71";
                }
            } else {
                let firstVal = parseFloat(moves[0].score) || 0.0;
                let currentVal = parseFloat(item.score) || 0.0;
                let diff = Math.abs(firstVal - currentVal);
                if (diff >= 2.0) {
                    badgeText = "BLUNDER";
                    badgeBg = "rgba(235, 60, 60, 0.2)";
                    badgeColor = "#e74c3c";
                } else if (diff >= 1.0) {
                    badgeText = "INACCURACY";
                    badgeBg = "rgba(240, 100, 40, 0.2)";
                    badgeColor = "#e67e22";
                } else if (diff <= 0.35) {
                    badgeText = "EXCELLENT";
                    badgeBg = "rgba(149, 183, 33, 0.2)";
                    badgeColor = "#a0d468";
                }
            }

            candidateRowsHtml += `
                <div style="display:flex; justify-content:space-between; align-items:center; background-color:rgba(255,255,255,0.03); padding:4px 8px; border-radius:4px;">
                    <div style="display:flex; align-items:center; gap:6px;">
                        <span style="width:5px; height:5px; border-radius:50%; background-color:${badgeColor};"></span>
                        <strong style="color:#e4e4e7;">${index+1}. ${item.move}</strong>
                        <span style="color:#8a8a93; font-size:10px;">(${item.score})</span>
                    </div>
                    <span style="font-size:9px; font-weight:bold; background-color:${badgeBg}; color:${badgeColor}; padding:2px 6px; border-radius:3px;">${badgeText}</span>
                </div>
            `;
        });

        hud.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:6px; margin-bottom:4px;">
                <span style="font-weight:bold; letter-spacing:0.5px; color:#ff3333;">🛡️ STEALTH ASSISTANT HUD</span>
                <span style="font-size:10px; color:#8a8a93;">TIME: <strong style="color:${timeColor}">${clockStr}</strong></span>
            </div>
            
            <div style="display:flex; gap:12px; align-items:center;">
                <!-- Vertical Power Bar -->
                <div style="width:10px; height:60px; background-color:#2a2a2f; border-radius:3px; position:relative; border:1px solid rgba(255,255,255,0.1); overflow:hidden;">
                    <div style="position:absolute; bottom:0; left:0; width:100%; height:${barRatio}%; background-color:#ececec; transition:height 0.3s;"></div>
                </div>

                <!-- Live Eval Panel -->
                <div style="flex:1; display:flex; flex-direction:column; gap:4px;">
                    <div style="display:flex; justify-content:space-between;">
                        <span style="color:#8a8a93;">Evaluation:</span>
                        <strong style="color:${scoreVal >= 0 ? '#2ecc71' : '#ff4f4f'}">${scoreVal > 0 ? '+' : ''}${bestScore}</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between;">
                        <span style="color:#8a8a93;">Panic Mode:</span>
                        <span style="font-weight:bold; color:${timeColor}">${timeState}</span>
                    </div>
                </div>
            </div>

            <!-- Candidate list -->
            <div style="display:flex; flex-direction:column; gap:4px; margin-top:2px;">
                ${candidateRowsHtml}
            </div>
        `;
    }

    // Secret Gesture to toggle UI visibility (Triple-tap)
    let lastTap = 0;
    let tapCount = 0;
    window.__stealth_ui_hidden = false;

    function handleTapGesture(e) {
        // If the tap target is inside the chess board, a piece, or a coordinate square, ignore it
        if (e.target && typeof e.target.closest === "function") {
            if (e.target.closest('wc-chess-board, chess-board, .board, .piece, [class*="square-"]')) {
                return;
            }
        }

        const now = Date.now();
        if (now - lastTap < 450) {
            tapCount++;
            if (tapCount === 3) {
                window.__stealth_ui_hidden = !window.__stealth_ui_hidden;
                console.log("Secret Gesture: Toggled UI hidden to", window.__stealth_ui_hidden);

                const boardElement = document.querySelector('wc-chess-board, chess-board, .board');
                const overlayRoot = boardElement ? (boardElement.shadowRoot || boardElement) : document;
                const svg = document.getElementById("stealth-board-overlay") || overlayRoot.querySelector("#stealth-board-overlay");
                const hud = document.getElementById("stealth-hud-card");

                if (window.__stealth_ui_hidden) {
                    if (hud) hud.style.setProperty("display", "none", "important");
                    if (svg) svg.style.setProperty("display", "none", "important");
                } else {
                    if (hud && window.__stealth_settings_hud !== false) hud.style.setProperty("display", "flex", "important");
                    if (svg && window.__stealth_settings_arrows !== false) svg.style.setProperty("display", "block", "important");
                }
                tapCount = 0;
            }
        } else {
            tapCount = 1;
        }
        lastTap = now;
    }

    document.addEventListener("click", handleTapGesture);
    document.addEventListener("touchstart", handleTapGesture);

    // Start the appropriate scanner based on hostname
    if (isLichess) {
        console.log("Stealth: Lichess.org detected. Starting Lichess scanner.");
        scanLichessBoard();
    } else {
        console.log("Stealth: Chess.com detected. Starting Chess.com scanner.");
        scanChessBoard();
    }
};
