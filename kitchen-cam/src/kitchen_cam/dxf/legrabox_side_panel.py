#!/usr/bin/env python3
"""
LEGRABOX Side Panel DXF Generator
==================================
Generuje DXF boku szafki dolnej z nawiertami pod 3 szuflady Blum LEGRABOX + BLUMOTION.

Zgodne ze standardami:
- System 32 (32mm grid, 37mm from front, 5mm holes)
- Blum LEGRABOX cabinet profile mounting
- European furniture manufacturing standards

Użycie:
    python3.11 legrabox_side_panel.py
    python3.11 legrabox_side_panel.py --width 600 --depth 510 --height 720
    python3.11 legrabox_side_panel.py --drawers N,M,K
"""

import ezdxf
import argparse
import math
import os
from pathlib import Path

# =============================================================================
# CONSTANTS - European Furniture Standards
# =============================================================================

# System 32
SYS32_SPACING = 32        # mm - standard grid spacing
SYS32_FRONT_OFFSET = 37   # mm - distance from front edge to first hole row
SYS32_BACK_OFFSET = 37    # mm - distance from back edge to last hole row
SYS32_HOLE_DIA = 5.0      # mm - standard System 32 hole diameter

# Standard panel thickness
PANEL_THICKNESS = 18.0    # mm - standard chipboard thickness

# Blum LEGRABOX side heights (internal drawer side height)
LEGRABOX_HEIGHTS = {
    'N': 66.5,    # mm - Normal
    'M': 90.5,    # mm - Medium
    'K': 128.5,   # mm - High
    'C': 177.0,   # mm - Very High
    'F': 241.0,   # mm - Free (extra high)
}

# LEGRABOX cabinet profile mounting
# Fixing holes are at 37mm from front edge (System 32)
# First hole at 9mm from bottom of drawer opening
# Then every 32mm (System 32 grid)
LEGRABOX_PROFILE_FIRST_HOLE = 9.0   # mm from bottom of opening
LEGRABOX_PROFILE_HOLE_DIA = 5.0     # mm (for screws into cabinet side)
LEGRABOX_PROFILE_FRONT_OFFSET = 37.0  # mm from front edge (System 32)

# LEGRABOX nominal lengths (runner lengths)
LEGRABOX_NOMINAL_LENGTHS = [270, 300, 350, 400, 450, 500, 550, 600, 650]

# Standard dowel holes for top/bottom panel connection
DOWEL_DIA = 8.0           # mm - standard dowel diameter
DOWEL_DEPTH = 13.0        # mm - dowel hole depth

# DXF Layer names
LAYER_OUTLINE = "01_OUTLINE"
LAYER_SYS32 = "02_SYSTEM32"
LAYER_PROFILE = "03_LEGRABOX_PROFILE"
LAYER_DOWELS = "04_DOWELS"
LAYER_DIMENSIONS = "05_DIMENSIONS"
LAYER_NOTES = "06_NOTES"
LAYER_EDGEBANDING = "07_EDGEBANDING"

# DXF Colors (AutoCAD color index)
COLOR_OUTLINE = 7      # White
COLOR_SYS32 = 3        # Green
COLOR_PROFILE = 1      # Red
COLOR_DOWELS = 2       # Yellow
COLOR_DIMENSIONS = 4   # Cyan
COLOR_NOTES = 8        # Gray
COLOR_EDGEBANDING = 6  # Magenta


def create_dxf_layers(doc):
    """Create standardized DXF layers for CNC processing."""
    layers = [
        (LAYER_OUTLINE, COLOR_OUTLINE, "Contour zewnetrzny"),
        (LAYER_SYS32, COLOR_SYS32, "Otwory System 32"),
        (LAYER_PROFILE, COLOR_PROFILE, "Otwory prowadnic LEGRABOX"),
        (LAYER_DOWELS, COLOR_DOWELS, "Otwory pod kolki"),
        (LAYER_DIMENSIONS, COLOR_DIMENSIONS, "Wymiary kontrolne"),
        (LAYER_NOTES, COLOR_NOTES, "Opisy i notatki"),
        (LAYER_EDGEBANDING, COLOR_EDGEBANDING, "Krawedzie do oklejenia"),
    ]
    for name, color, desc in layers:
        layer = doc.layers.add(name)
        layer.color = color
        layer.description = desc


