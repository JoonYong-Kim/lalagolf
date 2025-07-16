
import mysql.connector
from mysql.connector import pooling
from typing import Dict, List

# Global connection pool
connection_pool = None

def init_connection_pool(config: Dict[str, str]):
    global connection_pool
    if connection_pool is None:
        connection_pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="lalagolf_pool",
            pool_size=5,
            **config
        )

def get_db_connection():
    global connection_pool
    if connection_pool is None:
        raise Exception("Connection pool is not initialized. Call init_connection_pool first.")
    return connection_pool.get_connection()

def save_round_data(parsed_data: Dict, scores_and_stats: Dict, raw_data: str = None):
    print(f"[save_round_data] Called with round_id: {parsed_data.get('id')}, raw_data length: {len(raw_data) if raw_data else 0}")
    conn = get_db_connection()
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

    total_par = scores_and_stats['overall']['total_par']
    total_shots = scores_and_stats['overall']['total_shots']

    if total_par > 0 and len(parsed_data['holes']) != 18:
        score_to_save = round((total_shots / total_par) * 72)
    else:
        score_to_save = total_shots

    round_id = parsed_data.get('id') # Get round_id if it exists (for updates)

    if round_id:
        print(f"[save_round_data] Updating existing round: {round_id}")
        # If round_id exists, delete existing hole, nine, and shot data for this round
        delete_round_data(round_id, conn) # Pass conn to use the same transaction

        # Update rounds table
        update_round_sql = ("""
            UPDATE rounds
            SET player = %s, gcname = %s, coplayers = %s, playdate = %s, score = %s, gir = %s, raw_data = %s
            WHERE id = %s
        """)
        round_values = (
            default_player,
            parsed_data['golf_course'],
            co_players_to_save,
            parsed_data['tee_off_time'],
            score_to_save,
            scores_and_stats['overall']['gir'],
            raw_data,
            round_id
        )
        print(f"[save_round_data] Executing UPDATE rounds with values: {round_values}")
        cursor.execute(update_round_sql, round_values)
        print(f"[save_round_data] Successfully updated rounds table for ID: {round_id}")
    else:
        print("[save_round_data] Inserting new round.")
        # Insert into rounds table for new rounds
        add_round = ("""
            INSERT INTO rounds (player, gcname, coplayers, playdate, score, gir, raw_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """)
        round_values = (
            default_player,
            parsed_data['golf_course'],
            co_players_to_save,
            parsed_data['tee_off_time'],
            score_to_save,
            scores_and_stats['overall']['gir'],
            raw_data
        )
        print(f"[save_round_data] Executing INSERT rounds with values: {round_values}")
        cursor.execute(add_round, round_values)
        round_id = cursor.lastrowid
        print(f"[save_round_data] Successfully inserted new round with ID: {round_id}")

    # Insert into nines table
    print("[save_round_data] Inserting nines data.")
    for nine_type in ['front_nine', 'back_nine', 'extra_nine']:
        if nine_type in scores_and_stats and scores_and_stats[nine_type]['holes']:
            nine_data = scores_and_stats[nine_type]
            ord_num = 1 if nine_type == 'front_nine' else (2 if nine_type == 'back_nine' else 3)
            add_nine = ("""
                INSERT INTO nines (roundid, ordnum, course, par, score, gir)
                VALUES (%s, %s, %s, %s, %s, %s)
            """)
            nine_values = (
                round_id,
                ord_num,
                parsed_data['golf_course'], # Using overall golf_course for nines
                nine_data['total_par'],
                nine_data['total_shots'],
                nine_data['gir']
            )
            cursor.execute(add_nine, nine_values)
    print("[save_round_data] Nines data insertion complete.")

    print("[save_round_data] Inserting holes and shots data.")
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
            next((h['shots_taken'] for h in scores_and_stats['back_nine']['holes'] if h['hole_num'] == hole['hole_num']), None) or \
            next((h['shots_taken'] for h in scores_and_stats['extra_nine']['holes'] if h['hole_num'] == hole['hole_num']), None),
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
    print("[save_round_data] Holes and shots data insertion complete.")

    conn.commit()
    print("[save_round_data] Transaction committed.")
    cursor.close()
    conn.close()

def delete_round_data(round_id: int, conn=None):
    print(f"[delete_round_data] Called for round_id: {round_id}, conn provided: {conn is not None}")
    if conn is None:
        conn = get_db_connection()
        _close_conn = True
    else:
        _close_conn = False

    cursor = conn.cursor()
    try:
        # Delete from shots table
        cursor.execute("DELETE FROM shots WHERE roundid = %s", (round_id,))
        print(f"[delete_round_data] Deleted {cursor.rowcount} shots for round_id: {round_id}")
        # Delete from holes table
        cursor.execute("DELETE FROM holes WHERE roundid = %s", (round_id,))
        print(f"[delete_round_data] Deleted {cursor.rowcount} holes for round_id: {round_id}")
        # Delete from nines table
        cursor.execute("DELETE FROM nines WHERE roundid = %s", (round_id,))
        print(f"[delete_round_data] Deleted {cursor.rowcount} nines for round_id: {round_id}")
        
        # Only delete from rounds table if this is a standalone delete operation
        if _close_conn:
            cursor.execute("DELETE FROM rounds WHERE id = %s", (round_id,))
            print(f"[delete_round_data] Deleted {cursor.rowcount} round entry for round_id: {round_id}")
        
        if _close_conn:
            conn.commit()
            print("[delete_round_data] Transaction committed.")
    except Exception as e:
        if _close_conn:
            conn.rollback()
            print(f"[delete_round_data] Transaction rolled back due to error: {e}")
        raise e
    finally:
        cursor.close()
        if _close_conn:
            conn.close()
