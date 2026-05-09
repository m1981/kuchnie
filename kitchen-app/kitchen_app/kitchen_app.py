# kitchen_app/kitchen_app.py
import reflex as rx
from .state import KitchenState, CabinetUI, CostTraceLineUI

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

        rx.button(
            rx.icon(tag="receipt-text", size=16),
            "Trace Costs",
            on_click=KitchenState.open_project_cost_trace,
            color_scheme="gray",
            variant="soft",
            cursor="pointer",
            margin_right="1rem",
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


def cost_trace_row(line: CostTraceLineUI) -> rx.Component:
    return rx.hstack(
        rx.text(line.category, width="85px", font_size="0.72rem", color="#475569", font_weight="bold"),
        rx.vstack(
            rx.text(line.label, font_size="0.78rem", color="#0f172a", font_weight="600", line_height="1.2"),
            rx.text(line.formula, font_size="0.7rem", color="#64748b", font_family="monospace", line_height="1.2"),
            spacing="1",
            align_items="flex-start",
            flex="1",
            min_width="240px",
        ),
        rx.text(line.quantity_label, width="90px", font_size="0.72rem", color="#334155", text_align="right", font_family="monospace"),
        rx.text(line.unit_price_label, width="80px", font_size="0.72rem", color="#334155", text_align="right", font_family="monospace"),
        rx.text(line.waste_label, width="60px", font_size="0.72rem", color="#334155", text_align="right", font_family="monospace"),
        rx.text(line.subtotal_label, width="90px", font_size="0.78rem", color="#16a34a", text_align="right", font_family="monospace", font_weight="bold"),
        width="100%",
        padding="0.65rem 0",
        border_bottom="1px solid #e2e8f0",
        align_items="center",
        spacing="3",
    )


def cost_trace_panel() -> rx.Component:
    return rx.cond(
        KitchenState.cost_trace_open,
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.text("COST TRACE", font_size="0.68rem", color="#64748b", font_weight="bold", letter_spacing="0.05em"),
                        rx.heading(KitchenState.cost_trace_title, size="5", color="#0f172a"),
                        rx.text(KitchenState.cost_trace_summary, font_size="0.78rem", color="#64748b"),
                        spacing="1",
                        align_items="flex-start",
                    ),
                    rx.spacer(),
                    rx.icon(tag="x", cursor="pointer", color="#64748b", _hover={"color": "#0f172a"}, on_click=KitchenState.close_cost_trace),
                    width="100%",
                    align_items="flex-start",
                    padding_bottom="1rem",
                    border_bottom="1px solid #cbd5e1",
                ),
                rx.hstack(
                    rx.text("TYPE", width="85px", font_size="0.65rem", color="#64748b", font_weight="bold"),
                    rx.text("CALCULATION", flex="1", min_width="240px", font_size="0.65rem", color="#64748b", font_weight="bold"),
                    rx.text("QTY", width="90px", font_size="0.65rem", color="#64748b", font_weight="bold", text_align="right"),
                    rx.text("RATE", width="80px", font_size="0.65rem", color="#64748b", font_weight="bold", text_align="right"),
                    rx.text("WASTE", width="60px", font_size="0.65rem", color="#64748b", font_weight="bold", text_align="right"),
                    rx.text("COST", width="90px", font_size="0.65rem", color="#64748b", font_weight="bold", text_align="right"),
                    width="100%",
                    padding_top="0.5rem",
                    spacing="3",
                ),
                rx.box(
                    rx.foreach(KitchenState.cost_trace_lines, cost_trace_row),
                    width="100%",
                    max_height="55vh",
                    overflow_y="auto",
                ),
                rx.hstack(
                    rx.text("Traced total", font_size="0.85rem", color="#334155", font_weight="bold"),
                    rx.spacer(),
                    rx.text("$" + KitchenState.cost_trace_total.to_string(), font_size="1.4rem", color="#16a34a", font_weight="900", font_family="monospace"),
                    width="100%",
                    padding_top="1rem",
                ),
                width="min(960px, calc(100vw - 3rem))",
                max_height="calc(100vh - 4rem)",
                bg="white",
                border="1px solid #cbd5e1",
                border_radius="8px",
                box_shadow="0 24px 80px rgba(15, 23, 42, 0.28)",
                padding="1.25rem",
                spacing="3",
                align_items="flex-start",
            ),
            position="fixed",
            inset="0",
            bg="rgba(15, 23, 42, 0.35)",
            z_index="100",
            display="flex",
            align_items="center",
            justify_content="center",
            padding="1.5rem",
        ),
        rx.fragment(),
    )