def add_circle(msp, layer, center, diameter):
    """Add a circle (hole) to the DXF."""
    msp.add_circle(center, diameter / 2.0, dxfattribs={'layer': layer})


def add_outline(msp, width, height):
    """Draw the rectangular outline of the side panel."""
    points = [
        (0, 0),
        (width, 0),
        (width, height),
        (0, height),
        (0, 0),
    ]
    msp.add_lwpolyline(points, dxfattribs={'layer': LAYER_OUTLINE})

    # Mark corners with descriptions
    msp.add_text(
        f"0,0",
        height=3,
        dxfattribs={'layer': LAYER_NOTES, 'insert': (5, 5)}
    )
    msp.add_text(
        f"{width}x{height}mm",
        height=5,
        dxfattribs={'layer': LAYER_NOTES, 'insert': (width / 2 - 30, -10)}
    )


def add_system32_holes(msp, width, height, panel_thickness=PANEL_THICKNESS):
    """
    Add System 32 vertical hole rows on the side panel.
    
    Two rows:
    - Front row: 37mm from front edge (right side when looking at inside)
    - Back row: 37mm from back edge (left side when looking at inside)
    
    Vertical positions: calculated from bottom, spaced at 32mm multiples.
    First hole offset from edges: half of 32mm = 16mm (standard practice).
    """
    holes = []
    
    # Front row (37mm from right edge = front of cabinet)
    x_front = width - SYS32_FRONT_OFFSET
    
    # Back row (37mm from left edge = back of cabinet)  
    x_back = SYS32_BACK_OFFSET
    
    # Calculate vertical positions
    # Start from bottom edge + offset, end at top edge - offset
    # The offset is typically chosen so holes are evenly distributed
    # Standard: start at 16mm from bottom (half of 32mm), then every 32mm
    
    first_y = 16.0  # 16mm from bottom (half of 32mm)
    y = first_y
    
    while y <= height - first_y:
        # Add hole in front row
        add_circle(msp, LAYER_SYS32, (x_front, y), SYS32_HOLE_DIA)
        holes.append((x_front, y))
        
        # Add hole in back row
        add_circle(msp, LAYER_SYS32, (x_back, y), SYS32_HOLE_DIA)
        holes.append((x_back, y))
        
        y += SYS32_SPACING
    
    # Add annotations
    msp.add_text(
        "SYS32 FRONT",
        height=3,
        dxfattribs={'layer': LAYER_NOTES, 'insert': (x_front - 15, height + 3)}
    )
    msp.add_text(
        "SYS32 BACK",
        height=3,
        dxfattribs={'layer': LAYER_NOTES, 'insert': (x_back - 12, height + 3)}
    )
    
    return holes


