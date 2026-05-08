# kitchen_app/kitchen_app.py
import reflex as rx
from .state import KitchenState

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
            rx.text(f"${KitchenState.total_price}", font_size="2.5rem", font_weight="900", color="#16a34a", font_family="monospace"),
            spacing="0",
            align_items="flex-end"
        ),
        width="100%",
        padding="1.5rem 2rem",
        bg="white",
        border_bottom="1px solid #e2e8f0",
        align_items="center"
    )

def cabinet_2d_box(cabinet: dict) -> rx.Component:
    """Draws a single cabinet to scale using CSS."""
    # Scale: 10mm = 1px (e.g., 800mm = 80px)
    scaled_width = cabinet["width_mm"] / 10
    scaled_height = cabinet["height_mm"] / 10

    return rx.vstack(
        # Top Dimension Line
        rx.text(f"{cabinet['width_mm']}mm", font_size="0.7rem", color="#64748b", font_family="monospace"),
        
        # The Blueprint Box
        rx.box(
            width=f"{scaled_width}px",
            height=f"{scaled_height}px",
            border="2px solid #334155",
            bg="#f8fafc",
            position="relative",
            _hover={"bg": "#e0f2fe", "cursor": "pointer", "border_color": "#0284c7"},
            transition="all 0.2s ease",
            
            # A subtle inner shadow to make it look like a physical box
            box_shadow="inset 0 0 10px rgba(0,0,0,0.05)"
        ),
        
        # Cabinet Info
        rx.text(cabinet["name"], font_size="0.8rem", font_weight="bold", color="#334155", margin_top="0.5rem"),
        rx.text(f"${cabinet['price']}", font_size="0.8rem", color="#16a34a", font_family="monospace"),
        
        align_items="center",
        # Push base cabinets to the bottom so they align with tall cabinets
        justify_content="flex-end", 
        height="250px" # Fixed height container so they align on the "floor"
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

def index() -> rx.Component:
    return rx.vstack(
        top_bar(),
        main_canvas(),
        width="100%",
        min_height="100vh",
        bg="#f8fafc",
        spacing="0"
    )

# Initialize the app and add the page
app = rx.App()
app.add_page(index, on_load=KitchenState.load_mock_data)