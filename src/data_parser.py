
import re
import argparse
import json
from typing import List, Dict, Union

VALID_CLUBS = ["D", "W3", "W5", "UW", "U3", "U4", "I3", "I4", "I5", "I6", "I7", "I8", "I9", "IP", "IA", "48", "52", "56", "P"]
DEFAULT_DISTANCES = [220, 200, 180, 190, 180, 170, 175, 165, 155, 145, 135, 125, 115, 105, 95, 95, 85, 75, 7]

def parse_file(file_path: str) -> Dict[str, Union[str, List[Dict], List[str]]]:
    with open(file_path, 'r') as f:
        lines = f.readlines()

    round_data = {
        'file_name': file_path,
        'tee_off_time': None,
        'golf_course': None,
        'co_players': None,
        'holes': [],
        'unparsed_lines': []
    }
    current_hole = None

    for line_num, line in enumerate(lines):
        original_line = line.strip()
        processed_line = original_line.upper()

        if not processed_line:
            continue

        if line_num == 0:
            parts = original_line.split(' ', 3) # Split into date, time, golf_course, and co_players
            if len(parts) >= 2:
                round_data['tee_off_time'] = f"{parts[0]} {parts[1]}"
            if len(parts) >= 3:
                round_data['golf_course'] = parts[2]
            if len(parts) >= 4:
                round_data['co_players'] = parts[3]
            continue

        hole_match = re.match(r'(\d+)\s*P(\d+)', processed_line)
        if hole_match:
            if current_hole:
                round_data['holes'].append(current_hole)
            current_hole = {
                'hole_num': int(hole_match.group(1)),
                'par': int(hole_match.group(2)),
                'shots': []
            }
        elif current_hole:
            shot_components = processed_line.split()
            
            shot_data = {
                'club': None,
                'feel': None,
                'result': None,
                'distance': None,
                'score': 1, # Default score is 1
                'on': 'fairway', # Default 'on' status
                'concede': False, 
                'penalty': None, 
            }
            
            # Track if club, feel, result have been assigned
            c_f_r_assigned = 0 # 0: none, 1: club, 2: club+feel, 3: club+feel+result

            for part in shot_components:
                if part in VALID_CLUBS and shot_data['club'] is None:
                    shot_data['club'] = part
                    c_f_r_assigned = 1
                elif c_f_r_assigned == 1 and (part == 'A' or part == 'B' or part == 'C') and shot_data['feel'] is None:
                    shot_data['feel'] = part
                    c_f_r_assigned = 2
                elif c_f_r_assigned == 2 and (part == 'A' or part == 'B' or part == 'C') and shot_data['result'] is None:
                    shot_data['result'] = part
                    c_f_r_assigned = 3
                else:
                    try:
                        # Try to convert to float for distance
                        distance_val = float(part)
                        if distance_val == int(distance_val):
                            shot_data['distance'] = int(distance_val)
                        else:
                            shot_data['distance'] = distance_val
                    except ValueError:
                        # Not a distance, check for penalty/concede/bunker
                        if part == 'OK':
                            shot_data['score'] += 1 # Concede adds 1 stroke
                            shot_data['concede'] = True
                        elif part == 'H' or part == 'UN': 
                            shot_data['score'] += 1 # Penalty H/UN adds 1 stroke
                            shot_data['penalty'] = part
                        elif part == 'OB':
                            shot_data['score'] += 2 # Penalty OB adds 2 strokes
                            shot_data['penalty'] = part
                        elif part == 'B':
                            shot_data['on'] = 'bunker' # Bunker shot
                        else:
                            # If it's none of the above, it's an unparsed part
                            round_data['unparsed_lines'].append(original_line)
                            break # Stop processing this line

            # Set default distance if not explicitly provided and club is valid
            if shot_data['distance'] is None and shot_data['club'] in VALID_CLUBS:
                try:
                    club_index = VALID_CLUBS.index(shot_data['club'])
                    shot_data['distance'] = DEFAULT_DISTANCES[club_index]
                except ValueError:
                    pass # Club not found or index out of bounds

            # Add shot to current_hole only if a club or distance or penalty/concede was identified
            if shot_data['club'] or shot_data['distance'] is not None or shot_data['penalty'] is not None or shot_data['concede']:
                current_hole['shots'].append(shot_data)
            else:
                round_data['unparsed_lines'].append(original_line)

    if current_hole:
        # Calculate putt, retplace, and error for each shot in the current_hole
        putt_count = 0
        for i, shot in enumerate(current_hole['shots']):
            # Calculate putt count
            if shot['club'] == 'P':
                putt_count += 1

            # Calculate retplace
            if i < len(current_hole['shots']) - 1: # Not the last shot of the hole
                next_shot = current_hole['shots'][i+1]
                shot['retplace'] = next_shot['on']
            else: # Last shot of the hole
                shot['retplace'] = 'hole cup'

            # Calculate error
            if i < len(current_hole['shots']) - 1: # Not the last shot of the hole
                next_shot = current_hole['shots'][i+1]
                if next_shot['distance'] is not None and next_shot['distance'] < 100:
                    shot['error'] = next_shot['distance']
                else:
                    shot['error'] = None
            else:
                shot['error'] = None # Last shot has no next shot distance
        
        current_hole['putt'] = putt_count # Add putt count to hole data
        round_data['holes'].append(current_hole)

    return round_data, calculate_scores_and_stats(round_data)

