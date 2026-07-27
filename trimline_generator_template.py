from __future__ import annotations

from math import ceil, cos, radians, sin, hypot
from pathlib import Path
from typing import Iterable

try:
    import ezdxf
except ImportError as exc:
    raise SystemExit(
        "\nezDxf is not installed.\n"
        "Install it once from Command Prompt with:\n\n"
        "    py -m pip install ezdxf\n\n"
        "Then run this file again.\n"
    ) from exc




# ============================================================
# TRIMLINE GUTTER — PARAMETRIC DXF GENERATOR
# Units: millimetres
#
# USER PARAMETERS
# Edit the values in this section only.
# F, BC, FG, the girth, the small end and the stop end are
# calculated automatically.
# ============================================================


# ------------------------------------------------------------
# A. MAIN PROFILE
#
# Follow the metal from the front hem to the rear return:
# A — B — C — D — E — F — G — H
#
# F is not entered manually. It is calculated from
# GUTTER_ARM_DEPTH.
# ------------------------------------------------------------

A = 10.0
B = 29.0
C = 96.0
D = 96.0
E = 189.0
G = 25.0
H = 10.0

# Gap between the parallel A and B hem lines.
# This gap is geometric only and is not included in the girth.
HEM_GAP_AB = 1.0

# Flat-pattern length.
GUTTER_LENGTH = 300.0


# ------------------------------------------------------------
# B. ROOF AND PROFILE GEOMETRY
#
# B and G are always parallel and are both controlled by
# ROOF_PITCH.
#
# GUTTER_ARM_DEPTH is measured perpendicular to G, from the
# F/G junction to the extension of B.
# ------------------------------------------------------------

ROOF_PITCH = 5.0
GUTTER_ARM_DEPTH = 35.482907044268764

# Independently adjustable included/profile angles.
ANGLE_CD = 160.0
ANGLE_DE = 100.0
ANGLE_EF = 90.0


# ------------------------------------------------------------
# C. SMALL / MALE END ADJUSTMENTS
#
# The final small-end H dimension is calculated automatically so
# that the small-end girth remains equal to the main girth.
# ------------------------------------------------------------

A_SMALL_EXTRA = 5.0
B_SMALL_REDUCTION = 2.0
C_SMALL_REDUCTION = 1.0
D_SMALL_REDUCTION = 1.0
E_SMALL_REDUCTION = 2.0
F_SMALL_REDUCTION = 2.0
G_SMALL_REDUCTION = 2.0


# ------------------------------------------------------------
# D. JOINT AND MACHINING
# ------------------------------------------------------------

OVERLAP = 50.0
WHEEL_FORM_FROM_RIGHT = 55.0

# A+B and G+H are set back at the large end by this amount.
LEFT_END_RELIEF = 55.0

# Retained as a geometric safety reference.
NOTCH_LENGTH = 55.0

HOLE_DIAMETER = 5.0
HOLE_X_FROM_LEFT = 25.0
HOLE_DISTANCE_FROM_FOLD = 17.0
MAX_HOLE_SPACING = 75.0

HOLED_FACES = {"C", "D", "E", "F"}
NOTCHED_FOLDS = [1, 2, 3, 4, 5, 6, 7]


# ------------------------------------------------------------
# E. STOP END
# ------------------------------------------------------------

STOP_END_LAP = 50.0

STOP_C_REDUCTION = 1.0
STOP_D_REDUCTION = 1.0
STOP_E_REDUCTION = 2.0
STOP_F_REDUCTION = 1.0

# The actual C/D cut angle is never allowed below the triangular
# tool angle.
STOP_CD_CUT_ANGLE = 44.0
STOP_CD_MIN_CUT_ANGLE = 30.0

# Clear edge-to-edge distance from the flat pattern to the stop end.
STOP_END_GAP_FROM_FLAT = 250.0


# ------------------------------------------------------------
# F. DRAWING LAYOUT
# ------------------------------------------------------------

SECTION_GAP_FROM_FLAT = 200.0

SECTION_DIM_OFFSET = 24.0
SECTION_SMALL_DIM_OFFSET = 16.0
SECTION_ANGLE_RADIUS = 34.0
GUTTER_ARM_DIM_OFFSET = 38.0

FLAT_CHAIN_DIM_OFFSET = 32.0
FLAT_OVERALL_DIM_OFFSET = 88.0
FLAT_LENGTH_DIM_OFFSET = 72.0
WHEEL_FORM_DIM_OFFSET = 36.0

STOP_END_DIM_OFFSET = 22.0
STOP_END_SMALL_DIM_OFFSET = 14.0
STOP_END_ANGLE_RADIUS = 36.0

DIM_TEXT_HEIGHT = 5.0
DIM_ARROW_SIZE = 3.0

GEOMETRY_COLOUR = 7
BLOCK_COLOUR = 1
DIMENSION_COLOUR = 13
TEXT_STYLE_NAME = "Arial"
TEXT_FONT_FILE = "arial.ttf"

OUTPUT_FILENAME = "trimline_parametric.dxf"


# ------------------------------------------------------------
# G. FIXED MACRO BLOCK NAMES
#
# Do not rename these. The punching-machine macro relies on the
# exact name "New Up Mark".
# ------------------------------------------------------------

UPMARK_GEOMETRY_BLOCK_NAME = "UP Mark"
UPMARK_BLOCK_NAME = "New Up Mark"
UPMARK_ROTATION = 180.0


# ============================================================
# INTERNALLY CALCULATED VALUES
# Do not edit this section.
# ============================================================

DIRECTION_C = ANGLE_DE - (180.0 - ANGLE_CD)
DIRECTION_B = ROOF_PITCH
DIRECTION_G = ROOF_PITCH + 180.0

ANGLE_BC = 180.0 - (DIRECTION_C - DIRECTION_B)
ANGLE_FG = DIRECTION_G - ANGLE_EF


# ============================================================
# BASIC GEOMETRY
# ============================================================

Point = tuple[float, float]


