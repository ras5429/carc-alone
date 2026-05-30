import os
import json
import pygame
import sys

# Configuration
ASSETS_DIR = "assets"
WINDOW_SIZE = 600  # Large window for precise clicking

def calibrate():
    pygame.init()
    # Extra height for UI text
    screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE + 120))
    pygame.display.set_caption("Carcassonne Meeple Calibrator")
    font = pygame.font.SysFont("Arial", 20)
    small_font = pygame.font.SysFont("Arial", 16)

    json_files = [f for f in os.listdir(ASSETS_DIR) if f.endswith('.json')]
    json_files.sort()

    if not json_files:
        print(f"No JSON files found in {ASSETS_DIR}")
        return

    for filename in json_files:
        json_path = os.path.join(ASSETS_DIR, filename)
        
        with open(json_path, 'r') as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                continue

        img_filename = data.get("image")
        if not img_filename:
            continue
        
        img_path = os.path.join(ASSETS_DIR, img_filename)
        if not os.path.exists(img_path):
            print(f"Image {img_filename} not found for {filename}")
            continue

        # Load and scale image for calibration
        raw_img = pygame.image.load(img_path)
        tile_img = pygame.transform.scale(raw_img, (WINDOW_SIZE, WINDOW_SIZE))

        features = data.get("features", [])
        for i, feat in enumerate(features):
            calibrating = True
            while calibrating:
                screen.fill((40, 40, 40))
                screen.blit(tile_img, (0, 0))
                
                # Render Info
                f_type = feat.get("type", "Unknown").upper()
                f_sockets = feat.get("sockets", [])
                
                y_off = WINDOW_SIZE + 10
                screen.blit(font.render(f"File: {filename} ({i+1}/{len(features)})", True, (255, 255, 255)), (15, y_off))
                screen.blit(font.render(f"Feature: {f_type} | Sockets: {f_sockets}", True, (0, 255, 255)), (15, y_off + 25))
                screen.blit(small_font.render("CLICK on tile to set Meeple Position | SPACE to skip | ESC to quit", True, (255, 255, 0)), (15, y_off + 60))

                # Draw current meeple_pos if it exists
                if "meeple_pos" in feat:
                    curr_x = int(feat["meeple_pos"][0] * WINDOW_SIZE)
                    curr_y = int(feat["meeple_pos"][1] * WINDOW_SIZE)
                    pygame.draw.circle(screen, (255, 0, 0), (curr_x, curr_y), 10, 2)
                    pygame.draw.circle(screen, (255, 255, 255), (curr_x, curr_y), 4)

                pygame.display.flip()

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit(); sys.exit()
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            pygame.quit(); sys.exit()
                        if event.key == pygame.K_SPACE:
                            calibrating = False
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mx, my = event.pos
                        if 0 <= mx < WINDOW_SIZE and 0 <= my < WINDOW_SIZE:
                            # Save normalized coordinates
                            feat["meeple_pos"] = [round(mx / WINDOW_SIZE, 3), round(my / WINDOW_SIZE, 3)]
                            calibrating = False

        # Save updated JSON
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Successfully updated {filename}")

    print("Calibration complete for all tiles.")
    pygame.quit()

if __name__ == "__main__":
    calibrate()