def add_legarabox_profile_holes(msp, width, height, drawer_config, panel_thickness=PANEL_THICKNESS):
    """
    Add LEGRABOX cabinet profile mounting holes.
    
    For each drawer opening, the cabinet profile is fixed to the cabinet side
    with screws at specific positions.
    
    From Blum documentation:
    - Holes at 37mm from front edge (System 32 compatible)
    - First hole at 9mm from bottom of each opening
    - Then every 32mm upward (System 32 grid)
    - Additional fixing holes along the profile length
    
    Args:
        drawer_config: list of dicts with 'height' (opening height) and 'type' (N/M/K/C/F)
    
    Returns:
        List of (x, y) positions for all profile holes
    """
    all_holes = []
    
    # Calculate opening positions (from bottom to top)
    # Internal height = height - top_panel - bottom_panel
    # For a standard cabinet: top rail + bottom = 18mm each
    # But for a 3-drawer cabinet, the openings fill the full internal space
    
    total_opening_height = sum(d['height'] for d in drawer_config)
    
    # Start from the bottom of the internal space
    # Bottom panel is at y=0, internal starts at y=PANEL_THICKNESS (if bottom panel)
    # For simplicity, we work with opening heights from the bottom of the side panel
    # The bottom drawer sits on the cabinet bottom (at panel_thickness from ground)
    
    current_y = 0  # We'll position from the bottom of the side panel
    
    for i, drawer in enumerate(drawer_config):
        opening_height = drawer['height']
        drawer_type = drawer['type']
        
        # LEGRABOX cabinet profile holes
        # Position: 37mm from front edge (System 32 x-position)
        x_profile = width - LEGRABOX_PROFILE_FRONT_OFFSET
        
        # Vertical positions within this opening
        # First hole at 9mm from bottom of opening
        # Then every 32mm
        y_in_opening = LEGRABOX_PROFILE_FIRST_HOLE
        
        while y_in_opening < opening_height - 5:  # Leave 5mm from top
            y_absolute = current_y + y_in_opening
            hole_pos = (x_profile, y_absolute)
            
            add_circle(msp, LAYER_PROFILE, hole_pos, LEGRABOX_PROFILE_HOLE_DIA)
            all_holes.append(hole_pos)
            
            y_in_opening += SYS32_SPACING
        
        # Add second fixing position (if opening is deep enough)
        # Some cabinet profiles have a second row of holes
        # Typically at the middle of the profile for longer runners
        if opening_height > 200:
            y_in_opening = opening_height / 2
            # Snap to System 32 grid
            y_in_opening = round(y_in_opening / SYS32_SPACING) * SYS32_SPACING
            y_absolute = current_y + y_in_opening
            if y_absolute > current_y + LEGRABOX_PROFILE_FIRST_HOLE + 10:
                hole_pos = (x_profile, y_absolute)
                add_circle(msp, LAYER_PROFILE, hole_pos, LEGRABOX_PROFILE_HOLE_DIA)
                all_holes.append(hole_pos)
        
        # Add drawer opening label
        opening_center_y = current_y + opening_height / 2
        msp.add_text(
            f"Szuflada {i+1}: {drawer_type} ({opening_height}mm)",
            height=3,
            dxfattribs={'layer': LAYER_NOTES, 'insert': (5, opening_center_y)}
        )
        
        # Draw horizontal line showing drawer opening boundary
        if i < len(drawer_config) - 1:
            msp.add_line(
                (0, current_y + opening_height),
                (width, current_y + opening_height),
                dxfattribs={'layer': LAYER_NOTES, 'linetype': 'DASHED'}
            )
        
        current_y += opening_height
    
    return all_holes


def add_dowel_holes(msp, width, height, drawer_config):
    """
    Add dowel holes for connecting top and bottom panels.
    
    These are ∅8mm holes in the top and bottom edges of the side panel.
    For DXF representation, we show them as circles on the panel face
    at the top and bottom edges, positioned for panel connection.
    """
    holes = []
    
    # Dowel positions along the depth (width in our 2D representation)
    # Typically 2-3 dowels per edge, spaced evenly
    # Positions: 50mm from each end, and center if panel > 300mm deep
    
    dowel_x_positions = [50, width - 50]
    if width > 300:
        dowel_x_positions.insert(1, width / 2)
    
    # Bottom edge dowels (y = PANEL_THICKNESS/2 from bottom, but we show at y=9)
    for x in dowel_x_positions:
        # Bottom panel connection
        y_bottom = 9  # Center of 18mm panel
        add_circle(msp, LAYER_DOWELS, (x, y_bottom), DOWEL_DIA)
        holes.append((x, y_bottom, 'bottom'))
        
        # Top panel connection
        y_top = height - 9  # Center of 18mm panel
        add_circle(msp, LAYER_DOWELS, (x, y_top), DOWEL_DIA)
        holes.append((x, y_top, 'top'))
    
    # Add labels
    msp.add_text(
        "DNO korpusu (kolki ∅8)",
        height=2.5,
        dxfattribs={'layer': LAYER_NOTES, 'insert': (width / 2 - 30, 2)}
    )
    msp.add_text(
        "GORA korpusu (kolki ∅8)",
        height=2.5,
        dxfattribs={'layer': LAYER_NOTES, 'insert': (width / 2 - 30, height - 14)}
    )
    
    return holes