def cabinet_2d_box(cabinet: CabinetUI) -> rx.Component:
    is_selected = KitchenState.selected_cabinet_id == cabinet.id

    # UX: Visual styling for Custom Materials
    front_bg = rx.cond(cabinet.has_custom_front, "#fef3c7", "#ffffff")
    front_border = rx.cond(cabinet.has_custom_front, "1px solid #f59e0b", "1px solid #94a3b8")
    handle_color = rx.cond(cabinet.has_custom_front, "#d97706", "#94a3b8")  # Darker handles for contrast

    # UX: Symmetrical Doors
    def render_door(index: int) -> rx.Component:
        return rx.box(
            # The Handle (Dynamically positioned based on odd/even index)
            rx.box(
                width="4px", height="20px", bg=handle_color, border_radius="2px",
                position="absolute", top="50%", transform="translateY(-50%)",
                # If index is even (0), handle is on the right. If odd (1), handle is on the left.
                right=rx.cond(index % 2 == 0, "4px", "auto"),
                left=rx.cond(index % 2 == 0, "auto", "4px")
            ),
            width="100%", height="100%", border=front_border, bg=front_bg, position="relative"
        )

    def render_drawer(index: int) -> rx.Component:
        return rx.box(
            # The Handle (Centered)
            rx.box(
                width="30px", height="4px", bg=handle_color, border_radius="2px",
                position="absolute", top="50%", left="50%", transform="translate(-50%, -50%)"
            ),
            width="100%", height="100%", border=front_border, bg=front_bg, position="relative"
        )

    return rx.vstack(
        # 1. Top Dimension
        rx.text(cabinet.width_label, font_size="0.7rem", color="#64748b", font_family="monospace", text_align="center",
                width="100%"),

        # 2. The Blueprint Box
        rx.box(
            # UX: Custom Material Badge
            rx.cond(
                cabinet.has_custom_front,
                rx.icon(tag="palette", size=14, color="#d97706", position="absolute", top="4px", left="4px",
                        z_index="5"),
                rx.fragment()
            ),

            # CAD Elevation Logic: Stack Doors on top, Drawers on bottom
            rx.cond(
                (cabinet.doors.length() == 0) & (cabinet.drawers.length() == 0),

                # STATE A: OPEN SHELF
                rx.box(
                    width="100%", height="100%", bg="#e2e8f0",
                    box_shadow="inset 0 4px 10px rgba(0, 0, 0, 0.15)",
                    position="absolute", top="0", left="0"
                ),

                # STATE B: DOORS AND/OR DRAWERS
                rx.vstack(
                    # Top Half: Doors
                    rx.cond(
                        cabinet.doors.length() > 0,
                        rx.hstack(rx.foreach(cabinet.doors, render_door), width="100%", flex="1", spacing="0"),
                        rx.fragment()
                    ),
                    # Bottom Half: Drawers
                    rx.cond(
                        cabinet.drawers.length() > 0,
                        rx.vstack(rx.foreach(cabinet.drawers, render_drawer), width="100%", flex="1", spacing="0"),
                        rx.fragment()
                    ),
                    width="100%", height="100%", spacing="0", position="absolute", top="0", left="0"
                )
            ),

            # Arrows INSIDE the box
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

            on_click=lambda: KitchenState.select_cabinet(cabinet.id),
        ),

        # 3. Bottom Labels
        rx.vstack(
            rx.text(cabinet.name, font_size="0.7rem", font_weight="bold",
                    color=rx.cond(is_selected, "#0284c7", "#334155"), line_height="1.2", text_align="center"),
            rx.text("$" + cabinet.price.to_string(), font_size="0.7rem", color="#16a34a", font_family="monospace",
                    text_align="center"),
            spacing="1", width="100%", height="45px", justify_content="flex-start", align_items="center"
        ),

        width=cabinet.css_width, spacing="2", align_items="center", justify_content="flex-end",
    )


