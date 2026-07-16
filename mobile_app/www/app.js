// Stealth Chess Assistant - Mobile Controller Logic

// Configuration & Default State
const Config = {
    LICENSE_API_URL: "https://gist.githubusercontent.com/computerengineer1/c6b0466a666549755c0c149fbff7dbdd/raw/db.txt",
    SECRET_KEY: "STEALTH_CHESS_SECRET_KEY_2026",
    STOCKFISH_URL: "stockfish-18-lite-single.js"
};

// Generate or retrieve a persistent unique Device ID for this phone
function getDeviceId() {
    let deviceId = localStorage.getItem("device_id");
    if (!deviceId) {
        // Generate a random UUID-style device fingerprint
        deviceId = 'MOB-' + 'xxxx-xxxx-xxxx'.replace(/x/g, () => {
            return Math.floor(Math.random() * 16).toString(16).toUpperCase();
        });
        localStorage.setItem("device_id", deviceId);
    }
    return deviceId;
}

let appState = {
    licenseKey: "",
    isValidLicense: false,
    expiryDate: "N/A",
    tier: "N/A",
    
    // Engine Config
    gameMode: "blitz",
    engineDepth: 10,
    engineSkill: 15,
    randomizeMoves: true,
    engineThreads: 2,
    showArrows: true,
    showHud: true,
    stealthScreen: true,
    fullscreenMode: true,
    
    // Active Assistant State
    isBotRunning: false
};

// Chess turn tracking
let isWhiteTurn = true;
let lastMatrix = null;
let lastFen = "";
let pendingMoves = null;
let showMovesTimeout = null;

// Stockfish Web Worker instance
let stockfishWorker = null;
let isStockfishReady = false;
let currentSearchCallback = null;

// InAppBrowser Reference
let chessWebView = null;

// Initialize app when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
    loadSettings();
    initUI();
    checkStoredLicense();

    // Display Device ID on activation screen
    const deviceIdBox = document.getElementById("device-id-display");
    if (deviceIdBox) {
        const myDeviceId = getDeviceId();
        deviceIdBox.textContent = myDeviceId;
        deviceIdBox.addEventListener("click", () => {
            if (navigator.clipboard) {
                navigator.clipboard.writeText(myDeviceId).then(() => {
                    deviceIdBox.style.borderColor = "#00ff88";
                    deviceIdBox.textContent = "✅ Copied!";
                    setTimeout(() => {
                        deviceIdBox.textContent = myDeviceId;
                        deviceIdBox.style.borderColor = "rgba(255,165,0,0.4)";
                    }, 1500);
                });
            }
        });
    }

    // Beautiful Splash Screen transition logic (fade out after 2.2s)
    setTimeout(() => {
        const splash = document.getElementById("splash-screen");
        if (splash) {
            splash.classList.add("fade-out");
            setTimeout(() => splash.remove(), 600); // Clean up DOM after transition
        }
    }, 2200);
});

// Load Settings from LocalStorage
function loadSettings() {
    appState.licenseKey = localStorage.getItem("license_key") || "";
    appState.gameMode = localStorage.getItem("game_mode") || "blitz";
    appState.engineDepth = parseInt(localStorage.getItem("engine_depth")) || 10;
    appState.engineSkill = parseInt(localStorage.getItem("engine_skill")) || 15;
    appState.randomizeMoves = localStorage.getItem("randomize_moves") !== "false";
    appState.engineThreads = parseInt(localStorage.getItem("engine_threads")) || 2;
    appState.showArrows = localStorage.getItem("show_arrows") !== "false";
    appState.showHud = localStorage.getItem("show_hud") !== "false";
    appState.stealthScreen = localStorage.getItem("stealth_screen") !== "false";
    appState.fullscreenMode = localStorage.getItem("fullscreen_mode") !== "false";
}