def vector_point(point: Point, length: float, angle_degrees: float) -> Point:
    angle = radians(angle_degrees)
    return (
        point[0] + length * cos(angle),
        point[1] + length * sin(angle),
    )


def midpoint(p1: Point, p2: Point) -> Point:
    return ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)


def unit_vector(p1: Point, p2: Point) -> Point:
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = hypot(dx, dy)
    if length == 0:
        raise ValueError("Zero-length vector.")
    return (dx / length, dy / length)


def translate_point(point: Point, dx: float, dy: float) -> Point:
    return point[0] + dx, point[1] + dy


def cumulative_from_top(
    segments: list[float],
    girth: float,
) -> list[float]:
    folds: list[float] = []
    used = 0.0

    for segment in segments[:-1]:
        used += segment
        folds.append(girth - used)

    return folds


def face_ranges_from_top(
    names: list[str],
    segments: list[float],
    girth: float,
) -> dict[str, tuple[float, float]]:
    result: dict[str, tuple[float, float]] = {}
    top_y = girth

    for name, width in zip(names, segments):
        bottom_y = top_y - width
        result[name] = (bottom_y, top_y)
        top_y = bottom_y

    return result


def distributed_hole_positions(
    bottom_y: float,
    top_y: float,
) -> list[float]:
    face_width = top_y - bottom_y
    usable = face_width - 2.0 * HOLE_DISTANCE_FROM_FOLD

    if usable < 0:
        return []

    if usable == 0:
        return [bottom_y + HOLE_DISTANCE_FROM_FOLD]

    intervals = max(1, ceil(usable / MAX_HOLE_SPACING))
    spacing = usable / intervals

    return [
        bottom_y + HOLE_DISTANCE_FROM_FOLD + index * spacing
        for index in range(intervals + 1)
    ]


def build_folded_section() -> tuple[
    list[list[Point]],
    dict[str, tuple[Point, Point]],
    dict[str, tuple[Point, Point, Point]],
]:
    """Returns the section lines, segment endpoints and angle points."""

    # D/E junction.
    p_de = (0.0, 0.0)

    # Front face.
    direction_d = ANGLE_DE
    p_cd = vector_point(p_de, D, direction_d)

    direction_c = DIRECTION_C
    p_bc = vector_point(p_cd, C, direction_c)

    direction_b = DIRECTION_B
    p_b_free = vector_point(p_bc, B, direction_b)

    # A parallel to B, separated by a 1 mm geometric gap.
    p_a_at_fold = vector_point(
        p_b_free,
        HEM_GAP_AB,
        direction_b - 90.0,
    )
    p_a_free = vector_point(
        p_a_at_fold,
        A,
        direction_b + 180.0,
    )

    front_chain = [
        p_a_free,
        p_a_at_fold,
        p_b_free,   # 1 mm closure; excluded from girth
        p_bc,
        p_cd,
        p_de,
    ]

    # Base and rear.
    p_ef = vector_point(p_de, E, 0.0)
    p_fg = vector_point(p_ef, F, ANGLE_EF)

    direction_g = DIRECTION_G
    p_gh = vector_point(p_fg, G, direction_g)

    # H always vertical down.
    p_h_free = vector_point(p_gh, H, -90.0)

    rear_chain = [
        p_de,
        p_ef,
        p_fg,
        p_gh,
        p_h_free,
    ]

    # Perpendicular projection from the F/G junction to the
    # extension of B. This is the true gutter-arm depth.
    b_unit = vector_from_angle(direction_b)

    fg_from_bc = (
        p_fg[0] - p_bc[0],
        p_fg[1] - p_bc[1],
    )

    along_b = (
        fg_from_bc[0] * b_unit[0]
        + fg_from_bc[1] * b_unit[1]
    )

    p_gutter_arm_on_b = (
        p_bc[0] + along_b * b_unit[0],
        p_bc[1] + along_b * b_unit[1],
    )

    gutter_arm_vector = (
        p_gutter_arm_on_b[0] - p_fg[0],
        p_gutter_arm_on_b[1] - p_fg[1],
    )

    measured_gutter_arm_depth = hypot(
        gutter_arm_vector[0],
        gutter_arm_vector[1],
    )

    if abs(
        gutter_arm_vector[0] * b_unit[0]
        + gutter_arm_vector[1] * b_unit[1]
    ) > 1e-7:
        raise ValueError(
            "The generated gutter-arm-depth line is not perpendicular to G."
        )

    if abs(measured_gutter_arm_depth - GUTTER_ARM_DEPTH) > 1e-7:
        raise ValueError(
            "The generated profile does not satisfy GUTTER_ARM_DEPTH."
        )

    segments = {
        "A": (p_a_free, p_a_at_fold),
        "B": (p_b_free, p_bc),
        "C": (p_bc, p_cd),
        "D": (p_cd, p_de),
        "E": (p_de, p_ef),
        "F": (p_ef, p_fg),
        "G": (p_fg, p_gh),
        "H": (p_gh, p_h_free),

        # Perpendicular construction dimension only:
        # not part of the material girth.
        "GUTTER_ARM_DEPTH": (p_fg, p_gutter_arm_on_b),
    }

    angular_junctions = {
        "BC": (p_bc, p_b_free, p_cd),
        "CD": (p_cd, p_bc, p_de),
        "DE": (p_de, p_cd, p_ef),
        "FG": (p_fg, p_ef, p_gh),
    }

    return (
        [front_chain, rear_chain],
        segments,
        angular_junctions,
    )


def angle_bisector_point(
    center: Point,
    p1: Point,
    p2: Point,
    radius: float,
) -> Point:
    u1 = unit_vector(center, p1)
    u2 = unit_vector(center, p2)

    bx = u1[0] + u2[0]
    by = u1[1] + u2[1]
    length = hypot(bx, by)

    if length < 1e-9:
        # Fallback for almost-opposite vectors.
        bx, by = -u1[1], u1[0]
        length = 1.0

    return (
        center[0] + radius * bx / length,
        center[1] + radius * by / length,
    )