def add_edgebanding_marks(msp, width, height):
    """
    Add edgebanding indicators.
    
    In a standard kitchen cabinet side panel:
    - Front edge (right): EDGE BANDED (visible)
    - Top edge: EDGE BANDED (visible when no countertop above)
    - Back edge (left): NO edgebanding (against wall)
    - Bottom edge: NO edgebanding (in plinth/hidden)
    """
    # Front edge (right side) - mark with dashed line outside
    offset = 3
    msp.add_line(
        (width + offset, 0),
        (width + offset, height),
        dxfattribs={'layer': LAYER_EDGEBANDING}
    )
    msp.add_text(
        "OKLEINA ABS",
        height=2.5,
        rotation=90,
        dxfattribs={'layer': LAYER_EDGEBANDING, 'insert': (width + offset + 2, height / 2)}
    )
    
    # Top edge
    msp.add_line(
        (0, height + offset),
        (width, height + offset),
        dxfattribs={'layer': LAYER_EDGEBANDING}
    )
    msp.add_text(
        "OKLEINA ABS",
        height=2.5,
        dxfattribs={'layer': LAYER_EDGEBANDING, 'insert': (width / 2 - 15, height + offset + 2)}
    )


def add_dimensions_and_notes(msp, width, height, drawer_config):
    """Add dimension annotations and technical notes."""
    # Title block
    title_y = -20
    msp.add_text(
        "BOK SZAFKI DOLNEJ - LEGRABOX x3 + BLUMOTION",
        height=4,
        dxfattribs={'layer': LAYER_NOTES, 'insert': (0, title_y)}
    )
    msp.add_text(
        f"Wymiary: {width}mm (glebokosc) x {height}mm (wysokosc) x {int(PANEL_THICKNESS)}mm (grubosc)",
        height=3,
        dxfattribs={'layer': LAYER_NOTES, 'insert': (0, title_y - 6)}
    )
    
    # Drawer summary
    summary_y = title_y - 14
    msp.add_text(
        "Konfiguracja szuflad:",
        height=3,
        dxfattribs={'layer': LAYER_NOTES, 'insert': (0, summary_y)}
    )
    
    for i, drawer in enumerate(drawer_config):
        summary_y -= 5
        h = LEGRABOX_HEIGHTS.get(drawer['type'], 0)
        msp.add_text(
            f"  Szuflada {i+1}: LEGRABOX {drawer['type']} (bok {h}mm, otwor {drawer['height']}mm)",
            height=2.5,
            dxfattribs={'layer': LAYER_NOTES, 'insert': (0, summary_y)}
        )
    
    # Technical notes
    summary_y -= 10
    notes = [
        "UWAGI TECHNICZNE:",
        f"- System 32: otwory ∅{SYS32_HOLE_DIA}mm, rozstaw {SYS32_SPACING}mm",
        f"- Odsunięcie od krawędzi przedniej: {SYS32_FRONT_OFFSET}mm",
        f"- Odsunięcie od krawędzi tylnej: {SYS32_BACK_OFFSET}mm",
        f"- Kolki laczące: ∅{DOWEL_DIA}mm, głebokosc {DOWEL_DEPTH}mm",
        f"- Prowadnice LEGRABOX: profil kab. mocowany na ∅{LEGRABOX_PROFILE_HOLE_DIA}mm",
        f"- BLUMOTION: zintegrowany w prowadnicy LEGRABOX",
        "- Skala: 1:1, jednostki: mm",
        "- Format pliku: DXF R2000",
    ]
    for note in notes:
        msp.add_text(
            note,
            height=2,
            dxfattribs={'layer': LAYER_NOTES, 'insert': (0, summary_y)}
        )
        summary_y -= 4


