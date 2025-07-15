
import re
import argparse
import json
from typing import List, Dict, Union

VALID_CLUBS = ["D", "W3", "W5", "UW", "U3", "U4", "I3", "I4", "I5", "I6", "I7", "I8", "I9", "IP", "IA", "48", "52", "56", "P"]
DEFAULT_DISTANCES = [220, 200, 180, 190, 180, 170, 175, 165, 155, 145, 135, 125, 115, 105, 95, 95, 85, 75, 7]

def _parse_tee_off_time(original_line: str) -> Union[str, None]:
    """Parses a line to extract tee-off time in 'YYYY-MM-DD HH:MM' format."""
    processed_time = original_line.strip()

    # Try YYYY.MM.DD HH:MM
    match_dot_time = re.match(r'(\d{4})\.(\d{2})\.(\d{2})\s+(\d{2}:\d{2})', processed_time)
    if match_dot_time:
        return f"{match_dot_time.group(1)}-{match_dot_time.group(2)}-{match_dot_time.group(3)} {match_dot_time.group(4)}"

    # Try YYYYMMDD HH:MM
    match_8digit_time = re.match(r'(\d{8})\s+(\d{2}:\d{2})', processed_time)
    if match_8digit_time:
        date_part = match_8digit_time.group(1)
        time_part = match_8digit_time.group(2)
        return f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]} {time_part}"

    # Try YYYY-MM-DD HH:MM (already in target format)
    match_hyphen_time = re.match(r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})', processed_time)
    if match_hyphen_time:
        return processed_time

    # If only date is provided, append default time
    # Try YYYY.MM.DD
    match_dot_date_only = re.match(r'(\d{4})\.(\d{2})\.(\d{2})', processed_time)
    if match_dot_date_only:
        return f"{match_dot_date_only.group(1)}-{match_dot_date_only.group(2)}-{match_dot_date_only.group(3)} 00:00"

    # Try YYYYMMDD
    match_8digit_date_only = re.match(r'(\d{8})', processed_time)
    if match_8digit_date_only:
        date_part = match_8digit_date_only.group(1)
        return f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]} 00:00"

    # Try YYYY-MM-DD
    match_hyphen_date_only = re.match(r'(\d{4}-\d{2}-\d{2})', processed_time)
    if match_hyphen_date_only:
        return f"{match_hyphen_date_only.group(1)} 00:00"

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
    header_lines = []
    for line_num, line in enumerate(lines):
        original_line = line.strip()
        processed_line = original_line.upper()

        if not processed_line:
            continue

        hole_match = re.match(r'(\d+)\s*P(\d+)', processed_line)

        if not header_processing_done:
            header_lines.append(original_line)
            # Try to parse header information from accumulated header_lines
            # This makes the header parsing more robust to multi-line headers
            temp_tee_off_time = None
            temp_golf_course = None
            temp_co_players = None

            # Attempt to parse tee_off_time, golf_course, co_players from header_lines
            # This logic needs to be more flexible to handle various header formats
            # For now, let's assume tee_off_time is always the first valid line that matches the pattern
            # and golf_course/co_players follow.
            for h_line in header_lines:
                if temp_tee_off_time is None:
                    parsed_time = _parse_tee_off_time(h_line)
                    if parsed_time:
                        temp_tee_off_time = parsed_time
                        continue
                
                if temp_tee_off_time and temp_golf_course is None:
                    # Assuming golf course is the next non-empty line after tee-off time
                    if h_line != temp_tee_off_time and h_line.strip(): # Avoid using the time line itself
                        temp_golf_course = h_line.strip()
                        continue

                if temp_tee_off_time and temp_golf_course and temp_co_players is None:
                    # Assuming co_players is the next non-empty line after golf course
                    if h_line != temp_tee_off_time and h_line != temp_golf_course and h_line.strip():
                        temp_co_players = h_line.strip()
                        continue

            if temp_tee_off_time:
                round_data['tee_off_time'] = temp_tee_off_time
            if temp_golf_course:
                round_data['golf_course'] = temp_golf_course
            if temp_co_players:
                round_data['co_players'] = temp_co_players

            if hole_match or (round_data['tee_off_time'] and round_data['golf_course'] and round_data['co_players']):
                header_processing_done = True
                # If a hole match is found, process it immediately
                if hole_match:
                    if current_hole:
                        round_data['holes'].append(current_hole)
                    current_hole = {
                        'hole_num': int(hole_match.group(1)),
                        'par': int(hole_match.group(2)),
                        'shots': []
                    }
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
            shot_data = _parse_shot(original_line)
            if shot_data is None:
                round_data['unparsed_lines'].append(original_line)
            else:
                current_hole['shots'].append(shot_data)

    if current_hole:
        round_data['holes'].append(current_hole)

    _post_process_shots(round_data)
    return round_data, calculate_scores_and_stats(round_data)

