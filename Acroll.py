import pygame
import sys
from collections import deque

# --- Constants ---
CELL_SIZE = 10
COLS = 80
ROWS = 60
UI_HEIGHT = 40
WIDTH = COLS * CELL_SIZE
HEIGHT = ROWS * CELL_SIZE + UI_HEIGHT
FPS = 20

# Colors
COLORS = {
    "bg": (232, 232, 232),
    "ui_bg": (40, 40, 40),
    "text": (255, 255, 255),
    0: (232, 232, 232),          # Empty
    1: (255, 87, 51),            # P1 Territory (Orange)
    2: (51, 128, 255),           # P2 Territory (Blue)
    3: (255, 184, 168),          # P1 Trail
    4: (168, 200, 255),          # P2 Trail
    "p1_head": (200, 40, 20),
    "p2_head": (20, 80, 200)
}

class PaperIOGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("CG-io: Area Control (Pygame Edition)")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Segoe UI", 24, bold=True)
        self.large_font = pygame.font.SysFont("Segoe UI", 48, bold=True)
        
        self.state = "START" # START, PLAYING, GAME_OVER
        self.winner_msg = ""
        self.reset_game()

    def reset_game(self):
        # 0: Empty, 1: P1 Terr, 2: P2 Terr, 3: P1 Trail, 4: P2 Trail
        self.grid = [[0 for _ in range(ROWS)] for _ in range(COLS)]
        
        self.p1 = {
            "id": 1, "trail_id": 3, "head_color": COLORS["p1_head"],
            "x": 15, "y": ROWS // 2, "dx": 0, "dy": -1, "next_dx": 0, "next_dy": -1,
            "is_dead": False, "has_trail": False, "trail_points": [], "score": 9
        }
        self.p2 = {
            "id": 2, "trail_id": 4, "head_color": COLORS["p2_head"],
            "x": COLS - 15, "y": ROWS // 2, "dx": 0, "dy": -1, "next_dx": 0, "next_dy": -1,
            "is_dead": False, "has_trail": False, "trail_points": [], "score": 9
        }
        
        self._create_start_territory(self.p1)
        self._create_start_territory(self.p2)

    def _create_start_territory(self, player):
        px, py = player["x"], player["y"]
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                self.grid[px + dx][py + dy] = player["id"]

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.KEYDOWN:
                if self.state == "START":
                    self.state = "PLAYING"
                elif self.state == "GAME_OVER":
                    if event.key == pygame.K_SPACE:
                        self.reset_game()
                        self.state = "PLAYING"
                elif self.state == "PLAYING":
                    # Player 1 (WASD)
                    if event.key == pygame.K_w and self.p1["dy"] != 1:
                        self.p1["next_dx"], self.p1["next_dy"] = 0, -1
                    elif event.key == pygame.K_s and self.p1["dy"] != -1:
                        self.p1["next_dx"], self.p1["next_dy"] = 0, 1
                    elif event.key == pygame.K_a and self.p1["dx"] != 1:
                        self.p1["next_dx"], self.p1["next_dy"] = -1, 0
                    elif event.key == pygame.K_d and self.p1["dx"] != -1:
                        self.p1["next_dx"], self.p1["next_dy"] = 1, 0
                        
                    # Player 2 (Arrows)
                    if event.key == pygame.K_UP and self.p2["dy"] != 1:
                        self.p2["next_dx"], self.p2["next_dy"] = 0, -1
                    elif event.key == pygame.K_DOWN and self.p2["dy"] != -1:
                        self.p2["next_dx"], self.p2["next_dy"] = 0, 1
                    elif event.key == pygame.K_LEFT and self.p2["dx"] != 1:
                        self.p2["next_dx"], self.p2["next_dy"] = -1, 0
                    elif event.key == pygame.K_RIGHT and self.p2["dx"] != -1:
                        self.p2["next_dx"], self.p2["next_dy"] = 1, 0

    def update(self):
        if self.state != "PLAYING":
            return

        for p in (self.p1, self.p2):
            if p["is_dead"]: continue

            # Apply buffered direction
            p["dx"], p["dy"] = p["next_dx"], p["next_dy"]

            nx = p["x"] + p["dx"]
            ny = p["y"] + p["dy"]

            # Stop at walls (no death)
            if nx < 0 or nx >= COLS or ny < 0 or ny >= ROWS:
                continue

            target_cell = self.grid[nx][ny]

            # Territory & Movement Logic
            if target_cell == p["id"]:
                # Moving into own territory -> close the loop
                if p["has_trail"]:
                    self.capture_territory(p)
                    self.check_encirclement(p)
                    self.update_scores()
                p["has_trail"] = False
            else:
                # Moving through empty space, enemy territory, or trails -> leave a trail
                self.grid[nx][ny] = p["trail_id"]
                p["has_trail"] = True
                if (nx, ny) not in p["trail_points"]:
                    p["trail_points"].append((nx, ny))

            p["x"], p["y"] = nx, ny

        if self.p1["is_dead"] or self.p2["is_dead"]:
            self.state = "GAME_OVER"

    def capture_territory(self, player):
        """Outside-In Flood Fill (BFS) to capture encircled areas."""
        pid = player["id"]
        tid = player["trail_id"]
        
        visited = set()
        queue = deque()
        
        # 1. Queue boundary cells
        for x in range(COLS):
            queue.append((x, 0))
            queue.append((x, ROWS - 1))
        for y in range(ROWS):
            queue.append((0, y))
            queue.append((COLS - 1, y))

        # 2. BFS to find outside area
        while queue:
            cx, cy = queue.popleft()
            if (cx, cy) in visited: continue
            if cx < 0 or cx >= COLS or cy < 0 or cy >= ROWS: continue
            
            val = self.grid[cx][cy]
            if val == pid or val == tid: continue
                
            visited.add((cx, cy))
            queue.extend([(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)])

        # 3. Capture enclosed area
        for x in range(COLS):
            for y in range(ROWS):
                if (x, y) not in visited:
                    self.grid[x][y] = pid
        
        player["trail_points"].clear()

    def check_encirclement(self, active_player):
        """Check if enemy was trapped in the capture fill."""
        enemy = self.p2 if active_player["id"] == 1 else self.p1
        
        # Enemy head encircled
        if self.grid[enemy["x"]][enemy["y"]] == active_player["id"]:
            enemy["is_dead"] = True
            self.winner_msg = f"Player {active_player['id']} Wins! (Encircled Enemy)"
            return
            
        # Enemy lost all territory
        enemy_territory_count = sum(row.count(enemy["id"]) for row in self.grid)
        if enemy_territory_count == 0:
            enemy["is_dead"] = True
            self.winner_msg = f"Player {active_player['id']} Wins! (Wiped out Enemy)"

    def update_scores(self):
        self.p1["score"] = sum(row.count(self.p1["id"]) for row in self.grid)
        self.p2["score"] = sum(row.count(self.p2["id"]) for row in self.grid)

    def draw(self):
        self.screen.fill(COLORS["bg"])

        # Draw Grid
        for x in range(COLS):
            for y in range(ROWS):
                val = self.grid[x][y]
                if val != 0:
                    rect = (x * CELL_SIZE, y * CELL_SIZE + UI_HEIGHT, CELL_SIZE, CELL_SIZE)
                    pygame.draw.rect(self.screen, COLORS[val], rect)

        # Draw Player Heads
        for p in (self.p1, self.p2):
            if not p["is_dead"]:
                rect = (p["x"] * CELL_SIZE, p["y"] * CELL_SIZE + UI_HEIGHT, CELL_SIZE, CELL_SIZE)
                # Outline
                pygame.draw.rect(self.screen, COLORS["ui_bg"], 
                                 (rect[0]-2, rect[1]-2, CELL_SIZE+4, CELL_SIZE+4))
                # Inner head
                pygame.draw.rect(self.screen, p["head_color"], rect)

        # Draw UI Bar
        pygame.draw.rect(self.screen, COLORS["ui_bg"], (0, 0, WIDTH, UI_HEIGHT))
        
        p1_text = self.font.render(f"P1 Score: {self.p1['score']}", True, COLORS[1])
        p2_text = self.font.render(f"P2 Score: {self.p2['score']}", True, COLORS[2])
        controls_text = self.font.render("WASD vs Arrows", True, COLORS["text"])
        
        self.screen.blit(p1_text, (20, 5))
        self.screen.blit(controls_text, (WIDTH // 2 - controls_text.get_width() // 2, 5))
        self.screen.blit(p2_text, (WIDTH - p2_text.get_width() - 20, 5))

        # Overlays
        if self.state == "START":
            self._draw_overlay("Press ANY KEY to Start")
        elif self.state == "GAME_OVER":
            self._draw_overlay(self.winner_msg, "Press SPACE to Restart")

        pygame.display.flip()

    def _draw_overlay(self, main_text, sub_text=""):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        text_surf = self.large_font.render(main_text, True, COLORS["text"])
        self.screen.blit(text_surf, (WIDTH//2 - text_surf.get_width()//2, HEIGHT//2 - 40))
        
        if sub_text:
            sub_surf = self.font.render(sub_text, True, (200, 200, 200))
            self.screen.blit(sub_surf, (WIDTH//2 - sub_surf.get_width()//2, HEIGHT//2 + 20))

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

if __name__ == "__main__":
    game = PaperIOGame()
    game.run()