def vector_from_angle(angle_degrees: float) -> Point:
    angle = radians(angle_degrees)
    return cos(angle), sin(angle)


def add_scaled_vector(point: Point, vector: Point, scale: float) -> Point:
    return (
        point[0] + vector[0] * scale,
        point[1] + vector[1] * scale,
    )


def cross_2d(v1: Point, v2: Point) -> float:
    return v1[0] * v2[1] - v1[1] * v2[0]


def rotate_vector(vector: Point, angle_degrees: float) -> Point:
    angle = radians(angle_degrees)
    return (
        vector[0] * cos(angle) - vector[1] * sin(angle),
        vector[0] * sin(angle) + vector[1] * cos(angle),
    )


def right_normal(p1: Point, p2: Point) -> Point:
    ux, uy = unit_vector(p1, p2)
    return uy, -ux


def line_intersection(
    p1: Point,
    direction_1: Point,
    p2: Point,
    direction_2: Point,
) -> tuple[Point, float, float]:
    """Intersection of two infinite parametric lines."""
    denominator = cross_2d(direction_1, direction_2)
    if abs(denominator) < 1e-9:
        raise ValueError("The construction lines are parallel.")

    delta = p2[0] - p1[0], p2[1] - p1[1]
    t = cross_2d(delta, direction_2) / denominator
    u = cross_2d(delta, direction_1) / denominator
    return add_scaled_vector(p1, direction_1, t), t, u


def calculate_f_from_gutter_arm_depth() -> tuple[float, Point, float]:
    """
    Calculates F so that the perpendicular distance between the
    line of G and the extension of B equals GUTTER_ARM_DEPTH.

    B and G are parallel. The signed normal distance from any
    point on G to the B line is therefore constant.

    Construction:
      1. Build the fixed B line from C/D and ROOF_PITCH.
      2. Build the start point of F at E/F.
      3. Move F/G along the F direction by an unknown distance F.
      4. Solve F from the projection onto the normal to B/G.
      5. Project F/G perpendicularly onto the B extension.

    Returns:
      • calculated F,
      • perpendicular projection point on the B extension,
      • verified perpendicular distance.
    """

    if GUTTER_ARM_DEPTH <= 0:
        raise ValueError("GUTTER_ARM_DEPTH must be greater than zero.")

    p_de = (0.0, 0.0)
    p_cd = vector_point(p_de, D, ANGLE_DE)
    p_bc = vector_point(p_cd, C, DIRECTION_C)
    p_ef = vector_point(p_de, E, 0.0)

    b_unit = vector_from_angle(DIRECTION_B)
    f_unit = vector_from_angle(ANGLE_EF)

    # Clockwise unit normal to B. For the standard Trimline
    # orientation, the G line lies on the positive side.
    normal_to_g = (b_unit[1], -b_unit[0])

    base_vector = (
        p_ef[0] - p_bc[0],
        p_ef[1] - p_bc[1],
    )

    base_signed_distance = (
        base_vector[0] * normal_to_g[0]
        + base_vector[1] * normal_to_g[1]
    )

    f_normal_component = (
        f_unit[0] * normal_to_g[0]
        + f_unit[1] * normal_to_g[1]
    )

    if abs(f_normal_component) < 1e-9:
        raise ValueError(
            "Changing F cannot alter GUTTER_ARM_DEPTH because F is "
            "parallel to the B/G lines. Review ANGLE_EF."
        )

    calculated_f = (
        GUTTER_ARM_DEPTH - base_signed_distance
    ) / f_normal_component

    if calculated_f <= 0:
        raise ValueError(
            "The requested GUTTER_ARM_DEPTH produces a zero or "
            "negative F dimension. Review the profile parameters."
        )

    p_fg = vector_point(p_ef, calculated_f, ANGLE_EF)

    # Orthogonal projection of F/G onto the infinite B line.
    fg_from_bc = (
        p_fg[0] - p_bc[0],
        p_fg[1] - p_bc[1],
    )

    along_b = (
        fg_from_bc[0] * b_unit[0]
        + fg_from_bc[1] * b_unit[1]
    )

    point_on_b = (
        p_bc[0] + along_b * b_unit[0],
        p_bc[1] + along_b * b_unit[1],
    )

    perpendicular_vector = (
        point_on_b[0] - p_fg[0],
        point_on_b[1] - p_fg[1],
    )

    verified_distance = hypot(
        perpendicular_vector[0],
        perpendicular_vector[1],
    )

    perpendicular_check = abs(
        perpendicular_vector[0] * b_unit[0]
        + perpendicular_vector[1] * b_unit[1]
    )

    if perpendicular_check > 1e-7:
        raise ValueError(
            "Internal error: gutter-arm-depth construction is not "
            "perpendicular to G."
        )

    if abs(verified_distance - GUTTER_ARM_DEPTH) > 1e-7:
        raise ValueError(
            "Internal error: calculated profile does not satisfy "
            "GUTTER_ARM_DEPTH."
        )

    return calculated_f, point_on_b, verified_distance


# F is a derived global dimension used by the section, flat
# pattern, small end, holes and stop end.
(
    F,
    PROFILE_GUTTER_ARM_POINT_ON_B,
    CALCULATED_GUTTER_ARM_DEPTH,
) = calculate_f_from_gutter_arm_depth()


