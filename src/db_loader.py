
import mysql.connector
from typing import Dict, List

def get_db_connection(config: Dict[str, str]):
    return mysql.connector.connect(
        host=config['host'],
        user=config['user'],
        password=config['password'],
        database=config['database']
    )

def save_round_data(db_config: Dict[str, str], parsed_data: Dict, scores_and_stats: Dict):
    conn = get_db_connection(db_config)
    cursor = conn.cursor()

    # Determine player and co_players
    default_player = "김준용"
    co_players_str = parsed_data['co_players']
    if co_players_str and default_player in co_players_str:
        other_players = co_players_str.replace(default_player, '').strip()
        # Remove extra spaces if any
        co_players_to_save = ' '.join(other_players.split())
    else:
        co_players_to_save = co_players_str

    # Insert into rounds table
    add_round = ("""
        INSERT INTO rounds (player, club, coplayers, playdate, score)
        VALUES (%s, %s, %s, %s, %s)
    """)
    round_values = (
        default_player,
        parsed_data['golf_course'], # Assuming 'club' in rounds table is gcname
        co_players_to_save,
        parsed_data['tee_off_time'],
        scores_and_stats['overall']['total_shots']
    )
    cursor.execute(add_round, round_values)
    round_id = cursor.lastrowid

    # Insert into nines table
    for nine_type in ['front_nine', 'back_nine']:
        if nine_type in scores_and_stats and scores_and_stats[nine_type]['holes']:
            nine_data = scores_and_stats[nine_type]
            ord_num = 1 if nine_type == 'front_nine' else 2
            add_nine = ("""
                INSERT INTO nines (roundid, ordnum, course, par, score)
                VALUES (%s, %s, %s, %s, %s)
            """)
            nine_values = (
                round_id,
                ord_num,
                parsed_data['golf_course'], # Using overall golf_course for nines
                nine_data['total_par'],
                nine_data['total_shots']
            )
            cursor.execute(add_nine, nine_values)

    for hole in parsed_data['holes']:
        # Insert into holes table
        add_hole = ("""
            INSERT INTO holes (roundid, holenum, par, score, putt)
            VALUES (%s, %s, %s, %s, %s)
        """)
        hole_values = (
            round_id,
            hole['hole_num'],
            hole['par'],
            # Use shots_taken from scores_and_stats for hole score
            next((h['shots_taken'] for h in scores_and_stats['front_nine']['holes'] if h['hole_num'] == hole['hole_num']), None) or \
            next((h['shots_taken'] for h in scores_and_stats['back_nine']['holes'] if h['hole_num'] == hole['hole_num']), None),
            hole.get('putt', 0) # Use putt from parsed data, default to 0
        )
        cursor.execute(add_hole, hole_values)

        for shot in hole['shots']:
            # Insert into shots table
            add_shot = ("""
                INSERT INTO shots (roundid, holenum, club, feelgrade, retgrade, concede, score, penalty, retplace, shotplace, distance, error)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """)
            shot_values = (
                round_id,
                hole['hole_num'],
                shot['club'],
                shot['feel'],
                shot['result'],
                shot['concede'],
                shot['score'], # This is the stroke count for the shot including penalties
                shot['penalty'],
                shot.get('retplace'), # Use get to handle cases where it might not exist
                shot.get('on'), # shotplace
                shot.get('distance'),
                shot.get('error')
            )
            cursor.execute(add_shot, shot_values)

    conn.commit()
    cursor.close()
    conn.close()
