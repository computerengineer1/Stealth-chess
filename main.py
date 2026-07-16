import sys
import os
import time
import keyboard
import threading
import random
from PyQt6.QtWidgets import (
    QApplication, QWidget, QStackedWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QComboBox, QSlider, QSpinBox, 
    QCheckBox, QGroupBox, QFormLayout, QFrame, QMainWindow
)
from PyQt6.QtCore import pyqtSignal, QObject, Qt, QRect, QPoint
from PyQt6.QtGui import QPainter, QPixmap, QColor, QIcon, QBrush, QPainterPath, QPen

from config import Config
from vision_processor import VisionProcessor
from engine_wrapper import EngineWrapper
from overlay_ui import OverlayWindow
from licensing import LicenseManager

class WatermarkCentralWidget(QWidget):
    """A custom widget that paints a dark obsidian background and a semi-transparent logo watermark."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logo_pixmap = None
        # Locate logo.png in the main bot folder
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                self.logo_pixmap = pixmap

    def paintEvent(self, event):
        painter = QPainter(self)
        # Deep volcanic obsidian black base
        painter.fillRect(self.rect(), QColor("#08080a"))
        
        # Subtle glowing orange-red bottom corner gradient
        from PyQt6.QtGui import QLinearGradient
        grad = QLinearGradient(0, self.height(), self.width(), 0)
        grad.setColorAt(0.0, QColor(25, 4, 4, 120))
        grad.setColorAt(0.5, QColor(0, 0, 0, 0))
        grad.setColorAt(1.0, QColor(10, 10, 12, 100))
        painter.fillRect(self.rect(), grad)
        
        if self.logo_pixmap:
            size = 370
            scaled = self.logo_pixmap.scaled(
                size, size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            
            # Draw watermark with ultra-premium 7% opacity
            painter.setOpacity(0.07)
            painter.drawPixmap(x, y, scaled)
            painter.setOpacity(1.0)


class CalibrationOverlay(QWidget):
    """Full-screen translucent overlay for clicking and dragging to calibrate the board.
    Uses mss for pixel-perfect screen capture that respects DPI scaling."""
    finished = pyqtSignal(int, int, int, int) # Emits absolute mss-compatible (x, y, w, h)
    closed = pyqtSignal()
    
    def __init__(self, monitor_info):
        super().__init__()
        import mss
        import mss.tools
        
        # Capture the screen using mss (always physical pixels, DPI-correct)
        with mss.mss() as sct:
            monitor = sct.monitors[monitor_info]
            sct_img = sct.grab(monitor)
            # Convert raw mss screenshot to QPixmap
            from PyQt6.QtGui import QImage
            img_bytes = bytes(sct_img.rgb)
            qimg = QImage(img_bytes, sct_img.width, sct_img.height, sct_img.width * 3, QImage.Format.Format_RGB888)
            self.background_pixmap = QPixmap.fromImage(qimg)
            self.mss_monitor = monitor  # Store mss monitor bounds for coordinate mapping
        
        # Make the window frameless, stays on top, and works as a full-screen tool
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        self.start_pos = None
        self.end_pos = None
        self.is_dragging = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Scale the mss screenshot to fit the widget (logical) size
        painter.drawPixmap(self.rect(), self.background_pixmap)
        
        # Dim the background with a transparent overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))
        
        # Add instruction text on screen
        painter.setPen(QColor("#ffffff"))
        font = painter.font()
        font.setPointSize(16)
        font.setBold(True)
        painter.setFont(font)
        instructions = "Drag a rectangle over the 8x8 Chessboard | اسحب مستطيلاً بدقة فوق رقعة الشطرنج\n[ESC to Cancel / للإلغاء اضغط]"
        # Draw in center top
        painter.drawText(
            self.rect().adjusted(0, 50, 0, 0),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            instructions
        )
        
        if self.start_pos and self.end_pos:
            x1, y1 = self.start_pos.x(), self.start_pos.y()
            x2, y2 = self.end_pos.x(), self.end_pos.y()
            x = min(x1, x2)
            y = min(y1, y2)
            w = abs(x1 - x2)
            h = abs(y1 - y2)
            rect = QRect(x, y, w, h)
            
            # Clear the dimming overlay inside the selection box to make it highlight bright
            # Map widget-local rect to pixmap coordinates for correct source sampling
            sx = int(x * self.background_pixmap.width() / self.width())
            sy = int(y * self.background_pixmap.height() / self.height())
            sw = int(w * self.background_pixmap.width() / self.width())
            sh = int(h * self.background_pixmap.height() / self.height())
            src_rect = QRect(sx, sy, sw, sh)
            
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.drawPixmap(rect, self.background_pixmap, src_rect)
            
            # Restore normal mode to draw glowing red borders
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            
            pen = QPen(QColor("#ff3333"), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(rect)
            
            # Light red translucent fill inside selection
            painter.fillRect(rect, QColor(255, 51, 51, 30))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.position().toPoint()
            self.end_pos = self.start_pos
            self.is_dragging = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            self.end_pos = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            if self.start_pos and self.end_pos:
                x1, y1 = self.start_pos.x(), self.start_pos.y()
                x2, y2 = self.end_pos.x(), self.end_pos.y()
                lx = min(x1, x2)
                ly = min(y1, y2)
                lw = abs(x1 - x2)
                lh = abs(y1 - y2)
                
                # Check for minimum reasonable size
                if lw > 50 and lh > 50:
                    # Calculate the DPI scale factor between mss (physical) and widget (logical)
                    scale_x = self.mss_monitor["width"] / self.width()
                    scale_y = self.mss_monitor["height"] / self.height()
                    
                    # Convert logical widget coordinates to mss absolute physical coordinates
                    abs_x = int(lx * scale_x) + self.mss_monitor["left"]
                    abs_y = int(ly * scale_y) + self.mss_monitor["top"]
                    phys_w = int(lw * scale_x)
                    phys_h = int(ly * scale_y + lh * scale_y) - int(ly * scale_y)  # Precise rounding
                    
                    self.finished.emit(abs_x, abs_y, phys_w, phys_h)
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)


class Worker(QObject):
    """Background worker that handles DOM communication and engine logic."""
    update_ui = pyqtSignal(list, tuple, bool, float)
    overlay_status_changed = pyqtSignal(bool)
    stealth_toggled = pyqtSignal(bool)
    
    def __init__(self, license_manager=None):
        super().__init__()
        self.license_manager = license_manager
        self.vision = VisionProcessor(license_manager)
        self.engine = EngineWrapper()
        self.running = True
        self.last_fen = ""
        self.last_matrix = None
        self.last_emitted_state = None
        self.is_overlay_active = False  # Deactivated by default on startup
        
        # Non-blocking async delay variables
        self.current_moves = []
        self.pending_moves = None
        self.show_moves_at = 0.0
        self.last_emitted_time = 0.0

    def toggle_overlay(self, force_state=None):
        if force_state is not None:
            self.is_overlay_active = force_state
        else:
            self.is_overlay_active = not self.is_overlay_active
            
        print(f"Overlay active state changed to: {self.is_overlay_active}")
        self.overlay_status_changed.emit(self.is_overlay_active)
        
        if not self.is_overlay_active:
            self.current_moves = []
            self.pending_moves = None
            self.update_ui.emit([], (0, 0, 0, 0), True, 300.0) # Clear UI

    def toggle_stealth_mode(self):
        Config.STEALTH_DISPLAY = not Config.STEALTH_DISPLAY
        self.stealth_toggled.emit(Config.STEALTH_DISPLAY)
        print(f"Global hotkey toggled stealth display to: {Config.STEALTH_DISPLAY}")

    def run(self):
        hotkey_stealth = getattr(Config, 'HOTKEY_STEALTH', 'ctrl+shift+s')
        print(f"Bot core started. Exit hotkey: {Config.HOTKEY_EXIT}. Toggle hotkey: {Config.HOTKEY_TOGGLE}. Stealth hotkey: {hotkey_stealth}.")
        
        # Setup robust global hotkeys
        keyboard.add_hotkey(Config.HOTKEY_EXIT, lambda: os._exit(0))
        keyboard.add_hotkey(Config.HOTKEY_TOGGLE, self.toggle_overlay)
        keyboard.add_hotkey(hotkey_stealth, self.toggle_stealth_mode)
        
        while self.running:
            if not self.is_overlay_active:
                time.sleep(0.1)
                continue

            # Fetch instantly from the local HTTP server
            board_data = self.vision.get_board_data()
            matrix = board_data.get("matrix", [])
            is_white_bottom = board_data.get("is_white_bottom", True)
            time_left = board_data.get("time_left", 300.0)
            
            # Check if matrix is populated (not empty)
            if any(any(row) for row in matrix):
                if matrix != self.last_matrix:
                    self.last_matrix = matrix
                    self.engine.update_turn(matrix)
                    fen = self.engine.matrix_to_fen(matrix)

                    # If state changed, evaluate
                    if fen != self.last_fen and fen != "8/8/8/8/8/8/8/8 w - - 0 1" and fen != "8/8/8/8/8/8/8/8 b - - 0 1":
                        moves = self.engine.get_best_moves(fen, num_moves=3)
                        self.last_fen = fen
                        
                        if not moves:
                            print(f"Error: Stockfish failed to compute moves for FEN: {fen}")
                        else:
                            # Clear current moves instantly when a new state is detected, so old arrows vanish
                            self.current_moves = []
                            
                            # Humanize: log-normal human thinking delay model
                            base_delay = 0.5
                            
                            if len(moves) >= 2:
                                _, score1_str = moves[0]
                                _, score2_str = moves[1]
                                
                                if "M" in score1_str:
                                    # Forced mate: think lognormally around 1.8s
                                    base_delay = random.lognormvariate(0.5, 0.3)
                                else:
                                    try:
                                        score1 = float(score1_str)
                                        score2 = float(score2_str)
                                        diff = abs(score1 - score2)
                                        
                                        if diff > 3.0:
                                            # Very obvious move (e.g. recapture, check capture)
                                            base_delay = random.lognormvariate(-0.4, 0.25)
                                        elif diff < 0.5:
                                            # Highly complex position (multiple good choices)
                                            base_delay = random.lognormvariate(1.5, 0.45)
                                        else:
                                            # Standard chess position
                                            base_delay = random.lognormvariate(0.8, 0.35)
                                    except ValueError:
                                        base_delay = random.lognormvariate(0.8, 0.35)
                            
                            # Scale delay based on selected GAME_MODE in config
                            mode = getattr(Config, 'GAME_MODE', 'blitz').lower()
                            if mode == 'bullet':
                                multiplier = 0.25 # ~0.1s to 1.5s
                            elif mode == 'blitz':
                                multiplier = 0.55 # ~0.2s to 3.5s
                            else: # rapid or other
                                multiplier = 1.0  # ~0.4s to 6.5s
                                
                            # --- DYNAMIC TIME MANAGEMENT PANIC SYSTEM ---
                            if time_left <= 15.0:
                                # 0 to 15 seconds: Zero delay! Immediate arrows
                                multiplier = 0.0
                                print("🚨 TIME PANIC: Critical time! Showing hints instantly (0s delay).")
                            elif time_left <= 30.0:
                                # 15 to 30 seconds: 85% faster delay
                                multiplier *= 0.15
                                print(f"⚠️ TIME PANIC: Under 30s! Speeding up helper by 85% (Time Left: {time_left:.1f}s)")
                            elif time_left <= 60.0:
                                # 30 to 60 seconds (1 minute): 60% faster delay
                                multiplier *= 0.40
                                print(f"⚠️ TIME PANIC: Under 1 min! Speeding up helper by 60% (Time Left: {time_left:.1f}s)")
                            elif time_left <= 120.0:
                                # 60 to 120 seconds (2 minutes): 30% faster delay
                                multiplier *= 0.70
                                
                            thinking_time = base_delay * multiplier
                            
                            if thinking_time > 0.01:
                                print(f"🛡️ [Mode: {mode.upper()}] Delay: {thinking_time:.2f}s. Time Left: {time_left:.1f}s. Thinking...")
                                self.pending_moves = moves
                                self.show_moves_at = time.time() + thinking_time
                            else:
                                self.current_moves = moves
                                self.pending_moves = None
                                print(f"Stockfish suggests: {moves}")
                    
                # Check if pending moves are ready to be displayed (non-blocking)
                if self.pending_moves and time.time() >= self.show_moves_at:
                    self.current_moves = self.pending_moves
                    self.pending_moves = None
                    print(f"Stockfish suggests: {self.current_moves}")

                # Emit UI update only when changes occur (moves, bounding box, orientation, or clock second tick)
                current_time = time.time()
                rounded_time_left = int(time_left)
                current_state = (self.current_moves, Config.MANUAL_BOARD_BBOX, is_white_bottom, rounded_time_left)
                
                if current_state != self.last_emitted_state or (current_time - self.last_emitted_time >= 1.0):
                    if Config.MANUAL_BOARD_BBOX:
                        self.update_ui.emit(self.current_moves, Config.MANUAL_BOARD_BBOX, is_white_bottom, time_left)
                    self.last_emitted_state = current_state
                    self.last_emitted_time = current_time

            # Sleep slightly to prevent high CPU utilization
            time.sleep(0.015)
        self.engine.close()


class ChessBotDashboard(QMainWindow):
    """Unified application dashboard managing activation, configuration, and engine controls."""
    
    def __init__(self, license_manager, overlay_window, worker_obj):
        super().__init__()
        self.license_manager = license_manager
        self.overlay = overlay_window
        self.worker = worker_obj
        self.init_ui()
        
    def get_circular_logo(self, size=80):
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        if not os.path.exists(logo_path):
            return None
        
        src_pixmap = QPixmap(logo_path)
        if src_pixmap.isNull():
            return None
            
        target_pixmap = QPixmap(size, size)
        target_pixmap.fill(Qt.GlobalColor.transparent)
        
        scaled = src_pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        
        painter = QPainter(target_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Round clipping
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        
        x = (size - scaled.width()) // 2
        y = (size - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        
        # Draw circular glowing crimson border
        painter.setClipping(False)
        pen = QPen(QColor("#ff3333"), 2)
        painter.setPen(pen)
        painter.drawEllipse(1, 1, size - 2, size - 2)
        
        painter.end()
        return target_pixmap

    def init_ui(self):
        self.setWindowTitle("Stealth Chess Assistant Control Panel")
        self.setFixedSize(540, 720)
        
        # Load and set Window Icon
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))
            
        # Use our Watermark Central Widget to draw the background and watermark
        self.central_panel = WatermarkCentralWidget(self)
        self.setCentralWidget(self.central_panel)
        
        # Create a layout for central widget
        central_layout = QVBoxLayout(self.central_panel)
        central_layout.setContentsMargins(0, 0, 0, 0)
        
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background: transparent;")
        central_layout.addWidget(self.stacked_widget)
        
        # Apply premium dark volcanic glassmorphism stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background: transparent;
            }
            QWidget {
                color: #f5f5f7;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                font-size: 13px;
                font-weight: 500;
            }
            QLineEdit {
                background-color: rgba(22, 22, 28, 0.8);
                color: #ffffff;
                border: 1.5px solid rgba(255, 51, 51, 0.15);
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1.5px solid #ff3333;
                background-color: rgba(26, 22, 22, 0.9);
            }
            QComboBox {
                background-color: rgba(22, 22, 28, 0.8);
                color: #ffffff;
                border: 1.5px solid rgba(255, 51, 51, 0.15);
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QComboBox:focus {
                border: 1.5px solid #ff3333;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background-color: #0b0b0e;
                color: #ffffff;
                border: 1px solid rgba(255, 51, 51, 0.3);
                selection-background-color: #ff3333;
                selection-color: #ffffff;
            }
            QSpinBox {
                background-color: rgba(22, 22, 28, 0.8);
                color: #ffffff;
                border: 1.5px solid rgba(255, 51, 51, 0.15);
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QSpinBox:focus {
                border: 1.5px solid #ff3333;
            }
            QCheckBox {
                spacing: 8px;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                background-color: rgba(22, 22, 28, 0.8);
                border: 1.5px solid rgba(255, 51, 51, 0.15);
                border-radius: 5px;
            }
            QCheckBox::indicator:checked {
                background-color: #ff3333;
                border: 1.5px solid #ff3333;
            }
            QGroupBox {
                border: 1.5px solid rgba(255, 51, 51, 0.2);
                border-radius: 12px;
                margin-top: 18px;
                font-weight: bold;
                font-size: 14px;
                padding-top: 18px;
                background-color: rgba(15, 15, 20, 0.7);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #ff3333;
                font-weight: bold;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a0808, stop:1 #380d0d);
                color: #ffffff;
                font-weight: bold;
                border: 1.5px solid rgba(255, 51, 51, 0.35);
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2b0f0f, stop:1 #591515);
                border: 1.5px solid #ff3333;
            }
            QPushButton:pressed {
                background-color: #ff3333;
            }
            QPushButton#danger_btn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #240a0a, stop:1 #470d0d);
                border: 1.5px solid rgba(243, 139, 168, 0.35);
                color: #f38ba8;
            }
            QPushButton#danger_btn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #471111, stop:1 #821515);
                border: 1.5px solid #ff4f4f;
                color: #ffffff;
            }
            QSlider::groove:horizontal {
                border: 1px solid rgba(255, 51, 51, 0.15);
                height: 6px;
                background: rgba(22, 22, 28, 0.8);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ff3333;
                border: none;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #ff5555;
            }
        """)
        
        # Create the two views
        self.create_activation_view()
        self.create_dashboard_view()
        
        # Add views to stacked layout
        self.stacked_widget.addWidget(self.activation_widget)
        self.stacked_widget.addWidget(self.dashboard_widget)
        
        # Connect worker signals
        self.worker.overlay_status_changed.connect(self.handle_overlay_toggled)
        self.worker.stealth_toggled.connect(self.handle_stealth_toggled_from_worker)
        
        # Route to correct screen based on activation status
        if self.license_manager.is_valid:
            self.unlock_dashboard()
        else:
            self.stacked_widget.setCurrentWidget(self.activation_widget)
 
    # --- VIEW 1: ACTIVATION SCREEN ---
    def create_activation_view(self):
        self.activation_widget = QWidget()
        self.activation_widget.setObjectName("activation_view_widget")
        layout = QVBoxLayout(self.activation_widget)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(18)
        
        # Header / Title
        header_layout = QVBoxLayout()
        header_layout.setSpacing(10)
        
        circular_logo = self.get_circular_logo(110)
        if circular_logo:
            logo_img_label = QLabel()
            logo_img_label.setPixmap(circular_logo)
            logo_img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            header_layout.addWidget(logo_img_label)
            
        logo_label = QLabel("STEALTH CHESS HELPER")
        logo_label.setStyleSheet("font-size: 25px; font-weight: 800; color: #ff3333; letter-spacing: 1.5px;")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        sub_logo = QLabel("Subscription Activation Console | تفعيل الاشتراك")
        sub_logo.setStyleSheet("font-size: 12px; color: #8a8a93; font-weight: 600;")
        sub_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(logo_label)
        header_layout.addWidget(sub_logo)
        layout.addLayout(header_layout)
        
        # Middle activation Card
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 15, 20, 0.75);
                border-radius: 12px;
                border: 1.5px solid rgba(255, 51, 51, 0.2);
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(25, 25, 25, 25)
        card_layout.setSpacing(15)
        
        key_label = QLabel("Enter License Key (أدخل مفتاح الترخيص الخاص بك):")
        key_label.setStyleSheet("font-weight: bold; color: #f5f5f7; font-size: 13px;")
        card_layout.addWidget(key_label)
        
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Paste your activation key here (MON-... or LIF-...)...")
        card_layout.addWidget(self.key_input)
        
        self.act_status = QLabel("")
        self.act_status.setStyleSheet("color: #f38ba8; font-size: 12px; font-weight: bold;")
        self.act_status.setWordWrap(True)
        card_layout.addWidget(self.act_status)
        
        self.activate_button = QPushButton("Verify & Activate | تفعيل وتأكيد المفتاح")
        self.activate_button.clicked.connect(self.verify_license)
        card_layout.addWidget(self.activate_button)
        
        # Show Machine ID so subscriber can copy and send to admin
        from licensing import get_hwid
        hwid_str = get_hwid()
        self.hwid_label = QLabel(f"Machine ID (رمز الجهاز): <b>{hwid_str}</b>")
        self.hwid_label.setStyleSheet("color: #a6e3a1; font-size: 11px; margin-top: 5px;")
        self.hwid_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.hwid_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.hwid_label)
        
        layout.addWidget(card)
        
        # Bottom price options list
        info_group = QGroupBox("Available Subscription Plans | باقات الاشتراك المتوفرة")
        info_layout = QVBoxLayout(info_group)
        info_layout.setSpacing(8)
        info_layout.setContentsMargins(20, 15, 20, 15)
        
        plan1 = QLabel("⭐ Monthly Plan (اشتراك شهري): $10 - $15")
        plan1.setStyleSheet("color: #e4e4e7; font-size: 13px;")
        plan2 = QLabel("⭐ 3-Month Plan (اشتراك 3 أشهر): $25 - $30")
        plan2.setStyleSheet("color: #e4e4e7; font-size: 13px;")
        plan3 = QLabel("⭐ Lifetime Plan (اشتراك مدى الحياة): $70 - $90")
        plan3.setStyleSheet("color: #ff3333; font-weight: bold; font-size: 13px;")
        
        info_layout.addWidget(plan1)
        info_layout.addWidget(plan2)
        info_layout.addWidget(plan3)
        
        layout.addWidget(info_group)
        layout.addStretch()
 
    def verify_license(self):
        key = self.key_input.text().strip()
        if not key:
            self.act_status.setText("Error: Key field cannot be empty. (المفتاح مطلوب)")
            self.act_status.setStyleSheet("color: #ff4f4f;")
            return
            
        self.act_status.setText("Verifying with license server... (جاري التحقق)")
        self.act_status.setStyleSheet("color: #8a8a93;")
        QApplication.processEvents()
        
        if self.license_manager.validate_key(key):
            self.unlock_dashboard()
        else:
            self.act_status.setText(f"Verification Failed: {self.license_manager.error_message}")
            self.act_status.setStyleSheet("color: #ff4f4f;")
 
    def unlock_dashboard(self):
        # Refresh license parameters on dashboard
        self.lbl_license_status.setText(f"🟢 Subscription Active ({self.license_manager.tier.upper()})")
        self.lbl_expiry.setText(f"Expiration: {self.license_manager.expiry_date}")
        self.stacked_widget.setCurrentWidget(self.dashboard_widget)
 
    # --- VIEW 2: MAIN SETTINGS & CONTROLS DASHBOARD ---
    def create_dashboard_view(self):
        self.dashboard_widget = QWidget()
        self.dashboard_widget.setObjectName("dashboard_view_widget")
        main_layout = QVBoxLayout(self.dashboard_widget)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(12)
        
        # Top Header (Subscription Banner)
        banner = QFrame()
        banner.setObjectName("banner_frame")
        banner.setStyleSheet("""
            QFrame#banner_frame {
                background-color: rgba(15, 15, 20, 0.75);
                border-radius: 12px;
                border: 1.5px solid rgba(255, 51, 51, 0.2);
            }
        """)
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(15, 12, 15, 12)
        
        # Circular micro logo in header
        mini_logo = self.get_circular_logo(54)
        if mini_logo:
            logo_lbl = QLabel()
            logo_lbl.setPixmap(mini_logo)
            banner_layout.addWidget(logo_lbl)
            
        text_layout = QVBoxLayout()
        self.lbl_license_status = QLabel("🟢 Subscription Active")
        self.lbl_license_status.setStyleSheet("font-weight: bold; font-size: 14px; color: #2ecc71;")
        self.lbl_expiry = QLabel("Expiration: Never")
        self.lbl_expiry.setStyleSheet("font-size: 11px; color: #8a8a93;")
        text_layout.addWidget(self.lbl_license_status)
        text_layout.addWidget(self.lbl_expiry)
        
        self.logout_btn = QPushButton("Change Key / تغيير")
        self.logout_btn.setObjectName("danger_btn")
        self.logout_btn.setFixedWidth(120)
        self.logout_btn.clicked.connect(self.reset_key)
        
        banner_layout.addLayout(text_layout)
        banner_layout.addStretch()
        banner_layout.addWidget(self.logout_btn)
        main_layout.addWidget(banner)
        
        # Scrollable Configuration Controls
        controls_group = QGroupBox("Helper Configuration | إعدادات التحكم")
        form_layout = QFormLayout(controls_group)
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(20, 20, 20, 20)
        
        # Game Mode
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["Bullet", "Blitz", "Rapid"])
        current_mode = getattr(Config, 'GAME_MODE', 'blitz').capitalize()
        idx = self.combo_mode.findText(current_mode)
        if idx != -1:
            self.combo_mode.setCurrentIndex(idx)
        self.combo_mode.currentTextChanged.connect(self.update_game_mode)
        
        lbl_game_mode = QLabel("Game Mode / نمط اللعب:")
        lbl_game_mode.setStyleSheet("font-weight: bold;")
        form_layout.addRow(lbl_game_mode, self.combo_mode)
        
        # Engine Depth
        depth_layout = QHBoxLayout()
        self.slider_depth = QSlider(Qt.Orientation.Horizontal)
        self.slider_depth.setRange(5, 20)
        self.slider_depth.setValue(Config.ENGINE_DEPTH)
        self.lbl_depth_val = QLabel(str(Config.ENGINE_DEPTH))
        self.lbl_depth_val.setStyleSheet("font-weight: bold; color: #ff3333; font-size: 13px;")
        self.lbl_depth_val.setFixedWidth(20)
        self.slider_depth.valueChanged.connect(self.update_depth)
        depth_layout.addWidget(self.slider_depth)
        depth_layout.addWidget(self.lbl_depth_val)
        
        lbl_depth = QLabel("Engine Depth / عمق المحرك:")
        lbl_depth.setStyleSheet("font-weight: bold;")
        form_layout.addRow(lbl_depth, depth_layout)
        
        # Skill Level (Human ELO scaling)
        skill_layout = QHBoxLayout()
        self.slider_skill = QSlider(Qt.Orientation.Horizontal)
        self.slider_skill.setRange(1, 20)
        self.slider_skill.setValue(Config.ENGINE_SKILL_LEVEL)
        self.lbl_skill_val = QLabel(str(Config.ENGINE_SKILL_LEVEL))
        self.lbl_skill_val.setStyleSheet("font-weight: bold; color: #ff3333; font-size: 13px;")
        self.lbl_skill_val.setFixedWidth(20)
        self.slider_skill.valueChanged.connect(self.update_skill)
        skill_layout.addWidget(self.slider_skill)
        skill_layout.addWidget(self.lbl_skill_val)
        
        lbl_skill = QLabel("Skill Level / مستوى المهارة:")
        lbl_skill.setStyleSheet("font-weight: bold;")
        form_layout.addRow(lbl_skill, skill_layout)

        # Estimated ELO Rating
        self.lbl_elo_val = QLabel()
        self.lbl_elo_val.setStyleSheet("font-weight: bold; color: #2ecc71; font-size: 14px; padding: 2px;")
        
        lbl_elo = QLabel("Estimated ELO / التصنيف المتوقع:")
        lbl_elo.setStyleSheet("font-weight: bold;")
        form_layout.addRow(lbl_elo, self.lbl_elo_val)
        
        self.update_elo_display()
        
        # Humanize / Randomize Moves
        self.chk_randomize = QCheckBox("Occasionally suggest secondary move (Anti-Ban)")
        self.chk_randomize.setChecked(Config.RANDOMIZE_MOVES)
        self.chk_randomize.stateChanged.connect(self.update_randomize)
        
        lbl_humanize = QLabel("Humanize / مانع الباند:")
        lbl_humanize.setStyleSheet("font-weight: bold;")
        form_layout.addRow(lbl_humanize, self.chk_randomize)
        
        # Show/Hide Arrows Toggle
        self.chk_show_arrows = QCheckBox("Render board arrows overlay (ON/OFF)")
        self.chk_show_arrows.setChecked(Config.SHOW_ARROWS)
        self.chk_show_arrows.stateChanged.connect(self.update_show_arrows)
        
        lbl_arrows = QLabel("Show Arrows / إظهار الأسهم:")
        lbl_arrows.setStyleSheet("font-weight: bold;")
        form_layout.addRow(lbl_arrows, self.chk_show_arrows)

        # Stealth Display Toggle
        self.chk_stealth_display = QCheckBox("Hide overlay from screen recording/streaming (ON/OFF)")
        self.chk_stealth_display.setChecked(getattr(Config, 'STEALTH_DISPLAY', True))
        self.chk_stealth_display.stateChanged.connect(self.update_stealth_display)
        
        lbl_stealth = QLabel("Stealth Screen / حماية البث:")
        lbl_stealth.setStyleSheet("font-weight: bold;")
        form_layout.addRow(lbl_stealth, self.chk_stealth_display)
        
        # Thread Count
        self.spin_threads = QSpinBox()
        self.spin_threads.setRange(1, 16)
        self.spin_threads.setValue(Config.ENGINE_THREADS)
        self.spin_threads.valueChanged.connect(self.update_threads)
        
        lbl_threads = QLabel("CPU Threads / أنوية المعالج:")
        lbl_threads.setStyleSheet("font-weight: bold;")
        form_layout.addRow(lbl_threads, self.spin_threads)
        
        # Manual Screen Calibration BBOX
        bbox_layout = QHBoxLayout()
        self.spin_x = QSpinBox()
        self.spin_x.setRange(0, 4000)
        self.spin_x.setValue(Config.MANUAL_BOARD_BBOX[0] if Config.MANUAL_BOARD_BBOX else 0)
        self.spin_x.valueChanged.connect(self.update_bbox)
        
        self.spin_y = QSpinBox()
        self.spin_y.setRange(0, 4000)
        self.spin_y.setValue(Config.MANUAL_BOARD_BBOX[1] if Config.MANUAL_BOARD_BBOX else 0)
        self.spin_y.valueChanged.connect(self.update_bbox)
        
        self.spin_w = QSpinBox()
        self.spin_w.setRange(0, 4000)
        self.spin_w.setValue(Config.MANUAL_BOARD_BBOX[2] if Config.MANUAL_BOARD_BBOX else 0)
        self.spin_w.valueChanged.connect(self.update_bbox)
        
        self.spin_h = QSpinBox()
        self.spin_h.setRange(0, 4000)
        self.spin_h.setValue(Config.MANUAL_BOARD_BBOX[3] if Config.MANUAL_BOARD_BBOX else 0)
        self.spin_h.valueChanged.connect(self.update_bbox)
        
        bbox_layout.addWidget(QLabel("X:"))
        bbox_layout.addWidget(self.spin_x)
        bbox_layout.addWidget(QLabel("Y:"))
        bbox_layout.addWidget(self.spin_y)
        bbox_layout.addWidget(QLabel("W:"))
        bbox_layout.addWidget(self.spin_w)
        bbox_layout.addWidget(QLabel("H:"))
        bbox_layout.addWidget(self.spin_h)
        
        lbl_bbox = QLabel("Board BBox / إحداثيات اللوحة:")
        lbl_bbox.setStyleSheet("font-weight: bold;")
        form_layout.addRow(lbl_bbox, bbox_layout)
        
        self.btn_calibrate = QPushButton("Calibrate Chess Board 🎯 معايرة رقعة الشطرنج")
        self.btn_calibrate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_calibrate.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0a2412, stop:1 #114d23);
                border: 1.5px solid rgba(166, 227, 161, 0.4);
                color: #ffffff;
                font-weight: bold;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #113d1e, stop:1 #186c32);
                border: 1.5px solid #a6e3a1;
            }
        """)
        self.btn_calibrate.clicked.connect(self.start_calibration)
        form_layout.addRow("", self.btn_calibrate)
        
        # DPI Scaling factor
        scale_layout = QHBoxLayout()
        self.spin_scale = QSpinBox()
        self.spin_scale.setRange(50, 200)
        self.spin_scale.setValue(int(Config.OVERLAY_SCALE_FACTOR * 100))
        self.spin_scale.valueChanged.connect(self.update_scale)
        scale_layout.addWidget(self.spin_scale)
        scale_layout.addWidget(QLabel("%"))
        
        lbl_dpi = QLabel("DPI Scale / مقياس الدقة:")
        lbl_dpi.setStyleSheet("font-weight: bold;")
        form_layout.addRow(lbl_dpi, scale_layout)
        
        main_layout.addWidget(controls_group)
        
        # Helper Status Card
        status_card = QFrame()
        status_card.setObjectName("status_card")
        status_card.setStyleSheet("""
            QFrame#status_card {
                background-color: rgba(15, 15, 20, 0.75);
                border-radius: 12px;
                border: 1.5px solid rgba(255, 51, 51, 0.2);
            }
        """)
        sc_layout = QVBoxLayout(status_card)
        sc_layout.setContentsMargins(15, 12, 15, 12)
        sc_layout.setSpacing(6)
        
        self.lbl_server_status = QLabel("🌐 Local Stealth Server: Listening on port 5005")
        self.lbl_server_status.setStyleSheet("font-size: 11px; color: #8a8a93;")
        self.lbl_bot_state = QLabel("🚨 Assistant State: INACTIVE (غير نشط)")
        self.lbl_bot_state.setStyleSheet("font-weight: bold; font-size: 13px; color: #ff3333;")
        
        sc_layout.addWidget(self.lbl_server_status)
        sc_layout.addWidget(self.lbl_bot_state)
        main_layout.addWidget(status_card)
        
        # Chrome Launch Button
        self.chrome_button = QPushButton("Launch Chrome with Extension 🌐 تشغيل كروم بالامتداد")
        self.chrome_button.setObjectName("chrome_btn")
        self.chrome_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chrome_button.setStyleSheet("""
            QPushButton#chrome_btn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0a1f24, stop:1 #113f4d);
                border: 1.5px solid rgba(137, 220, 254, 0.4);
                color: #ffffff;
                font-size: 14px;
                padding: 10px;
                margin-bottom: 5px;
            }
            QPushButton#chrome_btn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #11333d, stop:1 #1a5b6e);
                border: 1.5px solid #89dcfe;
            }
        """)
        self.chrome_button.clicked.connect(self.launch_chrome_with_extension)
        main_layout.addWidget(self.chrome_button)

        # Main Start / Stop Button
        self.start_button = QPushButton("Start Assistant Overlay | تشغيل المساعد")
        self.start_button.setObjectName("start_btn")
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_button.setStyleSheet("""
            QPushButton#start_btn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0a2412, stop:1 #114d23);
                border: 1.5px solid rgba(166, 227, 161, 0.4);
                color: #ffffff;
                font-size: 15px;
            }
            QPushButton#start_btn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #113d1e, stop:1 #186c32);
                border: 1.5px solid #a6e3a1;
            }
        """)
        self.start_button.clicked.connect(self.toggle_assistant_state)
        main_layout.addWidget(self.start_button)
        
        main_layout.addStretch()
 
    # --- Live Settings Synchronization with Config & Engine ---
    def update_game_mode(self, text):
        Config.GAME_MODE = text.lower()
        print(f"Sync Config: GAME_MODE = {Config.GAME_MODE}")
        
    def update_depth(self, val):
        self.lbl_depth_val.setText(str(val))
        Config.ENGINE_DEPTH = val
        self.update_elo_display()
        print(f"Sync Config: ENGINE_DEPTH = {Config.ENGINE_DEPTH}")
 
    def update_skill(self, val):
        self.lbl_skill_val.setText(str(val))
        Config.ENGINE_SKILL_LEVEL = val
        if self.worker and self.worker.engine:
            self.worker.engine._send_command(f"setoption name Skill Level value {val}")
        self.update_elo_display()
        print(f"Sync Config: ENGINE_SKILL_LEVEL = {Config.ENGINE_SKILL_LEVEL}")

    SKILL_TO_ELO = {
        1: 800, 2: 900, 3: 1000, 4: 1100, 5: 1200,
        6: 1300, 7: 1400, 8: 1500, 9: 1600, 10: 1700,
        11: 1850, 12: 2000, 13: 2150, 14: 2300, 15: 2450,
        16: 2600, 17: 2750, 18: 2900, 19: 3050, 20: 3200
    }

    def update_elo_display(self):
        skill = Config.ENGINE_SKILL_LEVEL
        estimated_elo = self.SKILL_TO_ELO.get(skill, 2000)
        
        # Classify the tier based on estimated ELO
        if estimated_elo <= 1000:
            tier = "Beginner / مبتدئ 💻"
        elif estimated_elo <= 1400:
            tier = "Intermediate / متوسط 📈"
        elif estimated_elo <= 1800:
            tier = "Advanced / متقدم 🧠"
        elif estimated_elo <= 2200:
            tier = "Expert / خبير 🏆"
        elif estimated_elo <= 2400:
            tier = "Master / ماستر 👑"
        elif estimated_elo <= 2600:
            tier = "International Master / أستاذ دولي 🎖️"
        else:
            tier = "Grandmaster / أستاذ كبير 🔮"
            
        self.lbl_elo_val.setText(f"{estimated_elo} ELO ({tier})")
 
    def update_randomize(self, state):
        Config.RANDOMIZE_MOVES = (state == Qt.CheckState.Checked.value)
        print(f"Sync Config: RANDOMIZE_MOVES = {Config.RANDOMIZE_MOVES}")
 
    def update_show_arrows(self, state):
        Config.SHOW_ARROWS = (state == Qt.CheckState.Checked.value)
        if self.overlay:
            self.overlay.update()
        print(f"Sync Config: SHOW_ARROWS = {Config.SHOW_ARROWS}")

    def update_stealth_display(self, state):
        enabled = (state == Qt.CheckState.Checked.value)
        Config.STEALTH_DISPLAY = enabled
        if self.overlay:
            self.overlay.set_stealth_mode(enabled)
        print(f"Sync Config: STEALTH_DISPLAY = {Config.STEALTH_DISPLAY}")

    def handle_stealth_toggled_from_worker(self, enabled):
        self.chk_stealth_display.blockSignals(True)
        self.chk_stealth_display.setChecked(Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
        self.chk_stealth_display.blockSignals(False)
        if self.overlay:
            self.overlay.set_stealth_mode(enabled)
 
    def update_threads(self, val):
        Config.ENGINE_THREADS = val
        if self.worker and self.worker.engine:
            self.worker.engine._send_command(f"setoption name Threads value {val}")
        print(f"Sync Config: ENGINE_THREADS = {Config.ENGINE_THREADS}")
 
    def update_scale(self, val):
        Config.OVERLAY_SCALE_FACTOR = val / 100.0
        if self.overlay and self.overlay.isVisible():
            self.overlay.update()
        print(f"Sync Config: OVERLAY_SCALE_FACTOR = {Config.OVERLAY_SCALE_FACTOR}")
 
    def update_bbox(self):
        x = self.spin_x.value()
        y = self.spin_y.value()
        w = self.spin_w.value()
        h = self.spin_h.value()
        Config.MANUAL_BOARD_BBOX = (x, y, w, h)
        print(f"Sync Config: MANUAL_BOARD_BBOX = {Config.MANUAL_BOARD_BBOX}")
 
    def start_calibration(self):
        self.hide()
        QApplication.processEvents()
        time.sleep(0.35)  # Give time for the dashboard to fully hide
        
        self.calibration_win = CalibrationOverlay(Config.MONITOR_INDEX)
        self.calibration_win.finished.connect(self.handle_calibration_finished)
        self.calibration_win.closed.connect(self.show)
        self.calibration_win.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.calibration_win.showFullScreen()

    def handle_calibration_finished(self, x, y, w, h):
        self.spin_x.setValue(x)
        self.spin_y.setValue(y)
        self.spin_w.setValue(w)
        self.spin_h.setValue(h)
        Config.MANUAL_BOARD_BBOX = (x, y, w, h)
        print(f"Calibration successful: MANUAL_BOARD_BBOX updated to {Config.MANUAL_BOARD_BBOX}")

    def launch_chrome_with_extension(self):
        import subprocess
        import os
        
        # Locate chrome paths on Windows
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"chrome" # Fallback to system path
        ]
        
        chrome_exe = None
        for path in chrome_paths:
            if path == "chrome" or os.path.exists(path):
                chrome_exe = path
                break
                
        if not chrome_exe:
            print("Error: Google Chrome executable not found on standard paths.")
            return
            
        ext_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extension")
        profile_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stealth_profile")
        
        # Build command flags
        cmd = [
            chrome_exe,
            f"--load-extension={ext_path}",
            f"--user-data-dir={profile_path}",
            "https://www.chess.com/play/online"
        ]
        
        print(f"Launching Chrome via: {' '.join(cmd)}")
        try:
            # Launch asynchronously without waiting
            subprocess.Popen(cmd, creationflags=0x08000000)
        except Exception as e:
            print(f"Error launching Chrome: {e}")

    # --- Bot Engine Execution Toggling ---
    def toggle_assistant_state(self):
        new_state = not self.worker.is_overlay_active
        self.worker.toggle_overlay(force_state=new_state)
 
    def handle_overlay_toggled(self, is_active):
        if is_active:
            self.lbl_bot_state.setText("🟢 Assistant State: ACTIVE (الوضع نشط)")
            self.lbl_bot_state.setStyleSheet("font-weight: bold; font-size: 13px; color: #2ecc71;")
            self.start_button.setText("Stop Assistant Overlay | إيقاف المساعد")
            self.start_button.setStyleSheet("""
                QPushButton#start_btn {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3d0c0c, stop:1 #801414);
                    border: 1.5px solid #ff3333;
                    color: #ffffff;
                    font-size: 15px;
                }
                QPushButton#start_btn:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #5c1414, stop:1 #ad2121);
                }
            """)
            self.overlay.show()
        else:
            self.lbl_bot_state.setText("🚨 Assistant State: INACTIVE (غير نشط)")
            self.lbl_bot_state.setStyleSheet("font-weight: bold; font-size: 13px; color: #ff3333;")
            self.start_button.setText("Start Assistant Overlay | تشغيل المساعد")
            self.start_button.setStyleSheet("""
                QPushButton#start_btn {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0a2412, stop:1 #114d23);
                    border: 1.5px solid rgba(166, 227, 161, 0.4);
                    color: #ffffff;
                    font-size: 15px;
                }
                QPushButton#start_btn:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #113d1e, stop:1 #186c32);
                    border: 1.5px solid #a6e3a1;
                }
            """)
            self.overlay.hide()
 
    def reset_key(self):
        self.license_manager.clear_local_key()
        if self.worker.is_overlay_active:
            self.worker.toggle_overlay(force_state=False)
        self.stacked_widget.setCurrentWidget(self.activation_widget)
        self.key_input.clear()
        self.act_status.setText("")
 
 
def main():
    app = QApplication(sys.argv)
    
    # Initialize the License Manager
    license_mgr = LicenseManager(api_url=Config.LICENSE_API_URL)
    license_mgr.load_local_key()
    
    # Pre-verify saved license key on launch (silent verification)
    if license_mgr.license_key:
        print("Pre-verifying active license key...")
        license_mgr.validate_key(license_mgr.license_key)
            
    # Initialize the transparent overlay (kept hidden initially)
    overlay = OverlayWindow()
    overlay.hide()
 
    # Pass the license manager to Worker
    worker = Worker(license_mgr)
    worker.update_ui.connect(overlay.update_data)
    
    # Initialize the Main Dashboard UI
    dashboard = ChessBotDashboard(license_mgr, overlay, worker)
    dashboard.show()
    
    # Start the core background processing thread
    thread = threading.Thread(target=worker.run, daemon=True)
    thread.start()
 
    sys.exit(app.exec())
 
 
if __name__ == "__main__":
    main()
