"""P0-1: Coordinate System Contract Tests.

Canonical coordinate system (MUST match geometry_builder.py):
    - First run travels along +X (east)
    - Wall is at Y=0, parallel to X axis
    - Cabinet depth extends into room: +Y direction
    - Z is up (floor at Z=0)
    - Cabinet front face is at Y=0
    - Cabinet back face is at Y=depth

These tests enforce the SINGLE SOURCE OF TRUTH for coordinates.
If geometry_builder changes its convention, these tests MUST be updated first.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.config_parser import load_config, mm_to_m, CABINET_LEVELS


# ─── Canonical coordinate constants ───────────────────────────────────────────
# These are the CONTRACT. Both tests AND implementation must agree.

FIRST_RUN_DIRECTION = "east"
WALL_AT_Y = 0.0
DEPTH_GOES_POSITIVE = True  # +Y is into the room
Z_UP_IS_POSITIVE = True     # +Z is up


# ─── Check if bpy is available ────────────────────────────────────────────────

try:
    import bpy
    HAS_BPY = True
except ImportError:
    HAS_BPY = False

requires_bpy = pytest.mark.skipif(not HAS_BPY, reason="bpy not available (requires Blender)")


# ─── Config parser: position calculation tests ────────────────────────────────

class TestPositionCalculationContract:
    """Verify that position calculations follow the canonical coordinate system."""

    def _make_simple_run(self, widths: list[int]) -> dict:
        """Helper: create a run with base-door cabinets of given widths."""
        return {
            "label": "test wall",
            "base": [{"type": "base-door", "width": w} for w in widths],
        }

    def _make_settings(self, cabinet_gap: int = 0, front_gap: int = 2) -> dict:
        """Helper: create minimal settings."""
        return {
            "baseBodyHeight": 720,
            "baseDepth": 560,
            "wallHeight": 600,
            "wallDepth": 300,
            "plinthHeight": 120,
            "cabinetGap": cabinet_gap,
            "frontGap": front_gap,
        }

    def test_single_cabinet_starts_at_origin(self):
        """First cabinet in a run must start at x=0."""
        from src.config_parser import calculate_run_positions

        run = self._make_simple_run([600])
        settings = self._make_settings()
        positions = calculate_run_positions(run, settings)

        assert len(positions) == 1
        assert positions[0]["x_mm"] == 0

    def test_two_cabinets_second_starts_at_width_plus_cabinet_gap(self):
        """Second cabinet position = first.width + cabinetGap."""
        from src.config_parser import calculate_run_positions

        run = self._make_simple_run([600, 400])
        settings = self._make_settings(cabinet_gap=2)
        positions = calculate_run_positions(run, settings)

        assert positions[0]["x_mm"] == 0
        assert positions[1]["x_mm"] == 602  # 600 + 2

    def test_three_cabinets_positions_are_cumulative(self):
        """Each cabinet offset by previous widths + cabinetGaps."""
        from src.config_parser import calculate_run_positions

        run = self._make_simple_run([500, 600, 400])
        settings = self._make_settings(cabinet_gap=3)
        positions = calculate_run_positions(run, settings)

        assert positions[0]["x_mm"] == 0
        assert positions[1]["x_mm"] == 503    # 500 + 3
        assert positions[2]["x_mm"] == 1106   # 500 + 3 + 600 + 3

    def test_zero_cabinet_gap_cabinets_are_flush(self):
        """With cabinetGap=0, cabinets are adjacent with no spacing."""
        from src.config_parser import calculate_run_positions

        run = self._make_simple_run([600, 600])
        settings = self._make_settings(cabinet_gap=0)
        positions = calculate_run_positions(run, settings)

        assert positions[0]["x_mm"] == 0
        assert positions[1]["x_mm"] == 600

    def test_upper_cabinets_same_x_positions_as_base(self):
        """Upper cabinets must align with base cabinets (same x positions)."""
        from src.config_parser import calculate_run_positions, calculate_upper_positions

        run = {
            "label": "test",
            "base": [
                {"type": "base-door", "width": 600},
                {"type": "base-door", "width": 800},
            ],
            "upper": [
                {"type": "wall-door", "width": 600},
                {"type": "wall-door", "width": 800},
            ],
        }
        settings = self._make_settings(cabinet_gap=0, front_gap=2)

        base_pos = calculate_run_positions(run, settings)
        upper_pos = calculate_upper_positions(run, settings)

        assert len(base_pos) == len(upper_pos)
        for b, u in zip(base_pos, upper_pos):
            assert b["x_mm"] == u["x_mm"], "Base and upper must have same x positions"


# ─── Geometry builder: coordinate system tests ────────────────────────────────
# These tests require bpy (Blender). They verify the actual mesh coordinates.

@requires_bpy
class TestGeometryCoordinateContract:
    """Verify that geometry_builder produces coordinates matching the contract."""

    @pytest.fixture(autouse=True)
    def clean_scene(self):
        """Clean Blender scene before each test."""
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        yield
        # Cleanup after test
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)

    def _build_single_cabinet(self, width=600, depth=560, height=720):
        """Create a single cabinet box for testing coordinates."""
        from src.geometry_builder import _create_box
        return _create_box("test_cab", mm_to_m(width), mm_to_m(depth), mm_to_m(height))

    def test_box_has_8_vertices(self):
        """A box must have exactly 8 vertices."""
        obj = self._build_single_cabinet()
        assert len(obj.data.vertices) == 8

    def test_box_has_6_faces(self):
        """A box must have exactly 6 faces (quads)."""
        obj = self._build_single_cabinet()
        assert len(obj.data.polygons) == 6

    def test_box_origin_at_front_left_bottom(self):
        """Origin must be at (0,0,0) = front-left-bottom corner."""
        obj = self._build_single_cabinet(width=600, depth=560, height=720)
        verts = [v.co[:] for v in obj.data.vertices]

        # Minimum coordinates must be at origin
        min_x = min(v[0] for v in verts)
        min_y = min(v[1] for v in verts)
        min_z = min(v[2] for v in verts)

        assert min_x == pytest.approx(0.0, abs=1e-6)
        assert min_y == pytest.approx(0.0, abs=1e-6)
        assert min_z == pytest.approx(0.0, abs=1e-6)

    def test_box_width_extends_along_positive_x(self):
        """Width must extend from x=0 to x=+width."""
        obj = self._build_single_cabinet(width=600)
        verts = [v.co[:] for v in obj.data.vertices]

        max_x = max(v[0] for v in verts)
        assert max_x == pytest.approx(mm_to_m(600), abs=1e-6)

    def test_box_depth_extends_along_positive_y(self):
        """Depth must extend from y=0 to y=+depth (INTO the room)."""
        obj = self._build_single_cabinet(depth=560)
        verts = [v.co[:] for v in obj.data.vertices]

        max_y = max(v[1] for v in verts)
        assert max_y == pytest.approx(mm_to_m(560), abs=1e-6)

    def test_box_height_extends_along_positive_z(self):
        """Height must extend from z=0 to z=+height (UPWARD)."""
        obj = self._build_single_cabinet(height=720)
        verts = [v.co[:] for v in obj.data.vertices]

        max_z = max(v[2] for v in verts)
        assert max_z == pytest.approx(mm_to_m(720), abs=1e-6)

    def test_front_face_at_y_equals_zero(self):
        """Front face vertices must all have y=0."""
        obj = self._build_single_cabinet()
        front_face = None
        for poly in obj.data.polygons:
            verts = [obj.data.vertices[vi].co for vi in poly.vertices]
            if all(abs(v.y) < 1e-6 for v in verts):
                front_face = poly
                break

        assert front_face is not None, "Must have a face at y=0 (front face)"

    def test_back_face_at_y_equals_depth(self):
        """Back face vertices must all have y=depth."""
        obj = self._build_single_cabinet(depth=560)
        expected_y = mm_to_m(560)
        back_face = None
        for poly in obj.data.polygons:
            verts = [obj.data.vertices[vi].co for vi in poly.vertices]
            if all(abs(v.y - expected_y) < 1e-6 for v in verts):
                back_face = poly
                break

        assert back_face is not None, "Must have a face at y=depth (back face)"


@requires_bpy
class TestFrontFaceConvention:
    """Verify front face convention is consistent across all cabinet types.

    The front face is the face that:
    - Is at y=0 in local space
    - Faces +Y direction (into the room)
    - Contains doors/drawer fronts
    """

    @pytest.fixture(autouse=True)
    def clean_scene(self):
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        yield

    def test_front_face_normal_points_outward(self):
        """Front face normal must point -Y (outward from box, toward viewer)."""
        from src.geometry_builder import _create_box

        obj = _create_box("test", 0.6, 0.56, 0.72)
        front_face = None
        for poly in obj.data.polygons:
            verts = [obj.data.vertices[vi].co for vi in poly.vertices]
            if all(abs(v.y) < 1e-6 for v in verts):
                front_face = poly
                break

        assert front_face is not None
        # Normal should point in -Y direction (outward from the box)
        normal = front_face.normal
        assert abs(normal.x) < 0.01, f"Front face normal.x should be ~0, got {normal.x}"
        assert abs(normal.z) < 0.01, f"Front face normal.z should be ~0, got {normal.z}"
        # Front face normal points outward (-Y)
        assert normal.y < 0, f"Front face normal.y should be negative (outward), got {normal.y}"

    def test_door_front_is_separate_object_at_y_zero(self):
        """Door front must be a child object positioned at y=0 (or slightly in front)."""
        from src.geometry_builder import _create_box, _add_door_front

        parent = _create_box("test_cab", 0.6, 0.56, 0.72)
        cab = {"type": "base-door", "door": "right"}
        settings = {"gap": 2}

        _add_door_front(parent, 0.6, 0.72, 0.018, cab, "base")

        # Find door child
        door_children = [c for c in parent.children if "_door" in c.name]
        assert len(door_children) == 1, f"Expected 1 door child, got {len(door_children)}"

        door = door_children[0]
        # Door should be at y <= 0 (in front of or at the cabinet face)
        assert door.location.y <= 0, f"Door y={door.location.y} should be <= 0"


# ─── Direction Rotation Tests ─────────────────────────────────────────────────

@requires_bpy
class TestDirectionRotations:
    """Verify that rotation_for_direction produces correct orientations."""

    @pytest.fixture(autouse=True)
    def clean_scene(self):
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        yield

    def _get_front_face_center(self, obj):
        """Get the center point of the face at y=0 (front face)."""
        import mathutils
        for poly in obj.data.polygons:
            verts = [obj.data.vertices[vi].co for vi in poly.vertices]
            if all(abs(v.y) < 1e-6 for v in verts):
                center = sum((v for v in verts), mathutils.Vector()) / len(verts)
                return center
        return None

    def _rotate_and_get_world_front(self, direction):
        """Create box, rotate for direction, return world-space front face center."""
        from src.geometry_builder import _create_box, _rotate_for_direction

        obj = _create_box("test", 0.6, 0.56, 0.72)
        _rotate_for_direction(obj, direction)

        # Get world matrix
        world_mat = obj.matrix_world

        # Find front face (y=0 in local space) and transform to world
        front_verts = []
        for poly in obj.data.polygons:
            verts = [obj.data.vertices[vi].co for vi in poly.vertices]
            if all(abs(v.y) < 1e-6 for v in verts):
                for v in verts:
                    front_verts.append(world_mat @ v)
                break

        if not front_verts:
            return None

        import mathutils
        return sum(front_verts, mathutils.Vector()) / len(front_verts)

    def test_east_direction_front_faces_positive_y(self):
        """East: front face should face +Y (into room, away from south wall)."""
        center = self._rotate_and_get_world_front("east")
        assert center is not None
        # For east direction, front face is at y=0 in world space
        assert abs(center.y) < 0.01, f"East front face y={center.y}, should be ~0"

    def test_south_direction_front_faces_negative_x(self):
        """South: front face should face -X (into room, away from east wall)."""
        center = self._rotate_and_get_world_front("south")
        assert center is not None
        # Front face should be at x=0 in world space
        assert abs(center.x) < 0.01, f"South front face x={center.x}, should be ~0"

    def test_west_direction_front_faces_negative_y(self):
        """West: front face should face -Y (into room, away from north wall)."""
        center = self._rotate_and_get_world_front("west")
        assert center is not None
        # Front face at y=0 in world space
        assert abs(center.y) < 0.01, f"West front face y={center.y}, should be ~0"

    def test_north_direction_front_faces_positive_x(self):
        """North: front face should face +X (into room, away from west wall)."""
        center = self._rotate_and_get_world_front("north")
        assert center is not None
        # Front face at x=0 in world space
        assert abs(center.x) < 0.01, f"North front face x={center.x}, should be ~0"