def analyze_shots_and_stats(all_shots: List[Dict]) -> Dict:
    data = {
        # Penalty counts:
        "UN":0,  # Count of unplayable penalties (readdata.py specific, adds 1 stroke)
        "H": 0,   # Count of hazard penalties (adds 1 stroke)
        "OB" : 0,  # Count of out of bounds penalties (adds 2 strokes)

        # Club feel statistics (A: Excellent, B: Good, C: Poor) - stores counts for each feel category:
        "D":[0,0,0], # Driver feel counts [A, B, C]
        "U":[0,0,0], # Utility/Hybrid feel counts [A, B, C]

        # Driver specific penalty counts:
        "DH" : 0,  # Driver shots resulting in Hazard penalty
        "DOB" : 0, # Driver shots resulting in Out of Bounds penalty
        "DUN":0, # Driver shots resulting in Unplayable penalty

        # Feel-Result combination statistics (counts of specific feel-result pairs):
        "BT" : 0,  # Bad Touch shots (e.g., BA, CB, CA combinations of Feel and Result)
        "WS" : 0,  # Weak Shot shots (e.g., BC, AB, AC combinations of Feel and Result)
        "SA" : 0,  # Solid Shot shots (e.g., AA, BB, CC combinations of Feel and Result)

        # Putter and Concede (OK) counts:
        "P" : [0,0,0], # Putter feel counts [A, B, C]
        "OK" : 0, # Total shots conceded (marked as OK, adds 1 stroke)
        "WOK" : 0, # Conceded shots not made with Putter (Wedge OK)

        # Iron club feel statistics (A, B, C counts for each iron type):
        "LI":[0,0,0], # Long Iron (I3, I4) feel counts [A, B, C]
        "MI" : [0,0,0], # Mid Iron (I5, I6, I7) feel counts [A, B, C]
        "SI" : [0,0,0], # Short Iron (I8, I9, IP, IA, 48, 52, 56) feel counts [A, B, C]

        # Wedge club feel statistics (A, B, C counts):
        "W" : [0,0,0], # Wedge (UW, W3, W5) feel counts [A, B, C]

        # Overall Feel counts (total shots for each feel category):
        "FA" : 0,  # Total shots with 'A' Feel
        "FB" : 0,  # Total shots with 'B' Feel
        "FC" : 0,  # Total shots with 'C' Feel

        # Overall Result counts (total shots for each result category):
        "A" : 0,   # Total shots with 'A' Result
        "B" : 0,   # Total shots with 'B' Result
        "C" : 0,   # Total shots with 'C' Result

        # Specific Feel-Result combinations (raw counts):
        "AA" : 0, "AB" : 0, "AC": 0,
        "BA" : 0 , "BB" : 0, "BC" : 0,
        "CA" : 0, "CB" : 0, "CC" : 0
    }
    bdata = {"B" : 0, "ESB" : 0}

    def _update_club_feel(current_data, shot_feel):
        if shot_feel == "A":
            current_data[0] += 1
        elif shot_feel == "B":
            current_data[1] += 1
        else:
            current_data[2] += 1
        return current_data

    for shot in all_shots:
        # Penalty and OK counts
        if shot['penalty'] == 'H':
            data['H'] += 1
            if shot['club'] == 'D':
                data['DH'] += 1
        elif shot['penalty'] == 'OB':
            data['OB'] += 1
            if shot['club'] == 'D':
                data['DOB'] += 1
        elif shot['penalty'] == 'UN':
            data['UN'] += 1
            if shot['club'] == 'D':
                data['DUN'] += 1

        if shot['concede']:
            data['OK'] += 1 
            if shot['club'] != 'P':
                data['WOK'] += 1

        # Club specific stats
        if shot['club'] == 'D':
            data['D'] = _update_club_feel(data['D'], shot['feel'])
        elif shot['club'] in ["UW", "W3", "W5"]:
            data['W'] = _update_club_feel(data['W'], shot['feel'])
        elif shot['club'] in ["U3", "U4"]:
            data['U'] = _update_club_feel(data['U'], shot['feel'])
        elif shot['club'] == 'P':
            data['P'] = _update_club_feel(data['P'], shot['feel'])
        elif shot['club'] in ["I3", "I4"]:
            data['LI'] = _update_club_feel(data['LI'], shot['feel'])
        elif shot['club'] in ["I5", "I6", "I7"]:
            data['MI'] = _update_club_feel(data['MI'], shot['feel'])
        elif shot['club'] in ["I8", "I9", "IP", "IA", "48", "52", "56"]:
            data['SI'] = _update_club_feel(data['SI'], shot['feel'])

        # Feel and Result combinations
        if shot['feel']:
            data[shot['feel']] += 1
            data[f"F{shot['feel']}"] += 1
        if shot['result']:
            data[shot['result']] += 1
        if shot['feel'] and shot['result']:
            combo = f"{shot['feel']}{shot['result']}"
            data[combo] += 1
            if combo in ("AA", "BB", "CC"):
                data["SA"] += 1
            elif combo in ("BA", "CB", "CA"):
                data["BT"] += 1
            elif combo in ("BC", "AB", "AC"):
                data["WS"] += 1

        # Bunker stats
        if shot['on'] == 'bunker':
            bdata['B'] += 1

    total_shots = float(len(all_shots))
    
    # Calculate percentages for feel/result
    rdata = {}
    for k in ["H", "OB", "UN", "BT", "WS", "SA", "OK", "WOK", "FA", "FB", "FC", "A", "B", "C", "AA", "AB", "AC", "BA", "BB", "BC", "CA", "CB", "CC"]:
        rdata[k] = data[k] / total_shots if total_shots > 0 else 0

    # Calculate club feel percentages
    club_feel_stats = {}
    for club_type in ["D", "U", "LI", "MI", "SI", "W", "P"]:
        n = sum(data[club_type])
        if n > 0:
            club_feel_stats[club_type] = {
                "A": data[club_type][0] / n,
                "B": data[club_type][1] / n,
                "C": data[club_type][2] / n,
                "total_percentage": n / total_shots if total_shots > 0 else 0
            }
        else:
            club_feel_stats[club_type] = {"A": 0, "B": 0, "C": 0, "total_percentage": 0}

    # Bunker success rate (ESB - Exited Sand Bunker)
    rbdata = {"B" : bdata["B"] / total_shots if total_shots > 0 else 0, "ESB" : 0}
    # readdata.py's ESB logic is complex and depends on sequential shots. 
    # For simplicity, we'll just count bunker entries for now.
    # If detailed ESB is needed, more context (previous shot's 'on' status) is required.

    return {
        "raw_stats": data,
        "relative_stats": rdata,
        "club_feel_stats": club_feel_stats,
        "bunker_stats": rbdata,
        "total_shots_analyzed": total_shots
    }