// Save Settings to LocalStorage
function saveSettings() {
    localStorage.setItem("game_mode", appState.gameMode);
    localStorage.setItem("engine_depth", appState.engineDepth);
    localStorage.setItem("engine_skill", appState.engineSkill);
    localStorage.setItem("randomize_moves", appState.randomizeMoves);
    localStorage.setItem("engine_threads", appState.engineThreads);
    localStorage.setItem("show_arrows", appState.showArrows);
    localStorage.setItem("show_hud", appState.showHud);
    localStorage.setItem("stealth_screen", appState.stealthScreen);
    localStorage.setItem("fullscreen_mode", appState.fullscreenMode);
}

// XOR Encryption/Decryption matching python implementation
function xorEncryptDecrypt(data, key) {
    const keyLen = key.length;
    let output = [];
    for (let i = 0; i < data.length; i++) {
        const charCode = data.charCodeAt(i) ^ key.charCodeAt(i % keyLen);
        output.push(String.fromCharCode(charCode));
    }
    return output.join("");
}

// Verify Subscription License Key
async function verifyLicense(key, forceSave = true) {
    key = key.trim();
    if (!key) {
        return { success: false, message: "Key cannot be empty (المفتاح مطلوب)" };
    }



    try {
        const response = await fetch(Config.LICENSE_API_URL, { cache: "no-store" });
        if (!response.ok) {
            return { success: false, message: `Server error: ${response.status} (فشل الاتصال)` };
        }
        const payload = await response.text();
        
        // Base64 decode, then XOR decrypt
        const decodedBytes = atob(payload.trim());
        const decryptedJson = xorEncryptDecrypt(decodedBytes, Config.SECRET_KEY);
        const db = JSON.parse(decryptedJson);
        
        const keysDict = db.keys || {};
        if (!(key in keysDict)) {
            return { success: false, message: "Invalid license key (مفتاح ترخيص غير صحيح)" };
        }

        const keyInfo = keysDict[key];
        const expiryStr = keyInfo.expiry || "2026-05-22";
        const tierStr = keyInfo.tier || "Active";
        const allowedMobileHwid = keyInfo.mobile_hwid || "";

        // --- Mobile Device ID Lock Check ---
        if (allowedMobileHwid && allowedMobileHwid.trim() !== "") {
            const currentDeviceId = getDeviceId();
            if (allowedMobileHwid.trim().toUpperCase() !== currentDeviceId.toUpperCase()) {
                return { success: false, message: "Device lock mismatch. Key is registered to another phone. (المفتاح مسجل على جهاز آخر)" };
            }
        }
        
        const expiryDate = new Date(expiryStr);
        const currentDate = new Date();
        
        // Strip hours for pure date comparison
        expiryDate.setHours(0,0,0,0);
        currentDate.setHours(0,0,0,0);

        if (currentDate > expiryDate) {
            return { success: false, message: `Subscription expired on ${expiryStr} (انتهى الاشتراك)` };
        }

        appState.isValidLicense = true;
        appState.tier = tierStr;
        appState.expiryDate = expiryStr;
        appState.licenseKey = key;
        
        if (forceSave) localStorage.setItem("license_key", key);
        return { success: true };

    } catch (e) {
        console.error("License validation error:", e);
        return { success: false, message: "Verification failed (فشل التحقق من الشبكة)" };
    }
}

// Auto check stored key on startup
async function checkStoredLicense() {
    if (appState.licenseKey) {
        showStatus("Verifying saved subscription... (جاري التحقق)", "info");
        const res = await verifyLicense(appState.licenseKey, false);
        if (res.success) {
            unlockDashboard();
        } else {
            showStatus(res.message, "error");
            localStorage.removeItem("license_key");
            appState.licenseKey = "";
        }
    }
}

