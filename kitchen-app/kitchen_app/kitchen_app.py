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
    """Draws a single cabinet to scale using CSS."""
    return rx.vstack(
        # Top Dimension Line
        rx.text(cabinet.width_label, font_size="0.7rem", color="#64748b", font_family="monospace"),
        
        # The Blueprint Box
        rx.box(
            rx.cond(
                cabinet.drawers.length() > 0,
                rx.vstack(
                    rx.foreach(cabinet.drawers, lambda _: rx.box(width="100%", height="100%", border="1px solid #94a3b8")),
                    # FIX: Force the stack to fill the parent box
                    width="100%", height="100%", spacing="0", position="absolute", top="0", left="0"
                ),
                rx.cond(
                    cabinet.doors.length() > 0,
                    rx.hstack(
                        rx.foreach(cabinet.doors, lambda _: rx.box(width="100%", height="100%", border="1px solid #94a3b8")),
                        # FIX: Force the stack to fill the parent box
                        width="100%", height="100%", spacing="0", position="absolute", top="0", left="0"
                    ),
                    rx.fragment()
                )
            ),
            width=cabinet.css_width,
            height=cabinet.css_height,
            border="2px solid #334155",
            bg="#f8fafc",
            position="relative",
            _hover={"bg": "#e0f2fe", "cursor": "pointer", "border_color": "#0284c7"},
            transition="all 0.2s ease",
            box_shadow="inset 0 0 10px rgba(0,0,0,0.05)"
        ),
        
        # Cabinet Info
        rx.text(cabinet.name, font_size="0.8rem", font_weight="bold", color="#334155", margin_top="0.5rem"),
        rx.text("$" + cabinet.price.to_string(), font_size="0.8rem", color="#16a34a", font_family="monospace"),
        
        align_items="center",
        justify_content="flex-end", 
        height="250px"
    )

def main_canvas() -> rx.Component:
    """The infinite scrolling wall."""
    return rx.box(
        rx.hstack(
            rx.foreach(
                KitchenState.cabinets_ui,
                cabinet_2d_box
            ),
            spacing="4",
            align_items="flex-end", # Align to the "floor"
            padding="2rem",
        ),
        width="100%",
        overflow_x="auto",
        bg="#f1f5f9",
        min_height="60vh",
        border_bottom="2px dashed #cbd5e1" # The "Floor" line
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