def module_front(cabinet: CabinetUI) -> rx.Component:
    front_bg = rx.cond(cabinet.has_custom_front, "#fef3c7", "#f8fafc")
    front_border = rx.cond(cabinet.has_custom_front, "1px solid #d97706", "1px solid #94a3b8")
    handle_color = rx.cond(cabinet.has_custom_front, "#d97706", "#94a3b8")

    def render_door(index: int) -> rx.Component:
        return rx.box(
            rx.box(
                width="4px", height="22px", bg=handle_color, border_radius="2px",
                position="absolute", top="50%", transform="translateY(-50%)",
                right=rx.cond(index % 2 == 0, "8px", "auto"),
                left=rx.cond(index % 2 == 0, "auto", "8px"),
            ),
            width="100%", height="100%", border=front_border, bg=front_bg, position="relative",
        )

    def render_drawer(index: int) -> rx.Component:
        return rx.box(
            rx.box(
                width="34px", height="4px", bg=handle_color, border_radius="2px",
                position="absolute", top="14px", left="50%", transform="translateX(-50%)",
            ),
            width="100%", height="100%", border=front_border, bg=front_bg, position="relative",
        )

    return rx.cond(
        cabinet.is_appliance & (cabinet.is_hood == False) & (cabinet.is_cooktop == False),
        rx.vstack(
            rx.box(width="100%", height="18%", bg="#e5e7eb", border_bottom="1px solid #94a3b8"),
            rx.box(
                rx.cond(
                    cabinet.module_kind == "OVEN",
                    rx.box(width="72%", height="45%", bg="#111827", margin="18% auto 0", border_radius="3px"),
                    rx.box(width="82%", height="4px", bg="#94a3b8", margin="16px auto 0", border_radius="2px"),
                ),
                width="100%", flex="1", bg="#f8fafc",
            ),
            width="100%", height="100%", border="2px solid #334155", spacing="0", bg="#f8fafc",
        ),
        rx.cond(
            cabinet.drawers.length() > 0,
            rx.vstack(
                rx.foreach(cabinet.drawers, render_drawer),
                width="100%", height="100%", spacing="0",
            ),
            rx.cond(
                cabinet.doors.length() > 0,
                rx.hstack(rx.foreach(cabinet.doors, render_door), width="100%", height="100%", spacing="0"),
                rx.box(
                    width="100%", height="100%", bg="#eef2f7",
                    box_shadow="inset 0 6px 14px rgba(15, 23, 42, 0.14)",
                    border="2px solid #334155",
                ),
            ),
        ),
    )


