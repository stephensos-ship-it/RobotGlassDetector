"""Geometry checks for worlds/hallway.sdf, the world for the stopping-distance trials."""

from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

WORLD = Path(__file__).resolve().parents[1] / 'worlds' / 'hallway.sdf'
CLEAR_WIDTH = 2.0
LENGTH = 12.0
BOX_SIZE = 0.4


def world():
    element = ET.parse(WORLD).getroot().find('world')
    assert element is not None, f'{WORLD} has no <world>'
    return element


def numbers(text):
    return [float(value) for value in (text or '').split()]


def box_models():
    """Map each box-shaped model's name to its (pose, size) as float lists."""
    models = {}
    for model in world().findall('model'):
        size = model.find('link/collision/geometry/box/size')
        if size is not None:
            models[model.get('name')] = (numbers(model.findtext('pose')), numbers(size.text))
    return models


def test_world_name_matches_the_gazebo_service_paths():
    # place_box and the trial runner call /world/hallway/set_pose.
    assert world().get('name') == 'hallway'


def test_hallway_is_2_m_wide_and_12_m_long():
    models = box_models()
    (left, left_size), (right, right_size) = models['left_wall'], models['right_wall']
    clear = (left[1] - left_size[1] / 2) - (right[1] + right_size[1] / 2)
    assert clear == pytest.approx(CLEAR_WIDTH)
    assert left[1] == pytest.approx(-right[1])
    for pose, size in [(left, left_size), (right, right_size)]:
        assert size[0] == pytest.approx(LENGTH)
        assert pose[0] - size[0] / 2 == pytest.approx(0.0)
        # Taller than TIAGo's head camera, so the parked box stays hidden.
        assert size[2] >= 2.0


def test_only_the_floor_walls_and_box_are_in_the_world():
    # Both ends stay open: anything else ahead of TIAGo would look like an obstacle.
    names = {model.get('name') for model in world().findall('model')}
    assert names == {'ground_plane', 'left_wall', 'right_wall', 'box'}
    assert world().findall('include') == []


def test_walls_and_box_stand_on_the_floor():
    for pose, size in box_models().values():
        assert pose[2] == pytest.approx(size[2] / 2)
        assert pose[3:] == pytest.approx([0.0, 0.0, 0.0])


def test_box_is_a_static_0_4_m_cube_parked_out_of_sight():
    models = box_models()
    pose, size = models['box']
    assert size == pytest.approx([BOX_SIZE] * 3)
    box = next(model for model in world().findall('model') if model.get('name') == 'box')
    assert box.findtext('static') == 'true'
    wall_pose, wall_size = models['right_wall']
    outer_face = abs(wall_pose[1]) + wall_size[1] / 2
    assert abs(pose[1]) - BOX_SIZE / 2 > outer_face
    assert 0.0 < pose[0] < LENGTH
