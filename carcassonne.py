import pygame
import sys
from constants import SCREEN_SIZE, MIN_ZOOM, MAX_ZOOM, PLACING_TILE, PLACING_MEEPLE, PLAYER_MEEPLE_START, CITY, ROAD, FIELD
from models import Board, Tile
from utils import create_full_game_deck, load_and_render_tile, get_feature_center, copy_features

# Initialize Application Window Window View Setup
pygame.init()
screen = pygame.display.set_mode((SCREEN_SIZE, SCREEN_SIZE))
pygame.display.set_caption("Carcassonne Desktop App Framework")
clock = pygame.time.Clock()

# CAMERA ENVIRONMENT SETTINGS
camera_x = SCREEN_SIZE // 2
camera_y = SCREEN_SIZE // 2
zoom_scale = 1.0
MIN_ZOOM, MAX_ZOOM = 0.4, 2.5
is_dragging_cam = False
drag_origin_x, drag_origin_y = 0, 0

board = Board()
deck, starter_tile = create_full_game_deck()
if starter_tile:
    board.place_tile(0, 0, starter_tile)
active_tile = deck.pop() if deck else None

# Game Phase States
game_state = PLACING_TILE
last_placed_pos = None

# Game Loop
score = 0
meeple_count = PLAYER_MEEPLE_START
score_effects = []
history_log = []
show_history = False
history_scroll = 0

history_log.append(f"START: Placed {starter_tile.name} at (0, 0)")

