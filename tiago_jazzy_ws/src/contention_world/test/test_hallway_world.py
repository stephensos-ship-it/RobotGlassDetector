"""Geometry checks for worlds/hallway.sdf, the world for the stopping-distance trials."""

import importlib.machinery
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

PACKAGE = Path(__file__).resolve().parents[1]
WORLD = PACKAGE / 'worlds' / 'hallway.sdf'
CLEAR_WIDTH = 2.0
LENGTH = 12.0
BOX_SIZE = 0.4
# hallway number -> (wall on its right, wall on its left, its box)
HALLWAYS = {1: ('wall_right', 'wall_middle', 'box1'), 2: ('wall_middle', 'wall_left', 'box2')}


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


def centreline(hallway):
    right, left, _ = HALLWAYS[hallway]
    models = box_models()
    return (models[right][0][1] + models[left][0][1]) / 2


def load(path):
    """Import a Python file that may lack a .py suffix, such as scripts/place_box."""
    loader = importlib.machinery.SourceFileLoader(path.stem.replace('.', '_'), str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_world_name_matches_the_gazebo_service_paths():
    # place_box and the trial runner call /world/hallway/set_pose.
    assert world().get('name') == 'hallway'


@pytest.mark.parametrize('hallway', HALLWAYS)
def test_each_hallway_is_2_m_wide_and_12_m_long(hallway):
    right_name, left_name, _ = HALLWAYS[hallway]
    models = box_models()
    (right, right_size), (left, left_size) = models[right_name], models[left_name]
    clear = (left[1] - left_size[1] / 2) - (right[1] + right_size[1] / 2)
    assert clear == pytest.approx(CLEAR_WIDTH)
    for pose, size in [(left, left_size), (right, right_size)]:
        assert size[0] == pytest.approx(LENGTH)
        assert pose[0] - size[0] / 2 == pytest.approx(0.0)
        # Taller than TIAGo's head camera, so the parked boxes stay hidden.
        assert size[2] >= 2.0


def test_hallway_1_is_centred_on_y_0_where_the_one_robot_launch_spawns_tiago():
    assert centreline(1) == pytest.approx(0.0)


def test_place_box_and_the_two_robot_launch_use_the_world_centrelines():
    place_box = load(PACKAGE / 'scripts' / 'place_box')
    assert place_box.CENTRELINE_Y == pytest.approx({h: centreline(h) for h in HALLWAYS})
    launch = load(PACKAGE / 'launch' / 'two_tiagos.launch.py')
    assert [float(y) for _, y in launch.ROBOTS] == pytest.approx([centreline(1), centreline(2)])


def test_only_the_floor_walls_and_boxes_are_in_the_world():
    # The ends stay open: anything else ahead of a robot would look like an obstacle.
    names = {model.get('name') for model in world().findall('model')}
    assert names == {'ground_plane', 'wall_right', 'wall_middle', 'wall_left', 'box1', 'box2'}
    assert world().findall('include') == []


def test_walls_and_boxes_stand_on_the_floor():
    for pose, size in box_models().values():
        assert pose[2] == pytest.approx(size[2] / 2)
        assert pose[3:] == pytest.approx([0.0, 0.0, 0.0])


@pytest.mark.parametrize('hallway', HALLWAYS)
def test_each_box_is_a_static_0_4_m_cube_parked_behind_its_outer_wall(hallway):
    right_name, left_name, box_name = HALLWAYS[hallway]
    models = box_models()
    pose, size = models[box_name]
    assert size == pytest.approx([BOX_SIZE] * 3)
    box = next(model for model in world().findall('model') if model.get('name') == box_name)
    assert box.findtext('static') == 'true'
    # Hallway 1's outer wall is on its right (-y); hallway 2's is on its left (+y).
    outer_name, side = (right_name, -1) if hallway == 1 else (left_name, 1)
    wall_pose, wall_size = models[outer_name]
    outer_face = side * wall_pose[1] + wall_size[1] / 2
    assert side * pose[1] - BOX_SIZE / 2 > outer_face
    assert 0.0 < pose[0] < LENGTH