def calculate_drawer_openings(cabinet_height, drawer_types):
    """
    Calculate drawer opening heights for a given cabinet height and drawer type configuration.
    
    For 3 drawers in a kitchen base cabinet (720mm typical):
    - The cabinet has top and bottom panels (18mm each)
    - Internal height = cabinet_height - 2 * PANEL_THICKNESS
    
    The opening heights should accommodate the LEGRABOX side heights plus clearance.
    Typical clearance: 10-13mm above the drawer side.
    
    Args:
        cabinet_height: total cabinet height in mm
        drawer_types: list of LEGRABOX height types ['N', 'M', 'K'] etc.
    
    Returns:
        list of dicts with 'type' and 'height' for each drawer
    """
    internal_height = cabinet_height - 2 * PANEL_THICKNESS
    
    # Calculate required height for each drawer
    # Opening = drawer side height + clearance (typically 13mm for BLUMOTION)
    clearance = 13.0  # mm above drawer side for BLUMOTION mechanism
    
    drawer_config = []
    total_needed = 0
    
    for dt in drawer_types:
        side_height = LEGRABOX_HEIGHTS[dt]
        opening_height = side_height + clearance
        drawer_config.append({'type': dt, 'height': opening_height})
        total_needed += opening_height
    
    # Adjust to fit internal height
    # Distribute remaining space evenly among drawers
    remaining = internal_height - total_needed
    
    if remaining < 0:
        print(f"WARNING: Drawer configuration exceeds internal height!")
        print(f"  Internal height: {internal_height}mm")
        print(f"  Required: {total_needed}mm")
        print(f"  Deficit: {abs(remaining)}mm")
        # Scale down openings proportionally
        scale = internal_height / total_needed
        for d in drawer_config:
            d['height'] = round(d['height'] * scale, 1)
    elif remaining > 0:
        # Distribute extra space evenly
        extra_per_drawer = remaining / len(drawer_config)
        for d in drawer_config:
            d['height'] = round(d['height'] + extra_per_drawer, 1)
    
    return drawer_config


