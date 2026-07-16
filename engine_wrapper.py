import subprocess
import chess
from typing import List, Tuple, Optional
from config import Config
import random

class EngineWrapper:
    """Wrapper for the Stockfish engine using python-chess and subprocess."""
    
    def __init__(self):
        self.engine_path = Config.STOCKFISH_PATH
        self.board = chess.Board()
        self.process: Optional[subprocess.Popen] = None
        self.is_white_turn = True
        self.last_matrix = None
        self._start_engine()

    def _start_engine(self):
        """Starts the Stockfish subprocess."""
        try:
            import sys
            creationflags = 0
            if sys.platform == "win32":
                # BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
                creationflags = 0x00004000

            self.process = subprocess.Popen(
                [self.engine_path],
                universal_newlines=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,
                creationflags=creationflags
            )
            self._send_command("uci")
            self._send_command(f"setoption name Threads value {Config.ENGINE_THREADS}")
            self._send_command(f"setoption name Hash value {Config.ENGINE_HASH}")
            self._send_command(f"setoption name Skill Level value {Config.ENGINE_SKILL_LEVEL}")
            self._send_command("isready")
        except FileNotFoundError:
            print(f"ERROR: Stockfish not found at {self.engine_path}. Please update config.py.")
            self.process = None
        except Exception as e:
            print(f"ERROR: Failed to start Stockfish: {e}")
            self.process = None

    def _send_command(self, command: str) -> bool:
        """Sends a command to the engine. Returns True if successful, False if the engine pipe is broken."""
        if self.process and self.process.stdin:
            try:
                self.process.stdin.write(command + "\n")
                self.process.stdin.flush()
                return True
            except (OSError, BrokenPipeError) as e:
                print(f"ERROR: Failed to write to Stockfish ({e}). The engine may have crashed.")
                return False
        return False

    def _read_output(self, stop_condition: str) -> List[str]:
        """Reads output from the engine until the stop condition is met."""
        lines = []
        if self.process and self.process.stdout:
            while True:
                raw_line = self.process.stdout.readline()
                if raw_line == '': # EOF, engine crashed or pipe broken
                    print("ERROR: Engine subprocess died or stdout closed!")
                    break
                    
                line = raw_line.strip()
                if line:
                    lines.append(line)
                if stop_condition in line:
                    break
        return lines

    def update_turn(self, matrix: List[List[str]]):
        """Updates whose turn it is by analyzing the matrix changes."""
        if self.last_matrix is None:
            self.last_matrix = matrix
            return

        new_white = False
        new_black = False
        for r in range(8):
            for c in range(8):
                old = self.last_matrix[r][c]
                new = matrix[r][c]
                if old != new:
                    if new.isupper(): new_white = True
                    if new.islower(): new_black = True
        
        if new_white: self.is_white_turn = False
        elif new_black: self.is_white_turn = True
        
        self.last_matrix = matrix

    def matrix_to_fen(self, matrix: List[List[str]]) -> str:
        """Converts an 8x8 matrix to a FEN string."""
        fen_rows = []
        for row in matrix:
            empty_count = 0
            fen_row = ""
            for sq in row:
                if sq == '':
                    empty_count += 1
                else:
                    if empty_count > 0:
                        fen_row += str(empty_count)
                        empty_count = 0
                    fen_row += sq
            if empty_count > 0:
                fen_row += str(empty_count)
            fen_rows.append(fen_row)
        
        active_color = 'w' if self.is_white_turn else 'b'
        # Construct the FEN. We ignore castling/en passant for this basic state representation.
        fen = "/".join(fen_rows) + f" {active_color} - - 0 1"
        return fen

    def get_best_moves(self, fen: str, num_moves: int = 3) -> List[Tuple[str, str]]:
        """
        Evaluates the position and returns the top N best moves.
        Returns a list of tuples: (move_uci, score_str)
        """
        if self.process is None or self.process.poll() is not None:
            print("Stockfish process is dead. Restarting engine...")
            self._start_engine()
            
        if not self.process:
            return []

        try:
            self.board.set_fen(fen)
            if not self.board.is_valid():
                # FEN is structurally valid but illegal for chess rules (e.g. king can be captured)
                # Stockfish can crash if given highly invalid FENs.
                return []
        except ValueError:
            # Invalid FEN string (can happen during piece animation transitions)
            return []

        success1 = self._send_command(f"setoption name MultiPV value {num_moves}")
        success2 = self._send_command(f"position fen {fen}")
        success3 = self._send_command(f"go depth {Config.ENGINE_DEPTH}")
        
        if not (success1 and success2 and success3):
            # Engine crashed while sending commands, restart it for next time
            print("Restarting Stockfish due to communication failure...")
            self._start_engine()
            return []

        output = self._read_output("bestmove")
        
        moves = []
        for line in output:
            if "info depth" in line and " pv " in line:
                parts = line.split()
                try:
                    pv_idx = parts.index("pv")
                    move = parts[pv_idx + 1]
                    
                    score_str = ""
                    if "cp" in parts:
                        cp_idx = parts.index("cp")
                        score_str = f"{int(parts[cp_idx + 1]) / 100:.2f}"
                    elif "mate" in parts:
                        mate_idx = parts.index("mate")
                        score_str = f"M{parts[mate_idx + 1]}"

                    if "multipv" in parts:
                        mpv_idx = parts.index("multipv")
                        rank = int(parts[mpv_idx + 1])
                        
                        if rank > len(moves):
                            moves.append((move, score_str))
                        else:
                            moves[rank - 1] = (move, score_str)
                except ValueError:
                    continue

        # Anti-Ban Humanization: Force the user to play slightly imperfect moves
        # At 1800 ELO, players do not always find the absolute best move.
        if Config.RANDOMIZE_MOVES and len(moves) >= 2:
            try:
                move1, score1_str = moves[0]
                move2, score2_str = moves[1]
                
                # Never scramble if it's a forced mate
                if "M" not in score1_str and "M" not in score2_str:
                    score1 = float(score1_str)
                    score2 = float(score2_str)
                    
                    # If the second best move is decent (within 1.5 pawns of the best move)
                    if abs(score1 - score2) < 1.50:
                        rand_val = random.random()
                        # 40% chance to put the 2nd best move as the Green arrow
                        if rand_val < 0.40:
                            moves[0], moves[1] = moves[1], moves[0]
                        # 20% chance to put the 3rd best move as the Green arrow (if it exists)
                        elif rand_val < 0.60 and len(moves) >= 3:
                            move3, score3_str = moves[2]
                            if "M" not in score3_str:
                                score3 = float(score3_str)
                                if abs(score1 - score3) < 2.0:
                                    moves[0], moves[2] = moves[2], moves[0]
            except ValueError:
                pass

        return moves[:num_moves]

    def close(self):
        """Terminates the engine gracefully."""
        if self.process:
            self._send_command("quit")
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
