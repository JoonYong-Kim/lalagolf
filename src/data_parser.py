
import re
import argparse
import json
from typing import List, Dict, Union

VALID_CLUBS = ["D", "W3", "W5", "UW", "U3", "U4", "I3", "I4", "I5", "I6", "I7", "I8", "I9", "IP", "IA", "48", "52", "56", "P"]
DEFAULT_DISTANCES = [220, 200, 180, 190, 180, 170, 175, 165, 155, 145, 135, 125, 115, 105, 95, 95, 85, 75, 7]

def _parse_tee_off_time(original_line: str) -> Union[str, None]:
    """Parses a line to extract tee-off time in 'YYYY-MM-DD HH:MM' format."""
    processed_time = original_line

    # YYYY.MM.DD HH:MM -> YYYY-MM-DD HH:MM
    match_dot = re.match(r'(\d{4})\.(\d{2})\.(\d{2})(.*)', processed_time)
    if match_dot:
        processed_time = f"{match_dot.group(1)}-{match_dot.group(2)}-{match_dot.group(3)}{match_dot.group(4)}"

    # YYYYMMDD HH:MM -> YYYY-MM-DD HH:MM
    match_8digit = re.match(r'(\d{8})(.*)', processed_time)
    if match_8digit:
        date_part = match_8digit.group(1)
        rest_of_string = match_8digit.group(2).strip()
        processed_time = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]} {rest_of_string}".strip()

    if re.search(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}', processed_time):
        return processed_time
    return None

def _find_club(line:str) -> str:
    for i in range(1, 3):
        prefix = line[:i]
        if prefix in VALID_CLUBS:
            return prefix
    raise ValueError

def _find_grade(line:str) -> str:
    prefix = line[0]
    if prefix in ['A', 'B', 'C']:
        return prefix
    raise ValueError

def _find_distance(line:str) -> str:
    match = re.search(r'\d+', line)
    if match:
        return match.group()
    else:
        return ""

def _find_etc(line:str) -> str:
    return line

def _parse_shot_components(shot_line:str) -> List[str]:
    """Parse a line to shot components."""
    try:
        components = []

        for func in [_find_club, _find_grade, _find_grade, _find_distance, _find_etc]:
            shot_line = shot_line.lstrip()
            tmp = func(shot_line)
            components.append(tmp)
            shot_line = shot_line[len(tmp):]

        return components
    except:
        return None

def _parse_shot(original_line:str) -> Dict:
    processed_line = original_line.upper()
    shot_components = _parse_shot_components(processed_line)
    if shot_components is None:
        return None

    club_index = VALID_CLUBS.index(shot_components[0])
    
    shot_data = {
        'club': shot_components[0],
        'feel': shot_components[1],
        'result': shot_components[2],
        'distance': float(shot_components[3]) if shot_components[3] != "" else DEFAULT_DISTANCES[club_index],
        'score': 1, # Default score is 1
        'on': 'F',
        'concede': False, 
        'penalty': None, 
        'retplace': 'F',
        'original_line': original_line # Store original line for 'on' override
    }

    if shot_components[2] == 'C':
        shot_data['retplace'] = 'R'
    
    code = shot_components[4]
    if code == 'OK':
        shot_data['score'] += 1
        shot_data['concede'] = True
    elif code == 'H' or code == 'UN':
        shot_data['score'] += 1
        shot_data['penalty'] = code
        shot_data['retplace'] = 'F'     # hazard tee or replace
    elif code == 'OB':
        shot_data['score'] += 2
        shot_data['penalty'] = code
        shot_data['retplace'] = 'F'     # ob tee
    elif code == 'B':
        shot_data['retplace'] = 'B'     # bunker

    return shot_data

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
    header_processing_done = False

    for line_num, line in enumerate(lines):
        original_line = line.strip()
        processed_line = original_line.upper()

        if not processed_line:
            continue

        hole_match = re.match(r'(\d+)\s*P(\d+)', processed_line)

        if not header_processing_done:
            if line_num == 0:
                parts = original_line.split(' ', 3)
                if len(parts) >= 3 and re.match(r'\d{8}', parts[0]) and re.match(r'\d{2}:\d{2}', parts[1]):
                    parsed_time = _parse_tee_off_time(f"{parts[0]} {parts[1]}")
                    if parsed_time:
                        round_data['tee_off_time'] = parsed_time
                        round_data['golf_course'] = parts[2]
                        if len(parts) >= 4:
                            round_data['co_players'] = parts[3]
                        header_processing_done = True
                        continue
            
            if hole_match:
                header_processing_done = True
            else:
                # Process multi-line header
                if round_data['tee_off_time'] is None:
                    parsed_time = _parse_tee_off_time(original_line)
                    if parsed_time:
                        round_data['tee_off_time'] = parsed_time
                elif round_data['golf_course'] is None:
                    round_data['golf_course'] = original_line
                elif round_data['co_players'] is None:
                    round_data['co_players'] = original_line
                else:
                    round_data['co_players'] += f", {original_line}"
                continue

        if hole_match:
            if current_hole:
                round_data['holes'].append(current_hole)

            current_hole = {
                'hole_num': int(hole_match.group(1)),
                'par': int(hole_match.group(2)),
                'shots': []
            }

        elif current_hole:
            #shot_components = processed_line.split()
            shot_data = _parse_shot(original_line)
            if shot_data is None:
                round_data['unparsed_lines'].append(original_line)
            else:
                current_hole['shots'].append(shot_data)

    if current_hole:
        # Calculate putt for each shot in the current_hole
        putt_count = 0
        for i, shot in enumerate(current_hole['shots']):
            # Calculate putt count
            if shot['club'] == 'P':
                putt_count += 1
            if shot['concede'] is True:
                putt_count += 1
        
        current_hole['putt'] = putt_count # Add putt count to hole data
        round_data['holes'].append(current_hole)

    _post_process_shots(round_data)
    return round_data, calculate_scores_and_stats(round_data)

def _post_process_shots(round_data: Dict):
    for hole in round_data['holes']:
        for i, shot in enumerate(hole['shots']):
            # Determine 'on' status based on previous shot's retplace or default
            if i == 0:
                # First shot of the hole, default to 'T' (Tee)
                shot['on'] = 'T'
            else:
                # Subsequent shots, 'on' is previous shot's 'retplace'
                shot['on'] = hole['shots'][i-1]['retplace']

                if shot['club'] == 'P' and shot['on'] == 'F':
                    shot['on'] = 'G'  # Putter shots end in the hole cup
                    hole['shots'][i-1]['retplace'] = 'G'

            if i == len(hole['shots']) - 1:     # last shot
                shot['retplace'] = 'H'
                if shot['concede'] is True:
                    shot['error'] = 0.5
                else:
                    shot['error'] = 0
            else:
                if shot['distance'] is not None and shot['distance'] < 160:
                    shot['error'] = hole['shots'][i+1]['distance']
                else:
                    shot['error'] = None

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
        if shot['on'] == 'B':
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
