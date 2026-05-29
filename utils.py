import os, json, csv, random, pygame
from constants import CITY, ROAD, FIELD, IMAGE_CACHE
from models import Tile

def copy_features(features):
    return [{"type": f["type"], "edges": list(f["edges"]), "meeple_pos": f.get("meeple_pos"), "shield": f.get("shield", False)} for f in features]

def get_feature_center(feature):
    if feature.get('meeple_pos'): return tuple(feature['meeple_pos'])
    if not feature.get('edges'): return (0.5, 0.5)
    pts = {0:(0.15,0.05), 1:(0.5,0.05), 2:(0.85,0.05), 3:(0.95,0.15), 4:(0.95,0.5), 5:(0.95,0.85), 
           6:(0.85,0.95), 7:(0.5,0.95), 8:(0.15,0.95), 9:(0.05,0.85), 10:(0.05,0.5), 11:(0.05,0.15)}
    if feature['type'] == ROAD:
        raw_x, raw_y = pts[feature['edges'][0]]
        return (raw_x * 0.75 + 0.5 * 0.25, raw_y * 0.75 + 0.5 * 0.25)
    coords = [pts[s] for s in feature['edges']]
    avg_x, avg_y = sum(c[0] for c in coords)/len(coords), sum(c[1] for c in coords)/len(coords)
    if feature['type'] == FIELD:
        avg_x, avg_y = avg_x * 0.7 + 0.5 * 0.3, avg_y * 0.7 + 0.5 * 0.3
    return (avg_x, avg_y)

def create_full_game_deck():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "assets", "tiles.csv")
    deck, starter_tile = [], None
    if not os.path.exists(csv_path): return [], None
    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            img, ori, qty, feat_flags = row['image'], row['orientation'], int(row['quantity']), row['feature']
            has_shield, has_abbey, is_starter = 'S' in feat_flags, 'A' in feat_flags, 'X' in feat_flags
            n, e, s, w = ori[0], ori[1], ori[2], ori[3]
            json_path = os.path.join(current_dir, "assets", os.path.splitext(img)[0] + ".json")
            deck_item_features, tile_id = None, img
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r') as jf:
                        data = json.load(jf)
                        tile_id = data.get("id", img)
                        type_map = {"city": CITY, "road": ROAD, "field": FIELD, "a": "A", "c": CITY, "r": ROAD, "f": FIELD}
                        deck_item_features = [{"type": type_map.get(f["type"].lower(), f["type"]), "edges": f["sockets"], 
                                              "shield": f.get("shield", False), "meeple_pos": f.get("meeple_pos")} for f in data.get("features", [])]
                        if any(f.get("shield") for f in data.get("features", []) if f.get("type") == "city"): has_shield = True
                        if data.get("is_starter"): is_starter = True
                except Exception as err: print(f"Error loading JSON {json_path}: {err}")
            if deck_item_features is None: continue
            if has_abbey and not any(f['type'] == 'A' for f in deck_item_features):
                deck_item_features.append({"type": "A", "edges": []})
            if is_starter:
                starter_tile = Tile(tile_id, n, e, s, w, img, copy_features(deck_item_features), has_shield, has_abbey)
                qty -= 1
            for _ in range(qty):
                deck.append(Tile(tile_id, n, e, s, w, img, copy_features(deck_item_features), has_shield, has_abbey))
    random.shuffle(deck)
    return deck, starter_tile

def load_and_render_tile(surface, x, y, size, tile, is_preview=False, show_name=False):
    img_size = int(size)
    cache_key = (tile.filename, img_size)
    if cache_key not in IMAGE_CACHE:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        asset_path = os.path.join(current_dir, "assets", tile.filename)
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
    if is_preview: rotated_texture.set_alpha(150) 
    surface.blit(rotated_texture, (x, y))
    if show_name:
        debug_font = pygame.font.SysFont("Arial", 12)
        surface.blit(debug_font.render(tile.name, True, (255, 255, 255)), (x, y + img_size + 2))