// UI Elements & State Binding
function initUI() {
    // 1. Activation View Elements
    const keyInput = document.getElementById("license-key-input");
    const activateBtn = document.getElementById("activate-btn");
    
    if (appState.licenseKey) {
        keyInput.value = appState.licenseKey;
    }

    activateBtn.addEventListener("click", async () => {
        const key = keyInput.value.trim();
        activateBtn.disabled = true;
        showStatus("Checking license database... (جاري التحقق)", "info");
        
        const res = await verifyLicense(key);
        if (res.success) {
            showStatus("License Validated! Unlocking dashboard...", "success");
            setTimeout(() => {
                unlockDashboard();
                activateBtn.disabled = false;
            }, 1000);
        } else {
            showStatus(res.message, "error");
            activateBtn.disabled = false;
        }
    });

    // 2. Change Key / Logout
    document.getElementById("change-key-btn").addEventListener("click", () => {
        localStorage.removeItem("license_key");
        appState.licenseKey = "";
        appState.isValidLicense = false;
        
        document.getElementById("dashboard-view").classList.add("hidden");
        document.getElementById("activation-view").classList.remove("hidden");
        showStatus("Please enter your activation key.", "info");
    });

    // 3. Settings controls in Dashboard
    const selectMode = document.getElementById("select-game-mode");
    selectMode.value = appState.gameMode;
    selectMode.addEventListener("change", (e) => {
        appState.gameMode = e.target.value;
        saveSettings();
    });

    const sliderDepth = document.getElementById("slider-depth");
    const valDepth = document.getElementById("val-depth");
    sliderDepth.value = appState.engineDepth;
    valDepth.textContent = appState.engineDepth;
    sliderDepth.addEventListener("input", (e) => {
        appState.engineDepth = parseInt(e.target.value);
        valDepth.textContent = appState.engineDepth;
        saveSettings();
        if (isStockfishReady) configureStockfish();
    });

    const sliderSkill = document.getElementById("slider-skill");
    const valSkill = document.getElementById("val-skill");
    sliderSkill.value = appState.engineSkill;
    valSkill.textContent = appState.engineSkill;
    sliderSkill.addEventListener("input", (e) => {
        appState.engineSkill = parseInt(e.target.value);
        valSkill.textContent = appState.engineSkill;
        updateEloDisplay();
        saveSettings();
        if (isStockfishReady) configureStockfish();
    });
    updateEloDisplay();

    const chkAntiban = document.getElementById("chk-antiban");
    chkAntiban.checked = appState.randomizeMoves;
    chkAntiban.addEventListener("change", (e) => {
        appState.randomizeMoves = e.target.checked;
        saveSettings();
    });

    const chkShowArrows = document.getElementById("chk-show-arrows");
    chkShowArrows.checked = appState.showArrows;
    chkShowArrows.addEventListener("change", (e) => {
        appState.showArrows = e.target.checked;
        saveSettings();
    });

    const chkShowHud = document.getElementById("chk-show-hud");
    chkShowHud.checked = appState.showHud;
    chkShowHud.addEventListener("change", (e) => {
        appState.showHud = e.target.checked;
        saveSettings();
    });

    const chkFullscreen = document.getElementById("chk-fullscreen");
    chkFullscreen.checked = appState.fullscreenMode;
    chkFullscreen.addEventListener("change", (e) => {
        appState.fullscreenMode = e.target.checked;
        saveSettings();
    });

    const chkStealthScreen = document.getElementById("chk-stealth-screen");
    chkStealthScreen.checked = appState.stealthScreen;
    chkStealthScreen.addEventListener("change", (e) => {
        appState.stealthScreen = e.target.checked;
        saveSettings();
    });

    const inputThreads = document.getElementById("input-threads");
    inputThreads.value = appState.engineThreads;
    
    document.getElementById("btn-spin-down").addEventListener("click", () => {
        let val = parseInt(inputThreads.value);
        if (val > 1) {
            val--;
            inputThreads.value = val;
            appState.engineThreads = val;
            saveSettings();
            if (isStockfishReady) configureStockfish();
        }
    });
    document.getElementById("btn-spin-up").addEventListener("click", () => {
        let val = parseInt(inputThreads.value);
        if (val < 16) {
            val++;
            inputThreads.value = val;
            appState.engineThreads = val;
            saveSettings();
            if (isStockfishReady) configureStockfish();
        }
    });

    // 4. Start Assistant Button
    const startBtn = document.getElementById("start-bot-btn");
    startBtn.addEventListener("click", () => {
        if (!appState.isBotRunning) {
            startBot();
        }
    });
}