def plan_module_box(cabinet: CabinetUI) -> rx.Component:
    is_selected = KitchenState.selected_cabinet_id == cabinet.id

    return rx.box(
        rx.cond(
            cabinet.is_countertop,
            rx.box(
                width="100%", height="100%", bg="#9ca3af", border="1px solid #64748b",
                box_shadow="inset 0 1px 0 rgba(255,255,255,0.45)",
            ),
            rx.cond(
                cabinet.is_sink,
                rx.box(
                    rx.box(
                        width="68%", height="72%", border="2px solid #cbd5e1", bg="#f8fafc",
                        border_radius="5px", margin="8% auto 0",
                        box_shadow="inset 0 5px 12px rgba(15,23,42,0.12)",
                    ),
                    width="100%", height="100%", bg="transparent",
                ),
                rx.cond(
                    cabinet.is_faucet,
                    rx.box(
                        rx.box(width="7px", height="72%", bg="#94a3b8", border_radius="4px", position="absolute", bottom="0", left="45%"),
                        rx.box(width="48px", height="48px", border_top="7px solid #94a3b8", border_right="7px solid #94a3b8", border_radius="0 22px 0 0", position="absolute", top="4px", left="43%"),
                        width="100%", height="100%", position="relative",
                    ),
                    rx.cond(
                        cabinet.is_cooktop,
                        rx.box(
                            width="100%", height="100%", bg="#111827", border="1px solid #020617",
                            box_shadow="inset 0 0 0 2px rgba(255,255,255,0.05)",
                        ),
                        rx.cond(
                            cabinet.is_hood,
                            rx.box(
                                rx.box(width="22%", height="58%", bg="#e5e7eb", border="1px solid #94a3b8", margin="0 auto"),
                                rx.box(width="86%", height="20%", bg="#e5e7eb", border="1px solid #94a3b8", margin="0 auto", transform="skewX(-18deg)"),
                                rx.box(width="72%", height="8px", bg="#94a3b8", margin="0 auto", border_radius="0 0 3px 3px"),
                                width="100%", height="100%", padding_top="3px",
                            ),
                            module_front(cabinet),
                        ),
                    ),
                ),
            ),
        ),
        rx.cond(
            cabinet.show_canvas_label,
            rx.box(
                rx.text(cabinet.width_label, font_size="0.62rem", color="#475569", font_family="monospace"),
                rx.text(cabinet.module_label, font_size="0.58rem", color="#334155", font_weight="bold", line_height="1.05"),
                position="absolute", left="2px", bottom="-31px", width="100%", text_align="center",
            ),
            rx.fragment(),
        ),
        rx.cond(
            is_selected & cabinet.is_reorderable,
            rx.hstack(
                rx.icon(
                    tag="chevron-left", size=16, color="#0f172a", bg="rgba(255,255,255,0.92)",
                    border="1px solid #cbd5e1", border_radius="4px", cursor="pointer",
                    _hover={"bg": "#e2e8f0"},
                    on_click=lambda: KitchenState.move_cabinet(cabinet.id, -1),
                ),
                rx.icon(
                    tag="chevron-right", size=16, color="#0f172a", bg="rgba(255,255,255,0.92)",
                    border="1px solid #cbd5e1", border_radius="4px", cursor="pointer",
                    _hover={"bg": "#e2e8f0"},
                    on_click=lambda: KitchenState.move_cabinet(cabinet.id, 1),
                ),
                position="absolute",
                left="50%",
                top="-28px",
                transform="translateX(-50%)",
                spacing="1",
                z_index="30",
            ),
            rx.fragment(),
        ),
        position="absolute",
        left=cabinet.css_left,
        bottom=cabinet.css_bottom,
        width=cabinet.css_width,
        height=cabinet.css_height,
        cursor="pointer",
        border=rx.cond(is_selected, "2px solid #0284c7", "0"),
        box_shadow=rx.cond(is_selected, "0 0 0 4px rgba(2, 132, 199, 0.2)", "none"),
        z_index=rx.cond(is_selected, "20", rx.cond(cabinet.is_countertop, "8", rx.cond(cabinet.is_sink | cabinet.is_faucet | cabinet.is_cooktop, "12", "10"))),
        on_click=lambda: KitchenState.select_cabinet(cabinet.id),
    )


