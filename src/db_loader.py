
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

def get_filtered_rounds(year: str = 'all', golf_course: str = 'all', companion: str = 'all', sort_by: str = 'playdate', sort_order: str = 'ASC', search_query: str = None):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT *, gir FROM rounds WHERE score IS NOT NULL"
    params = []

    if year != 'all':
        query += " AND YEAR(playdate) = %s"
        params.append(year)
    
    if golf_course != 'all':
        query += " AND gcname = %s"
        params.append(golf_course)

    if companion != 'all':
        query += " AND coplayers LIKE %s"
        params.append(f'%{companion}%')

    if search_query:
        search_term = f'%{search_query}%'
        query += " AND (gcname LIKE %s OR coplayers LIKE %s)"
        params.append(search_term)
        params.append(search_term)
    
    # Validate sort_by to prevent SQL injection
    valid_sort_columns = ['playdate', 'gcname', 'coplayers', 'score', 'gir']
    if sort_by not in valid_sort_columns:
        sort_by = 'playdate' # Default to playdate if invalid

    # Validate sort_order
    if sort_order.upper() not in ['ASC', 'DESC']:
        sort_order = 'ASC' # Default to ASC if invalid

    query += f" ORDER BY {sort_by} {sort_order}"

    cursor.execute(query, params)
    rounds = cursor.fetchall()

    cursor.close()
    conn.close()
    return rounds

def get_unique_years():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT DISTINCT YEAR(playdate) AS year FROM rounds ORDER BY year DESC")
    unique_years = [row['year'] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return unique_years

def get_unique_golf_courses():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT DISTINCT gcname FROM rounds ORDER BY gcname ASC")
    unique_golf_courses = [row['gcname'] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return unique_golf_courses

def get_unique_companions():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT DISTINCT coplayers FROM rounds")
    all_coplayers = []
    for row in cursor.fetchall():
        if row['coplayers']:
            all_coplayers.extend([c.strip() for c in row['coplayers'].split(',')])
    unique_companions = sorted(list(set(all_coplayers)))
    cursor.close()
    conn.close()
    return unique_companions

def save_round_data(parsed_data: Dict, scores_and_stats: Dict, raw_data: str = None):
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check for duplicate tee_off_time before proceeding
    cursor.execute("SELECT id FROM rounds WHERE playdate = %s", (parsed_data['tee_off_time'],))
    if cursor.fetchone() and not parsed_data.get('id'): # Check only for new entries
        cursor.close()
        conn.close()
        raise Exception(f"Duplicate entry: A round with tee-off time {parsed_data['tee_off_time']} already exists.")

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
        
        cursor.execute(update_round_sql, round_values)
        
    else:
        
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
        
        cursor.execute(add_round, round_values)
        round_id = cursor.lastrowid
        

    # Insert into nines table
    
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
    

    conn.commit()
    
    cursor.close()
    conn.close()

def get_yearly_round_statistics():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT
            YEAR(playdate) AS year,
            COUNT(id) AS total_rounds,
            AVG(score) AS average_score,
            MIN(score) AS lowest_score,
            MAX(score) AS highest_score
        FROM rounds
        GROUP BY YEAR(playdate)
        ORDER BY year DESC
    """
    cursor.execute(query)
    yearly_stats = cursor.fetchall()
    cursor.close()
    conn.close()
    return yearly_stats

def delete_round_data(round_id: int, conn=None):
    if conn is None:
        conn = get_db_connection()
        _close_conn = True
    else:
        _close_conn = False

    cursor = conn.cursor()
    try:
        # Delete from shots table
        cursor.execute("DELETE FROM shots WHERE roundid = %s", (round_id,))
        # Delete from holes table
        cursor.execute("DELETE FROM holes WHERE roundid = %s", (round_id,))
        # Delete from nines table
        cursor.execute("DELETE FROM nines WHERE roundid = %s", (round_id,))
        
        # Only delete from rounds table if this is a standalone delete operation
        if _close_conn:
            cursor.execute("DELETE FROM rounds WHERE id = %s", (round_id,))
        
        if _close_conn:
            conn.commit()
    except Exception as e:
        if _close_conn:
            conn.rollback()
        raise e
    finally:
        cursor.close()
        if _close_conn:
            conn.close()

def get_all_rounds_for_trend_analysis():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT
            r.id AS round_id,
            r.score AS round_score,
            r.gir AS round_gir,
            r.playdate,
            h.holenum,
            h.par AS hole_par,
            h.score AS hole_score,
            h.putt,
            s.club,
            s.penalty,
            s.distance,
            s.retgrade
        FROM rounds r
        LEFT JOIN holes h ON r.id = h.roundid
        LEFT JOIN shots s ON r.id = s.roundid AND h.holenum = s.holenum
        ORDER BY r.playdate ASC, h.holenum ASC, s.id ASC
    """
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data
