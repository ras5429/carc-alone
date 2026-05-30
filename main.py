import os
import random
import pygame
import sys
import asyncio
from constants import SCREEN_SIZE, MIN_ZOOM, MAX_ZOOM, PLACING_TILE, PLACING_MEEPLE, PLAYER_MEEPLE_START, CITY, ROAD, FIELD
from models import Board, Tile
from utils import create_full_game_deck, load_and_render_tile, get_feature_center, copy_features

# Game Phase States
CONFIRMING_TILE = "confirming_tile"

class Particle:
    """Simple particle for firework effects."""
    def __init__(self, x, y):
        self.pos = [x, y]
        self.vel = [random.uniform(-4, 4), random.uniform(-7, 1)]
        self.color = random.choice([(255, 215, 0), (255, 69, 0), (0, 255, 127), (30, 144, 255), (238, 130, 238)])
        self.life = random.randint(60, 110)

    def update(self):
        self.pos[0] += self.vel[0]
        self.pos[1] += self.vel[1]
        self.vel[1] += 0.12 # Gravity
        self.life -= 1

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.pos[0]), int(self.pos[1])), 2)

async def main():
    # Desktop Audio Optimization
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_SIZE, SCREEN_SIZE))
    pygame.display.set_caption("Carcassonne Web App")
    clock = pygame.time.Clock()
    
    # Robust Audio Loading for Desktop
    base_path = os.path.dirname(__file__)
    music_path = os.path.join(base_path, "assets", "Mysterious-Lands_Looping.ogg")
    
    try:
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.set_volume(1.0)
        pygame.mixer.music.play(-1)
    except Exception as e:
        print(f"Music Error: Could not load {music_path}. Error: {e}")

    # CAMERA ENVIRONMENT SETTINGS
    camera_x = SCREEN_SIZE // 2
    camera_y = SCREEN_SIZE // 2
    zoom_scale = 1.0
    is_dragging_cam = False
    drag_origin_x, drag_origin_y = 0, 0

    board = Board()
    deck, starter_tile = create_full_game_deck()
    
    if not starter_tile:
        print("FATAL: Starter tile not found. Assets may not be bundled correctly.")
        return

    board.place_tile(0, 0, starter_tile)
    active_tile = deck.pop() if deck else None

    # Game Phase States
    game_state = PLACING_TILE
    last_placed_pos = None

    # Game Stats
    score = 0
    meeple_count = PLAYER_MEEPLE_START
    score_effects = []
    particles = []
    history_log = []
    show_history = False
    history_scroll = 0
    muted = False
    menu_open = False
    game_over = False

    # Touch/Gesture Tracking
    finger_touches = {}
    pinch_start_dist = 0
    pinch_start_zoom = 1.0
    drag_happened = False

    # New Constants for Game States (Using strings for simplicity)
    STATE_PLAYING = "playing"
    STATE_OVER = "game_over"
    current_state = STATE_PLAYING

    # UI Rects for Mobile Touch
    rotate_btn_rect = pygame.Rect(SCREEN_SIZE - 145, SCREEN_SIZE - 145, 130, 130)
    skip_btn_rect = pygame.Rect(20, SCREEN_SIZE - 70, 180, 50)
    confirm_btn_rect = pygame.Rect(20, SCREEN_SIZE - 130, 130, 50)
    undo_btn_rect = pygame.Rect(160, SCREEN_SIZE - 130, 130, 50)
    log_btn_rect = pygame.Rect(SCREEN_SIZE - 100, 20, 80, 30)
    mute_btn_rect = pygame.Rect(SCREEN_SIZE - 190, 20, 80, 30)
    menu_btn_rect = pygame.Rect(SCREEN_SIZE - 280, 20, 80, 30)
    restart_opt_rect = pygame.Rect(SCREEN_SIZE - 280, 55, 100, 40)

    history_log.append(f"START: Placed {starter_tile.name} at (0, 0)")

    running = True
    while running:
        screen.fill((30, 30, 30)) 
        mx, my = pygame.mouse.get_pos() 
        current_grid_tile_size = 80 * zoom_scale

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.FINGERDOWN:
                # Track touch position (event.x/y are normalized 0-1)
                finger_touches[event.finger_id] = pygame.Vector2(event.x, event.y)
                if len(finger_touches) == 2:
                    # Start of a pinch gesture
                    ids = list(finger_touches.keys())
                    pinch_start_dist = finger_touches[ids[0]].distance_to(finger_touches[ids[1]])
                    pinch_start_zoom = zoom_scale
                drag_happened = False

            elif event.type == pygame.FINGERMOTION:
                # Update touch position
                finger_touches[event.finger_id] = pygame.Vector2(event.x, event.y)
                if len(finger_touches) == 1:
                    # One finger pan
                    camera_x += event.dx * SCREEN_SIZE
                    camera_y += event.dy * SCREEN_SIZE
                    if abs(event.dx) > 0.005 or abs(event.dy) > 0.005:
                        drag_happened = True
                elif len(finger_touches) == 2:
                    # Two finger pinch zoom
                    ids = list(finger_touches.keys())
                    current_dist = finger_touches[ids[0]].distance_to(finger_touches[ids[1]])
                    if pinch_start_dist > 0:
                        scale_factor = current_dist / pinch_start_dist
                        zoom_scale = max(MIN_ZOOM, min(MAX_ZOOM, pinch_start_zoom * scale_factor))
                    drag_happened = True

            elif event.type == pygame.FINGERUP:
                if event.finger_id in finger_touches:
                    del finger_touches[event.finger_id]
                if len(finger_touches) < 2:
                    pinch_start_dist = 0
                # Note: MOUSEBUTTONUP will fire after this on mobile, 
                # we use drag_happened there to allow/block placement.
                
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
                    if fx:
                        score_effects.extend(fx)
                        # Spawn fireworks in the bottom-left area
                        for _ in range(60): particles.append(Particle(150, SCREEN_SIZE - 150))
                    
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
                drag_happened = False

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 3: 
                    is_dragging_cam = False
                elif event.button == 1 and not drag_happened:
                    # HUD Button Interactions
                    if log_btn_rect.collidepoint(event.pos):
                        show_history = not show_history
                        history_scroll = 0
                        menu_open = False
                        continue

                    if mute_btn_rect.collidepoint(event.pos):
                        muted = not muted
                        pygame.mixer.music.set_volume(0.0 if muted else 1.0)
                        continue

                    if menu_btn_rect.collidepoint(event.pos):
                        menu_open = not menu_open
                        show_history = False
                        continue

                    if menu_open and restart_opt_rect.collidepoint(event.pos):
                        # Stop music before restart to avoid overlapping audio instances
                        pygame.mixer.music.stop()
                        await main()
                        return

                    if game_state == CONFIRMING_TILE:
                        if confirm_btn_rect.collidepoint(event.pos):
                            # Commit the staged placement to the board
                            placed_tile = Tile(active_tile.name, *active_tile.base_edges, 
                                            active_tile.filename, copy_features(active_tile.features),
                                            active_tile.has_shield, active_tile.has_abbey)
                            placed_tile.edges = list(active_tile.edges)
                            placed_tile.rotation = active_tile.rotation
                            board.grid[last_placed_pos] = placed_tile
                            history_log.append(f"TILE: {active_tile.name} at ({last_placed_pos[0]}, {last_placed_pos[1]}) rot {active_tile.rotation}°")
                            
                            # Evaluate scoring for cloisters/features completed by this placement
                            s, m, fx_list = board.evaluate_scoring(history_log)
                            score += s
                            meeple_count += m
                            if fx_list:
                                score_effects.extend(fx_list)
                                for _ in range(60): particles.append(Particle(150, SCREEN_SIZE - 150))
                            
                            game_state = PLACING_MEEPLE
                            continue
                        elif undo_btn_rect.collidepoint(event.pos):
                            last_placed_pos = None
                            game_state = PLACING_TILE
                            continue
                    
                    # Check for Virtual Rotate Button (Mobile)
                    if rotate_btn_rect.collidepoint(event.pos) and active_tile and (game_state == PLACING_TILE or game_state == CONFIRMING_TILE):
                        active_tile.rotate_clockwise()
                        continue

                    # Check for Virtual Skip Button (Mobile)
                    if skip_btn_rect.collidepoint(event.pos) and game_state == PLACING_MEEPLE:
                        game_state = PLACING_TILE
                        s, m, fx = board.evaluate_scoring(history_log)
                        score += s
                        meeple_count += m
                        if fx:
                            score_effects.extend(fx)
                            for _ in range(60): particles.append(Particle(150, SCREEN_SIZE - 150))
                        
                        active_tile = deck.pop() if deck else None
                        if not active_tile:
                            current_state = STATE_OVER
                            s, fx = board.calculate_final_scores(history_log)
                            score += s
                            if fx:
                                score_effects.extend(fx)
                                for _ in range(60): particles.append(Particle(150, SCREEN_SIZE - 150))
                        last_placed_pos = None
                        continue

                    # 4. Game Board Interactions (Grid / Meeple placement)
                    if active_tile and (game_state == PLACING_TILE or game_state == CONFIRMING_TILE) and not show_history and current_state == STATE_PLAYING: 
                        grid_x = round((event.pos[0] - camera_x) / current_grid_tile_size)
                        grid_y = round((event.pos[1] - camera_y) / current_grid_tile_size)
                        
                        if board.is_valid_placement(grid_x, grid_y, active_tile):
                            last_placed_pos = (grid_x, grid_y)
                            game_state = CONFIRMING_TILE
                    
                    elif game_state == PLACING_MEEPLE and meeple_count > 0 and not show_history and current_state == STATE_PLAYING:
                        tile = board.grid[last_placed_pos]
                        off_x = camera_x + (last_placed_pos[0] * current_grid_tile_size) - (current_grid_tile_size // 2)
                        off_y = camera_y + (last_placed_pos[1] * current_grid_tile_size) - (current_grid_tile_size // 2)
                        
                        # Check if user clicked a valid feature slot
                        for i, feat in enumerate(tile.features):
                            if not board.is_feature_occupied(last_placed_pos[0], last_placed_pos[1], i):
                                fx, fy = get_feature_center(feat)
                                slot_pos = (off_x + int(fx * current_grid_tile_size), off_y + int(fy * current_grid_tile_size))
                                if pygame.Vector2(slot_pos).distance_to(event.pos) < 15:
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
                                    if fx_list:
                                        score_effects.extend(fx_list)
                                        for _ in range(60): particles.append(Particle(150, SCREEN_SIZE - 150))

                                    active_tile = deck.pop() if deck else None
                                    if not active_tile:
                                        current_state = STATE_OVER
                                        s, fx = board.calculate_final_scores(history_log)
                                        score += s
                                        if fx:
                                            score_effects.extend(fx)
                                            for _ in range(60): particles.append(Particle(150, SCREEN_SIZE - 150))
                                    last_placed_pos = None
                                    break

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
                pygame.draw.circle(screen, (255, 255, 255), m_pos, 8) 
                pygame.draw.circle(screen, (200, 0, 0), m_pos, 6) 

        # Render Staged/Preview Tile
        if game_state == CONFIRMING_TILE and last_placed_pos:
            staged_x = camera_x + (last_placed_pos[0] * current_grid_tile_size) - (current_grid_tile_size // 2)
            staged_y = camera_y + (last_placed_pos[1] * current_grid_tile_size) - (current_grid_tile_size // 2)
            load_and_render_tile(screen, staged_x, staged_y, current_grid_tile_size, active_tile, is_preview=True)

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
                    
                    f_type_low = feat['type'].lower()
                    color = (255, 255, 0) if f_type_low == 'a' else (0, 0, 255) if f_type_low in ["city", "c"] else (255, 0, 0) if f_type_low in ["road", "r"] else (0, 255, 0)
                    
                    s = pygame.Surface((30, 30), pygame.SRCALPHA)
                    pygame.draw.circle(s, (*color, 180), (15, 15), 10)
                    screen.blit(s, (slot_pos[0]-15, slot_pos[1]-15))

                    if pygame.Vector2(slot_pos).distance_to((mx, my)) < 15:
                        hovered_feature = feat

            if hovered_feature:
                t_map = {"city": "City", "c": "City", "road": "Road", "r": "Road", "field": "Field", "f": "Field", "a": "Cloister"}
                f_display_name = t_map.get(hovered_feature['type'].lower(), hovered_feature['type'].capitalize())
                
                tooltip_font = pygame.font.SysFont("Arial", 14, bold=True)
                txt_surf = tooltip_font.render(f_display_name, True, (255, 255, 255))
                txt_rect = txt_surf.get_rect(midbottom=(mx, my - 15))
                
                bg_rect = txt_rect.inflate(12, 8)
                pygame.draw.rect(screen, (40, 40, 40), bg_rect)
                pygame.draw.rect(screen, (200, 200, 200), bg_rect, 1)
                screen.blit(txt_surf, txt_rect)
            
            if meeple_count == 0:
                font = pygame.font.SysFont("Arial", 14)
                screen.blit(font.render("(OUT OF MEEPLES)", True, (255, 100, 100)), (20, 85))

        # Update and Draw Particles (Fireworks)
        for p in particles[:]:
            p.update()
            if p.life <= 0: particles.remove(p)
            else: p.draw(screen)

        # Draw Score Alerts in Dedicated Area (Bottom Left)
        y_alert = SCREEN_SIZE - 200
        for fx in score_effects[:]:
            fx.update()
            if fx.alpha <= 0: score_effects.remove(fx)
            else:
                f_ui = pygame.font.SysFont("Arial", 20, bold=True)
                txt = f_ui.render("✨ " + fx.text, True, (255, 255, 0))
                txt.set_alpha(fx.alpha)
                screen.blit(txt, (20, y_alert))
                y_alert -= 30

        if game_state == PLACING_MEEPLE:
            font = pygame.font.SysFont("Arial", 18, bold=True)
            screen.blit(font.render("PLACE MEEPLE or PRESS SPACE TO SKIP", True, (255, 255, 255)), (20, 60))

        if active_tile and (game_state == PLACING_TILE or game_state == CONFIRMING_TILE):
            p_size = 120
            px, py = SCREEN_SIZE - p_size - 20, SCREEN_SIZE - p_size - 20
            pygame.draw.rect(screen, (20, 20, 20), (px-5, py-5, p_size+10, p_size+10))
            pygame.draw.rect(screen, (255, 255, 255), (px-5, py-5, p_size+10, p_size+10), 2)
            load_and_render_tile(screen, px, py, p_size, active_tile, is_preview=False, show_name=True)
            
            # Rotate Button Label for Mobile
            font_small = pygame.font.SysFont("Arial", 12, bold=True)
            label = font_small.render("TAP TO ROTATE", True, (255, 255, 0))
            screen.blit(label, (SCREEN_SIZE - 130, SCREEN_SIZE - 35))
            
            font = pygame.font.SysFont("Arial", 16, bold=True)
            tiles_left = len(deck) + 1
            ui_str = f"SCORE: {score} | TILES: {tiles_left} | R = Rotate"
            screen.blit(font.render(ui_str, True, (240, 240, 240)), (20, 20))
            screen.blit(font.render(f"MEEPLES: {meeple_count}", True, (255, 255, 255)), (20, 40))
            screen.blit(font.render("Keyboard: 'R' to Rotate | Panning: Mouse Drag / Swipe", True, (150, 150, 150)), (20, 60))
            
        # HUD Buttons
        for rect, label in [(log_btn_rect, "LOG (H)"), (mute_btn_rect, "MUTE" if not muted else "UNMUTE"), (menu_btn_rect, "MENU")]:
            pygame.draw.rect(screen, (50, 50, 50), rect)
            pygame.draw.rect(screen, (200, 200, 200), rect, 2)
            btn_font = pygame.font.SysFont("Arial", 12, bold=True)
            lbl_surf = btn_font.render(label, True, (255, 255, 255))
            screen.blit(lbl_surf, lbl_surf.get_rect(center=rect.center))

        if menu_open:
            pygame.draw.rect(screen, (40, 40, 40), restart_opt_rect)
            pygame.draw.rect(screen, (255, 255, 0), restart_opt_rect, 1)
            screen.blit(btn_font.render("RESTART", True, (255, 255, 0)), (restart_opt_rect.x + 10, restart_opt_rect.y + 12))

        # Confirmation Buttons (Confirm and Undo)
        if game_state == CONFIRMING_TILE:
            # Confirm Button (Green)
            pygame.draw.rect(screen, (0, 100, 0), confirm_btn_rect)
            pygame.draw.rect(screen, (255, 255, 255), confirm_btn_rect, 2)
            c_font = pygame.font.SysFont("Arial", 16, bold=True)
            c_text = c_font.render("CONFIRM", True, (255, 255, 255))
            screen.blit(c_text, c_text.get_rect(center=confirm_btn_rect.center))

            # Undo Button (Red)
            pygame.draw.rect(screen, (100, 0, 0), undo_btn_rect)
            pygame.draw.rect(screen, (255, 255, 255), undo_btn_rect, 2)
            u_text = c_font.render("UNDO", True, (255, 255, 255))
            screen.blit(u_text, u_text.get_rect(center=undo_btn_rect.center))

            prompt_font = pygame.font.SysFont("Arial", 14, bold=True)
            screen.blit(prompt_font.render("Confirm placement or tap 'Undo' to pick up", True, (255, 255, 0)), (20, 85))

        # Draw Skip Button for Mobile
        if game_state == PLACING_MEEPLE and not show_history and current_state == STATE_PLAYING:
            pygame.draw.rect(screen, (70, 70, 70), skip_btn_rect)
            pygame.draw.rect(screen, (255, 255, 255), skip_btn_rect, 2)
            skip_font = pygame.font.SysFont("Arial", 16, bold=True)
            skip_text = skip_font.render("SKIP MEEPLE", True, (255, 255, 255))
            text_rect = skip_text.get_rect(center=skip_btn_rect.center)
            screen.blit(skip_text, text_rect)
            
            prompt_font = pygame.font.SysFont("Arial", 14, bold=True)
            screen.blit(prompt_font.render("Tap feature or use SKIP", True, (255, 255, 0)), (20, 85))

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
        
        if current_state == STATE_OVER:
            overlay = pygame.Surface((SCREEN_SIZE, SCREEN_SIZE), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0,0))
            
            panel = pygame.Rect(SCREEN_SIZE // 2 - 150, SCREEN_SIZE // 2 - 150, 300, 300)
            pygame.draw.rect(screen, (30, 30, 30), panel)
            pygame.draw.rect(screen, (255, 255, 255), panel, 3)
            
            title_font = pygame.font.SysFont("Arial", 32, bold=True)
            score_font = pygame.font.SysFont("Arial", 48, bold=True)
            
            t_surf = title_font.render("GAME OVER", True, (255, 255, 255))
            s_surf = score_font.render(str(score), True, (255, 255, 0))
            
            screen.blit(t_surf, (SCREEN_SIZE // 2 - t_surf.get_width() // 2, SCREEN_SIZE // 2 - 100))
            screen.blit(s_surf, (SCREEN_SIZE // 2 - s_surf.get_width() // 2, SCREEN_SIZE // 2 - 40))
            screen.blit(btn_font.render("FINAL SCORE", True, (200, 200, 200)), (SCREEN_SIZE // 2 - 40, SCREEN_SIZE // 2 + 20))
            
            # Restart / Quit Buttons
            for r, l in [(pygame.Rect(SCREEN_SIZE // 2 - 110, SCREEN_SIZE // 2 + 100, 100, 40), "RESTART"), 
                         (pygame.Rect(SCREEN_SIZE // 2 + 10, SCREEN_SIZE // 2 + 100, 100, 40), "QUIT")]:
                pygame.draw.rect(screen, (60, 60, 60), r)
                pygame.draw.rect(screen, (255, 255, 255), r, 1)
                screen.blit(btn_font.render(l, True, (255, 255, 255)), (r.x + 20, r.y + 12))

        pygame.display.flip()
        await asyncio.sleep(0) # Yield control back to browser

if __name__ == "__main__":
    asyncio.run(main())