def build_stop_end() -> dict[str, object]:
    """Builds the one-handed stop end from the gutter parameters."""
    stop_c = C - STOP_C_REDUCTION
    stop_d = D - STOP_D_REDUCTION
    stop_e = E - STOP_E_REDUCTION
    stop_f = F - STOP_F_REDUCTION

    if min(stop_c, stop_d, stop_e, stop_f) <= 0:
        raise ValueError(
            "Stop-end reductions produce a zero or negative dimension."
        )

    cut_angle = max(STOP_CD_CUT_ANGLE, STOP_CD_MIN_CUT_ANGLE)
    if cut_angle >= 170.0:
        raise ValueError("STOP_CD_CUT_ANGLE must be below 170 degrees.")

    direction_d = ANGLE_DE
    direction_c = DIRECTION_C
    direction_b = DIRECTION_B
    direction_f = ANGLE_EF

    p_de = (0.0, 0.0)
    p_cd = vector_point(p_de, stop_d, direction_d)
    p_bc = vector_point(p_cd, stop_c, direction_c)
    p_ef = vector_point(p_de, stop_e, 0.0)
    p_f_end = vector_point(p_ef, stop_f, direction_f)

    # The approximately 188 mm line in the example is not entered
    # independently: it is B continued at the same angle.
    p_top, b_extension_length, f_total_height = line_intersection(
        p_bc,
        vector_from_angle(direction_b),
        p_ef,
        vector_from_angle(direction_f),
    )
    f_extension_length = f_total_height - stop_f

    if b_extension_length <= 0:
        raise ValueError("The B continuation points away from F.")
    if f_extension_length <= 0:
        raise ValueError(
            "F reaches above the B continuation; review stop-end dimensions."
        )

    central_segments = {
        "C": (p_bc, p_cd),
        "D": (p_cd, p_de),
        "E": (p_de, p_ef),
        "F": (p_ef, p_f_end),
        "B_EXT": (p_bc, p_top),
        "F_EXT": (p_f_end, p_top),
    }

    normal_c = right_normal(p_bc, p_cd)
    normal_d = right_normal(p_cd, p_de)
    normal_e = right_normal(p_de, p_ef)
    normal_f = right_normal(p_ef, p_f_end)

    c_outer_top = add_scaled_vector(p_bc, normal_c, STOP_END_LAP)
    d_outer_bottom = add_scaled_vector(p_de, normal_d, STOP_END_LAP)
    e_outer_start = add_scaled_vector(p_de, normal_e, STOP_END_LAP)
    e_outer_end = add_scaled_vector(p_ef, normal_e, STOP_END_LAP)
    f_outer_start = add_scaled_vector(p_ef, normal_f, STOP_END_LAP)
    f_outer_end = add_scaled_vector(p_f_end, normal_f, STOP_END_LAP)

    # Symmetrical triangular relief around the outward C/D bisector.
    bisector_raw = (
        normal_c[0] + normal_d[0],
        normal_c[1] + normal_d[1],
    )
    bisector_length = hypot(bisector_raw[0], bisector_raw[1])
    if bisector_length < 1e-9:
        raise ValueError("Cannot calculate the C/D cut bisector.")

    outward_bisector = (
        bisector_raw[0] / bisector_length,
        bisector_raw[1] / bisector_length,
    )
    c_cut_direction = rotate_vector(outward_bisector, -cut_angle / 2.0)
    d_cut_direction = rotate_vector(outward_bisector, cut_angle / 2.0)

    c_cut_point, c_ray_length, _ = line_intersection(
        p_cd,
        c_cut_direction,
        c_outer_top,
        unit_vector(p_bc, p_cd),
    )
    d_cut_point, d_ray_length, _ = line_intersection(
        p_cd,
        d_cut_direction,
        d_outer_bottom,
        unit_vector(p_cd, p_de),
    )
    if c_ray_length <= 0 or d_ray_length <= 0:
        raise ValueError(
            "The selected C/D cut angle does not meet the 50 mm laps."
        )

    # White continuous cutting outline.
    cut_lines = [
        # Upper and rear closure edges have no laps.
        central_segments["B_EXT"],
        central_segments["F_EXT"],

        # C lap cutting edges.
        (p_bc, c_outer_top),
        (c_outer_top, c_cut_point),
        (c_cut_point, p_cd),

        # D lap cutting edges.
        (p_cd, d_cut_point),
        (d_cut_point, d_outer_bottom),
        (d_outer_bottom, p_de),

        # E lap cutting edges.
        (p_de, e_outer_start),
        (e_outer_start, e_outer_end),
        (e_outer_end, p_ef),

        # F lap cutting edges. The lap stops at the end of F.
        (p_ef, f_outer_start),
        (f_outer_start, f_outer_end),
        (f_outer_end, p_f_end),
    ]

    # Indicative fold lines inside the stop end.
    # These are drawn in colour 13 with a dotted line type.
    indicative_lines = [
        central_segments["C"],
        central_segments["D"],
        central_segments["E"],
        central_segments["F"],
    ]

    lap_dimensions = {
        "C_LAP": (p_bc, c_outer_top),
        "D_LAP": (p_de, d_outer_bottom),
        "E_LAP": (p_de, e_outer_start),
        "F_LAP": (p_ef, f_outer_start),
    }

    all_points = [
        point
        for line in cut_lines + indicative_lines
        for point in line
    ]

    return {
        "cut_lines": cut_lines,
        "indicative_lines": indicative_lines,
        "central_segments": central_segments,
        "lap_dimensions": lap_dimensions,
        "cut_angle_points": (p_cd, c_cut_point, d_cut_point),
        "all_points": all_points,
        "cut_angle": cut_angle,
        "dimensions": {
            "C": stop_c,
            "D": stop_d,
            "E": stop_e,
            "F": stop_f,
            "B_EXT": b_extension_length,
            "F_EXT": f_extension_length,
        },
    }

# ============================================================
# PARAMETRIC DIMENSION SETS
# ============================================================

FACE_NAMES = ["A", "B", "C", "D", "E", "F", "G", "H"]
BIG = [A, B, C, D, E, F, G, H]
GIRTH = sum(BIG)

A1 = A + A_SMALL_EXTRA
B1 = B - B_SMALL_REDUCTION
C1 = C - C_SMALL_REDUCTION
D1 = D - D_SMALL_REDUCTION
E1 = E - E_SMALL_REDUCTION
F1 = F - F_SMALL_REDUCTION
G1 = G - G_SMALL_REDUCTION

small_first_seven = [A1, B1, C1, D1, E1, F1, G1]
H1 = GIRTH - sum(small_first_seven)

