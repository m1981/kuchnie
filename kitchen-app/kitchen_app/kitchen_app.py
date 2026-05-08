# kitchen_app/kitchen_app.py
import reflex as rx
from .state import KitchenState, CabinetUI

def top_bar() -> rx.Component:
    """The Deal Closer Header."""
    return rx.hstack(
        rx.vstack(
            rx.text("PROJECT", font_size="0.75rem", font_weight="bold", color="#64748b", letter_spacing="0.05em"),
            rx.heading(KitchenState.project_name, size="6", color="#0f172a"),
            spacing="0",
        ),
        rx.spacer(),
        rx.vstack(
            rx.text("TOTAL ESTIMATE", font_size="0.75rem", font_weight="bold", color="#64748b", text_align="right", letter_spacing="0.05em"),
            # Reflex string concatenation for Vars
            rx.text("$" + KitchenState.total_price.to_string(), font_size="2.5rem", font_weight="900", color="#16a34a", font_family="monospace"),
            spacing="0",
            align_items="flex-end"
        ),
        width="100%",
        padding="1.5rem 2rem",
        bg="white",
        border_bottom="1px solid #e2e8f0",
        align_items="center"
    )


def cabinet_2d_box(cabinet: CabinetUI) -> rx.Component:
    return rx.vstack(
        # 1. Top Dimension (Normal Flow)
        rx.text(cabinet.width_label, font_size="0.7rem", color="#64748b", font_family="monospace", text_align="center", width="100%"),

        # The Blueprint Box
        rx.box(
            # Insides (Doors/Drawers)
            rx.cond(
                cabinet.drawers.length() > 0,
                rx.vstack(rx.foreach(cabinet.drawers,
                                     lambda _: rx.box(width="100%", height="100%", border="1px solid #94a3b8")),
                          width="100%", height="100%", spacing="0", position="absolute", top="0", left="0"),
                rx.cond(
                    cabinet.doors.length() > 0,
                    rx.hstack(rx.foreach(cabinet.doors,
                                         lambda _: rx.box(width="100%", height="100%", border="1px solid #94a3b8")),
                              width="100%", height="100%", spacing="0", position="absolute", top="0", left="0"),
                    rx.fragment()
                )
            ),

            # NEW: Move Arrows INSIDE the box at the bottom
            rx.hstack(
                rx.icon(tag="chevron-left", size=16, color="#0f172a", bg="rgba(255,255,255,0.8)", border_radius="sm",
                        cursor="pointer", _hover={"bg": "#e2e8f0"},
                        on_click=lambda: KitchenState.move_cabinet(cabinet.id, -1)),
                rx.spacer(),
                rx.icon(tag="chevron-right", size=16, color="#0f172a", bg="rgba(255,255,255,0.8)", border_radius="sm",
                        cursor="pointer", _hover={"bg": "#e2e8f0"},
                        on_click=lambda: KitchenState.move_cabinet(cabinet.id, 1)),
                width="100%", position="absolute", bottom="2px", padding_x="2px"
            ),

            width=cabinet.css_width,
            height=cabinet.css_height,
            border="2px solid #334155",
            bg="#f8fafc",
            position="relative",
            margin_right="-2px",  # Prevents double borders when sticking together
            _hover={"bg": "#e0f2fe", "border_color": "#0284c7"},
            transition="all 0.2s ease",
        ),

        # 3. Bottom Labels (Normal Flow, Fixed Height Pedestal)
        rx.vstack(
            rx.text(cabinet.name, font_size="0.7rem", font_weight="bold", color="#334155", line_height="1.2", text_align="center"),
            rx.text("$" + cabinet.price.to_string(), font_size="0.7rem", color="#16a34a", font_family="monospace", text_align="center"),
            spacing="1",
            width="100%",
            height="45px", # <--- CRITICAL: Reserves exact space so flex-end aligns the boxes perfectly
            justify_content="flex-start",
            align_items="center"
        ),

        # STRICT WIDTH ENFORCEMENT
        width=cabinet.css_width,
        spacing="2", # Small natural gap between text and box
        align_items="center",
        justify_content="flex-end", # Pushes the box down to the floor line
    )


def main_canvas() -> rx.Component:
    return rx.box(
        rx.vstack(
            # TOP ROW: Wall Cabinets
            rx.hstack(
                rx.foreach(KitchenState.wall_cabinets, cabinet_2d_box),
                # NEW: Total Width Indicator for Wall Row
                rx.cond(
                    KitchenState.total_wall_width > 0,
                    rx.vstack(
                        rx.text("TOTAL WALL", font_size="0.6rem", color="#94a3b8", font_weight="bold"),
                        rx.text(KitchenState.total_wall_width.to_string() + "mm", font_size="1rem", color="#0f172a",
                                font_family="monospace", font_weight="bold"),
                        padding_left="2rem",
                        justify_content="flex-end",
                        height="45px" # Matches the text pedestal height of the cabinets!
                    ),
                    rx.fragment()
                ),
                spacing="0", align_items="flex-end", padding_left="2rem"
            ),

            # THE BACKSPLASH GAP (Now acts as a proper spacer in the normal flow)
            rx.box(height="60px", width="100%", border_bottom="1px dashed #cbd5e1"),

            # BOTTOM ROW: Base and Tall Cabinets
            rx.hstack(
                rx.foreach(KitchenState.base_cabinets, cabinet_2d_box),
                # NEW: Total Width Indicator for Base Row
                rx.cond(
                    KitchenState.total_base_width > 0,
                    rx.vstack(
                        rx.text("TOTAL BASE", font_size="0.6rem", color="#94a3b8", font_weight="bold"),
                        rx.text(KitchenState.total_base_width.to_string() + "mm", font_size="1rem", color="#0f172a",
                                font_family="monospace", font_weight="bold"),
                        padding_left="2rem",
                        justify_content="flex-end",
                        height="45px" # Matches the text pedestal height of the cabinets!
                    ),
                    rx.fragment()
                ),
                spacing="0", align_items="flex-end", padding_left="2rem",
            ),

            spacing="0",
            align_items="flex-start",
            padding_top="2rem",
            padding_bottom="0"
        ),
        width="100%", overflow_x="auto", bg="#f1f5f9", border_bottom="2px solid #94a3b8"
    )

# In kitchen_app/kitchen_app.py

def action_bar() -> rx.Component:
    """Buttons to add new cabinets."""
    return rx.hstack(
        # Use lambda to pass the specific cabinet type to the backend
        rx.button("+ Base Cabinet", on_click=lambda: KitchenState.add_cabinet("BASE"), color_scheme="blue", variant="outline", cursor="pointer"),
        rx.button("+ Wall Cabinet", on_click=lambda: KitchenState.add_cabinet("WALL"), color_scheme="blue", variant="outline", cursor="pointer"),
        rx.button("+ Tall Unit", on_click=lambda: KitchenState.add_cabinet("TALL"), color_scheme="blue", variant="outline", cursor="pointer"),
        padding="2rem",
        width="100%",
        justify_content="center",
        bg="white",
        border_top="1px solid #e2e8f0"
    )

def index() -> rx.Component:
    return rx.vstack(
        top_bar(),
        main_canvas(),
        action_bar(), # <-- Added the action bar here
        width="100%",
        min_height="100vh",
        bg="#f8fafc",
        spacing="0"
    )


# Initialize the app and add the page
app = rx.App()
app.add_page(index, on_load=KitchenState.load_mock_data)