import os, json, csv, random, pygame
from constants import CITY, ROAD, FIELD, IMAGE_CACHE
from models import Tile

def copy_features(features):
    return [{"type": f["type"], "edges": list(f["edges"]), "meeple_pos": f.get("meeple_pos"), "shield": f.get("shield", False)} for f in features]

def get_feature_center(feature, rotation=0):
    # Get base coordinates (either from calibrated meeple_pos or calculated fallback)
    if feature.get('meeple_pos'):
        fx, fy = feature['meeple_pos']
    elif not feature.get('edges'):
        fx, fy = (0.5, 0.5)
    else:
        pts = {0:(0.15,0.05), 1:(0.5,0.05), 2:(0.85,0.05), 3:(0.95,0.15), 4:(0.95,0.5), 5:(0.95,0.85), 
               6:(0.85,0.95), 7:(0.5,0.95), 8:(0.15,0.95), 9:(0.05,0.85), 10:(0.05,0.5), 11:(0.05,0.15)}
        if feature['type'] == ROAD:
            raw_x, raw_y = pts[feature['edges'][0]]
            fx, fy = (raw_x * 0.75 + 0.5 * 0.25, raw_y * 0.75 + 0.5 * 0.25)
        else:
            coords = [pts[s] for s in feature['edges']]
            fx, fy = sum(c[0] for c in coords)/len(coords), sum(c[1] for c in coords)/len(coords)
            if feature['type'] == FIELD:
                fx, fy = fx * 0.7 + 0.5 * 0.3, fy * 0.7 + 0.5 * 0.3

    # Apply rotation transform to the chosen coordinates
    if rotation == 90:
        return (1 - fy, fx)
    elif rotation == 180:
        return (1.0 - fx, 1.0 - fy)
    elif rotation == 270:
        return (fy, 1 - fx)
    return (fx, fy)

def create_full_game_deck():
    assets_dir = "assets"
    deck, starter_tile = [], None
    tile_counts = {}
    skipped_tiles = []
    total_loaded_count = 0
    
    if not os.path.exists(assets_dir):
        print(f"FATAL: {assets_dir} directory not found.")
        return [], None

    for filename in os.listdir(assets_dir):
        if not filename.endswith(".json"):
            continue
            
        json_path = os.path.join(assets_dir, filename)
        try:
            with open(json_path, 'r') as jf:
                data = json.load(jf)
                
                # Required fields now come directly from JSON
                img = data.get("image")
                ori = data.get("orientation")
                qty = int(data.get("quantity", 1))
                tile_id = data.get("id", filename.replace(".json", ""))
                is_starter = data.get("is_starter", False)

                if not img or not ori:
                    skipped_tiles.append(f"{filename} (Missing 'image' or 'orientation')")
                    continue

                n, e, s, w = ori[0], ori[1], ori[2], ori[3]
                type_map = {"city": CITY, "road": ROAD, "field": FIELD, "a": "A", "c": CITY, "r": ROAD, "f": FIELD}
                deck_item_features = [{"type": type_map.get(f["type"].lower(), f["type"]), "edges": f["sockets"], 
                                      "shield": f.get("shield", False), "meeple_pos": f.get("meeple_pos")} for f in data.get("features", [])]
                
                has_shield = any(f.get("shield") for f in deck_item_features if f.get("type") == CITY)
                has_abbey = any(f.get("type") == "A" for f in deck_item_features)

                tile_counts[tile_id] = qty
                if is_starter:
                    starter_tile = Tile(tile_id, n, e, s, w, img, copy_features(deck_item_features), has_shield, has_abbey)
                    qty -= 1
                    total_loaded_count += 1
                
                for _ in range(qty):
                    deck.append(Tile(tile_id, n, e, s, w, img, copy_features(deck_item_features), has_shield, has_abbey))
                    total_loaded_count += 1
        except Exception as err:
            skipped_tiles.append(f"{filename} (Error: {err})")

    if skipped_tiles:
        for reason in skipped_tiles:
            print(f"WARN: skipped tile — {reason}")

    print(f"DECK LOADED: {total_loaded_count} tiles.")
    random.shuffle(deck)
    return deck, starter_tile

def load_and_render_tile(surface, x, y, size, tile, is_preview=False, show_name=False):
    img_size = int(size)
    cache_key = (tile.filename, img_size)
    if cache_key not in IMAGE_CACHE:
        asset_path = os.path.join("assets", tile.filename)
        if not os.path.exists(asset_path):
            fallback = pygame.Surface((img_size, img_size))
            fallback.fill((200, 50, 50))
            pygame.draw.rect(fallback, (255, 255, 255), (0, 0, img_size, img_size), 2)
            font = pygame.font.SysFont("Arial", 12)
            fallback.blit(font.render(tile.filename, True, (255, 255, 255)), (5, img_size // 2 - 10))
            IMAGE_CACHE[cache_key] = fallback
        else:
            try:
                loaded_image = pygame.image.load(asset_path).convert_alpha()
                IMAGE_CACHE[cache_key] = pygame.transform.smoothscale(loaded_image, (img_size, img_size))
            except:
                fallback = pygame.Surface((img_size, img_size))
                fallback.fill((200, 0, 0))
                IMAGE_CACHE[cache_key] = fallback
    rotated_texture = pygame.transform.rotate(IMAGE_CACHE[cache_key], -tile.rotation)
    
    if is_preview:
        # Render the tile opaque (as it looks normally) to ensure it is visible during staging
        surface.blit(rotated_texture, (x, y))
        # High-visibility purple border as requested to indicate staging status
        pygame.draw.rect(surface, (255, 0, 255), (x, y, img_size, img_size), 4)
    else:
        surface.blit(rotated_texture, (x, y))

    if show_name:
        debug_font = pygame.font.SysFont("Arial", 12)
        surface.blit(debug_font.render(tile.name, True, (255, 255, 255)), (x, y + img_size + 2))