SMALL = small_first_seven + [H1]
SMALL_NAMES = ["A1", "B1", "C1", "D1", "E1", "F1", "G1", "H1"]


# ============================================================
# VALIDATION
# ============================================================

if any(value <= 0 for value in BIG):
    raise ValueError("All A–H dimensions must be greater than zero.")

if F <= 0:
    raise ValueError("The calculated F dimension must be greater than zero.")

if abs(
    CALCULATED_GUTTER_ARM_DEPTH - GUTTER_ARM_DEPTH
) > 1e-7:
    raise ValueError(
        "Calculated F does not satisfy the perpendicular "
        "GUTTER_ARM_DEPTH."
    )

if not -45.0 < ROOF_PITCH < 45.0:
    raise ValueError(
        "ROOF_PITCH must be between -45 and +45 degrees."
    )

if not 0.0 < ANGLE_BC < 180.0:
    raise ValueError(
        "The calculated ANGLE_BC is outside the valid 0–180° range. "
        "Review ROOF_PITCH, ANGLE_CD and ANGLE_DE."
    )

if not 0.0 < ANGLE_FG < 180.0:
    raise ValueError(
        "The calculated ANGLE_FG is outside the valid 0–180° range. "
        "Review ROOF_PITCH and ANGLE_EF."
    )

if abs((DIRECTION_G - DIRECTION_B) - 180.0) > 1e-9:
    raise ValueError("B and G are not parallel.")

if any(value <= 0 for value in SMALL):
    raise ValueError(
        "The derived small-end dimensions are invalid. "
        "Adjust the small-end reductions."
    )

if abs(sum(SMALL) - GIRTH) > 1e-9:
    raise ValueError("Small and large girths do not match.")

if GUTTER_LENGTH <= WHEEL_FORM_FROM_RIGHT:
    raise ValueError(
        "GUTTER_LENGTH must exceed WHEEL_FORM_FROM_RIGHT."
    )

if LEFT_END_RELIEF <= 0:
    raise ValueError("LEFT_END_RELIEF must be greater than zero.")

if LEFT_END_RELIEF + NOTCH_LENGTH >= GUTTER_LENGTH:
    raise ValueError(
        "The left relief plus notch length must be smaller "
        "than GUTTER_LENGTH."
    )


if STOP_END_LAP <= 0:
    raise ValueError("STOP_END_LAP must be greater than zero.")

if STOP_END_GAP_FROM_FLAT < 0:
    raise ValueError("STOP_END_GAP_FROM_FLAT cannot be negative.")

if STOP_CD_MIN_CUT_ANGLE < 30.0:
    raise ValueError(
        "STOP_CD_MIN_CUT_ANGLE cannot be below the 30-degree tool angle."
    )

# ============================================================
# DXF DOCUMENT AND LAYERS
# ============================================================

doc = ezdxf.new("R2010", setup=True)
doc.header["$INSUNITS"] = 4  # millimetres
msp = doc.modelspace()


# ============================================================
# CREATE THE ORIGINAL UP MARK BLOCKS DIRECTLY
#
# Exact hierarchy from the supplied upmark.dxf:
#
#   "New Up Mark"
#       └── INSERT of "UP Mark"
#
# The punching-machine macro sees model-space INSERT entities
# whose exact name is "New Up Mark". No external DXF is needed.
# ============================================================

if "TEXT" not in doc.layers:
    doc.layers.add("TEXT", color=GEOMETRY_COLOUR)

# Exact coordinates from the original supplied block.
UPMARK_NESTED_DX = 0.0015152379346546
UPMARK_NESTED_DY = 0.0388965550155263

UPMARK_TOP_Y = 0.9611034449844737
UPMARK_BOTTOM_Y = -1.038896555015526
UPMARK_CENTRE_Y = -0.0388965550155263

UPMARK_BODY_LEFT_X = 1.498484762065345
UPMARK_BODY_RIGHT_X = 23.49848476206535
UPMARK_LEFT_POINT_X = 0.4984847620653455
UPMARK_RIGHT_POINT_X = 24.49848476206535
UPMARK_REFERENCE_X = -0.0015152379346546


# Source geometry block: exact original name "UP Mark".
up_mark_geometry = doc.blocks.new(
    name=UPMARK_GEOMETRY_BLOCK_NAME,
    base_point=(0.0, 0.0, 0.0),
)

# Original entity 1: upper LWPOLYLINE.
up_mark_geometry.add_lwpolyline(
    [
        (UPMARK_BODY_RIGHT_X, UPMARK_TOP_Y),
        (UPMARK_BODY_LEFT_X, UPMARK_TOP_Y),
    ],
    format="xy",
    dxfattribs={
        "layer": "TEXT",
        "color": BLOCK_COLOUR,
        "const_width": 0.0,
    },
)

# Original entity 2: lower LWPOLYLINE.
up_mark_geometry.add_lwpolyline(
    [
        (UPMARK_BODY_LEFT_X, UPMARK_BOTTOM_Y),
        (UPMARK_BODY_RIGHT_X, UPMARK_BOTTOM_Y),
    ],
    format="xy",
    dxfattribs={
        "layer": "TEXT",
        "color": BLOCK_COLOUR,
        "const_width": 0.0,
    },
)

# Original entities 3–6: four LINE entities forming the ends.
up_mark_geometry.add_line(
    (UPMARK_BODY_LEFT_X, UPMARK_TOP_Y),
    (UPMARK_LEFT_POINT_X, UPMARK_CENTRE_Y),
    dxfattribs={"layer": "TEXT", "color": BLOCK_COLOUR},
)
up_mark_geometry.add_line(
    (UPMARK_LEFT_POINT_X, UPMARK_CENTRE_Y),
    (UPMARK_BODY_LEFT_X, UPMARK_BOTTOM_Y),
    dxfattribs={"layer": "TEXT", "color": BLOCK_COLOUR},
)
up_mark_geometry.add_line(
    (UPMARK_BODY_RIGHT_X, UPMARK_TOP_Y),
    (UPMARK_RIGHT_POINT_X, UPMARK_CENTRE_Y),
    dxfattribs={"layer": "TEXT", "color": BLOCK_COLOUR},
)
up_mark_geometry.add_line(
    (UPMARK_RIGHT_POINT_X, UPMARK_CENTRE_Y),
    (UPMARK_BODY_RIGHT_X, UPMARK_BOTTOM_Y),
    dxfattribs={"layer": "TEXT", "color": BLOCK_COLOUR},
)