def generate_side_panel_dxf(
    cabinet_depth=510,
    cabinet_height=720,
    drawer_types=None,
    output_dir=None,
    side='left'
):
    """
    Generate a DXF file for a cabinet side panel with LEGRABOX drilling.
    
    Args:
        cabinet_depth: depth of the cabinet in mm (this becomes the panel width)
        cabinet_height: height of the cabinet in mm (this becomes the panel height)
        drawer_types: list of LEGRABOX height types, e.g. ['N', 'M', 'K']
        output_dir: directory to save the DXF file
        side: 'left' or 'right' (for mirrored panels)
    """
    if drawer_types is None:
        drawer_types = ['N', 'M', 'K']  # Normal, Medium, High - typical 3-drawer config
    
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / 'output'
    
    # Panel dimensions
    width = cabinet_depth - PANEL_THICKNESS  # Internal depth (panel width in 2D)
    height = cabinet_height
    
    # Alternative: panel width = cabinet depth (if panel IS the full depth)
    # For standard construction, the side panel spans the full depth
    width = cabinet_depth
    
    # Calculate drawer openings
    drawer_config = calculate_drawer_openings(height, drawer_types)
    
    # Create DXF document
    doc = ezdxf.new('R2000')
    create_dxf_layers(doc)
    msp = doc.modelspace()
    
    # 1. Draw outline
    add_outline(msp, width, height)
    
    # 2. Add System 32 holes
    sys32_holes = add_system32_holes(msp, width, height)
    
    # 3. Add LEGRABOX profile holes
    profile_holes = add_legarabox_profile_holes(msp, width, height, drawer_config)
    
    # 4. Add dowel holes for panel connection
    dowel_holes = add_dowel_holes(msp, width, height, drawer_config)
    
    # 5. Add edgebanding marks
    add_edgebanding_marks(msp, width, height)
    
    # 6. Add dimensions and notes
    add_dimensions_and_notes(msp, width, height, drawer_config)
    
    # 7. Add coordinate origin marker
    msp.add_circle((0, 0), 2, dxfattribs={'layer': LAYER_NOTES})
    msp.add_line((-5, 0), (5, 0), dxfattribs={'layer': LAYER_NOTES})
    msp.add_line((0, -5), (0, 5), dxfattribs={'layer': LAYER_NOTES})
    
    # Mirror for right side panel
    if side == 'right':
        # Note: We generate the same file with a note about mirroring
        msp.add_text(
            "UWAGA: Ten plik jest dla LEWEGO boku. Prawy bok = lustro tego pliku.",
            height=3,
            dxfattribs={'layer': LAYER_NOTES, 'insert': (0, height + 10)}
        )
    
    # Generate filename
    drawer_str = '_'.join(drawer_types)
    filename = f"bok_szafki_legrabox_{drawer_str}_{int(width)}x{int(height)}_{side}.dxf"
    filepath = Path(output_dir) / filename
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Save
    doc.saveas(str(filepath))
    
    # Print summary
    print(f"{'='*60}")
    print(f"WYGENEROWANO DXF: {filepath}")
    print(f"{'='*60}")
    print(f"Wymiary panelu: {width}mm x {height}mm x {int(PANEL_THICKNESS)}mm")
    print(f"Szuflady: {len(drawer_config)}")
    for i, d in enumerate(drawer_config):
        print(f"  {i+1}. LEGRABOX {d['type']} (bok {LEGRABOX_HEIGHTS[d['type']]}mm, otwor {d['height']}mm)")
    print(f"Otwory System 32: {len(sys32_holes)}")
    print(f"Otwory prowadnic LEGRABOX: {len(profile_holes)}")
    print(f"Otwory kolki ∅8mm: {len(dowel_holes)}")
    print(f"{'='*60}")
    
    return filepath


def main():
    parser = argparse.ArgumentParser(
        description='Generator DXF boku szafki dolnej z nawiertami LEGRABOX + BLUMOTION',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  python3.11 legrabox_side_panel.py
  python3.11 legrabox_side_panel.py --depth 510 --height 720 --drawers N M K
  python3.11 legrabox_side_panel.py --depth 560 --height 720 --drawers M M K
  python3.11 legrabox_side_panel.py --depth 480 --height 860 --drawers N K C

Typy szuflad LEGRABOX:
  N = Normalna (66.5mm)   - sztuccce, drobiazgi
  M = Srednia (90.5mm)    - garnki, przyprawy
  K = Wysoka (128.5mm)    - garnki, patelnie
  C = Bardzo wysoka (177mm) - duze garnki, produkty
  F = Wolna (241mm)       - specjalne zastosowania
        """
    )
    
    parser.add_argument('--depth', type=int, default=510,
                        help='Glebokosc szafki w mm (default: 510)')
    parser.add_argument('--height', type=int, default=720,
                        help='Wysokosc szafki w mm (default: 720)')
    parser.add_argument('--drawers', nargs='+', default=['N', 'M', 'K'],
                        choices=['N', 'M', 'K', 'C', 'F'],
                        help='Typy szuflad od dolnej do gornej (default: N M K)')
    parser.add_argument('--side', default='left', choices=['left', 'right'],
                        help='Strona boku: left/right (default: left)')
    parser.add_argument('--output', type=str, default=None,
                        help='Katalog wyjsciowy')
    
    args = parser.parse_args()
    
    output_dir = args.output or Path(__file__).parent.parent / 'output'
    
    generate_side_panel_dxf(
        cabinet_depth=args.depth,
        cabinet_height=args.height,
        drawer_types=args.drawers,
        output_dir=output_dir,
        side=args.side,
    )


if __name__ == '__main__':
    main()