const SkillToElo = {
    1: 800, 2: 900, 3: 1000, 4: 1100, 5: 1200,
    6: 1300, 7: 1400, 8: 1500, 9: 1600, 10: 1700,
    11: 1850, 12: 2000, 13: 2150, 14: 2300, 15: 2450,
    16: 2600, 17: 2750, 18: 2900, 19: 3050, 20: 3200
};

function updateEloDisplay() {
    const elo = SkillToElo[appState.engineSkill] || 2000;
    document.getElementById("val-elo").textContent = `~${elo} ELO`;
}

function showStatus(msg, type) {
    const el = document.getElementById("activation-status");
    el.textContent = msg;
    el.className = "status-msg";
    if (type === "success") el.style.color = "var(--success-green)";
    else if (type === "info") el.style.color = "var(--text-muted)";
    else el.style.color = "var(--danger-red)";
}

function addLiveLog(msg, type = "info") {
    const consoleEl = document.getElementById("live-logs-console");
    if (!consoleEl) return;
    
    const div = document.createElement("div");
    let color = "#a0aec0"; // default gray
    if (type === "success") color = "#48bb78"; // green
    else if (type === "error") color = "#f56565"; // red
    else if (type === "warning") color = "#ed8936"; // orange
    else if (type === "engine") color = "#38b2ac"; // teal
    
    div.style.color = color;
    const timeStr = new Date().toTimeString().split(' ')[0];
    div.textContent = `[${timeStr}] ${msg}`;
    consoleEl.appendChild(div);
    consoleEl.scrollTop = consoleEl.scrollHeight;
}

function unlockDashboard() {
    document.getElementById("lbl-license-status").textContent = `🟢 Subscription Active (${appState.tier.toUpperCase()})`;
    document.getElementById("lbl-expiry").textContent = `Expiration: ${appState.expiryDate}`;
    
    document.getElementById("activation-view").classList.add("hidden");
    document.getElementById("dashboard-view").classList.remove("hidden");
    
    // Initialize Stockfish WASM in background
    initStockfish();
}

// Initialize Stockfish WASM Web Worker
function initStockfish() {
    if (stockfishWorker) return;
    
    console.log("Initializing Stockfish Web Worker...");
    addLiveLog("Initializing Stockfish worker...", "info");

    function createWorker(useBlob) {
        try {
            if (useBlob) {
                addLiveLog("Attempting Blob worker creation fallback...", "warning");
                const absoluteJsUrl = new URL(Config.STOCKFISH_URL, window.location.href).href;
                const absoluteWasmUrl = new URL(Config.STOCKFISH_URL.replace(".js", ".wasm"), window.location.href).href;
                const workerBlobCode = `
                    self.Module = {
                        locateFile: function(path) {
                            if (path.endsWith('.wasm')) {
                                return "${absoluteWasmUrl}";
                            }
                            return path;
                        }
                    };
                    importScripts("${absoluteJsUrl}");
                `;
                const blob = new Blob([workerBlobCode], { type: "application/javascript" });
                stockfishWorker = new Worker(URL.createObjectURL(blob));
            } else {
                stockfishWorker = new Worker(Config.STOCKFISH_URL);
                addLiveLog("Stockfish worker created directly.", "success");
            }
            
            stockfishWorker.onmessage = (event) => {
                const line = event.data;
                if (typeof line !== 'string') return;
                // Suppress verbose output to keep console clean, but parse evaluations
                if (line.includes("info depth") && line.includes(" pv ")) {
                    parseSearchInfo(line);
                } else if (line.startsWith("bestmove")) {
                    isSearching = false;
                    if (pendingSearch) {
                        const next = pendingSearch;
                        pendingSearch = null;
                        setTimeout(() => {
                            triggerSearch(next.fen, next.isWhiteBottom, next.timeLeft);
                        }, 10);
                    } else if (currentSearchCallback) {
                        currentSearchCallback();
                    }
                } else if (line === "readyok" || line.includes("uciok")) {
                    isStockfishReady = true;
                    console.log("Stockfish is ready to calculate moves.");
                    addLiveLog("Stockfish ready to calculate.", "success");
                }
            };

            stockfishWorker.onerror = (err) => {
                console.error("Stockfish Worker Error:", err);
                addLiveLog("Stockfish worker error: " + (err.message || "Load failed"), "error");
                
                // If direct worker failed asynchronously on startup, try Blob worker fallback once!
                if (!useBlob && !isStockfishReady) {
                    addLiveLog("Direct worker failed. Switching to Blob fallback...", "warning");
                    stockfishWorker.terminate();
                    stockfishWorker = null;
                    createWorker(true);
                }
            };

            // Initialize UCI communication
            stockfishWorker.postMessage("uci");
            configureStockfish();
            stockfishWorker.postMessage("isready");

        } catch (e) {
            console.error("Worker creation exception:", e);
            addLiveLog("Worker creation failed: " + e.message, "error");
            if (!useBlob) {
                createWorker(true);
            } else {
                // Final fallback: mark as ready so user can at least open the browser
                isStockfishReady = true;
            }
        }
    }

    // Start by trying direct worker creation
    createWorker(false);

    // Fallback: If Stockfish doesn't respond within 5 seconds,
    // force-mark it as ready so the user isn't stuck forever.
    setTimeout(() => {
        if (!isStockfishReady && stockfishWorker) {
            console.warn("Stockfish readyok not received in time. Forcing ready state.");
            isStockfishReady = true;
            addLiveLog("Stockfish readyok timeout. Forced ready.", "warning");
        }
    }, 5000);
}