# Original entity 7: reference POINT.
up_mark_geometry.add_point(
    (UPMARK_REFERENCE_X, UPMARK_CENTRE_Y),
    dxfattribs={"layer": "TEXT", "color": BLOCK_COLOUR},
)


# Macro-facing wrapper block: exact original name "New Up Mark".
new_up_mark = doc.blocks.new(
    name=UPMARK_BLOCK_NAME,
    base_point=(0.0, 0.0, 0.0),
)

# Exact nested insertion and offset from the original DXF.
new_up_mark.add_blockref(
    UPMARK_GEOMETRY_BLOCK_NAME,
    (UPMARK_NESTED_DX, UPMARK_NESTED_DY, 0.0),
    dxfattribs={
        "layer": "0",
        "color": BLOCK_COLOUR,
    },
)


# Define the dotted line type explicitly.
# ezdxf setup=True includes DOT, but it does not include a line type
# named DOTTED. Referencing an undefined line type causes AutoCAD to
# report DXF errors and pause with "Press ENTER to continue".
if "DOTTED" not in doc.linetypes:
    doc.linetypes.add(
        name="DOTTED",
        pattern=[2.0, 0.0, -2.0],
        description="Dotted . . . . . . . . . . . .",
    )

layers = [
    ("TEXT", GEOMETRY_COLOUR),
    ("CUT", GEOMETRY_COLOUR),
    ("NOTCH", GEOMETRY_COLOUR),
    ("FOLD_MARK", GEOMETRY_COLOUR),
    ("WHEEL_FORM", GEOMETRY_COLOUR),
    ("HOLES", GEOMETRY_COLOUR),
    ("SECTION", GEOMETRY_COLOUR),
    ("STOP_END", GEOMETRY_COLOUR),
    ("STOP_END_INDICATIVE", DIMENSION_COLOUR),
    ("DIMENSIONS", DIMENSION_COLOUR),
]

for name, colour in layers:
    if name not in doc.layers:
        doc.layers.add(name, color=colour)

# Internal stop-end fold lines: colour 13 and dotted.
indicative_layer = doc.layers.get("STOP_END_INDICATIVE")
indicative_layer.dxf.color = DIMENSION_COLOUR
indicative_layer.dxf.linetype = "DOTTED"

doc.header["$LTSCALE"] = 1.0


# Arial text style used by every dimension.
if TEXT_STYLE_NAME not in doc.styles:
    dimension_text_style = doc.styles.new(
        TEXT_STYLE_NAME,
        dxfattribs={"font": TEXT_FONT_FILE},
    )
else:
    dimension_text_style = doc.styles.get(TEXT_STYLE_NAME)

doc.header["$TEXTSTYLE"] = TEXT_STYLE_NAME


def create_dimension_style(
    name: str,
    *,
    angular: bool = False,
) -> None:
    attributes = {
        "dimtxt": DIM_TEXT_HEIGHT,
        "dimasz": DIM_ARROW_SIZE,
        "dimexe": 3.0,
        "dimexo": 1.5,
        "dimgap": 2.0,
        "dimtad": 1,
        "dimclrd": DIMENSION_COLOUR,
        "dimclre": DIMENSION_COLOUR,
        "dimclrt": DIMENSION_COLOUR,
        "dimtxsty": TEXT_STYLE_NAME,
    }

    if angular:
        attributes.update({
            "dimadec": 1,
            "dimazin": 2,
        })
    else:
        attributes.update({
            "dimdec": 2,
            "dimzin": 8,
        })

    if name not in doc.dimstyles:
        doc.dimstyles.new(name, dxfattribs=attributes)


create_dimension_style("TRIMLINE_LINEAR")
create_dimension_style("TRIMLINE_ANGULAR", angular=True)
create_dimension_style("TRIMLINE_DIAMETER")


# ============================================================
# DXF HELPERS
# ============================================================

def add_line(p1: Point, p2: Point, layer: str) -> None:
    msp.add_line(p1, p2, dxfattribs={"layer": layer})


def add_chain(points: Iterable[Point], layer: str) -> None:
    point_list = list(points)
    for p1, p2 in zip(point_list, point_list[1:]):
        add_line(p1, p2, layer)


def add_aligned_dimension(
    p1: Point,
    p2: Point,
    distance: float,
    text: str = "<>",
) -> None:
    """Add a dimension showing the measured numerical value only."""
    dimension = msp.add_aligned_dim(
        p1=p1,
        p2=p2,
        distance=distance,
        text="<>",
        dimstyle="TRIMLINE_LINEAR",
        dxfattribs={
            "layer": "DIMENSIONS",
            "color": DIMENSION_COLOUR,
        },
    )
    dimension.render()


def add_angular_dimension(
    label: str,
    center: Point,
    p1: Point,
    p2: Point,
    radius: float,
) -> None:
    """Add an angular dimension showing the numerical value only."""
    base = angle_bisector_point(center, p1, p2, radius)

    dimension = msp.add_angular_dim_3p(
        base=base,
        center=center,
        p1=p2,
        p2=p1,
        text="<>",
        dimstyle="TRIMLINE_ANGULAR",
        dxfattribs={
            "layer": "DIMENSIONS",
            "color": DIMENSION_COLOUR,
        },
    )
    dimension.render()




def add_outward_aligned_dimension(
    p1: Point,
    p2: Point,
    centroid: Point,
    distance: float,
    text: str,
) -> None:
    ux, uy = unit_vector(p1, p2)
    left_normal = (-uy, ux)
    segment_mid = midpoint(p1, p2)
    outward_test = (
        (segment_mid[0] - centroid[0]) * left_normal[0]
        + (segment_mid[1] - centroid[1]) * left_normal[1]
    )
    signed_distance = distance if outward_test >= 0 else -distance
    add_aligned_dimension(p1, p2, signed_distance, text)

