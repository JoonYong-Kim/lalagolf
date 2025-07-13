import os
import pytest
from src.data_parser import parse_file

@pytest.fixture
def sample_data_path():
    # Create a dummy data file for testing
    data_dir = 'tests/data'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    file_path = os.path.join(data_dir, 'test_round.txt')
    with open(file_path, 'w') as f:
        f.write("2024.07.13 08:00\n") # Tee-off time
        f.write("Lala Golf Club\n") # Golf Course
        f.write("John, Jane, Mike\n") # Co-players
        f.write("1P4\n")
        f.write("D B C\n")
        f.write("I5 A C 150 H\n")
        f.write("P C A 10 OK\n")
        f.write("2P3\n")
        f.write("I7 A A\n")
        f.write("P B B 5\n")
    return file_path

def test_parse_file(sample_data_path):
    parsed_data, _ = parse_file(sample_data_path)

    assert parsed_data['file_name'] == sample_data_path
    assert parsed_data['tee_off_time'] == "2024-07-13 08:00"
    assert parsed_data['golf_course'] == "Lala Golf Club"
    assert parsed_data['co_players'] == "John, Jane, Mike"
    assert len(parsed_data['holes']) == 2
    assert parsed_data['unparsed_lines'] == []

    # Test Hole 1
    hole1 = parsed_data['holes'][0]
    assert hole1['hole_num'] == 1
    assert hole1['par'] == 4
    assert len(hole1['shots']) == 3

    shot1_1 = hole1['shots'][0]
    assert shot1_1['club'] == 'D'
    assert shot1_1['feel'] == 'B'
    assert shot1_1['result'] == 'C'
    assert shot1_1['distance'] == 220
    assert shot1_1['penalty'] is None
    assert shot1_1['concede'] is False

    shot1_2 = hole1['shots'][1]
    assert shot1_2['club'] == 'I5'
    assert shot1_2['feel'] == 'A'
    assert shot1_2['result'] == 'C'
    assert shot1_2['distance'] == 150
    assert shot1_2['penalty'] == 'H'
    assert shot1_2['concede'] is False

    shot1_3 = hole1['shots'][2]
    assert shot1_3['club'] == 'P'
    assert shot1_3['feel'] == 'C'
    assert shot1_3['result'] == 'A'
    assert shot1_3['distance'] == 10
    assert shot1_3['penalty'] is None
    assert shot1_3['concede'] is True

    # Test Hole 2
    hole2 = parsed_data['holes'][1]
    assert hole2['hole_num'] == 2
    assert hole2['par'] == 3
    assert len(hole2['shots']) == 2

    shot2_1 = hole2['shots'][0]
    assert shot2_1['club'] == 'I7'
    assert shot2_1['feel'] == 'A'
    assert shot2_1['result'] == 'A'
    assert shot2_1['distance'] == 135
    assert shot2_1['penalty'] is None
    assert shot2_1['concede'] is False

    shot2_2 = hole2['shots'][1]
    assert shot2_2['club'] == 'P'
    assert shot2_2['feel'] == 'B'
    assert shot2_2['result'] == 'B'
    assert shot2_2['distance'] == 5
    assert shot2_2['penalty'] is None
    assert shot2_2['concede'] is False

@pytest.fixture
def robust_sample_data_path():
    data_dir = 'tests/data'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    file_path = os.path.join(data_dir, 'test_round_robust.txt')
    with open(file_path, 'w') as f:
        f.write("2024.07.13 09:00\n") # Tee-off time
        f.write("Robust Golf Course\n") # Golf Course
        f.write("Alice, Bob\n") # Co-players
        f.write("1p4\n")
        f.write("d b c\n")
        f.write("i5 a c 150 h\n")
        f.write("p c a 10 ok\n")
        f.write("2 p3\n")
        f.write("i7 a a\n")
        f.write("p b b 5\n")
    return file_path

def test_parse_file_robustness(robust_sample_data_path):
    parsed_data, _ = parse_file(robust_sample_data_path)

    assert parsed_data['file_name'] == robust_sample_data_path
    assert parsed_data['tee_off_time'] == "2024-07-13 09:00"
    assert parsed_data['golf_course'] == "Robust Golf Course"
    assert parsed_data['co_players'] == "Alice, Bob"
    assert len(parsed_data['holes']) == 2

    # Test Hole 1 (lowercase and incomplete spacing)
    hole1 = parsed_data['holes'][0]
    assert hole1['hole_num'] == 1
    assert hole1['par'] == 4
    assert len(hole1['shots']) == 3

    shot1_1 = hole1['shots'][0]
    assert shot1_1['club'] == 'D'
    assert shot1_1['feel'] == 'B'
    assert shot1_1['result'] == 'C'

    shot1_2 = hole1['shots'][1]
    assert shot1_2['club'] == 'I5'
    assert shot1_2['distance'] == 150
    assert shot1_2['penalty'] == 'H'

    shot1_3 = hole1['shots'][2]
    assert shot1_3['club'] == 'P'
    assert shot1_3['concede'] == True

    # Test Hole 2 (lowercase and incomplete spacing)
    hole2 = parsed_data['holes'][1]
    assert hole2['hole_num'] == 2
    assert hole2['par'] == 3
    assert len(hole2['shots']) == 2

    shot2_1 = hole2['shots'][0]
    assert shot2_1['club'] == 'I7'
    assert shot2_1['feel'] == 'A'
    assert shot2_1['result'] == 'A'

    shot2_2 = hole2['shots'][1]
    assert shot2_2['club'] == 'P'
    assert shot2_2['feel'] == 'B'
    assert shot2_2['result'] == 'B'
    assert shot2_2['distance'] == 5

@pytest.fixture
def sample_data_with_unparsed_lines_path():
    data_dir = 'tests/data'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    file_path = os.path.join(data_dir, 'test_unparsed.txt')
    with open(file_path, 'w') as f:
        f.write("2024.07.13 10:00\n") # Tee-off time
        f.write("Unparsed Test Course\n") # Golf Course
        f.write("Charlie, David\n") # Co-players
        f.write("1P4\n")
        f.write("D B C\n")
        f.write("This is an unparseable line\n")
        f.write("I5 A C 150 H\n")
        f.write("Another unparseable line\n")
        f.write("2P3\n")
        f.write("I7 A A\n")
    return file_path

def test_parse_file_unparsed_lines(sample_data_with_unparsed_lines_path):
    parsed_data, _ = parse_file(sample_data_with_unparsed_lines_path)

    assert parsed_data['file_name'] == sample_data_with_unparsed_lines_path
    assert parsed_data['tee_off_time'] == "2024-07-13 10:00"
    assert parsed_data['golf_course'] == "Unparsed Test Course"
    assert parsed_data['co_players'] == "Charlie, David"
    assert len(parsed_data['holes']) == 2
    assert parsed_data['unparsed_lines'] == [
        'This is an unparseable line',
        'Another unparseable line'
    ]

    # Verify that the parsed data is still correct despite unparsed lines
    hole1 = parsed_data['holes'][0]
    assert hole1['hole_num'] == 1
    assert hole1['par'] == 4
    assert len(hole1['shots']) == 2
    assert hole1['shots'][0]['club'] == 'D'
    assert hole1['shots'][1]['club'] == 'I5'

    hole2 = parsed_data['holes'][1]
    assert hole2['hole_num'] == 2
    assert hole2['par'] == 3
    assert len(hole2['shots']) == 1
    assert hole2['shots'][0]['club'] == 'I7'