def calculate_scores_and_stats(round_data: Dict) -> Dict:
    stats = {
        'front_nine': {'total_shots': 0, 'total_par': 0, 'score_relative_to_par': 0, 'holes': []},
        'back_nine': {'total_shots': 0, 'total_par': 0, 'score_relative_to_par': 0, 'holes': []},
        'overall': {'total_shots': 0, 'total_par': 0, 'score_relative_to_par': 0}
    }

    for i, hole in enumerate(round_data['holes']):
        # Use the accumulated score from parsing, not len(hole['shots'])
        shots_taken = sum(shot['score'] for shot in hole['shots'])
        
        par = hole['par']
        score_diff = shots_taken - par

        hole_stats = {
            'hole_num': hole['hole_num'],
            'par': par,
            'shots_taken': shots_taken,
            'score_diff': score_diff
        }

        if i < 9: # Front nine
            current_nine = stats['front_nine']
        else: # Back nine
            current_nine = stats['back_nine']
        
        current_nine['total_shots'] += shots_taken
        current_nine['total_par'] += par
        current_nine['score_relative_to_par'] += score_diff
        current_nine['holes'].append(hole_stats)

        stats['overall']['total_shots'] += shots_taken
        stats['overall']['total_par'] += par
        stats['overall']['score_relative_to_par'] += score_diff
    
    return stats

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse golf round data from a file.")
    parser.add_argument("file_path", help="Path to the data file to parse.")
    args = parser.parse_args()

    try:
        parsed_data = parse_file(args.file_path)
        print(json.dumps(parsed_data, indent=4, ensure_ascii=False))
        
        # Calculate and print scores and statistics
        scores_and_stats = calculate_scores_and_stats(parsed_data)
        print("\n--- Scores and Statistics (9-hole breakdown) ---")
        print(json.dumps(scores_and_stats, indent=4, ensure_ascii=False))

        # Collect all shots for detailed analysis
        all_shots = []
        for hole in parsed_data['holes']:
            all_shots.extend(hole['shots'])

        # Analyze detailed shot statistics
        detailed_shot_stats = analyze_shots_and_stats(all_shots)
        print("\n--- Detailed Shot Statistics ---")
        print(json.dumps(detailed_shot_stats, indent=4, ensure_ascii=False))

    except FileNotFoundError:
        print(f"Error: File not found at {args.file_path}")
    except Exception as e:
        import traceback
        print(f"An error occurred: {e}")
        traceback.print_exc()