# ============================================================
# 1. FLAT PATTERN
#
# The original Trimline detail is not a plain rectangle at the
# large/left-hand end:
#
#   • A+B are set back LEFT_END_RELIEF at the top.
#   • G+H are set back LEFT_END_RELIEF at the bottom.
#   • C+D+E+F continue to x = 0.
#
# The girth remains A+B+C+D+E+F+G+H; the 55 mm relief is in the
# gutter-length direction and therefore does not affect girth.
# ============================================================

top_relief_depth = A + B
bottom_relief_depth = G + H

flat_outline = [
    (LEFT_END_RELIEF, 0.0),
    (GUTTER_LENGTH, 0.0),
    (GUTTER_LENGTH, GIRTH),
    (LEFT_END_RELIEF, GIRTH),
    (LEFT_END_RELIEF, GIRTH - top_relief_depth),
    (0.0, GIRTH - top_relief_depth),
    (0.0, bottom_relief_depth),
    (LEFT_END_RELIEF, bottom_relief_depth),
    (LEFT_END_RELIEF, 0.0),
]
add_chain(flat_outline, "CUT")


# Large-end fold marks.
#
# Fold numbering from the top:
#   1 = A/B
#   2 = B/C
#   3 = C/D
#   4 = D/E
#   5 = E/F
#   6 = F/G
#   7 = G/H
#
# A/B, B/C, F/G and G/H are attached to the relieved local
# edge x=55. C/D, D/E and E/F are attached to x=0.
big_folds = cumulative_from_top(BIG, GIRTH)

relieved_fold_numbers = {1, 2, 6, 7}

for fold_number in NOTCHED_FOLDS:
    y = big_folds[fold_number - 1]

    # The local left edge depends on the 55 mm stepped relief:
    #   A/B, B/C, F/G and G/H use x = LEFT_END_RELIEF.
    #   C/D, D/E and E/F use x = 0.
    local_left_edge = (
        LEFT_END_RELIEF
        if fold_number in relieved_fold_numbers
        else 0.0
    )

    # No separate red 55 mm line is drawn.
    # The UP MARK block is attached directly to the relevant
    # left-hand edge and points rightwards into the sheet.
    msp.add_blockref(
        UPMARK_BLOCK_NAME,
        (local_left_edge, y),
        dxfattribs={
            "layer": "FOLD_MARK",
            "color": BLOCK_COLOUR,
            "rotation": 0.0,
        },
    )


# Right-hand / small-end fold marks.
#
# The supplied New Up Mark block is inserted on the right-hand edge
# and rotated 180°, so the symbol extends left into the sheet.
small_folds = cumulative_from_top(SMALL, GIRTH)

for y in small_folds:
    msp.add_blockref(
        UPMARK_BLOCK_NAME,
        (GUTTER_LENGTH, y),
        dxfattribs={
            "layer": "FOLD_MARK",
            "color": BLOCK_COLOUR,
            "rotation": UPMARK_ROTATION,
        },
    )


# Wheel-form line.
wheel_x = GUTTER_LENGTH - WHEEL_FORM_FROM_RIGHT
add_line((wheel_x, 0.0), (wheel_x, GIRTH), "WHEEL_FORM")


# Holes.
big_face_ranges = face_ranges_from_top(FACE_NAMES, BIG, GIRTH)
hole_centres: list[Point] = []

for face_name in FACE_NAMES:
    if face_name not in HOLED_FACES:
        continue

    bottom_y, top_y = big_face_ranges[face_name]

    for y in distributed_hole_positions(bottom_y, top_y):
        centre = (HOLE_X_FROM_LEFT, y)
        hole_centres.append(centre)

        msp.add_circle(
            centre,
            radius=HOLE_DIAMETER / 2.0,
            dxfattribs={"layer": "HOLES"},
        )


# ============================================================
# 2. FLAT-PATTERN DIMENSIONS
# ============================================================

# Large A–H chain on the left.
# A, B, G and H use the relieved local edge at x=55.
# C, D, E and F use the main local edge at x=0.
large_ranges = face_ranges_from_top(FACE_NAMES, BIG, GIRTH)

for name in FACE_NAMES:
    bottom_y, top_y = large_ranges[name]
    local_dimension_edge = (
        LEFT_END_RELIEF
        if name in {"A", "B", "G", "H"}
        else 0.0
    )

    add_aligned_dimension(
        (local_dimension_edge, top_y),
        (local_dimension_edge, bottom_y),
        -FLAT_CHAIN_DIM_OFFSET - local_dimension_edge,
        f"{name} <>",
    )


# Small A1–H1 chain on the right.
small_ranges = face_ranges_from_top(SMALL_NAMES, SMALL, GIRTH)

for name in SMALL_NAMES:
    bottom_y, top_y = small_ranges[name]
    add_aligned_dimension(
        (GUTTER_LENGTH, top_y),
        (GUTTER_LENGTH, bottom_y),
        FLAT_CHAIN_DIM_OFFSET,
        f"{name} <>",
    )


# 55 mm left-end relief dimensions for A+B and G+H.
add_aligned_dimension(
    (0.0, GIRTH - top_relief_depth),
    (LEFT_END_RELIEF, GIRTH - top_relief_depth),
    18.0,
    "<>",
)

add_aligned_dimension(
    (0.0, bottom_relief_depth),
    (LEFT_END_RELIEF, bottom_relief_depth),
    -18.0,
    "<>",
)


# Overall girth.
add_aligned_dimension(
    (0.0, GIRTH),
    (0.0, 0.0),
    -FLAT_OVERALL_DIM_OFFSET,
    "<>",
)


# Overall gutter length.
add_aligned_dimension(
    (0.0, 0.0),
    (GUTTER_LENGTH, 0.0),
    -FLAT_LENGTH_DIM_OFFSET,
    "<>",
)