def main_canvas() -> rx.Component:
    return rx.box(
        rx.box(
            rx.hstack(
                rx.text("0", font_size="0.65rem", color="#64748b", font_family="monospace"),
                rx.spacer(),
                rx.text(KitchenState.canvas_width_label, font_size="0.65rem", color="#64748b", font_family="monospace"),
                position="absolute", top="-24px", left="0", width=KitchenState.canvas_css_width,
            ),
            rx.vstack(
                rx.text(KitchenState.canvas_height_label, font_size="0.65rem", color="#64748b", font_family="monospace"),
                rx.spacer(),
                rx.text("floor", font_size="0.65rem", color="#64748b", font_family="monospace"),
                position="absolute", right="-54px", top="0", height=KitchenState.canvas_css_height,
            ),
            rx.box(position="absolute", left="0", bottom="18px", width="100%", height="2px", bg="#64748b"),
            rx.box(position="absolute", left="0", bottom="196px", width="100%", height="1px", border_top="1px dashed #94a3b8"),
            rx.foreach(KitchenState.plan_modules, plan_module_box),
            position="relative",
            width=KitchenState.canvas_css_width,
            height=KitchenState.canvas_css_height,
            margin="3rem 5rem 4rem 2rem",
            bg="#f8fafc",
            border="1px solid #94a3b8",
            background_image="linear-gradient(#e2e8f0 1px, transparent 1px), linear-gradient(90deg, #e2e8f0 1px, transparent 1px)",
            background_size="40px 40px",
        ),
        width="100%", overflow_x="auto", bg="#eef2f7", border_bottom="2px solid #94a3b8"
    )