// Update settings inside Stockfish engine
function configureStockfish() {
    if (!stockfishWorker) return;
    // Note: Since we are using the single-threaded WebAssembly build of Stockfish 18
    // (stockfish-18-lite-single.js), configuring Threads > 1 will cause low-level memory
    // and thread desync crashes (Unreachable code should not be executed / Out of bounds call_indirect).
    // Force Threads to 1 to guarantee absolute stability.
    stockfishWorker.postMessage(`setoption name Threads value 1`);
    stockfishWorker.postMessage(`setoption name Hash value 64`);
    stockfishWorker.postMessage(`setoption name Skill Level value ${appState.engineSkill}`);
    stockfishWorker.postMessage(`setoption name MultiPV value 3`);
}

// Candidate moves variables
let parsedMoves = [];

function parseSearchInfo(line) {
    const parts = line.split(" ");
    try {
        const pvIdx = parts.indexOf("pv");
        if (pvIdx === -1) return;
        
        const move = parts[pvIdx + 1];
        
        let scoreStr = "0.00";
        if (parts.includes("cp")) {
            const cpIdx = parts.indexOf("cp");
            scoreStr = (parseInt(parts[cpIdx + 1]) / 100).toFixed(2);
        } else if (parts.includes("mate")) {
            const mateIdx = parts.indexOf("mate");
            scoreStr = "M" + parts[mateIdx + 1];
        }

        if (parts.includes("multipv")) {
            const mpvIdx = parts.indexOf("multipv");
            const rank = parseInt(parts[mpvIdx + 1]) - 1;
            
            // Populate/update the moves array
            parsedMoves[rank] = { move, score: scoreStr };
        }
    } catch (e) {
        console.error("Error parsing search info:", e);
    }
}

// Convert Board Matrix to standard FEN
function translateMatrixToFen(matrix) {
    let fenRows = [];
    for (let r = 0; r < 8; r++) {
        let emptyCount = 0;
        let fenRow = "";
        for (let c = 0; c < 8; c++) {
            let sq = matrix[r][c];
            if (sq === "") {
                emptyCount++;
            } else {
                if (emptyCount > 0) {
                    fenRow += emptyCount;
                    emptyCount = 0;
                }
                fenRow += sq;
            }
        }
        if (emptyCount > 0) {
            fenRow += emptyCount;
        }
        fenRows.push(fenRow);
    }
    const activeColor = isWhiteTurn ? "w" : "b";
    return fenRows.join("/") + ` ${activeColor} - - 0 1`;
}