# Wheel-form distance from the right-hand end.
add_aligned_dimension(
    (wheel_x, 0.0),
    (GUTTER_LENGTH, 0.0),
    -WHEEL_FORM_DIM_OFFSET,
    "<>",
)


# Hole offset from the left-hand end.
if hole_centres:
    sample_hole = hole_centres[len(hole_centres) // 2]

    add_aligned_dimension(
        (0.0, sample_hole[1]),
        sample_hole,
        18.0,
        "<>",
    )

    diameter_dim = msp.add_diameter_dim(
        center=sample_hole,
        radius=HOLE_DIAMETER / 2.0,
        angle=35.0,
        text="<>",
        dimstyle="TRIMLINE_DIAMETER",
        dxfattribs={
            "layer": "DIMENSIONS",
            "color": DIMENSION_COLOUR,
        },
    )
    diameter_dim.render()




# ============================================================
# 3. FOLDED SECTION
# ============================================================

(
    section_chains,
    section_segments,
    angular_junctions,
) = build_folded_section()

all_section_points = [
    point
    for chain in section_chains
    for point in chain
]

max_section_x = max(point[0] for point in all_section_points)
min_section_y = min(point[1] for point in all_section_points)
max_section_y = max(point[1] for point in all_section_points)

section_dx = -SECTION_GAP_FROM_FLAT - max_section_x
section_dy = GIRTH / 2.0 - (min_section_y + max_section_y) / 2.0


def position_section_point(point: Point) -> Point:
    return translate_point(point, section_dx, section_dy)


for chain in section_chains:
    add_chain(
        [position_section_point(point) for point in chain],
        "SECTION",
    )


positioned_segments = {
    name: (
        position_section_point(points[0]),
        position_section_point(points[1]),
    )
    for name, points in section_segments.items()
}

positioned_angles = {
    name: (
        position_section_point(points[0]),
        position_section_point(points[1]),
        position_section_point(points[2]),
    )
    for name, points in angular_junctions.items()
}

positioned_section_points = [
    position_section_point(point)
    for point in all_section_points
]

section_centroid = (
    sum(point[0] for point in positioned_section_points)
    / len(positioned_section_points),
    sum(point[1] for point in positioned_section_points)
    / len(positioned_section_points),
)


# A–H aligned section dimensions.
for name in FACE_NAMES:
    p1, p2 = positioned_segments[name]

    ux, uy = unit_vector(p1, p2)
    left_normal = (-uy, ux)
    segment_mid = midpoint(p1, p2)

    outward_test = (
        (segment_mid[0] - section_centroid[0]) * left_normal[0]
        + (segment_mid[1] - section_centroid[1]) * left_normal[1]
    )

    base_offset = (
        SECTION_SMALL_DIM_OFFSET
        if name in {"A", "B", "G", "H"}
        else SECTION_DIM_OFFSET
    )

    signed_offset = base_offset if outward_test >= 0 else -base_offset

    add_aligned_dimension(
        p1,
        p2,
        signed_offset,
        f"{name} <>",
    )


# Gutter-arm depth, measured perpendicular to G from the
# F/G junction to the extension of B.
gutter_arm_p1, gutter_arm_p2 = positioned_segments["GUTTER_ARM_DEPTH"]

add_aligned_dimension(
    gutter_arm_p1,
    gutter_arm_p2,
    GUTTER_ARM_DIM_OFFSET,
    "<>",
)


# 1 mm hem gap note/dimension.
p_a_fold = position_section_point(section_chains[0][1])
p_b_free = position_section_point(section_chains[0][2])

add_aligned_dimension(
    p_a_fold,
    p_b_free,
    SECTION_SMALL_DIM_OFFSET,
    "<>",
)


# Angular dimensions as on the original drawing.
angle_radii = {
    "BC": SECTION_ANGLE_RADIUS,
    "CD": SECTION_ANGLE_RADIUS + 4.0,
    "DE": SECTION_ANGLE_RADIUS + 2.0,
    "FG": SECTION_ANGLE_RADIUS,
}

for label, (center, p1, p2) in positioned_angles.items():
    add_angular_dimension(
        label,
        center,
        p1,
        p2,
        angle_radii[label],
    )







# ============================================================
# 4. PARAMETRIC STOP END — RIGHT OF THE FLAT PATTERN
# ============================================================

stop_end = build_stop_end()
stop_local_points = stop_end["all_points"]

stop_local_min_x = min(point[0] for point in stop_local_points)
stop_local_max_x = max(point[0] for point in stop_local_points)
stop_local_min_y = min(point[1] for point in stop_local_points)
stop_local_max_y = max(point[1] for point in stop_local_points)

stop_local_centre_y = (stop_local_min_y + stop_local_max_y) / 2.0

# Place the stop end 250 mm clear to the right of the flat pattern.
# The flat pattern occupies x = 0 to x = GUTTER_LENGTH.
stop_dx = (
    GUTTER_LENGTH
    + STOP_END_GAP_FROM_FLAT
    - stop_local_min_x
)

# Vertically centre the stop end on the flat-pattern girth.
stop_dy = GIRTH / 2.0 - stop_local_centre_y


def position_stop_point(point: Point) -> Point:
    return translate_point(point, stop_dx, stop_dy)


for p1, p2 in stop_end["cut_lines"]:
    add_line(
        position_stop_point(p1),
        position_stop_point(p2),
        "STOP_END",
    )

for p1, p2 in stop_end["indicative_lines"]:
    msp.add_line(
        position_stop_point(p1),
        position_stop_point(p2),
        dxfattribs={
            "layer": "STOP_END_INDICATIVE",
            "color": DIMENSION_COLOUR,
            "linetype": "DOTTED",
        },
    )


# The stop end is intentionally generated without dimensions.

# ============================================================
# SAVE
# ============================================================

output_path = Path(__file__).resolve().with_name(OUTPUT_FILENAME)
doc.saveas(output_path)

