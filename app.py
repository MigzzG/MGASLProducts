from __future__ import annotations

from datetime import date
from io import BytesIO
from math import hypot
from pathlib import Path
from textwrap import fill

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Polygon, Rectangle

from analytics import log_usage_event
from trimline_engine import (
    DEFAULT_PARAMETERS,
    CalculationResult,
    calculate_profile,
    generate_dxf,
)


st.set_page_config(
    page_title="Trimline Gutter Section Generator",
    layout="wide",
)

BRAND_SKY_BLUE = "#0072CE"
BRAND_STEEL_GREY = "#53565A"
BRAND_BLUE_2 = "#89B7D9"
BRAND_BLUE_3 = "#D0E2F0"
BRAND_BLUE_4 = "#E9F1F8"
BRAND_GREY_2 = "#B0AFB0"
BRAND_GREY_3 = "#E0E0E0"
BRAND_GREY_4 = "#F0EFF0"
BRAND_ARCELOR_ORANGE = "#F04E23"
BRAND_CHARCOAL = "#333333"
BRAND_LIGHT = "#F7F7F5"
BRAND_LINE = "#D8D8D6"

COMPANY_NAME = "ArcelorMittal Building Solutions"
MANCHESTER_CONTACT_LINES = [
    "Manchester",
    "Lyons Road",
    "Trafford Park",
    "M17 1RN",
    "United Kingdom",
    "Sales Office: 0161 872 6333",
    "info@archsteel.co.uk",
]
GLASGOW_CONTACT_LINES = [
    "Glasgow",
    "Suite F, Campsie Softnet Centre,",
    "Enterprise House, Kirkintilloch",
    "G66 1XQ",
    "United Kingdom",
    "Sales Office: 0141 530 1485",
    "info.uk@arcelormittal.com",
]
COMPANY_WEBSITE = "construction-uk.arcelormittal.com"
COMPANY_TAGLINE = "Smarter steels for people and planet"
PRODUCT_TAGLINE = "Inspiring Smarter Building"

ASSET_DIR = Path(__file__).resolve().parent / "assets"
ASL_LOGO_PATH = ASSET_DIR / "archsteel_logo.jpg"
ARCELOR_LOGO_PATH = ASSET_DIR / "arcelormittal_logo.png"