// Update Turn Direction based on move changes
function updateTurnDirection(matrix) {
    if (!lastMatrix) {
        lastMatrix = matrix;
        return;
    }

    let newWhite = false;
    let newBlack = false;
    for (let r = 0; r < 8; r++) {
        for (let c = 0; c < 8; c++) {
            const oldSq = lastMatrix[r][c];
            const newSq = matrix[r][c];
            if (oldSq !== newSq) {
                if (newSq !== "") {
                    if (newSq === newSq.toUpperCase()) {
                        newWhite = true;
                    } else {
                        newBlack = true;
                    }
                }
            }
        }
    }

    if (newWhite) {
        isWhiteTurn = false;
    } else if (newBlack) {
        isWhiteTurn = true;
    }

    lastMatrix = matrix;
}

// Anti-Ban humanization scrambling
function humanizeMoves(moves) {
    if (!appState.randomizeMoves || moves.length < 2) return moves;

    try {
        const move1 = moves[0];
        const move2 = moves[1];
        
        // Do not randomize mate threats
        if (move1.score.includes("M") || move2.score.includes("M")) {
            return moves;
        }

        const score1 = parseFloat(move1.score);
        const score2 = parseFloat(move2.score);
        
        // If 2nd option is decent (within 1.5 pawns value)
        if (Math.abs(score1 - score2) < 1.50) {
            const rand = Math.random();
            if (rand < 0.40) {
                // Swap 1st and 2nd best move
                moves[0] = move2;
                moves[1] = move1;
            } else if (rand < 0.60 && moves.length >= 3) {
                const move3 = moves[2];
                if (!move3.score.includes("M")) {
                    const score3 = parseFloat(move3.score);
                    if (Math.abs(score1 - score3) < 2.0) {
                        // Swap 1st and 3rd best move
                        moves[0] = move3;
                        moves[2] = move1;
                    }
                }
            }
        }
    } catch(e) {}
    
    return moves;
}

// Log-normal random variable (Box-Muller transform)
function lognormvariate(mu, sigma) {
    let u1 = Math.random();
    let u2 = Math.random();
    // Avoid log(0)
    if (u1 < 1e-10) u1 = 1e-10;
    const z = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);
    return Math.exp(mu + sigma * z);
}

// Calculate thinking delay based on board evaluation and remaining time
function calculateDelay(moves, timeLeft) {
    if (moves.length === 0) return 0.5;

    let baseDelay = 0.5;
    const bestMove = moves[0];
    
    if (bestMove.score.includes("M")) {
        // Forced mate: think lognormally around 1.8s
        baseDelay = lognormvariate(0.5, 0.3);
    } else if (moves.length >= 2) {
        try {
            const score1 = parseFloat(moves[0].score);
            const score2 = parseFloat(moves[1].score);
            const diff = Math.abs(score1 - score2);
            
            if (diff > 3.0) {
                // Very obvious move (recapture, check capture)
                baseDelay = lognormvariate(-0.4, 0.25);
            } else if (diff < 0.5) {
                // Highly complex position (multiple good choices)
                baseDelay = lognormvariate(1.5, 0.45);
            } else {
                // Standard chess position
                baseDelay = lognormvariate(0.8, 0.35);
            }
        } catch (e) {
            baseDelay = lognormvariate(0.8, 0.35);
        }
    }

    // Adjust delay multiplier based on Game Mode
    let multiplier = 1.0;
    if (appState.gameMode === "bullet") {
        multiplier = 0.25;
    } else if (appState.gameMode === "blitz") {
        multiplier = 0.55;
    }

    // Time Panic multipliers
    if (timeLeft <= 15.0) {
        multiplier = 0.0; // Instantly display arrows
    } else if (timeLeft <= 30.0) {
        multiplier *= 0.15;
    } else if (timeLeft <= 60.0) {
        multiplier *= 0.40;
    } else if (timeLeft <= 120.0) {
        multiplier *= 0.70;
    }

    return baseDelay * multiplier;
}