running = True
while running:
    screen.fill((30, 30, 30)) 
    mx, my = pygame.mouse.get_pos() # Updated per frame for hover logic
    current_grid_tile_size = 80 * zoom_scale

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r and active_tile: 
                active_tile.rotate_clockwise()
            if event.key == pygame.K_h:
                show_history = not show_history
                history_scroll = 0
            if event.key == pygame.K_SPACE and game_state == PLACING_MEEPLE:
                # Skip meeple placement and check scoring
                game_state = PLACING_TILE
                s, m, fx = board.evaluate_scoring(history_log)
                score += s
                meeple_count += m
                score_effects.extend(fx)
                
                active_tile = deck.pop() if deck else None
                last_placed_pos = None

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4: 
                if show_history:
                    history_scroll = max(0, history_scroll - 25)
                else:
                    zoom_scale = min(MAX_ZOOM, zoom_scale + 0.1)
            elif event.button == 5: 
                if show_history:
                    history_scroll += 25
                else:
                    zoom_scale = max(MIN_ZOOM, zoom_scale - 0.1)
                
            elif event.button == 3: 
                is_dragging_cam = True
                mx, my = pygame.mouse.get_pos()
                drag_origin_x = mx - camera_x
                drag_origin_y = my - camera_y
                
            elif event.button == 1:
                # Check for Log Button Click
                if pygame.Rect(SCREEN_SIZE - 100, 20, 80, 30).collidepoint(event.pos):
                    show_history = not show_history
                    history_scroll = 0
                    continue

            if event.button == 1 and active_tile and game_state == PLACING_TILE and not show_history: 
                mx, my = pygame.mouse.get_pos()
                
                grid_x = round((mx - camera_x) / current_grid_tile_size)
                grid_y = round((my - camera_y) / current_grid_tile_size)
                
                if board.is_valid_placement(grid_x, grid_y, active_tile):
                    # Deep copy tile state into the board including Abbey and Shield status
                    placed_tile = Tile(active_tile.name, *active_tile.base_edges, 
                                       active_tile.filename, copy_features(active_tile.features),
                                       active_tile.has_shield, active_tile.has_abbey)
                    placed_tile.edges = list(active_tile.edges)
                    placed_tile.rotation = active_tile.rotation

                    board.grid[(grid_x, grid_y)] = placed_tile
                    history_log.append(f"TILE: {active_tile.name} at ({grid_x}, {grid_y}) rot {active_tile.rotation}°")
                    last_placed_pos = (grid_x, grid_y)
                    game_state = PLACING_MEEPLE
            
            elif event.button == 1 and game_state == PLACING_MEEPLE and meeple_count > 0 and not show_history:
                mx, my = pygame.mouse.get_pos()
                tile = board.grid[last_placed_pos]
                off_x = camera_x + (last_placed_pos[0] * current_grid_tile_size) - (current_grid_tile_size // 2)
                off_y = camera_y + (last_placed_pos[1] * current_grid_tile_size) - (current_grid_tile_size // 2)
                
                # Check if user clicked a valid feature slot
                for i, feat in enumerate(tile.features):
                    if not board.is_feature_occupied(last_placed_pos[0], last_placed_pos[1], i):
                        fx, fy = get_feature_center(feat)
                        slot_pos = (off_x + int(fx * current_grid_tile_size), off_y + int(fy * current_grid_tile_size))
                        if pygame.Vector2(slot_pos).distance_to((mx, my)) < 15:
                            tile.meeple = (i, 1) # Feature index and Player ID
                            t_map = {"city": "City", "c": "City", "road": "Road", "r": "Road", "field": "Field", "f": "Field", "a": "Cloister"}
                            f_name = t_map.get(feat['type'].lower(), feat['type'])
                            history_log.append(f"  -> Meeple on {f_name}")
                            meeple_count -= 1
                            game_state = PLACING_TILE
                            
                            # Evaluate scoring immediately after meeple placement
                            s, m, fx_list = board.evaluate_scoring(history_log)
                            score += s
                            meeple_count += m
                            score_effects.extend(fx_list)

                            active_tile = deck.pop() if deck else None
                            last_placed_pos = None
                            break

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 3: 
                is_dragging_cam = False

        elif event.type == pygame.MOUSEMOTION:
            if is_dragging_cam:
                mx, my = pygame.mouse.get_pos()
                camera_x = mx - drag_origin_x
                camera_y = my - drag_origin_y

    # Render board elements
    for (x, y), tile in board.grid.items():
        screen_x = camera_x + (x * current_grid_tile_size) - (current_grid_tile_size // 2)
        screen_y = camera_y + (y * current_grid_tile_size) - (current_grid_tile_size // 2)
        load_and_render_tile(screen, screen_x, screen_y, current_grid_tile_size, tile, is_preview=False)
        
        # Render placed meeples
        if tile.meeple:
            feat = tile.features[tile.meeple[0]]
            fx, fy = get_feature_center(feat)
            m_pos = (screen_x + int(fx * current_grid_tile_size), screen_y + int(fy * current_grid_tile_size))
            pygame.draw.circle(screen, (255, 255, 255), m_pos, 8) # White border
            pygame.draw.circle(screen, (200, 0, 0), m_pos, 6) # Red Meeple

    # Draw Meeple Placement Options
    if game_state == PLACING_MEEPLE and last_placed_pos:
        tile = board.grid[last_placed_pos]
        screen_x = camera_x + (last_placed_pos[0] * current_grid_tile_size) - (current_grid_tile_size // 2)
        screen_y = camera_y + (last_placed_pos[1] * current_grid_tile_size) - (current_grid_tile_size // 2)
        
        hovered_feature = None
        for i, feat in enumerate(tile.features):
            if not board.is_feature_occupied(last_placed_pos[0], last_placed_pos[1], i):
                fx, fy = get_feature_center(feat)
                slot_pos = (screen_x + int(fx * current_grid_tile_size), screen_y + int(fy * current_grid_tile_size))
                
                # Draw indicator (Semi-transparent circle)
                f_type_low = feat['type'].lower()
                color = (255, 255, 0) if f_type_low == 'a' else \
                        (0, 0, 255) if f_type_low in ["city", "c"] else \
                        (255, 0, 0) if f_type_low in ["road", "r"] else (0, 255, 0)
                
                s = pygame.Surface((30, 30), pygame.SRCALPHA)
                pygame.draw.circle(s, (*color, 180), (15, 15), 10)
                screen.blit(s, (slot_pos[0]-15, slot_pos[1]-15))

                # Check for hover
                if pygame.Vector2(slot_pos).distance_to((mx, my)) < 15:
                    hovered_feature = feat

        # Draw tooltip if hovering over a placement slot
        if hovered_feature:
            t_map = {"city": "City", "c": "City", "road": "Road", "r": "Road", "field": "Field", "f": "Field", "a": "Cloister"}
            f_display_name = t_map.get(hovered_feature['type'].lower(), hovered_feature['type'].capitalize())
            
            tooltip_font = pygame.font.SysFont("Arial", 14, bold=True)
            txt_surf = tooltip_font.render(f_display_name, True, (255, 255, 255))
            txt_rect = txt_surf.get_rect(midbottom=(mx, my - 15))
            
            # Draw background box for tooltip
            bg_rect = txt_rect.inflate(12, 8)
            pygame.draw.rect(screen, (40, 40, 40), bg_rect)
            pygame.draw.rect(screen, (200, 200, 200), bg_rect, 1)
            screen.blit(txt_surf, txt_rect)
        
        if meeple_count == 0:
            font = pygame.font.SysFont("Arial", 14)
            screen.blit(font.render("(OUT OF MEEPLES)", True, (255, 100, 100)), (20, 85))

    # Update and Draw Score Effects
    for fx in score_effects[:]:
        fx.update()
        if fx.alpha <= 0: score_effects.remove(fx)
        else:
            f_ui = pygame.font.SysFont("Arial", 24, bold=True)
            txt = f_ui.render(fx.text, True, (255, 255, 0))
            txt.set_alpha(fx.alpha)
            # Calculate screen position for score pop-up
            sx = camera_x + (fx.x * current_grid_tile_size)
            sy = camera_y + (fx.y * current_grid_tile_size)
            screen.blit(txt, (sx, sy))

        font = pygame.font.SysFont("Arial", 18, bold=True)
        screen.blit(font.render("PLACE MEEPLE or PRESS SPACE TO SKIP", True, (255, 255, 255)), (20, 60))

    # Draw Floating HUD
    if active_tile and game_state == PLACING_TILE:
        # Render Active Tile in Bottom Right Preview Area
        p_size = 120
        px, py = SCREEN_SIZE - p_size - 20, SCREEN_SIZE - p_size - 20
        pygame.draw.rect(screen, (20, 20, 20), (px-5, py-5, p_size+10, p_size+10))
        pygame.draw.rect(screen, (255, 255, 255), (px-5, py-5, p_size+10, p_size+10), 2)
        load_and_render_tile(screen, px, py, p_size, active_tile, is_preview=False, show_name=True)
        
        font = pygame.font.SysFont("Arial", 16, bold=True)
        ui_str = f"SCORE: {score} | MEEPLES: {meeple_count} | DECK: {len(deck)} | R = Rotate"
        ui_overlay = font.render(ui_str, True, (240, 240, 240))
        screen.blit(ui_overlay, (20, 20))
        screen.blit(font.render("Drag Right-Click to Pan | Scroll to Zoom", True, (150, 150, 150)), (20, 45))

    # Draw History Button
    btn_rect = pygame.Rect(SCREEN_SIZE - 100, 20, 80, 30)
    pygame.draw.rect(screen, (50, 50, 50), btn_rect)
    pygame.draw.rect(screen, (200, 200, 200), btn_rect, 2)
    btn_font = pygame.font.SysFont("Arial", 14, bold=True)
    screen.blit(btn_font.render("LOG (H)", True, (255, 255, 255)), (SCREEN_SIZE - 85, 27))

    # Draw History Modal
    if show_history:
        modal_overlay = pygame.Surface((SCREEN_SIZE, SCREEN_SIZE), pygame.SRCALPHA)
        modal_overlay.fill((0, 0, 0, 200))
        screen.blit(modal_overlay, (0, 0))

        modal_rect = pygame.Rect(150, 100, 500, 500)
        pygame.draw.rect(screen, (40, 40, 40), modal_rect)
        pygame.draw.rect(screen, (255, 255, 255), modal_rect, 2)
        
        h_font = pygame.font.SysFont("Courier New", 14)
        screen.blit(btn_font.render("GAME HISTORY LOG", True, (255, 255, 0)), (170, 115))
        
        y_pos = 150 - history_scroll
        for entry in history_log:
            if 140 < y_pos < 580:
                screen.blit(h_font.render(entry, True, (255, 255, 255)), (170, y_pos))
            y_pos += 22

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