def _post_process_shots(round_data: Dict):
    for hole in round_data['holes']:
        putt = 0
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

            if shot['club'] == 'P':
                putt += 1
            if shot['concede'] is True:
                putt += 1
        hole['putt'] = putt

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
        "BT" : 0,  # Lucky Shot (e.g., CB, CA combinations of Feel and Result)
        "WS" : 0,  # Bad Management (e.g., BC, AC combinations of Feel and Result)
        "SA" : 0,  # Normal shots (e.g., AA, AB, BA, BB, CC combinations of Feel and Result)

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
            if combo in ("AA", "AB", "BA", "BB", "CC"):
                data["SA"] += 1
            elif combo in ("CB", "CA"):
                data["BT"] += 1
            elif combo in ("BC", "AC"):
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
        'front_nine': {'total_shots': 0, 'total_par': 0, 'score_relative_to_par': 0, 'holes': [], 'gir': 0},
        'back_nine': {'total_shots': 0, 'total_par': 0, 'score_relative_to_par': 0, 'holes': [], 'gir': 0},
        'extra_nine': {'total_shots': 0, 'total_par': 0, 'score_relative_to_par': 0, 'holes': [], 'gir': 0},
        'overall': {'total_shots': 0, 'total_par': 0, 'score_relative_to_par': 0, 'gir': 0}
    }

    gir_count = 0
    for i, hole in enumerate(round_data['holes']):
        shots_taken = sum(shot['score'] for shot in hole['shots'])
        
        par = hole['par']
        score_diff = shots_taken - par

        is_gir = True if par >= shots_taken - hole['putt'] + 2 else False
        if is_gir:
            gir_count += 1

        hole_stats = {
            'hole_num': hole['hole_num'],
            'par': par,
            'shots_taken': shots_taken,
            'score_diff': score_diff,
            'GIR': is_gir,
            'GIR1': True if par >= shots_taken - hole['putt'] + 1 else False
        }

        if i < 9: # Front nine
            current_nine = stats['front_nine']
        elif i < 18: # Back nine
            current_nine = stats['back_nine']
        else: # Extra nine
            current_nine = stats['extra_nine']
        
        current_nine['total_shots'] += shots_taken
        current_nine['total_par'] += par
        current_nine['score_relative_to_par'] += score_diff
        current_nine['holes'].append(hole_stats)

        stats['overall']['total_shots'] += shots_taken
        stats['overall']['total_par'] += par
        stats['overall']['score_relative_to_par'] += score_diff

    # Calculate GIR percentages
    num_holes = len(round_data['holes'])
    if num_holes > 0:
        stats['overall']['gir'] = (gir_count / num_holes) * 100

    num_front_nine_holes = len(stats['front_nine']['holes'])
    if num_front_nine_holes > 0:
        front_nine_gir_count = sum(1 for h in stats['front_nine']['holes'] if h['GIR'])
        stats['front_nine']['gir'] = (front_nine_gir_count / num_front_nine_holes) * 100

    num_back_nine_holes = len(stats['back_nine']['holes'])
    if num_back_nine_holes > 0:
        back_nine_gir_count = sum(1 for h in stats['back_nine']['holes'] if h['GIR'])
        stats['back_nine']['gir'] = (back_nine_gir_count / num_back_nine_holes) * 100

    num_extra_nine_holes = len(stats['extra_nine']['holes'])
    if num_extra_nine_holes > 0:
        extra_nine_gir_count = sum(1 for h in stats['extra_nine']['holes'] if h['GIR'])
        stats['extra_nine']['gir'] = (extra_nine_gir_count / num_extra_nine_holes) * 100

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
