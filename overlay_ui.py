import sys
import ctypes
import math
from typing import List, Tuple, Optional
import mss
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QRect, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QPolygonF, QLinearGradient, QBrush, QFont, QPainterPath

from config import Config

class OverlayWindow(QWidget):
    """Transparent, click-through overlay window using PyQt6."""
    
    def __init__(self):
        super().__init__()
        self.moves: List[Tuple[str, str]] = [] 
        self.board_bbox: Optional[Tuple[int, int, int, int]] = None
        self.is_white_bottom = True
        self.time_left = 300.0
        
        # Get monitor bounds to align the overlay perfectly
        with mss.mss() as sct:
            self.monitor = sct.monitors[Config.MONITOR_INDEX]
            
        self.initUI()

    def initUI(self):
        # Frameless, transparent, always on top, click-through
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Align exactly with the target monitor's absolute coordinates
        self.setGeometry(self.monitor["left"], self.monitor["top"], self.monitor["width"], self.monitor["height"])
        self.show()

        # Hide window from screen recording/streaming based on config
        if sys.platform == "win32":
            try:
                hwnd = int(self.winId())
                affinity = 0x00000011 if getattr(Config, 'STEALTH_DISPLAY', True) else 0x00000000
                ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, affinity)
            except Exception as e:
                print(f"Failed to set initial screen capture display affinity: {e}")

        # Reusable font objects to avoid layout/system lookups in paintEvent
        self.font_segoe_9_bold = QFont("Segoe UI", 9, QFont.Weight.Bold)
        self.font_segoe_8_bold = QFont("Segoe UI", 8, QFont.Weight.Bold)
        self.font_segoe_13_bold = QFont("Segoe UI", 13, QFont.Weight.Bold)
        self.font_segoe_7_bold = QFont("Segoe UI", 7, QFont.Weight.Bold)
        self.font_segoe_7 = QFont("Segoe UI", 7)

    def set_stealth_mode(self, enabled: bool):
        """Dynamically toggle window visibility to screen recording/streaming tools."""
        if sys.platform == "win32":
            try:
                hwnd = int(self.winId())
                affinity = 0x00000011 if enabled else 0x00000000
                ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, affinity)
                print(f"Stealth display mode toggled to: {enabled} (affinity: {hex(affinity)})")
            except Exception as e:
                print(f"Failed to change screen capture display affinity: {e}")

    def update_data(self, moves: List[Tuple[str, str]], board_bbox: Tuple[int, int, int, int], is_white_bottom: bool, time_left: float):
        """Thread-safe update of the drawing data."""
        self.moves = moves
        self.board_bbox = board_bbox
        self.is_white_bottom = is_white_bottom
        self.time_left = time_left
        self.update() # Trigger immediate window repaint

    def _get_sq_rect(self, sq: str, left: float, top: float, sq_w: float, sq_h: float) -> QRectF:
        """Converts a square like 'e2' to its bounding box rectangle on the overlay."""
        file_char = sq[0]
        rank_char = sq[1]
        
        col = ord(file_char) - ord('a')
        row = 8 - int(rank_char)
        
        if not self.is_white_bottom:
            col = 7 - col
            row = 7 - row
            
        x = left + col * sq_w
        y = top + row * sq_h
        return QRectF(x, y, sq_w, sq_h)

    def draw_diamond(self, painter: QPainter, center: QPointF, size: float, color: QColor):
        """Draws a beautiful, glowing 3D-like Diamond symbol."""
        painter.save()
        glow = QColor(color.red(), color.green(), color.blue(), 60)
        painter.setBrush(glow)
        painter.setPen(Qt.PenStyle.NoPen)
        r_glow = size * 1.4
        p_glow = QPolygonF([
            QPointF(center.x(), center.y() - r_glow),
            QPointF(center.x() + r_glow, center.y()),
            QPointF(center.x(), center.y() + r_glow),
            QPointF(center.x() - r_glow, center.y())
        ])
        painter.drawPolygon(p_glow)

        painter.setBrush(color)
        painter.setPen(QPen(QColor(255, 255, 255, 200), 1.5))
        r = size
        p = QPolygonF([
            QPointF(center.x(), center.y() - r),
            QPointF(center.x() + r, center.y()),
            QPointF(center.x(), center.y() + r),
            QPointF(center.x() - r, center.y())
        ])
        painter.drawPolygon(p)
        
        painter.setBrush(QColor(255, 255, 255, 120))
        painter.setPen(Qt.PenStyle.NoPen)
        p_facet = QPolygonF([
            QPointF(center.x(), center.y() - r),
            QPointF(center.x() + r * 0.4, center.y()),
            QPointF(center.x(), center.y() + r * 0.4),
            QPointF(center.x() - r * 0.4, center.y())
        ])
        painter.drawPolygon(p_facet)
        painter.restore()

    def draw_star(self, painter: QPainter, center: QPointF, size: float, color: QColor):
        """Draws a premium 5-pointed Star with subtle glow and gold borders."""
        painter.save()
        glow = QColor(color.red(), color.green(), color.blue(), 50)
        painter.setBrush(glow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, size * 1.5, size * 1.5)

        painter.setBrush(color)
        painter.setPen(QPen(QColor(255, 255, 255, 200), 1.2))
        
        points = []
        for i in range(10):
            angle = math.radians(i * 36 - 90)
            r = size if i % 2 == 0 else size * 0.45
            points.append(QPointF(center.x() + r * math.cos(angle), center.y() + r * math.sin(angle)))
            
        painter.drawPolygon(QPolygonF(points))
        painter.restore()

    def draw_target(self, painter: QPainter, center: QPointF, size: float, color: QColor):
        """Draws a high-tech bullseye/target crosshair symbol."""
        painter.save()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        pen1 = QPen(color, 2)
        painter.setPen(pen1)
        painter.drawEllipse(center, size * 0.9, size * 0.9)
        
        pen2 = QPen(color, 1.2, Qt.PenStyle.DashLine)
        painter.setPen(pen2)
        painter.drawEllipse(center, size * 0.5, size * 0.5)
        
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, size * 0.22, size * 0.22)
        
        painter.setPen(QPen(color, 1.5))
        r = size * 1.15
        painter.drawLine(int(center.x() - r), int(center.y()), int(center.x() + r), int(center.y()))
        painter.drawLine(int(center.x()), int(center.y() - r), int(center.x()), int(center.y() + r))
        painter.restore()

    def draw_crown(self, painter: QPainter, center: QPointF, size: float, color: QColor):
        """Draws a beautiful, elegant royal Crown symbol (for checkmates)."""
        painter.save()
        glow = QColor(color.red(), color.green(), color.blue(), 60)
        painter.setBrush(glow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, size * 1.4, size * 1.4)
        
        painter.setBrush(color)
        painter.setPen(QPen(QColor(255, 255, 255, 200), 1.5))
        
        cx = center.x()
        cy = center.y()
        w = size * 1.3
        h = size * 1.0
        
        p = QPolygonF([
            QPointF(cx - w/2, cy + h/2),
            QPointF(cx - w/2 - 2, cy - h/3),
            QPointF(cx - w/3, cy - h/4), 
            QPointF(cx - w/4, cy + h/6), 
            QPointF(cx, cy - h/2),
            QPointF(cx + w/4, cy + h/6),
            QPointF(cx + w/3, cy - h/4),
            QPointF(cx + w/2 + 2, cy - h/3),
            QPointF(cx + w/2, cy + h/2),
        ])
        painter.drawPolygon(p)
        
        painter.setBrush(QColor(255, 255, 255, 200))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(cx - w/2 + 2, cy + h/2 - 3, w - 4, 3), 1, 1)
        painter.restore()

    def draw_warning_cross(self, painter: QPainter, center: QPointF, size: float, color: QColor):
        """Draws a crimson Warning Triangle with a bold Exclamation mark inside."""
        painter.save()
        cx = center.x()
        cy = center.y()
        r = size * 1.2
        
        p1 = QPointF(cx, cy - r)
        p2 = QPointF(cx + r, cy + r * 0.9)
        p3 = QPointF(cx - r, cy + r * 0.9)
        triangle = QPolygonF([p1, p2, p3])
        
        glow = QColor(color.red(), color.green(), color.blue(), 50)
        painter.setBrush(glow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(QPolygonF([p1 + QPointF(0, -2), p2 + QPointF(2, 2), p3 + QPointF(-2, 2)]))
        
        painter.setBrush(color)
        painter.setPen(QPen(QColor(255, 255, 255, 220), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPolygon(triangle)
        
        painter.setPen(QPen(QColor(255, 255, 255), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(int(cx), int(cy - r * 0.2), int(cx), int(cy + r * 0.3))
        
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy + r * 0.6), 1.8, 1.8)
        painter.restore()

    def draw_hud_dashboard(self, painter: QPainter, board_left: float, board_top: float, board_w: float, board_h: float):
        """Draws a beautiful, floating glassmorphic dashboard next to the board."""
        hud_w = 260
        hud_h = 320
        
        # Decide if HUD fits on the right or the left side of the board
        if board_left + board_w + hud_w + 30 <= self.width():
            hud_x = board_left + board_w + 25
        elif board_left - hud_w - 25 >= 0:
            hud_x = board_left - hud_w - 25
        else:
            hud_x = board_left + board_w - hud_w - 10
            
        hud_y = board_top
        
        # Draw soft outer card shadow
        painter.setBrush(QColor(0, 0, 0, 160))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(hud_x + 3, hud_y + 3, hud_w, hud_h), 12, 12)
        
        # Draw Main HUD Card background (Glassmorphic Gradient)
        hud_grad = QLinearGradient(hud_x, hud_y, hud_x, hud_y + hud_h)
        hud_grad.setColorAt(0, QColor(25, 25, 30, 240))
        hud_grad.setColorAt(1, QColor(15, 15, 20, 240))
        painter.setBrush(QBrush(hud_grad))
        
        # Change border color depending on time panic state
        border_color = QColor(27, 172, 166, 180) # Default Teal
        if self.time_left <= 15:
            border_color = QColor(235, 60, 60, 220) # Red Panic
        elif self.time_left <= 60:
            border_color = QColor(240, 150, 20, 200) # Orange Warning
            
        painter.setPen(QPen(border_color, 2))
        painter.drawRoundedRect(QRectF(hud_x, hud_y, hud_w, hud_h), 12, 12)
        
        # 1. Header
        painter.setFont(self.font_segoe_9_bold)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRectF(hud_x + 15, hud_y + 15, hud_w - 30, 25), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "🛡️ STEALTH AI ENGINE HUD")
        
        # Separator line
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.drawLine(int(hud_x + 15), int(hud_y + 40), int(hud_x + hud_w - 15), int(hud_y + 40))
        
        # Get score values
        best_score_str = "0.00"
        if self.moves:
            best_score_str = self.moves[0][1]
            
        score_val = 0.0
        is_mate = False
        if "M" in best_score_str:
            is_mate = True
            score_val = 5.0 if "-" not in best_score_str else -5.0
        else:
            try:
                score_val = float(best_score_str)
            except ValueError:
                score_val = 0.0
                
        # 2. Draw live vertical White/Black Power balance bar
        bar_x = hud_x + 20
        bar_y = hud_y + 55
        bar_w = 12
        bar_h = 100
        
        # Black background
        painter.setBrush(QColor(40, 40, 45))
        painter.setPen(QPen(QColor(255, 255, 255, 50), 1))
        painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 3, 3)
        
        # White fill height representing score [-5.0, 5.0]
        clamped = max(-5.0, min(5.0, score_val))
        ratio = (clamped + 5.0) / 10.0
        white_h = bar_h * ratio
        
        # White fill from bottom upwards
        painter.setBrush(QColor(240, 240, 240))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(bar_x, bar_y + bar_h - white_h, bar_w, white_h), 3, 3)
        
        # Center evaluation tick
        painter.setPen(QPen(QColor(128, 128, 135, 180), 1))
        painter.drawLine(int(bar_x - 3), int(bar_y + bar_h / 2), int(bar_x + bar_w + 3), int(bar_y + bar_h / 2))
        
        # 3. Draw Engine Evaluation card
        score_card_x = hud_x + 45
        score_card_y = hud_y + 55
        score_card_w = hud_w - 65
        score_card_h = 45
        
        painter.setBrush(QColor(30, 30, 35, 180))
        painter.setPen(QPen(border_color, 1))
        painter.drawRoundedRect(QRectF(score_card_x, score_card_y, score_card_w, score_card_h), 8, 8)
        
        painter.setFont(self.font_segoe_8_bold)
        painter.setPen(QColor(180, 180, 190))
        painter.drawText(QRectF(score_card_x + 10, score_card_y + 5, score_card_w - 20, 15), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, "ENGINE EVAL")
        
        painter.setFont(self.font_segoe_13_bold)
        if score_val > 0.3:
            score_color = QColor(38, 187, 92) # Green
        elif score_val < -0.3:
            score_color = QColor(235, 60, 60) # Red
        else:
            score_color = QColor(255, 255, 255)
            
        if is_mate:
            score_color = QColor(138, 43, 226) # Purple
            
        painter.setPen(score_color)
        disp_score = f"{best_score_str}"
        if not disp_score.startswith("-") and not disp_score.startswith("+") and not disp_score.startswith("M") and score_val > 0:
            disp_score = f"+{disp_score}"
            
        painter.drawText(QRectF(score_card_x + 10, score_card_y + 20, score_card_w - 20, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, disp_score)
        
        # 4. Draw Time Left card
        time_card_x = hud_x + 45
        time_card_y = hud_y + 110
        time_card_w = hud_w - 65
        time_card_h = 45
        
        painter.setBrush(QColor(30, 30, 35, 180))
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
        painter.drawRoundedRect(QRectF(time_card_x, time_card_y, time_card_w, time_card_h), 8, 8)
        
        painter.setFont(self.font_segoe_8_bold)
        painter.setPen(QColor(180, 180, 190))
        painter.drawText(QRectF(time_card_x + 10, time_card_y + 5, time_card_w - 20, 15), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, "TIME REMAINING")
        
        # Format clock MM:SS
        m = int(self.time_left // 60)
        s = int(self.time_left % 60)
        clock_str = f"{m:02d}:{s:02d}"
        
        panic_text = "SAFE"
        panic_color = QColor(38, 187, 92)
        if self.time_left <= 15:
            panic_text = "PANIC!"
            panic_color = QColor(235, 60, 60)
        elif self.time_left <= 60:
            panic_text = "WARNING"
            panic_color = QColor(240, 150, 20)
            
        painter.setFont(self.font_segoe_13_bold)
        painter.setPen(panic_color)
        painter.drawText(QRectF(time_card_x + 10, time_card_y + 20, 80, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, clock_str)
        
        # Panic pill badge
        painter.setFont(self.font_segoe_7_bold)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(panic_color.red(), panic_color.green(), panic_color.blue(), 40))
        
        pill_w = 60
        pill_h = 16
        pill_x = time_card_x + time_card_w - pill_w - 8
        pill_y = time_card_y + 15
        painter.drawRoundedRect(QRectF(pill_x, pill_y, pill_w, pill_h), 4, 4)
        
        painter.setPen(panic_color)
        painter.drawText(QRectF(pill_x, pill_y, pill_w, pill_h), Qt.AlignmentFlag.AlignCenter, panic_text)
        
        # 5. Candidate Moves Grid
        grid_y = hud_y + 165
        painter.setFont(self.font_segoe_8_bold)
        painter.setPen(QColor(255, 255, 255, 180))
        painter.drawText(QRectF(hud_x + 15, grid_y, hud_w - 30, 15), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "CANDIDATE MOVES")
        
        # Divider line
        painter.setPen(QPen(QColor(255, 255, 255, 25), 1))
        painter.drawLine(int(hud_x + 15), int(grid_y + 18), int(hud_x + hud_w - 15), int(grid_y + 18))
        
        row_y = grid_y + 24
        row_h = 24
        
        parsed_scores = []
        best_score_val = 0.0
        
        for move_uci, s_str in self.moves:
            val = 0.0
            is_m = False
            if "M" in s_str:
                is_m = True
                try:
                    val = 1000.0 if "-" not in s_str else -1000.0
                except Exception:
                    val = 1000.0
            else:
                try:
                    val = float(s_str)
                except ValueError:
                    val = 0.0
            parsed_scores.append((val, is_m))
            
        if parsed_scores:
            best_score_val = parsed_scores[0][0]
            
        for idx, (move_uci, s_str) in enumerate(self.moves):
            if idx >= 3:
                break
                
            score_val, is_m = parsed_scores[idx]
            
            classification = "GOOD"
            color = QColor(240, 150, 20)
            badge_text = "GOOD"
            
            if is_m:
                classification = "MATE"
                color = QColor(138, 43, 226)
                badge_text = "MATE"
            elif idx == 0:
                if score_val >= 3.5:
                    classification = "BRILLIANT"
                    color = QColor(27, 172, 166)
                    badge_text = "BRILLIANT"
                else:
                    classification = "BEST"
                    color = QColor(38, 187, 92)
                    badge_text = "BEST"
            else:
                diff = abs(best_score_val - score_val)
                if diff >= 2.0:
                    classification = "BAD"
                    color = QColor(235, 60, 60)
                    badge_text = "BLUNDER"
                elif diff >= 1.0:
                    classification = "INACCURACY"
                    color = QColor(240, 100, 40)
                    badge_text = "INACCURACY"
                elif diff <= 0.35:
                    classification = "EXCELLENT"
                    color = QColor(149, 183, 33)
                    badge_text = "EXCELLENT"
                else:
                    classification = "GOOD"
                    color = QColor(240, 150, 20)
                    badge_text = "GOOD"
                    
            # Zebra row background
            bg_color = QColor(255, 255, 255, 8) if idx % 2 == 0 else QColor(0, 0, 0, 12)
            painter.setBrush(bg_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(hud_x + 15, row_y, hud_w - 30, row_h - 4), 4, 4)
            
            # Indicator dot
            painter.setBrush(color)
            painter.drawEllipse(QPointF(hud_x + 25, row_y + row_h / 2 - 2), 4, 4)
            
            # Algebraic Move notation
            painter.setFont(self.font_segoe_8_bold)
            painter.setPen(QColor(240, 240, 255))
            painter.drawText(QRectF(hud_x + 38, row_y, 70, row_h - 4), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"{idx+1}. {move_uci}")
            
            # centipawn value
            disp_cp = s_str
            if not disp_cp.startswith("-") and not disp_cp.startswith("+") and not disp_cp.startswith("M") and score_val > 0:
                disp_cp = f"+{disp_cp}"
                
            painter.setFont(self.font_segoe_7)
            painter.setPen(QColor(180, 180, 190))
            painter.drawText(QRectF(hud_x + 105, row_y, 45, row_h - 4), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, disp_cp)
            
            # Badge pill
            badge_w = 60
            badge_h = 13
            badge_x = hud_x + hud_w - 15 - badge_w - 5
            badge_y = row_y + (row_h - badge_h) / 2 - 2
            
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 30))
            painter.drawRoundedRect(QRectF(badge_x, badge_y, badge_w, badge_h), 3, 3)
            
            painter.setFont(self.font_segoe_7_bold)
            painter.setPen(color)
            painter.drawText(QRectF(badge_x, badge_y, badge_w, badge_h), Qt.AlignmentFlag.AlignCenter, badge_text)
            
            row_y += row_h
            
        # 6. Shortcuts at the bottom
        shortcuts_y = hud_y + 275
        painter.setPen(QPen(QColor(255, 255, 255, 25), 1))
        painter.drawLine(int(hud_x + 15), int(shortcuts_y), int(hud_x + hud_w - 15), int(shortcuts_y))
        
        painter.setFont(self.font_segoe_7)
        painter.setPen(QColor(150, 150, 160))
        shortcut_text = f"🔄 {Config.HOTKEY_TOGGLE.upper()} : إخفاء/إظهار  |  ❌ {Config.HOTKEY_EXIT.upper()} : خروج"
        painter.drawText(QRectF(hud_x + 10, shortcuts_y + 8, hud_w - 20, 20), Qt.AlignmentFlag.AlignCenter, shortcut_text)
    def paintEvent(self, event):
        """Draws the board highlights, tactical symbols, arrows, and floating HUD dashboard."""
        if not self.moves or not self.board_bbox:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Convert board_bbox to local coordinates
        abs_left, abs_top, width, height = self.board_bbox
        
        abs_left = (abs_left / Config.OVERLAY_SCALE_FACTOR) + Config.OVERLAY_OFFSET_X
        abs_top = (abs_top / Config.OVERLAY_SCALE_FACTOR) + Config.OVERLAY_OFFSET_Y
        width = width / Config.OVERLAY_SCALE_FACTOR
        height = height / Config.OVERLAY_SCALE_FACTOR
        
        local_left = abs_left - (self.monitor["left"] / Config.OVERLAY_SCALE_FACTOR)
        local_top = abs_top - (self.monitor["top"] / Config.OVERLAY_SCALE_FACTOR)
        
        sq_w = width / 8
        sq_h = height / 8
        
        # --- Draw floating glassmorphic HUD dashboard first ---
        self.draw_hud_dashboard(painter, local_left, local_top, width, height)
        
        # If arrows are disabled, only show HUD and skip board drawing
        if not Config.SHOW_ARROWS:
            painter.end()
            return
        
        # Pre-parse scores to determine move classification and comparisons
        parsed_scores = []
        best_score_val = 0.0
        
        for move_uci, score_str in self.moves:
            val = 0.0
            is_mate = False
            if "M" in score_str:
                is_mate = True
                try:
                    val = 1000.0 if "-" not in score_str else -1000.0
                except Exception:
                    val = 1000.0
            else:
                try:
                    val = float(score_str)
                except ValueError:
                    val = 0.0
            parsed_scores.append((val, is_mate))
            
        if parsed_scores:
            best_score_val = parsed_scores[0][0]

        # Draw candidate moves in reverse order so the best move is drawn on top of inferior ones
        for i, (move_uci, score) in reversed(list(enumerate(self.moves))):
            if i >= len(parsed_scores):
                continue
                
            score_val, is_mate = parsed_scores[i]
            if len(move_uci) < 4:
                continue
 
            # Determine classification, custom color, and tag text
            classification = "GOOD"
            color = QColor(240, 150, 20, 180) # Orange default
            badge_text = "GOOD"
            
            if is_mate:
                classification = "MATE"
                color = QColor(138, 43, 226, 200) # Royal Purple
                mate_num = score.replace("M", "").replace("+", "").replace("-", "")
                badge_text = f"MATE #{mate_num}"
            elif i == 0:
                # 1st best move
                if score_val >= 3.5:
                    classification = "BRILLIANT"
                    color = QColor(27, 172, 166, 210) # Vibrant Teal
                    badge_text = "BRILLIANT !!"
                else:
                    classification = "BEST"
                    color = QColor(38, 187, 92, 210) # Vibrant Green
                    badge_text = "BEST !"
            else:
                # 2nd or 3rd moves
                diff = abs(best_score_val - score_val)
                if diff >= 2.0:
                    classification = "BAD"
                    color = QColor(235, 60, 60, 210) # Crimson Red
                    badge_text = "BLUNDER ❌"
                elif diff >= 1.0:
                    classification = "INACCURACY"
                    color = QColor(240, 100, 40, 180) # Orange/Red
                    badge_text = "INACCURACY ⚠️"
                elif diff <= 0.35:
                    classification = "EXCELLENT"
                    color = QColor(149, 183, 33, 200) # Lime Green
                    badge_text = "EXCELLENT !"
                else:
                    classification = "GOOD"
                    color = QColor(240, 150, 20, 180) # Yellow-Orange
                    badge_text = "GOOD"
 
            start_sq = move_uci[:2]
            end_sq = move_uci[2:4]
            
            start_x, start_y = self._sq_to_coords(start_sq, local_left, local_top, sq_w, sq_h)
            end_x, end_y = self._sq_to_coords(end_sq, local_left, local_top, sq_w, sq_h)
 
            start_rect = self._get_sq_rect(start_sq, local_left, local_top, sq_w, sq_h)
            end_rect = self._get_sq_rect(end_sq, local_left, local_top, sq_w, sq_h)
            
            # --- A. Draw Sleek Board Square Highlights ---
            fill_color = QColor(color.red(), color.green(), color.blue(), 25 if i != 0 else 40)
            painter.setBrush(fill_color)
            border_pen = QPen(color, 2.0 if i == 0 else 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(border_pen)
            
            painter.drawRoundedRect(start_rect.adjusted(3, 3, -3, -3), 6, 6)
            painter.drawRoundedRect(end_rect.adjusted(3, 3, -3, -3), 6, 6)
            
            # --- B. Draw Premium Tactical Symbol inside destination square ---
            center_pt = QPointF(end_x, end_y)
            symbol_size = min(sq_w, sq_h) * 0.16
            
            if classification == "MATE":
                self.draw_crown(painter, center_pt, symbol_size, color)
            elif classification == "BRILLIANT":
                self.draw_diamond(painter, center_pt, symbol_size, color)
            elif classification == "BEST":
                self.draw_target(painter, center_pt, symbol_size, color)
            elif classification == "EXCELLENT":
                self.draw_star(painter, center_pt, symbol_size, color)
            elif classification == "BAD":
                self.draw_warning_cross(painter, center_pt, symbol_size, color)

            # --- C. Draw Connective 3D Arrows ---
            dx = end_x - start_x
            dy = end_y - start_y
            length = math.hypot(dx, dy)
            if length < 1e-3:
                continue
            
            # Normalize vector
            ux = dx / length
            uy = dy / length
 
            # Shorten arrow slightly so it doesn't overlap symbols/square borders
            padding_start = 12
            padding_end = 26 if classification in ["BEST", "BRILLIANT", "EXCELLENT", "MATE", "BAD"] else 20
            
            new_start_x = start_x + ux * padding_start
            new_start_y = start_y + uy * padding_start
            new_end_x = start_x + ux * (length - padding_end)
            new_end_y = start_y + uy * (length - padding_end)
 
            # Draw outer glow / shadow for premium glassmorphic feel
            shadow_color = QColor(0, 0, 0, 80)
            shadow_pen = QPen(shadow_color, 9 if i == 0 else 6.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(shadow_pen)
            painter.drawLine(int(new_start_x), int(new_start_y), int(new_end_x), int(new_end_y))
 
            # Draw main shaft (sleek and vibrant)
            pen_width = 5.5 if i == 0 else 3.5
            shaft_pen = QPen(color, pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(shaft_pen)
            painter.drawLine(int(new_start_x), int(new_start_y), int(new_end_x), int(new_end_y))
            
            # Draw beautiful arrow head (triangle pointing to destination)
            arrow_head_size = 17 if i == 0 else 13
            
            # Perpendicular vector
            px = -uy
            py = ux
            
            p1 = QPointF(new_end_x, new_end_y)
            p2 = QPointF(new_end_x - ux * arrow_head_size + px * (arrow_head_size * 0.65),
                         new_end_y - uy * arrow_head_size + py * (arrow_head_size * 0.65))
            p3 = QPointF(new_end_x - ux * arrow_head_size - px * (arrow_head_size * 0.65),
                         new_end_y - uy * arrow_head_size - py * (arrow_head_size * 0.65))
            
            arrow_head = QPolygonF([p1, p2, p3])
            
            # Arrow head shadow
            painter.setBrush(shadow_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPolygon(QPolygonF([p1 + QPointF(1, 1), p2 + QPointF(1, 1), p3 + QPointF(1, 1)]))
 
            # Main arrow head
            painter.setBrush(color)
            painter.drawPolygon(arrow_head)
            
            # Draw a premium circular node at the start point
            node_r = 6.0 if i == 0 else 4.0
            painter.setBrush(color)
            painter.setPen(QPen(QColor(255, 255, 255, 200), 1.2))
            painter.drawEllipse(QPointF(new_start_x, new_start_y), node_r, node_r)
            
            # --- Draw Elegant Score Tag / Badge at destination ---
            score_text = str(score)
            
            if score_text.startswith("M"):
                score_text = f"#{score_text[1:]}"
            elif not score_text.startswith("-") and not score_text.startswith("+"):
                try:
                    val = float(score_text)
                    if val > 0:
                        score_text = f"+{score_text}"
                except ValueError:
                    pass
            
            badge_label = f"{badge_text} ({score_text})"
 
            painter.setFont(self.font_segoe_8_bold)
            
            # Measure text size
            metrics = painter.fontMetrics()
            text_rect = metrics.boundingRect(badge_label)
            
            # Badge dimensions
            padding_x = 8
            padding_y = 4
            badge_w = int(text_rect.width() + padding_x * 2)
            badge_h = int(text_rect.height() + padding_y * 2)
            
            badge_x = int(end_x - badge_w / 2)
            badge_y = int(end_y - badge_h / 2 - 26) # Float above the arrow tip
            
            # Draw Badge Shadow
            painter.setBrush(QColor(0, 0, 0, 140))
            painter.drawRoundedRect(QRect(badge_x + 1, badge_y + 1, badge_w, badge_h), 5, 5)
            
            # Draw Badge Background (Dark premium glassmorphic with dynamic border)
            painter.setBrush(QColor(20, 20, 25, 230))
            painter.setPen(QPen(color, 1.5))
            painter.drawRoundedRect(QRect(badge_x, badge_y, badge_w, badge_h), 5, 5)
            
            # Draw Text
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(QRect(badge_x, badge_y, badge_w, badge_h), Qt.AlignmentFlag.AlignCenter, badge_label)

        painter.end()

    def _sq_to_coords(self, sq: str, left: float, top: float, sq_w: float, sq_h: float) -> Tuple[float, float]:
        """Converts a square like 'e2' to local screen coordinates (center of the square)."""
        file_char = sq[0]
        rank_char = sq[1]
        
        col = ord(file_char) - ord('a')
        row = 8 - int(rank_char)
        
        if not self.is_white_bottom:
            col = 7 - col
            row = 7 - row
            
        x = left + col * sq_w + sq_w / 2
        y = top + row * sq_h + sq_h / 2
        return x, y