// Start Chess Assistant & Load Webview
function startBot() {
    if (!isStockfishReady) {
        alert("Stockfish engine is still loading. Please wait! (المحرك جاري التحميل)");
        return;
    }

    appState.isBotRunning = true;
    addLiveLog("Starting Assistant Bot...", "info");
    
    const startBtn = document.getElementById("start-bot-btn");
    startBtn.textContent = "Assisting Active... (البوت يعمل)";
    startBtn.style.background = "linear-gradient(135deg, #1b380d, #275915)";
    startBtn.style.borderColor = "var(--success-green)";
    
    // Check if Cordova is available
    if (typeof cordova === 'undefined' || !cordova.InAppBrowser) {
        console.warn("Cordova InAppBrowser plugin not found. Mocking WebView for desktop testing.");
        addLiveLog("Cordova InAppBrowser not found. Running desktop simulation mock.", "warning");
        mockWebViewDesktop();
        return;
    }

    // Open Chess.com inside customizable in-app browser overlay
    addLiveLog("Opening Chess.com in WebView overlay...", "info");
    
    // Build InAppBrowser options based on fullscreen preference
    let browserOptions = "location=no,hidden=no";
    if (appState.fullscreenMode) {
        browserOptions += ",toolbar=no,fullscreen=yes";
        addLiveLog("Fullscreen mode enabled. Triple-tap to toggle UI.", "info");
    } else {
        browserOptions += ",toolbar=yes,closebuttoncaption=Close,toolbarcolor=#08080a,navigationbuttoncolor=#ff3333,closebuttoncolor=#ff3333";
    }
    
    chessWebView = cordova.InAppBrowser.open(
        "https://www.chess.com/play/online", 
        "_blank", 
        browserOptions
    );

    // When page finished loading, inject board detector & arrow painter scripts
    chessWebView.addEventListener("loadstop", () => {
        console.log("InAppBrowser loaded Chess.com. Injecting stealth reader...");
        addLiveLog("WebView loaded. Injecting stealth reader script...", "info");
        
        // First inject CSS rules for overlay
        chessWebView.insertCSS({
            code: `
                #stealth-hud-container {
                    position: absolute;
                    pointer-events: none;
                    z-index: 99999;
                }
            `
        });

        // Inject the script directly by stringifying the function already loaded in memory.
        // This is 100% reliable and avoids local file fetching issues in Capacitor/iOS WKWebView.
        if (window.injectedStealthFunction) {
            const code = `(${window.injectedStealthFunction.toString()})();`;
            chessWebView.executeScript({ code: code }, (res) => {
                addLiveLog("Stealth reader successfully injected.", "success");
            });
        } else {
            console.error("Error: window.injectedStealthFunction is not loaded on the main window!");
            addLiveLog("Failed to inject: stealth script function not found in memory.", "error");
        }
    });

    // Listen to board data events sent from WebView (supports stringified JSON and raw object payloads)
    chessWebView.addEventListener("message", (event) => {
        let data = event.data;
        if (typeof data === "string") {
            try {
                data = JSON.parse(data);
            } catch (e) {
                console.error("Failed to parse message string from InAppBrowser:", e);
                addLiveLog("Failed to parse message: " + e.message, "error");
                return;
            }
        }
        if (data && data.type === "BOARD_STATE") {
            handleBoardUpdate(data.matrix, data.is_white_bottom, data.time_left);
        } else if (data && data.type === "ERROR") {
            addLiveLog("WebView Error: " + data.message, "error");
            console.error("WebView script error:", data.message, data.stack);
        }
    });

    // Reset button when closed
    chessWebView.addEventListener("exit", () => {
        addLiveLog("WebView overlay exited by user.", "warning");
        stopBot();
    });
}

function stopBot() {
    appState.isBotRunning = false;
    addLiveLog("Assistant Bot stopped.", "warning");
    
    const startBtn = document.getElementById("start-bot-btn");
    startBtn.innerHTML = `<span>Start Assistant Bot</span><span class="btn-ar">بدء بوت المساعد الذكي</span>`;
    startBtn.style.background = "linear-gradient(135deg, #2b0f0f, #7a0f0f)";
    startBtn.style.borderColor = "var(--primary-red)";
    
    // Clear chess structures
    lastMatrix = null;
    lastFen = "";
    isWhiteTurn = true;
    isSearching = false;
    pendingSearch = null;
    if (showMovesTimeout) clearTimeout(showMovesTimeout);
}