def _inject_brand_css() -> None:
    """Apply the revised brochure-inspired style using the approved brand colours."""
    st.markdown(
        f"""
        <style>
            .stApp, .stApp * {{
                font-family: Arial, Helvetica, sans-serif;
            }}

            .stApp {{
                background: #ffffff;
                color: {BRAND_CHARCOAL};
            }}

            .block-container {{
                padding-top: 1.9rem;
                padding-bottom: 2.0rem;
                max-width: 1480px;
            }}

            .brand-logo-box {{
                padding-top: 0.55rem;
            }}

            .company-footer {{
                margin-bottom: 1.25rem;
                padding-bottom: 0.8rem;
            }}

            .company-tagline {{
                margin-top: 1.15rem;
                margin-bottom: 0.45rem;
                line-height: 1.35;
            }}

            .brand-shell {{
                position: relative;
                min-height: 150px;
                border-left: 6px solid {BRAND_STEEL_GREY};
                padding: 1.10rem 1.20rem 1.00rem 1.20rem;
                background: #ffffff;
                overflow: hidden;
            }}

            .brand-kicker {{
                font-size: 0.92rem;
                font-weight: 700;
                color: {BRAND_STEEL_GREY};
                margin-bottom: 0.25rem;
            }}

            .brand-title {{
                font-size: 2.10rem;
                font-weight: 750;
                color: {BRAND_SKY_BLUE};
                line-height: 1.05;
                margin-bottom: 0.35rem;
            }}

            .brand-subtitle {{
                font-size: 1rem;
                color: {BRAND_STEEL_GREY};
                line-height: 1.4;
                max-width: 760px;
            }}

            .brand-message {{
                display: inline-block;
                margin-top: 0.85rem;
                padding: 0;
                color: #000000;
                font-weight: 700;
                background: transparent;
            }}

            .meta-card {{
                border-top: 4px solid {BRAND_SKY_BLUE};
                background: {BRAND_BLUE_4};
                padding: 0.8rem 0.95rem;
                margin-bottom: 0.75rem;
            }}

            .meta-card h4 {{
                margin: 0 0 0.3rem 0;
                color: {BRAND_SKY_BLUE};
            }}

            .company-footer {{
                margin-top: 1.4rem;
                border-top: 1px solid {BRAND_GREY_3};
                padding-top: 1rem;
                color: {BRAND_CHARCOAL};
            }}

            .company-footer-grid {{
                display: grid;
                grid-template-columns: 1.3fr 1fr 1fr;
                gap: 1.4rem;
            }}

            .company-footer h4 {{
                margin: 0 0 0.35rem 0;
                font-size: 1rem;
                color: {BRAND_SKY_BLUE};
            }}

            .company-footer p {{
                margin: 0;
                line-height: 1.35;
                font-size: 0.88rem;
            }}

            .company-tagline {{
                margin-top: 0.9rem;
                padding: 0;
                color: #000000;
                font-weight: 700;
                background: transparent;
            }}

            div[data-baseweb="tab-list"] {{
                gap: 0.4rem;
            }}

            button[data-baseweb="tab"][aria-selected="true"] {{
                color: {BRAND_SKY_BLUE} !important;
                font-weight: 700;
            }}

            div[data-baseweb="tab-highlight"] {{
                background-color: {BRAND_SKY_BLUE} !important;
            }}

            .stFormSubmitButton > button[kind="primary"],
            .stButton > button[kind="primary"] {{
                color: #ffffff;
                border: none;
                background: {BRAND_STEEL_GREY};
            }}

            .stFormSubmitButton > button[kind="primary"]:hover,
            .stButton > button[kind="primary"]:hover {{
                color: #ffffff;
                border: none;
                background: {BRAND_SKY_BLUE};
            }}

            h1, h2, h3 {{
                color: {BRAND_SKY_BLUE};
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _show_brand_header() -> None:
    """Display the logos and the simplified heading panel."""
    logo_left, title_col, logo_right = st.columns([1.35, 2.70, 1.35])

    with logo_left:
        st.markdown('<div class="brand-logo-box">', unsafe_allow_html=True)
        if ASL_LOGO_PATH.exists():
            st.image(str(ASL_LOGO_PATH), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with title_col:
        st.markdown(
            f"""
            <div class="brand-shell">
                <div class="brand-kicker">ArcelorMittal Building Solutions</div>
                <div class="brand-title">Trimline Gutter Section Generator</div>
                <div class="brand-subtitle">
                    Create coordinated technical outputs containing the DXF,
                    branded PDF, project details and requester information.
                </div>
                <div class="brand-message">{PRODUCT_TAGLINE}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with logo_right:
        st.markdown('<div class="brand-logo-box">', unsafe_allow_html=True)
        if ARCELOR_LOGO_PATH.exists():
            st.image(str(ARCELOR_LOGO_PATH), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)


def _show_company_footer() -> None:
    """Show the contact information using the simplified styling."""
    st.markdown(
        f"""
        <div class="company-footer">
            <div class="company-footer-grid">
                <div>
                    <h4>Get in touch</h4>
                    <p><strong>{COMPANY_NAME}</strong></p>
                    <p>{COMPANY_WEBSITE}</p>
                </div>
                <div>
                    <h4>Manchester</h4>
                    <p>
                        Lyons Road<br>
                        Trafford Park<br>
                        M17 1RN<br>
                        United Kingdom<br>
                        Sales Office: 0161 872 6333<br>
                        info@archsteel.co.uk
                    </p>
                </div>
                <div>
                    <h4>Glasgow</h4>
                    <p>
                        Suite F, Campsie Softnet Centre,<br>
                        Enterprise House, Kirkintilloch<br>
                        G66 1XQ<br>
                        United Kingdom<br>
                        Sales Office: 0141 530 1485<br>
                        info.uk@arcelormittal.com
                    </p>
                </div>
            </div>
            <div class="company-tagline">{COMPANY_TAGLINE}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


_inject_brand_css()


def _show_login_screen() -> None:
    """Block access to the generator until Google login succeeds."""
    _show_brand_header()
    st.info(
        "Sign in with Google to use the generator. While OAuth remains in "
        "Testing mode, access is limited to the approved Google accounts."
    )

    if st.button(
        "Log in with Google",
        type="primary",
        use_container_width=True,
    ):
        st.login()


if not st.user.is_logged_in:
    _show_login_screen()
    st.stop()


signed_in_name = str(getattr(st.user, "name", "") or "")
signed_in_email = str(getattr(st.user, "email", "") or "")

_show_brand_header()

info_column, account_column = st.columns([4, 1])

with info_column:
    st.caption(
        "Enter the project information and the profile values, review the "
        "preview, then generate the DXF and branded PDF together."
    )

with account_column:
    st.markdown(
        f"""
        <div class="meta-card">
            <h4>Signed in</h4>
            <div><strong>{signed_in_name or signed_in_email or "User"}</strong></div>
            <div>{signed_in_email or ""}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Log out", use_container_width=True):
        st.logout()


APP_REVISION = "2026-07-28-STYLE-V8"


def _current_user_identity() -> tuple[str, str]:
    """Return the authenticated Google user's name and email."""
    name = str(getattr(st.user, "name", "") or "")
    email = str(getattr(st.user, "email", "") or "")
    return name, email


def _usage_payload(
    *,
    result: CalculationResult | None,
    parameters: dict[str, float],
    file_name: str,
    dxf_generated: bool,
    pdf_generated: bool,
    success: bool,
    error_message: str = "",
) -> dict[str, object]:
    user_name, user_email = _current_user_identity()

    return {
        "user_name": user_name,
        "user_email": user_email,
        "file_name": file_name,
        "A": parameters["A"],
        "B": parameters["B"],
        "C": parameters["C"],
        "D": parameters["D"],
        "E": parameters["E"],
        "F": result.f if result is not None else "",
        "G": parameters["G"],
        "H": parameters["H"],
        "roof_pitch": parameters["ROOF_PITCH"],
        "gutter_arm_depth": parameters["GUTTER_ARM_DEPTH"],
        "angle_bc": result.angle_bc if result is not None else "",
        "angle_cd": parameters["ANGLE_CD"],
        "angle_de": parameters["ANGLE_DE"],
        "angle_ef": parameters["ANGLE_EF"],
        "angle_fg": result.angle_fg if result is not None else "",
        "girth": result.girth if result is not None else "",
        "dxf_generated_yes_no": "Yes" if dxf_generated else "No",
        "pdf_generated_yes_no": "Yes" if pdf_generated else "No",
        "success": "Yes" if success else "No",
        "error_message": error_message,
        "app_revision": APP_REVISION,
    }


def _record_usage(
    *,
    result: CalculationResult | None,
    parameters: dict[str, float],
    file_name: str,
    dxf_generated: bool,
    pdf_generated: bool,
    success: bool,
    error_message: str = "",
) -> None:
    saved, logging_error = log_usage_event(
        _usage_payload(
            result=result,
            parameters=parameters,
            file_name=file_name,
            dxf_generated=dxf_generated,
            pdf_generated=pdf_generated,
            success=success,
            error_message=error_message,
        )
    )

    if not saved:
        st.warning(
            "The usage record could not be saved to Google Sheets: "
            f"{logging_error}"
        )




def _display_text(value: object) -> str:
    """Return a printable text value for PDF fields."""
    if value is None:
        return "—"

    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")

    text = str(value).strip()
    return text if text else "—"


def _draw_pdf_info_block(
    figure: plt.Figure,
    *,
    x: float,
    y_top: float,
    title: str,
    items: list[tuple[str, object]],
) -> None:
    """Draw a title/value block in figure coordinates."""
    figure.text(
        x,
        y_top,
        title,
        fontsize=11.5,
        fontweight="bold",
        color=BRAND_ARCELOR_ORANGE,
        ha="left",
        va="top",
    )

    y = y_top - 0.032
    for label, value in items:
        figure.text(
            x,
            y,
            f"{label}:",
            fontsize=9.5,
            fontweight="bold",
            color=BRAND_CHARCOAL,
            ha="left",
            va="top",
        )
        figure.text(
            x + 0.14,
            y,
            _display_text(value),
            fontsize=9.5,
            color=BRAND_CHARCOAL,
            ha="left",
            va="top",
        )
        y -= 0.028


def number_field(
    label: str,
    key: str,
    *,
    step: float = 1.0,
    help_text: str | None = None,
    min_value: float | None = None,
) -> float:
    kwargs = {
        "label": label,
        "value": float(DEFAULT_PARAMETERS[key]),
        "step": float(step),
        "format": "%.3f",
        "key": key,
        "help": help_text,
    }

    if min_value is not None:
        kwargs["min_value"] = float(min_value)

    return float(st.number_input(**kwargs))


def _format_number(value: float, decimal_places: int = 2) -> str:
    """Return a compact engineering value without unnecessary zeros."""
    rounded = round(float(value), decimal_places)

    if abs(rounded - round(rounded)) < 1e-9:
        return str(int(round(rounded)))

    return f"{rounded:.{decimal_places}f}".rstrip("0").rstrip(".")


def _midpoint(
    p1: tuple[float, float],
    p2: tuple[float, float],
) -> tuple[float, float]:
    return (
        (p1[0] + p2[0]) / 2.0,
        (p1[1] + p2[1]) / 2.0,
    )


def _unit_vector(
    p1: tuple[float, float],
    p2: tuple[float, float],
) -> tuple[float, float]:
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = hypot(dx, dy)

    if length < 1e-9:
        return 1.0, 0.0

    return dx / length, dy / length


def _profile_segments(
    result: CalculationResult,
) -> dict[str, tuple[tuple[float, float], tuple[float, float]]]:
    """Map A-H to the actual section segments."""
    front = result.front_chain
    rear = result.rear_chain

    return {
        "A": (front[0], front[1]),
        "B": (front[2], front[3]),
        "C": (front[3], front[4]),
        "D": (front[4], front[5]),
        "E": (rear[0], rear[1]),
        "F": (rear[1], rear[2]),
        "G": (rear[2], rear[3]),
        "H": (rear[3], rear[4]),
    }


def _profile_centre(
    result: CalculationResult,
) -> tuple[float, float]:
    points = result.front_chain + result.rear_chain

    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )


def _outward_label_position(
    p1: tuple[float, float],
    p2: tuple[float, float],
    centre: tuple[float, float],
    distance: float,
) -> tuple[float, float]:
    """Place a horizontal label outside the section near its segment."""
    midpoint = _midpoint(p1, p2)
    ux, uy = _unit_vector(p1, p2)

    normal_1 = -uy, ux
    normal_2 = uy, -ux

    centre_vector = (
        midpoint[0] - centre[0],
        midpoint[1] - centre[1],
    )

    score_1 = (
        centre_vector[0] * normal_1[0]
        + centre_vector[1] * normal_1[1]
    )
    normal = normal_1 if score_1 >= 0 else normal_2

    return (
        midpoint[0] + normal[0] * distance,
        midpoint[1] + normal[1] * distance,
    )


def _angle_label_position(
    previous: tuple[float, float],
    vertex: tuple[float, float],
    following: tuple[float, float],
    distance: float,
) -> tuple[float, float]:
    """Place an angle value inside the smaller angle at a bend."""
    u1 = _unit_vector(vertex, previous)
    u2 = _unit_vector(vertex, following)

    bisector = u1[0] + u2[0], u1[1] + u2[1]
    length = hypot(bisector[0], bisector[1])

    if length < 1e-9:
        bisector = -u1[1], u1[0]
        length = 1.0

    return (
        vertex[0] + distance * bisector[0] / length,
        vertex[1] + distance * bisector[1] / length,
    )


def create_section_figure(
    result: CalculationResult,
    parameters: dict[str, float],
    *,
    for_pdf: bool = False,
) -> plt.Figure:
    """
    Draw only the folded section.

    The preview intentionally has no grid, chart axes or formal dimension
    lines. Segment sizes and angles are shown as simple horizontal text
    close to the relevant geometry.
    """
    figure_size = (11.69, 8.27) if for_pdf else (9.0, 6.2)
    fig, ax = plt.subplots(figsize=figure_size)

    profile_colour = BRAND_STEEL_GREY
    text_colour = BRAND_STEEL_GREY
    depth_colour = BRAND_ARCELOR_ORANGE

    front_x = [point[0] for point in result.front_chain]
    front_y = [point[1] for point in result.front_chain]
    rear_x = [point[0] for point in result.rear_chain]
    rear_y = [point[1] for point in result.rear_chain]

    ax.plot(
        front_x,
        front_y,
        linewidth=2.2,
        solid_capstyle="round",
        solid_joinstyle="round",
        color=profile_colour,
    )
    ax.plot(
        rear_x,
        rear_y,
        linewidth=2.2,
        solid_capstyle="round",
        solid_joinstyle="round",
        color=profile_colour,
    )

    all_points = result.front_chain + result.rear_chain
    minimum_x = min(point[0] for point in all_points)
    maximum_x = max(point[0] for point in all_points)
    minimum_y = min(point[1] for point in all_points)
    maximum_y = max(point[1] for point in all_points)

    width = max(maximum_x - minimum_x, 1.0)
    height = max(maximum_y - minimum_y, 1.0)
    overall_span = max(width, height)

    segment_offset = max(overall_span * 0.045, 7.0)
    angle_offset = max(overall_span * 0.055, 9.0)
    centre = _profile_centre(result)
    segments = _profile_segments(result)

    segment_values = {
        "A": parameters["A"],
        "B": parameters["B"],
        "C": parameters["C"],
        "D": parameters["D"],
        "E": parameters["E"],
        "F": result.f,
        "G": parameters["G"],
        "H": parameters["H"],
    }

    for letter, segment in segments.items():
        label_position = _outward_label_position(
            segment[0],
            segment[1],
            centre,
            segment_offset,
        )

        # Short upper segments need deliberate separation so their labels
        # remain readable even when the profile changes slightly.
        segment_midpoint = _midpoint(segment[0], segment[1])

        if letter == "A":
            label_position = (
                segment_midpoint[0] + segment_offset * 0.75,
                segment_midpoint[1] + segment_offset * 1.35,
            )
        elif letter == "B":
            label_position = (
                segment_midpoint[0] - segment_offset * 0.75,
                segment_midpoint[1] + segment_offset * 1.55,
            )
        elif letter == "G":
            label_position = (
                segment_midpoint[0],
                segment_midpoint[1] + segment_offset * 1.35,
            )
        elif letter == "H":
            label_position = (
                segment_midpoint[0] - segment_offset * 1.55,
                segment_midpoint[1] - segment_offset * 0.20,
            )

        ax.text(
            label_position[0],
            label_position[1],
            f"{letter} {_format_number(segment_values[letter])}",
            horizontalalignment="center",
            verticalalignment="center",
            rotation=0,
            fontsize=10.5 if not for_pdf else 11.5,
            color=text_colour,
            bbox={
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.88,
                "pad": 1.5,
            },
        )

    front = result.front_chain
    rear = result.rear_chain

    # Plain numerical angle values only - no BC, CD, DE, EF, FG or GH text.
    angle_annotations = [
        (
            "BC",
            front[2],
            front[3],
            front[4],
            result.angle_bc,
        ),
        (
            "CD",
            front[3],
            front[4],
            front[5],
            parameters["ANGLE_CD"],
        ),
        (
            "DE",
            front[4],
            front[5],
            rear[1],
            parameters["ANGLE_DE"],
        ),
        (
            "EF",
            rear[0],
            rear[1],
            rear[2],
            parameters["ANGLE_EF"],
        ),
        (
            "FG",
            rear[1],
            rear[2],
            rear[3],
            result.angle_fg,
        ),
        (
            "GH",
            rear[2],
            rear[3],
            rear[4],
            90.0 + parameters["ROOF_PITCH"],
        ),
    ]

    for angle_name, previous, vertex, following, angle_value in angle_annotations:
        angle_position = _angle_label_position(
            previous,
            vertex,
            following,
            angle_offset,
        )

        # F/G and G/H are close together. Keep their numerical values on
        # opposite sides of G, with the G/H angle inside the return.
        if angle_name == "FG":
            angle_position = (
                vertex[0] - angle_offset * 1.00,
                vertex[1] - angle_offset * 1.70,
            )
        elif angle_name == "GH":
            angle_position = (
                vertex[0] + angle_offset * 0.85,
                vertex[1] - angle_offset * 0.15,
            )

        ax.text(
            angle_position[0],
            angle_position[1],
            f"{_format_number(angle_value)}°",
            horizontalalignment="center",
            verticalalignment="center",
            rotation=0,
            fontsize=9.5 if not for_pdf else 10.5,
            color=text_colour,
            bbox={
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.82,
                "pad": 1.0,
            },
        )

    # Roof pitch note near B. The value is not a formal dimension.
    b_start, b_end = segments["B"]
    b_midpoint = _midpoint(b_start, b_end)
    b_label_position = (
        b_midpoint[0],
        b_midpoint[1] + segment_offset * 3.0,
    )

    ax.text(
        b_label_position[0],
        b_label_position[1],
        f"Roof pitch {_format_number(parameters['ROOF_PITCH'])}°",
        horizontalalignment="center",
        verticalalignment="center",
        rotation=0,
        fontsize=9.5 if not for_pdf else 10.5,
        color=text_colour,
    )

    # Gutter arm depth remains a simple dashed construction and nearby note.
    depth_start, depth_end = result.gutter_arm_line
    ax.plot(
        [depth_start[0], depth_end[0]],
        [depth_start[1], depth_end[1]],
        linestyle=(0, (5, 4)),
        linewidth=1.2,
        color=depth_colour,
    )

    depth_midpoint = _midpoint(depth_start, depth_end)
    depth_label_position = _outward_label_position(
        depth_start,
        depth_end,
        centre,
        segment_offset * 2.0,
    )

    ax.text(
        depth_label_position[0],
        depth_label_position[1],
        "Gutter arm depth\n"
        f"{_format_number(parameters['GUTTER_ARM_DEPTH'])} mm",
        horizontalalignment="center",
        verticalalignment="center",
        rotation=0,
        fontsize=9.5 if not for_pdf else 10.5,
        color=text_colour,
        linespacing=1.15,
        bbox={
            "facecolor": "white",
            "edgecolor": "none",
            "alpha": 0.88,
            "pad": 2.0,
        },
    )

    # Generous white margin prevents labels from being clipped.
    padding_x = max(width * 0.23, 28.0)
    padding_y = max(height * 0.19, 24.0)

    ax.set_xlim(minimum_x - padding_x, maximum_x + padding_x)
    ax.set_ylim(minimum_y - padding_y, maximum_y + padding_y)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    if for_pdf:
        ax.set_title(
            "Parametric gutter section",
            loc="left",
            fontsize=16,
            fontweight="bold",
            color=text_colour,
            pad=16,
        )

    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    fig.tight_layout(pad=1.2)

    return fig


def generate_section_pdf(
    result: CalculationResult,
    parameters: dict[str, float],
    dxf_filename: str,
    project_info: dict[str, object],
) -> tuple[bytes, str]:
    """Create a brochure-inspired branded section PDF."""
    section_buffer = BytesIO()
    section_figure = create_section_figure(
        result,
        parameters,
        for_pdf=True,
    )
    section_figure.savefig(
        section_buffer,
        format="png",
        dpi=220,
        bbox_inches="tight",
        pad_inches=0.2,
        facecolor="white",
    )
    plt.close(section_figure)
    section_buffer.seek(0)
    section_image = plt.imread(section_buffer)

    pdf_buffer = BytesIO()
    figure = plt.figure(figsize=(11.69, 8.27), facecolor="white")

    # Full-page background axes for the brochure-inspired gradient wedges.
    background_ax = figure.add_axes([0.0, 0.0, 1.0, 1.0], zorder=-10)
    background_ax.set_xlim(0.0, 1.0)
    background_ax.set_ylim(0.0, 1.0)
    background_ax.axis("off")

    colour_map = LinearSegmentedColormap.from_list(
        "am_gradient",
        [BRAND_AMBER, BRAND_ARCELOR_ORANGE, BRAND_RED, BRAND_MAGENTA],
    )
    horizontal_gradient = np.linspace(0.0, 1.0, 1200).reshape(1, -1)

    bottom_gradient = background_ax.imshow(
        horizontal_gradient,
        extent=[0.0, 1.0, 0.0, 0.105],
        aspect="auto",
        origin="lower",
        cmap=colour_map,
    )
    bottom_clip = Polygon(
        [(0.0, 0.0), (0.62, 0.0), (0.53, 0.105), (0.08, 0.105)],
        closed=True,
        transform=background_ax.transData,
    )
    bottom_gradient.set_clip_path(bottom_clip)

    top_gradient = background_ax.imshow(
        horizontal_gradient,
        extent=[0.72, 1.0, 0.84, 0.97],
        aspect="auto",
        origin="lower",
        cmap=colour_map,
    )
    top_clip = Polygon(
        [(0.78, 0.97), (1.0, 0.97), (1.0, 0.84), (0.72, 0.86)],
        closed=True,
        transform=background_ax.transData,
    )
    top_gradient.set_clip_path(top_clip)

    # Official logos supplied by the user.
    if ASL_LOGO_PATH.exists():
        logo_ax = figure.add_axes([0.045, 0.845, 0.30, 0.105])
        logo_ax.imshow(plt.imread(ASL_LOGO_PATH))
        logo_ax.axis("off")

    if ARCELOR_LOGO_PATH.exists():
        logo_ax = figure.add_axes([0.79, 0.845, 0.16, 0.10])
        logo_ax.imshow(plt.imread(ARCELOR_LOGO_PATH))
        logo_ax.axis("off")

    figure.text(
        0.05,
        0.815,
        "Trimline Gutter Section",
        fontsize=23,
        fontweight="bold",
        color="#111111",
        ha="left",
        va="top",
    )
    figure.text(
        0.05,
        0.775,
        "Technical section and project issue information",
        fontsize=12.5,
        color=BRAND_CHARCOAL,
        ha="left",
        va="top",
    )
    figure.add_artist(
        Rectangle(
            (0.05, 0.747),
            0.90,
            0.004,
            transform=figure.transFigure,
            facecolor=BRAND_ARCELOR_ORANGE,
            edgecolor="none",
        )
    )

    left_items = [
        ("Client", project_info.get("client_name")),
        ("Site", project_info.get("site_name")),
        ("Order / reference", project_info.get("order_reference")),
        ("Section date", project_info.get("section_date")),
    ]
    right_items = [
        ("Requested by", project_info.get("requested_by")),
        ("Requester company", project_info.get("requester_company")),
        ("Requester email", project_info.get("requester_email")),
        ("Requester phone", project_info.get("requester_phone")),
    ]

    _draw_pdf_info_block(
        figure,
        x=0.05,
        y_top=0.71,
        title="Project details",
        items=left_items,
    )
    _draw_pdf_info_block(
        figure,
        x=0.56,
        y_top=0.71,
        title="Requester details",
        items=right_items,
    )

    prepared_by = " / ".join(
        item for item in [
            _display_text(project_info.get("prepared_by_name")),
            _display_text(project_info.get("prepared_by_email")),
        ]
        if item and item != "—"
    )
    figure.text(
        0.56,
        0.565,
        f"Prepared by: {prepared_by or '—'}",
        fontsize=9.2,
        color=BRAND_CHARCOAL,
        ha="left",
        va="top",
    )

    notes = _display_text(project_info.get("requester_notes"))
    if notes != "—":
        figure.text(
            0.05,
            0.565,
            "Notes:",
            fontsize=9.5,
            fontweight="bold",
            color=BRAND_CHARCOAL,
            ha="left",
            va="top",
        )
        figure.text(
            0.12,
            0.565,
            fill(notes, 84),
            fontsize=9.2,
            color=BRAND_CHARCOAL,
            ha="left",
            va="top",
        )

    section_ax = figure.add_axes([0.06, 0.205, 0.88, 0.33])
    section_ax.imshow(section_image)
    section_ax.axis("off")

    # Contact area follows the brochure's 'Get in touch' page.
    figure.text(
        0.05,
        0.185,
        "Get in touch",
        fontsize=10.8,
        fontweight="bold",
        color="#111111",
        ha="left",
        va="top",
    )
    figure.text(
        0.05,
        0.158,
        "Manchester",
        fontsize=9.4,
        fontweight="bold",
        color=BRAND_CHARCOAL,
        ha="left",
        va="top",
    )
    figure.text(
        0.15,
        0.158,
        "Lyons Road, Trafford Park, M17 1RN, United Kingdom\\n"
        "Sales Office: 0161 872 6333  |  info@archsteel.co.uk",
        fontsize=8.5,
        color=BRAND_CHARCOAL,
        ha="left",
        va="top",
        linespacing=1.3,
    )
    figure.text(
        0.53,
        0.158,
        "Glasgow",
        fontsize=9.4,
        fontweight="bold",
        color=BRAND_CHARCOAL,
        ha="left",
        va="top",
    )
    figure.text(
        0.60,
        0.158,
        "Suite F, Campsie Softnet Centre, Enterprise House, Kirkintilloch, G66 1XQ\\n"
        "Sales Office: 0141 530 1485  |  info.uk@arcelormittal.com",
        fontsize=8.3,
        color=BRAND_CHARCOAL,
        ha="left",
        va="top",
        linespacing=1.3,
    )

    figure.text(
        0.05,
        0.060,
        COMPANY_TAGLINE,
        fontsize=11.0,
        fontweight="bold",
        color="#000000",
        ha="left",
        va="center",
    )
    figure.text(
        0.05,
        0.038,
        PRODUCT_TAGLINE,
        fontsize=9.4,
        fontweight="bold",
        color="#000000",
        ha="left",
        va="center",
    )
    figure.text(
        0.94,
        0.060,
        COMPANY_WEBSITE,
        fontsize=8.8,
        fontweight="bold",
        color=BRAND_STEEL_GREY,
        ha="right",
        va="center",
    )
    figure.text(
        0.94,
        0.035,
        f"DXF file: {Path(dxf_filename).name}",
        fontsize=8.2,
        color=BRAND_STEEL_GREY,
        ha="right",
        va="center",
    )

    figure.savefig(
        pdf_buffer,
        format="pdf",
        bbox_inches="tight",
        pad_inches=0.15,
        facecolor="white",
    )
    plt.close(figure)

    pdf_buffer.seek(0)
    pdf_filename = f"{Path(dxf_filename).stem}_section.pdf"
    return pdf_buffer.getvalue(), pdf_filename




with st.form("profile_form"):
    project_tab, main_tab, geometry_tab, manufacturing_tab, stop_end_tab = st.tabs(
        [
            "Project details",
            "Main profile",
            "Roof geometry",
            "Manufacturing",
            "Stop end",
        ]
    )

    with project_tab:
        st.subheader("Project details")
        p1, p2 = st.columns(2)

        with p1:
            client_name = st.text_input(
                "Client",
                value="",
            )
            site_name = st.text_input(
                "Site",
                value="",
            )
            order_reference = st.text_input(
                "Order / reference",
                value="",
            )
            section_date = st.date_input(
                "Section creation date",
                value=date.today(),
                format="DD/MM/YYYY",
            )

        with p2:
            requested_by = st.text_input(
                "Requested by",
                value=signed_in_name or "",
            )
            requester_company = st.text_input(
                "Requester company",
                value="",
            )
            requester_email = st.text_input(
                "Requester email",
                value=signed_in_email or "",
            )
            requester_phone = st.text_input(
                "Requester phone",
                value="",
            )

        requester_notes = st.text_area(
            "Notes",
            value="",
            height=90,
            help="Optional issue notes, remarks or request context.",
        )

    with main_tab:
        st.subheader("Main profile dimensions")
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            a = number_field("A (mm)", "A", min_value=0.001)
            e = number_field("E (mm)", "E", min_value=0.001)

        with c2:
            b = number_field("B (mm)", "B", min_value=0.001)
            g = number_field("G (mm)", "G", min_value=0.001)

        with c3:
            c = number_field("C (mm)", "C", min_value=0.001)
            h = number_field("H (mm)", "H", min_value=0.001)

        with c4:
            d = number_field("D (mm)", "D", min_value=0.001)
            hem_gap = number_field(
                "A/B hem gap (mm)",
                "HEM_GAP_AB",
                step=0.1,
                min_value=0.0,
            )

        gutter_length = number_field(
            "Flat-pattern length (mm)",
            "GUTTER_LENGTH",
            min_value=0.001,
        )

    with geometry_tab:
        st.subheader("Roof and profile geometry")
        c1, c2 = st.columns(2)

        with c1:
            roof_pitch = number_field(
                "Roof pitch (degrees)",
                "ROOF_PITCH",
                step=0.5,
                help_text=(
                    "Controls B and G. These two flanges remain parallel."
                ),
            )
            gutter_arm_depth = number_field(
                "Gutter arm depth (mm)",
                "GUTTER_ARM_DEPTH",
                step=0.1,
                min_value=0.001,
                help_text=(
                    "Measured perpendicular to G, from F/G to the "
                    "extension of B."
                ),
            )

        with c2:
            angle_cd = number_field(
                "C/D angle (degrees)",
                "ANGLE_CD",
                step=0.5,
            )
            angle_de = number_field(
                "D/E angle (degrees)",
                "ANGLE_DE",
                step=0.5,
            )
            angle_ef = number_field(
                "E/F angle (degrees)",
                "ANGLE_EF",
                step=0.5,
            )

        with st.expander("Small / male-end adjustments"):
            c1, c2, c3, c4 = st.columns(4)

            with c1:
                a_small_extra = number_field(
                    "A extra (mm)",
                    "A_SMALL_EXTRA",
                    step=0.1,
                )
                e_small_reduction = number_field(
                    "E reduction (mm)",
                    "E_SMALL_REDUCTION",
                    step=0.1,
                )

            with c2:
                b_small_reduction = number_field(
                    "B reduction (mm)",
                    "B_SMALL_REDUCTION",
                    step=0.1,
                )
                f_small_reduction = number_field(
                    "F reduction (mm)",
                    "F_SMALL_REDUCTION",
                    step=0.1,
                )

            with c3:
                c_small_reduction = number_field(
                    "C reduction (mm)",
                    "C_SMALL_REDUCTION",
                    step=0.1,
                )
                g_small_reduction = number_field(
                    "G reduction (mm)",
                    "G_SMALL_REDUCTION",
                    step=0.1,
                )

            with c4:
                d_small_reduction = number_field(
                    "D reduction (mm)",
                    "D_SMALL_REDUCTION",
                    step=0.1,
                )

    with manufacturing_tab:
        st.subheader("Joint, wheel forming and holes")
        c1, c2, c3 = st.columns(3)

        with c1:
            overlap = number_field(
                "Overlap (mm)",
                "OVERLAP",
                min_value=0.001,
            )
            wheel_form = number_field(
                "Wheel-form line from right (mm)",
                "WHEEL_FORM_FROM_RIGHT",
                min_value=0.001,
            )
            left_relief = number_field(
                "Left-end relief (mm)",
                "LEFT_END_RELIEF",
                min_value=0.001,
            )

        with c2:
            notch_length = number_field(
                "Notch safety length (mm)",
                "NOTCH_LENGTH",
                min_value=0.001,
            )
            hole_diameter = number_field(
                "Hole diameter (mm)",
                "HOLE_DIAMETER",
                step=0.5,
                min_value=0.001,
            )
            hole_x = number_field(
                "Hole centre from left (mm)",
                "HOLE_X_FROM_LEFT",
                min_value=0.0,
            )

        with c3:
            hole_from_fold = number_field(
                "First/last hole from fold (mm)",
                "HOLE_DISTANCE_FROM_FOLD",
                min_value=0.0,
            )
            maximum_hole_spacing = number_field(
                "Maximum hole spacing (mm)",
                "MAX_HOLE_SPACING",
                min_value=0.001,
            )
            section_gap = number_field(
                "Section gap from flat (mm)",
                "SECTION_GAP_FROM_FLAT",
                min_value=0.0,
            )

    with stop_end_tab:
        st.subheader("Stop-end settings")
        c1, c2, c3 = st.columns(3)

        with c1:
            stop_lap = number_field(
                "Lap (mm)",
                "STOP_END_LAP",
                min_value=0.001,
            )
            stop_c_reduction = number_field(
                "C reduction (mm)",
                "STOP_C_REDUCTION",
                step=0.1,
            )
            stop_d_reduction = number_field(
                "D reduction (mm)",
                "STOP_D_REDUCTION",
                step=0.1,
            )

        with c2:
            stop_e_reduction = number_field(
                "E reduction (mm)",
                "STOP_E_REDUCTION",
                step=0.1,
            )
            stop_f_reduction = number_field(
                "F reduction (mm)",
                "STOP_F_REDUCTION",
                step=0.1,
            )
            stop_cut_angle = number_field(
                "C/D cut angle (degrees)",
                "STOP_CD_CUT_ANGLE",
                step=0.5,
            )

        with c3:
            stop_min_angle = number_field(
                "Minimum tool angle (degrees)",
                "STOP_CD_MIN_CUT_ANGLE",
                step=0.5,
                min_value=30.0,
            )
            stop_gap = number_field(
                "Gap to right of flat (mm)",
                "STOP_END_GAP_FROM_FLAT",
                min_value=0.0,
            )

    output_name = st.text_input(
        "DXF file name",
        value="parametric_gutter.dxf",
    )

    project_info = {
        "client_name": client_name,
        "site_name": site_name,
        "order_reference": order_reference,
        "section_date": section_date,
        "requested_by": requested_by,
        "requester_company": requester_company,
        "requester_email": requester_email,
        "requester_phone": requester_phone,
        "requester_notes": requester_notes,
        "prepared_by_name": signed_in_name,
        "prepared_by_email": signed_in_email,
    }

    submitted = st.form_submit_button(
        "Generate DXF and PDF",
        type="primary",
        use_container_width=True,
    )


parameters = {
    "A": a,
    "B": b,
    "C": c,
    "D": d,
    "E": e,
    "G": g,
    "H": h,
    "HEM_GAP_AB": hem_gap,
    "GUTTER_LENGTH": gutter_length,
    "ROOF_PITCH": roof_pitch,
    "GUTTER_ARM_DEPTH": gutter_arm_depth,
    "ANGLE_CD": angle_cd,
    "ANGLE_DE": angle_de,
    "ANGLE_EF": angle_ef,
    "A_SMALL_EXTRA": a_small_extra,
    "B_SMALL_REDUCTION": b_small_reduction,
    "C_SMALL_REDUCTION": c_small_reduction,
    "D_SMALL_REDUCTION": d_small_reduction,
    "E_SMALL_REDUCTION": e_small_reduction,
    "F_SMALL_REDUCTION": f_small_reduction,
    "G_SMALL_REDUCTION": g_small_reduction,
    "OVERLAP": overlap,
    "WHEEL_FORM_FROM_RIGHT": wheel_form,
    "LEFT_END_RELIEF": left_relief,
    "NOTCH_LENGTH": notch_length,
    "HOLE_DIAMETER": hole_diameter,
    "HOLE_X_FROM_LEFT": hole_x,
    "HOLE_DISTANCE_FROM_FOLD": hole_from_fold,
    "MAX_HOLE_SPACING": maximum_hole_spacing,
    "STOP_END_LAP": stop_lap,
    "STOP_C_REDUCTION": stop_c_reduction,
    "STOP_D_REDUCTION": stop_d_reduction,
    "STOP_E_REDUCTION": stop_e_reduction,
    "STOP_F_REDUCTION": stop_f_reduction,
    "STOP_CD_CUT_ANGLE": stop_cut_angle,
    "STOP_CD_MIN_CUT_ANGLE": stop_min_angle,
    "STOP_END_GAP_FROM_FLAT": stop_gap,
    "SECTION_GAP_FROM_FLAT": section_gap,
}


try:
    preview = calculate_profile(parameters)

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("Calculated F", f"{preview.f:.2f} mm")
    metric_2.metric("Girth", f"{preview.girth:.2f} mm")
    metric_3.metric("Calculated BC", f"{preview.angle_bc:.2f}°")
    metric_4.metric("Calculated FG", f"{preview.angle_fg:.2f}°")

    preview_col, small_end_col = st.columns([1.6, 1.0])

    with preview_col:
        st.subheader("Section preview")
        figure = create_section_figure(preview, parameters)
        st.pyplot(figure, clear_figure=True)
        plt.close(figure)

    with small_end_col:
        st.subheader("Calculated small end")
        st.dataframe(
            {
                "Face": list(preview.small_end.keys()),
                "Dimension (mm)": [
                    round(value, 3)
                    for value in preview.small_end.values()
                ],
            },
            hide_index=True,
            use_container_width=True,
        )

except Exception as exc:
    preview = None
    st.error(str(exc))


if submitted:
    if preview is None:
        error_message = "Invalid profile parameters."
        st.error("Correct the invalid parameters before generating the DXF.")

        _record_usage(
            result=None,
            parameters=parameters,
            file_name=output_name,
            dxf_generated=False,
            pdf_generated=False,
            success=False,
            error_message=error_message,
        )
    else:
        dxf_generated = False
        pdf_generated = False
        generated = preview
        safe_name = output_name

        try:
            with st.spinner("Generating DXF and section PDF..."):
                dxf_bytes, generated, safe_name = generate_dxf(
                    parameters,
                    output_name,
                )
                dxf_generated = True

                pdf_bytes, pdf_name = generate_section_pdf(
                    generated,
                    parameters,
                    safe_name,
                    project_info,
                )
                pdf_generated = True

            st.session_state["generated_dxf"] = dxf_bytes
            st.session_state["generated_name"] = safe_name
            st.session_state["generated_pdf"] = pdf_bytes
            st.session_state["generated_pdf_name"] = pdf_name

            _record_usage(
                result=generated,
                parameters=parameters,
                file_name=safe_name,
                dxf_generated=dxf_generated,
                pdf_generated=pdf_generated,
                success=True,
            )

            st.success("DXF and section PDF generated successfully.")

        except ModuleNotFoundError as exc:
            error_message = (
                "A required Python package is missing. Install the packages "
                "listed in requirements.txt."
            )

            _record_usage(
                result=generated,
                parameters=parameters,
                file_name=safe_name,
                dxf_generated=dxf_generated,
                pdf_generated=pdf_generated,
                success=False,
                error_message=str(exc),
            )

            st.error(error_message)
            st.exception(exc)

        except Exception as exc:
            _record_usage(
                result=generated,
                parameters=parameters,
                file_name=safe_name,
                dxf_generated=dxf_generated,
                pdf_generated=pdf_generated,
                success=False,
                error_message=str(exc),
            )

            st.error(f"Drawing generation failed: {exc}")
            st.exception(exc)


if (
    "generated_dxf" in st.session_state
    and "generated_pdf" in st.session_state
):
    dxf_column, pdf_column = st.columns(2)

    with dxf_column:
        st.download_button(
            "Download generated DXF",
            data=st.session_state["generated_dxf"],
            file_name=st.session_state["generated_name"],
            mime="application/dxf",
            type="primary",
            use_container_width=True,
        )

    with pdf_column:
        st.download_button(
            "Download branded section PDF",
            data=st.session_state["generated_pdf"],
            file_name=st.session_state["generated_pdf_name"],
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )


_show_company_footer()

with st.expander("Deployment and file information"):
    st.markdown(
        """
        This application requires the following files in the same folder:

        - `app.py`
        - `analytics.py`
        - `trimline_engine.py`
        - `trimline_generator_template.py`
        - `requirements.txt`

        Google login uses Streamlit OIDC authentication. Usage records are sent to the private Google Sheet through the configured Apps Script endpoint.

        The PDF is produced directly from the calculated folded section. It does not contain the flat pattern or stop end.

        Run locally with:

        ```bash
        python -m pip install -r requirements.txt
        python -m streamlit run app.py
        ```
        """
    )
