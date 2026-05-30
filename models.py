import pygame
from constants import CITY, ROAD, FIELD

class ScoreEffect:
    """UI element for celebration points."""
    def __init__(self, text, x, y):
        self.text = text
        self.x, self.y = x, y
        self.timer = 480 # 8 seconds at 60fps
        self.alpha = 255

    def update(self):
        self.timer -= 1
        if self.timer < 180: # Fade out in the last 3 seconds
            self.alpha = max(0, int((self.timer / 180) * 255))

class Tile:
    def __init__(self, name, north, east, south, west, filename, features=None, has_shield=False, has_abbey=False):
        self.name = name
        self.base_edges = [north, east, south, west]
        self.edges = [north, east, south, west]
        self.filename = filename 
        self.rotation = 0 
        self.has_shield = has_shield
        self.has_abbey = has_abbey
        self.meeple = None # Stores (feature_index, player_id)
        self.features = features if features else []

    def rotate_clockwise(self):
        self.edges = [self.edges[-1]] + self.edges[0:3]
        self.rotation = (self.rotation + 90) % 360
        for feature in self.features:
            feature['edges'] = [(idx + 3) % 12 for idx in feature['edges']]

class Board:
    def __init__(self):
        self.grid = {}
        
    def place_tile(self, x, y, tile):
        self.grid[(x, y)] = tile

    def trace_feature(self, x, y, feature_index, visited=None):
        if visited is None: visited = set()
        tile = self.grid.get((x, y))
        if not tile or (x, y, feature_index) in visited:
            return set(), True

        visited.add((x, y, feature_index))
        feat = tile.features[feature_index]
        components = {(x, y, feature_index)}
        is_closed = True

        for s in feat.get('edges', []):
            nx, ny = x, y
            if 0 <= s <= 2: ny -= 1
            elif 3 <= s <= 5: nx += 1
            elif 6 <= s <= 8: ny += 1
            elif 9 <= s <= 11: nx -= 1
            
            neighbor = self.grid.get((nx, ny))
            if not neighbor:
                is_closed = False 
                continue
            
            target_s = (8 - s) if (s <= 2 or 6 <= s <= 8) else (14 - s)
            for idx, nf in enumerate(neighbor.features):
                if target_s in nf.get('edges', []):
                    sub_comps, sub_closed = self.trace_feature(nx, ny, idx, visited)
                    components.update(sub_comps)
                    if not sub_closed: is_closed = False
        
        return components, is_closed

    def evaluate_scoring(self, log):
        new_effects = []
        scored_points = 0
        returned_meeples = 0

        for (x, y), tile in self.grid.items():
            if tile.meeple:
                feat_idx, _ = tile.meeple
                feat = tile.features[feat_idx]
                f_type = feat['type']

                if f_type == 'A': # Cloister
                    neighbors = sum(1 for dx in [-1,0,1] for dy in [-1,0,1] if (dx!=0 or dy!=0) and (x+dx, y+dy) in self.grid)
                    if neighbors == 8:
                        points = 9
                        scored_points += points
                        returned_meeples += 1
                        msg = f"CLOISTER COMPLETE: +{points} pts"
                        print(msg, flush=True); log.append(msg)
                        ret_msg = "  -> 1 meeple returned"
                        print(ret_msg, flush=True); log.append(ret_msg)
                        new_effects.append(ScoreEffect(msg, x, y))
                        tile.meeple = None
                
                elif f_type in [CITY, ROAD]:
                    components, is_closed = self.trace_feature(x, y, feat_idx)
                    if is_closed:
                        unique_tiles = set((cx, cy) for cx, cy, ci in components)
                        points = 0
                        f_name = "CITY" if f_type == CITY else "ROAD"
                        
                        if f_type == CITY:
                            # Count every shield symbol found in the city network
                            shield_count = sum(1 for cx, cy, ci in components if self.grid[(cx, cy)].features[ci].get('shield'))
                            points = (len(unique_tiles) * 2) + (shield_count * 2)
                            summary = f"{len(unique_tiles)} tiles, {shield_count} shields"
                        else: # ROAD
                            points = len(unique_tiles)
                            summary = f"{len(unique_tiles)} tiles"

                        if points > 0:
                            scored_points += points
                            m_count = 0
                            for cx, cy, ci in components:
                                if self.grid[(cx, cy)].meeple and self.grid[(cx, cy)].meeple[0] == ci:
                                    self.grid[(cx, cy)].meeple = None
                                    returned_meeples += 1
                                    m_count += 1
                            msg = f"{f_name} CLOSED: +{points} pts ({summary})"
                            print(msg, flush=True); log.append(msg)
                            ret_msg = f"  -> {m_count} meeple(s) returned"
                            print(ret_msg, flush=True); log.append(ret_msg)
                            new_effects.append(ScoreEffect(msg, x, y))
                                    
        return scored_points, returned_meeples, new_effects

    def calculate_final_scores(self, log):
        """Scores incomplete features at the end of the game."""
        final_points = 0
        final_effects = []
        
        header = "--- FINAL SCORING ---"
        print(header, flush=True); log.append(header)
        
        for (x, y), tile in list(self.grid.items()):
            if tile.meeple:
                feat_idx, _ = tile.meeple
                feat = tile.features[feat_idx]
                f_type = feat['type']
                
                if f_type == 'A': # Cloister
                    neighbors = sum(1 for dx in [-1,0,1] for dy in [-1,0,1] if (dx!=0 or dy!=0) and (x+dx, y+dy) in self.grid)
                    points = 1 + neighbors
                    final_points += points
                    msg = f"Incomplete Cloister: +{points} pts"
                    print(msg, flush=True); log.append(msg)
                    final_effects.append(ScoreEffect(msg, x, y))
                
                elif f_type in [CITY, ROAD]:
                    components, _ = self.trace_feature(x, y, feat_idx)
                    unique_tiles = set((cx, cy) for cx, cy, ci in components)
                    
                    if f_type == CITY:
                        # Incomplete cities get 1 pt per tile + 1 pt per shield
                        # Count unique shield symbols found in the city network
                        shield_count = sum(1 for cx, cy, ci in components if self.grid[(cx, cy)].features[ci].get('shield'))
                        points = len(unique_tiles) + shield_count
                        f_name = "City"
                    else: # ROAD
                        points = len(unique_tiles)
                        f_name = "Road"
                        
                    final_points += points
                    msg = f"Incomplete {f_name}: +{points} pts"
                    print(msg); log.append(msg)
                    final_effects.append(ScoreEffect(msg, x, y))
                
                # Remove meeple to avoid double counting if the same feature has multiple meeples
                # (Standard rules dictate the player with the most meeples gets full points, 
                # but this keeps it simple for a single player version)
                tile.meeple = None
                
        footer = f"TOTAL FINAL SCORE: {final_points}"
        print(footer); log.append(footer)
        return final_points, final_effects

    def is_feature_occupied(self, x, y, feature_index, visited=None):
        # (Standard recursive check using trace_feature logic or similar)
        # Included here for brevity:
        components, _ = self.trace_feature(x, y, feature_index)
        for cx, cy, ci in components:
            if self.grid[(cx, cy)].meeple and self.grid[(cx, cy)].meeple[0] == ci:
                return True
        return False

    def is_valid_placement(self, x, y, tile):
        if (x, y) in self.grid: return False 
        checks = {(x,y-1):([0,1,2],[8,7,6]), (x+1,y):([3,4,5],[11,10,9]), (x,y+1):([6,7,8],[2,1,0]), (x-1,y):([9,10,11],[5,4,3])}
        has_neighbor = False
        for (nx, ny), (own_s, nb_s) in checks.items():
            if (nx, ny) in self.grid:
                has_neighbor = True
                for i in range(3):
                    own_f = next((f for f in tile.features if own_s[i] in f['edges']), None)
                    nb_f = next((f for f in self.grid[(nx, ny)].features if nb_s[i] in f['edges']), None)
                    if not own_f or not nb_f or own_f['type'] != nb_f['type']: return False
        return has_neighbor