let isSearching = false;
let pendingSearch = null;

function triggerSearch(fen, isWhiteBottom, timeLeft) {
    if (!stockfishWorker || !appState.isBotRunning) return;
    isSearching = true;
    parsedMoves = [];
    
    stockfishWorker.postMessage(`position fen ${fen}`);
    
    currentSearchCallback = () => {
        let finalMoves = [...parsedMoves].filter(m => m !== undefined && m !== null);
        if (finalMoves.length === 0) return;

        // Apply Anti-Ban scrambling
        finalMoves = humanizeMoves(finalMoves);
        
        // Calculate randomized delay based on position difficulty and clock
        const delaySeconds = calculateDelay(finalMoves, timeLeft);
        
        addLiveLog("Best move: " + finalMoves[0].move + " (Score: " + finalMoves[0].score + ")", "success");
        if (delaySeconds > 0.01) {
            addLiveLog(`Delaying display by ${delaySeconds.toFixed(1)}s (Anti-Ban)`, "info");
            showMovesTimeout = setTimeout(() => {
                sendMovesToWebView(finalMoves, isWhiteBottom, timeLeft);
            }, delaySeconds * 1000);
        } else {
            sendMovesToWebView(finalMoves, isWhiteBottom, timeLeft);
        }
    };

    stockfishWorker.postMessage(`go depth ${appState.engineDepth}`);
}

// Process board updates
function handleBoardUpdate(matrix, isWhiteBottom, timeLeft) {
    updateTurnDirection(matrix);
    const fen = translateMatrixToFen(matrix);
    
    // Position changed, start Stockfish search
    if (fen !== lastFen && fen !== "8/8/8/8/8/8/8/8 w - - 0 1" && fen !== "8/8/8/8/8/8/8/8 b - - 0 1") {
        lastFen = fen;
        addLiveLog("Board state updated. FEN: " + fen, "engine");
        
        // Clear any pending render timers so we don't display outdated moves
        if (showMovesTimeout) {
            clearTimeout(showMovesTimeout);
            showMovesTimeout = null;
        }

        if (isSearching) {
            // Queue this search to run immediately after the current one stops
            pendingSearch = { fen, isWhiteBottom, timeLeft };
            stockfishWorker.postMessage("stop");
        } else {
            pendingSearch = null;
            triggerSearch(fen, isWhiteBottom, timeLeft);
        }
    }
}

// Send calculations back to the WebView to draw overlays
function sendMovesToWebView(moves, isWhiteBottom, timeLeft) {
    if (!chessWebView) return;
    
    addLiveLog("Rendering arrows overlay in WebView...", "info");
    // Convert to JSON and evaluate injection in WebView DOM
    const serializedMoves = JSON.stringify(moves);
    const code = `
        if (window.drawStealthOverlay) {
            window.drawStealthOverlay(${serializedMoves}, ${isWhiteBottom}, ${timeLeft}, ${appState.showArrows}, ${appState.showHud}, ${appState.stealthScreen});
        }
    `;
    chessWebView.executeScript({ code: code });
}

// Desktop Simulator Mock for browser testing
function mockWebViewDesktop() {
    console.log("Mock started. Open Chess.com in browser and paste mock moves.");
    // Simulate periodic dummy Chess board updates
    setInterval(() => {
        if (!appState.isBotRunning) return;
        const dummyMatrix = [
            ["r","n","b","q","k","b","n","r"],
            ["p","p","p","p","p","p","p","p"],
            ["","","","","","","",""],
            ["","","","","","","",""],
            ["","","","","","","",""],
            ["","","","","","","",""],
            ["P","P","P","P","P","P","P","P"],
            ["R","N","B","Q","K","B","N","R"]
        ];
        handleBoardUpdate(dummyMatrix, true, 280);
    }, 4000);
}