def action_bar() -> rx.Component:
    """Buttons to add new cabinets."""
    return rx.hstack(
        rx.button(rx.icon(tag="layout-template", size=16), "Reference Layout", on_click=KitchenState.load_ikea_layout, color_scheme="green", variant="solid", cursor="pointer"),
        rx.button(rx.icon(tag="eraser", size=16), "Clear", on_click=KitchenState.clear_layout, color_scheme="gray", variant="outline", cursor="pointer"),
        rx.button(rx.icon(tag="archive", size=16), "Base", on_click=lambda: KitchenState.add_cabinet("BASE"), color_scheme="blue", variant="outline", cursor="pointer"),
        rx.button(rx.icon(tag="panel-top", size=16), "Wall", on_click=lambda: KitchenState.add_cabinet("WALL"), color_scheme="blue", variant="outline", cursor="pointer"),
        rx.button(rx.icon(tag="columns-3", size=16), "Tall", on_click=lambda: KitchenState.add_cabinet("TALL"), color_scheme="blue", variant="outline", cursor="pointer"),
        rx.menu.root(
            rx.menu.trigger(
                rx.button(rx.icon(tag="plus", size=16), "Equipment", color_scheme="gray", variant="soft", cursor="pointer")
            ),
            rx.menu.content(
                rx.menu.item("Drawer Base", on_click=lambda: KitchenState.add_equipment("Drawer Base")),
                rx.menu.item("Sink Base", on_click=lambda: KitchenState.add_equipment("Sink Base")),
                rx.menu.item("Dishwasher", on_click=lambda: KitchenState.add_equipment("Dishwasher")),
                rx.menu.item("Oven", on_click=lambda: KitchenState.add_equipment("Oven")),
                rx.menu.item("Cooktop", on_click=lambda: KitchenState.add_equipment("Cooktop")),
                rx.menu.item("Filler", on_click=lambda: KitchenState.add_equipment("Filler")),
                rx.menu.item("Side Panel", on_click=lambda: KitchenState.add_equipment("Side Panel")),
                rx.menu.item("Countertop", on_click=lambda: KitchenState.add_equipment("Countertop")),
                rx.menu.item("Sink", on_click=lambda: KitchenState.add_equipment("Sink")),
                rx.menu.item("Faucet", on_click=lambda: KitchenState.add_equipment("Faucet")),
                rx.menu.item("Wall Cabinet 400", on_click=lambda: KitchenState.add_equipment("Wall Cabinet 400")),
                rx.menu.item("Wall Cabinet 800", on_click=lambda: KitchenState.add_equipment("Wall Cabinet 800")),
                rx.menu.item("Hood", on_click=lambda: KitchenState.add_equipment("Hood")),
            ),
        ),
        padding="1.25rem", width="100%", justify_content="center", bg="white", border_top="1px solid #e2e8f0", spacing="3"
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
            rx.hstack(
                rx.text(KitchenState.selected_cabinet.module_label, font_size="0.7rem", color="#0f172a", font_weight="bold"),
                rx.spacer(),
                rx.text("$" + KitchenState.selected_cabinet.price.to_string(), font_size="0.7rem", color="#16a34a", font_family="monospace", font_weight="bold"),
                width="100%",
                padding="0.55rem 0.7rem",
                bg="#f8fafc",
                border="1px solid #e2e8f0",
                border_radius="6px",
            ),
            rx.hstack(
                rx.button(
                    rx.icon(tag="chevron-left", size=16), "Move left",
                    on_click=lambda: KitchenState.move_selected_cabinet(-1),
                    color_scheme="gray", variant="soft", cursor="pointer", flex="1", color="#334155",
                ),
                rx.button(
                    "Move right", rx.icon(tag="chevron-right", size=16),
                    on_click=lambda: KitchenState.move_selected_cabinet(1),
                    color_scheme="gray", variant="soft", cursor="pointer", flex="1", color="#334155",
                ),
                width="100%",
                spacing="3",
                display=rx.cond(KitchenState.selected_cabinet.is_reorderable, "flex", "none"),
            ),

            # INPUT FORM (Now using the UX-optimized component)
            rx.vstack(
                form_input_group("Name", "name", KitchenState.selected_cabinet.name),
                rx.cond(
                    KitchenState.selected_cabinet.is_reorderable,
                    rx.fragment(),
                    rx.hstack(
                        form_input_group("X (mm)", "x_mm", KitchenState.selected_cabinet.x_mm.to_string()),
                        form_input_group("Y (mm)", "y_mm", KitchenState.selected_cabinet.y_mm.to_string()),
                        width="100%", spacing="4"
                    ),
                ),
                form_input_group("Width (mm)", "width_mm", KitchenState.selected_cabinet.width_mm.to_string()),
                form_input_group("Height (mm)", "height_mm", KitchenState.selected_cabinet.height_mm.to_string()),
                form_input_group("Depth (mm)", "depth_mm", KitchenState.selected_cabinet.depth_mm.to_string()),

                rx.cond(
                    KitchenState.selected_cabinet.can_have_fronts,
                    rx.hstack(
                        form_input_group("Doors", "door_count", KitchenState.selected_cabinet.door_count.to_string()),
                        form_input_group("Drawers", "drawer_count", KitchenState.selected_cabinet.drawer_count.to_string()),
                        width="100%", spacing="4"
                    ),
                    form_input_group("Equipment Price", "equipment_price", KitchenState.selected_cabinet.equipment_price.to_string()),
                ),

                width="100%", align_items="flex-start", spacing="3", margin_top="1rem",
                # Forces the inputs to reset their default_value when you click a new cabinet or math changes
                key=(
                    KitchenState.selected_cabinet_id.to_string() + "_" +
                    KitchenState.selected_cabinet.x_mm.to_string() + "_" +
                    KitchenState.selected_cabinet.y_mm.to_string() + "_" +
                    KitchenState.selected_cabinet.width_mm.to_string() + "_" +
                    KitchenState.selected_cabinet.height_mm.to_string() + "_" +
                    KitchenState.selected_cabinet.price.to_string()
                )
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

            rx.button(
                rx.icon(tag="receipt-text", size=16), "Trace This Cabinet",
                color_scheme="gray", variant="soft", width="100%", cursor="pointer",
                on_click=KitchenState.open_selected_cabinet_cost_trace
            ),

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

        cost_trace_panel(),

        width="100%", min_height="100vh", bg="#f8fafc", spacing="0"
    )


# Initialize the app and add the page
app = rx.App()
app.add_page(index, on_load=KitchenState.load_mock_data)
