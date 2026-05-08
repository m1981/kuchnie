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

        # Global Material Switcher
        rx.vstack(
            rx.text("GLOBAL FRONTS", font_size="0.6rem", font_weight="bold", color="#64748b", letter_spacing="0.05em"),
            rx.select(
                KitchenState.materials,
                value=KitchenState.global_front_mat_name,
                on_change=KitchenState.change_global_front,
                width="250px",
                color_scheme="blue"
            ),
            spacing="1",
            margin_right="2rem"
        ),

        rx.vstack(
            rx.text("TOTAL ESTIMATE", font_size="0.75rem", font_weight="bold", color="#64748b", text_align="right", letter_spacing="0.05em"),
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
    is_selected = KitchenState.selected_cabinet_id == cabinet.id

    # UX: Visual styling for Custom Materials
    # If custom, use a warm amber tint. If default, use clean white.
    front_bg = rx.cond(cabinet.has_custom_front, "#fef3c7", "#ffffff")
    front_border = rx.cond(cabinet.has_custom_front, "1px solid #f59e0b", "1px solid #94a3b8")

    # UX: Reusable Door Component (with Handle)
    def render_door(index: int) -> rx.Component:
        return rx.box(
            # The Handle (Vertical line on the side)
            rx.box(width="4px", height="20px", bg="#cbd5e1", border_radius="2px", position="absolute", top="50%",
                   right="4px", transform="translateY(-50%)"),
            width="100%", height="100%", border=front_border, bg=front_bg, position="relative"
        )

    # UX: Reusable Drawer Component (with Handle)
    def render_drawer(index: int) -> rx.Component:
        return rx.box(
            # The Handle (Horizontal line in the middle)
            rx.box(width="30px", height="4px", bg="#cbd5e1", border_radius="2px", position="absolute", top="50%",
                   left="50%", transform="translate(-50%, -50%)"),
            width="100%", height="100%", border=front_border, bg=front_bg, position="relative"
        )

    return rx.vstack(
        # 1. Top Dimension
        rx.text(cabinet.width_label, font_size="0.7rem", color="#64748b", font_family="monospace", text_align="center",
                width="100%"),

        # 2. The Blueprint Box
        rx.box(
            # UX: Custom Material Badge (Top Left Corner)
            rx.cond(
                cabinet.has_custom_front,
                rx.icon(tag="palette", size=14, color="#d97706", position="absolute", top="4px", left="4px",
                        z_index="5"),
                rx.fragment()
            ),

            # Insides (Drawers, Doors, or Open Shelf)
            rx.cond(
                cabinet.drawers.length() > 0,
                # HAS DRAWERS
                rx.vstack(rx.foreach(cabinet.drawers, render_drawer), width="100%", height="100%", spacing="0",
                          position="absolute", top="0", left="0"),

                rx.cond(
                    cabinet.doors.length() > 0,
                    # HAS DOORS
                    rx.hstack(rx.foreach(cabinet.doors, render_door), width="100%", height="100%", spacing="0",
                              position="absolute", top="0", left="0"),

                    # OPEN SHELF (0 Doors, 0 Drawers)
                    # UX: Inset shadow and darker background creates the illusion of an empty cavity
                    rx.box(
                        width="100%", height="100%", bg="#e2e8f0",
                        box_shadow="inset 0 4px 10px rgba(0, 0, 0, 0.15)",
                        position="absolute", top="0", left="0"
                    )
                )
            ),

            # Arrows INSIDE the box (for moving)
            rx.hstack(
                rx.icon(tag="chevron-left", size=16, color="#0f172a", bg="rgba(255,255,255,0.8)", border_radius="sm",
                        cursor="pointer", _hover={"bg": "#e2e8f0"},
                        on_click=lambda: KitchenState.move_cabinet(cabinet.id, -1)),
                rx.spacer(),
                rx.icon(tag="chevron-right", size=16, color="#0f172a", bg="rgba(255,255,255,0.8)", border_radius="sm",
                        cursor="pointer", _hover={"bg": "#e2e8f0"},
                        on_click=lambda: KitchenState.move_cabinet(cabinet.id, 1)),
                width="100%", position="absolute", bottom="2px", padding_x="2px", z_index="10"
            ),

            width=cabinet.css_width,
            height=cabinet.css_height,
            bg="#f8fafc",
            position="relative",
            margin_right="-2px",
            transition="all 0.2s ease",
            cursor="pointer",

            # Highlight styling when selected
            border=rx.cond(is_selected, "2px solid #0284c7", "2px solid #334155"),
            box_shadow=rx.cond(is_selected, "0 0 0 4px rgba(2, 132, 199, 0.2)", "none"),
            z_index=rx.cond(is_selected, "10", "1"),

            # Click to select
            on_click=lambda: KitchenState.select_cabinet(cabinet.id),
        ),

        # 3. Bottom Labels (Fixed Height Pedestal)
        rx.vstack(
            rx.text(cabinet.name, font_size="0.7rem", font_weight="bold",
                    color=rx.cond(is_selected, "#0284c7", "#334155"), line_height="1.2", text_align="center"),
            rx.text("$" + cabinet.price.to_string(), font_size="0.7rem", color="#16a34a", font_family="monospace",
                    text_align="center"),
            spacing="1", width="100%", height="45px", justify_content="flex-start", align_items="center"
        ),

        width=cabinet.css_width, spacing="2", align_items="center", justify_content="flex-end",
    )


def main_canvas() -> rx.Component:
    return rx.box(
        rx.vstack(
            # TOP ROW: Wall Cabinets
            rx.hstack(
                rx.foreach(KitchenState.wall_cabinets, cabinet_2d_box),
                # Total Width Indicator for Wall Row
                rx.cond(
                    KitchenState.total_wall_width > 0,
                    rx.vstack(
                        rx.text("TOTAL WALL", font_size="0.6rem", color="#94a3b8", font_weight="bold"),
                        rx.text(KitchenState.total_wall_width.to_string() + "mm", font_size="1rem", color="#0f172a", font_family="monospace", font_weight="bold"),
                        padding_left="2rem", justify_content="flex-end", height="45px"
                    ),
                    rx.fragment()
                ),
                spacing="0", align_items="flex-end", padding_left="2rem"
            ),

            # THE BACKSPLASH GAP
            rx.box(height="60px", width="100%", border_bottom="1px dashed #cbd5e1"),

            # BOTTOM ROW: Base and Tall Cabinets
            rx.hstack(
                rx.foreach(KitchenState.base_cabinets, cabinet_2d_box),
                # Total Width Indicator for Base Row
                rx.cond(
                    KitchenState.total_base_width > 0,
                    rx.vstack(
                        rx.text("TOTAL BASE", font_size="0.6rem", color="#94a3b8", font_weight="bold"),
                        rx.text(KitchenState.total_base_width.to_string() + "mm", font_size="1rem", color="#0f172a", font_family="monospace", font_weight="bold"),
                        padding_left="2rem", justify_content="flex-end", height="45px"
                    ),
                    rx.fragment()
                ),
                spacing="0", align_items="flex-end", padding_left="2rem",
            ),

            spacing="0", align_items="flex-start", padding_top="2rem", padding_bottom="0"
        ),
        width="100%", overflow_x="auto", bg="#f1f5f9", border_bottom="2px solid #94a3b8"
    )


def action_bar() -> rx.Component:
    """Buttons to add new cabinets."""
    return rx.hstack(
        rx.button("+ Base Cabinet", on_click=lambda: KitchenState.add_cabinet("BASE"), color_scheme="blue", variant="outline", cursor="pointer"),
        rx.button("+ Wall Cabinet", on_click=lambda: KitchenState.add_cabinet("WALL"), color_scheme="blue", variant="outline", cursor="pointer"),
        rx.button("+ Tall Unit", on_click=lambda: KitchenState.add_cabinet("TALL"), color_scheme="blue", variant="outline", cursor="pointer"),
        padding="2rem", width="100%", justify_content="center", bg="white", border_top="1px solid #e2e8f0"
    )


def form_input_group(label: str, field_name: str, default_val: str) -> rx.Component:
    """UX: Reusable component that pairs an input with its specific inline warning."""
    return rx.vstack(
        rx.text(label, font_size="0.75rem", font_weight="bold", color="#64748b"),
        rx.input(
            default_value=default_val,
            on_blur=lambda v: KitchenState.update_cabinet_field(field_name, v),
            width="100%"
        ),
        # UX: Inline warning text that only appears if this specific field has an error
        rx.cond(
            KitchenState.field_warnings.contains(field_name),
            rx.text(
                KitchenState.field_warnings[field_name],
                color="#ef4444", # Red color for visibility
                font_size="0.65rem",
                margin_top="-0.25rem"
            ),
            rx.fragment()
        ),
        width="100%",
        spacing="1"
    )


def sidebar() -> rx.Component:
    """The Right Panel Inspector."""
    return rx.cond(
        KitchenState.selected_cabinet_id != None,
        rx.vstack(
            # Header
            rx.hstack(
                rx.heading("Cabinet Details", size="4", color="#0f172a"),
                rx.spacer(),
                rx.icon(tag="x", cursor="pointer", color="#64748b", _hover={"color": "#0f172a"}, on_click=KitchenState.close_sidebar),
                width="100%", align_items="center", padding_bottom="1rem", border_bottom="1px solid #e2e8f0"
            ),

            # INPUT FORM (Now using the UX-optimized component)
            rx.vstack(
                form_input_group("Name", "name", KitchenState.selected_cabinet.name),
                form_input_group("Width (mm)", "width_mm", KitchenState.selected_cabinet.width_mm.to_string()),
                form_input_group("Height (mm)", "height_mm", KitchenState.selected_cabinet.height_mm.to_string()),
                form_input_group("Depth (mm)", "depth_mm", KitchenState.selected_cabinet.depth_mm.to_string()),

                rx.hstack(
                    form_input_group("Doors", "door_count", KitchenState.selected_cabinet.door_count.to_string()),
                    form_input_group("Drawers", "drawer_count", KitchenState.selected_cabinet.drawer_count.to_string()),
                    width="100%", spacing="4"
                ),

                width="100%", align_items="flex-start", spacing="3", margin_top="1rem",
                # Forces the inputs to reset their default_value when you click a new cabinet or math changes
                key=KitchenState.selected_cabinet_id.to_string() + "_" + KitchenState.selected_cabinet.price.to_string()
            ),

            rx.divider(margin_y="1rem"),

            # Local Material Override
            rx.text("Custom Front Material", font_size="0.75rem", font_weight="bold", color="#64748b"),
            rx.select(
                KitchenState.local_material_options,
                value=KitchenState.local_front_mat_name,
                on_change=KitchenState.change_local_front,
                width="100%",
                color_scheme="amber"
            ),

            rx.spacer(),

            # Delete Button
            rx.button(
                rx.icon(tag="trash-2", size=16), "Delete Cabinet",
                color_scheme="red", variant="soft", width="100%", cursor="pointer",
                on_click=KitchenState.delete_cabinet
            ),

            width="350px", height="calc(100vh - 85px)", bg="white", border_left="1px solid #e2e8f0",
            padding="1.5rem", align_items="flex-start", position="sticky", top="0"
        ),
        rx.fragment()
    )


def index() -> rx.Component:
    return rx.vstack(
        top_bar(),

        # Horizontal layout for Canvas + Sidebar
        rx.hstack(
            # Left Side: Canvas and Action Bar
            rx.vstack(
                main_canvas(),
                action_bar(),
                width="100%", flex="1", spacing="0"
            ),

            # Right Side: The Sidebar
            sidebar(),

            width="100%", align_items="flex-start", spacing="0"
        ),

        width="100%", min_height="100vh", bg="#f8fafc", spacing="0"
    )


# Initialize the app and add the page
app = rx.App()
app.add_page(index, on_load=KitchenState.load_mock_data)