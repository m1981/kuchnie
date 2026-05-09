import reflex as rx
from .admin_state import AdminState, MaterialUI, HardwareUI, HardwareRuleUI


def material_row(material: MaterialUI) -> rx.Component:
    """Single row in materials table"""
    return rx.table.row(
        rx.table.cell(material.brand),
        rx.table.cell(material.name),
        rx.table.cell(f"{material.price_per_unit:,.2f} zł".replace(',', "'"), font_family="monospace"),
        rx.table.cell(material.unit),
        rx.table.cell(
            rx.hstack(
                rx.button(
                    rx.icon(tag="pencil", size=14),
                    on_click=lambda: AdminState.open_edit_material_form(material.id),
                    size="1",
                    variant="soft",
                    color_scheme="blue"
                ),
                rx.button(
                    rx.icon(tag="trash-2", size=14),
                    on_click=lambda: AdminState.delete_material(material.id),
                    size="1",
                    variant="soft",
                    color_scheme="red"
                ),
                spacing="2"
            )
        ),
    )


def hardware_row(hardware: HardwareUI) -> rx.Component:
    """Single row in hardware table"""
    return rx.table.row(
        rx.table.cell(hardware.brand),
        rx.table.cell(hardware.name),
        rx.table.cell(f"{hardware.price_per_set:,.2f} zł".replace(',', "'"), font_family="monospace"),
        rx.table.cell(
            rx.hstack(
                rx.button(
                    rx.icon(tag="pencil", size=14),
                    on_click=lambda: AdminState.open_edit_hardware_form(hardware.id),
                    size="1",
                    variant="soft",
                    color_scheme="blue"
                ),
                rx.button(
                    rx.icon(tag="trash-2", size=14),
                    on_click=lambda: AdminState.delete_hardware(hardware.id),
                    size="1",
                    variant="soft",
                    color_scheme="red"
                ),
                spacing="2"
            )
        ),
    )


def hardware_rule_row(rule: HardwareRuleUI) -> rx.Component:
    """Single row in hardware rules table"""
    return rx.table.row(
        rx.table.cell(
            rx.badge(rule.tag, color_scheme="blue", variant="soft")
        ),
        rx.table.cell(rule.hardware_name),
        rx.table.cell(f"{rule.qty_per_unit} {rule.unit}"),
        rx.table.cell(f"{rule.price:,.2f} zł".replace(',', "'"), font_family="monospace"),
        rx.table.cell(rule.description, font_size="0.75rem", color="#64748b"),
        rx.table.cell(
            rx.hstack(
                rx.button(
                    rx.icon(tag="pencil", size=14),
                    on_click=lambda: AdminState.open_edit_rule_form(rule.id),
                    size="1",
                    variant="soft",
                    color_scheme="blue"
                ),
                rx.button(
                    rx.icon(tag="trash-2", size=14),
                    on_click=lambda: AdminState.delete_hardware_rule(rule.id),
                    size="1",
                    variant="soft",
                    color_scheme="red"
                ),
                spacing="2"
            )
        ),
    )


def material_form() -> rx.Component:
    """Form for adding/editing materials"""
    return rx.cond(
        AdminState.show_material_form,
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.heading(
                        rx.cond(AdminState.is_editing, "Edit Material", "New Material"),
                        size="5"
                    ),
                    rx.spacer(),
                    rx.icon(
                        tag="x",
                        cursor="pointer",
                        on_click=AdminState.cancel_form
                    ),
                    width="100%",
                    align_items="center"
                ),
                
                rx.vstack(
                    rx.text("Brand", font_size="0.75rem", font_weight="bold"),
                    rx.input(
                        value=AdminState.edit_material_brand,
                        on_change=AdminState.set_edit_material_brand,
                        placeholder="e.g., Egger, Krono, Forner"
                    ),
                    width="100%",
                    spacing="1"
                ),
                
                rx.vstack(
                    rx.text("Name", font_size="0.75rem", font_weight="bold"),
                    rx.input(
                        value=AdminState.edit_material_name,
                        on_change=AdminState.set_edit_material_name,
                        placeholder="e.g., W1000 Premium White"
                    ),
                    width="100%",
                    spacing="1"
                ),
                
                rx.hstack(
                    rx.vstack(
                        rx.text("Price", font_size="0.75rem", font_weight="bold"),
                        rx.input(
                            type="number",
                            value=AdminState.edit_material_price.to_string(),
                            on_change=AdminState.set_edit_material_price,
                            placeholder="12.50"
                        ),
                        flex="1",
                        spacing="1"
                    ),
                    rx.vstack(
                        rx.text("Unit", font_size="0.75rem", font_weight="bold"),
                        rx.select(
                            ["m2", "lm", "pcs"],
                            value=AdminState.edit_material_unit,
                            on_change=AdminState.set_edit_material_unit,
                        ),
                        flex="1",
                        spacing="1"
                    ),
                    width="100%",
                    spacing="3"
                ),
                
                rx.vstack(
                    rx.text("Category", font_size="0.75rem", font_weight="bold"),
                    rx.select(
                        ["Board", "Panel", "Edge", "Countertop", "Back"],
                        value=AdminState.edit_material_category,
                        on_change=AdminState.set_edit_material_category,
                    ),
                    width="100%",
                    spacing="1"
                ),
                
                rx.hstack(
                    rx.button(
                        "Cancel",
                        on_click=AdminState.cancel_form,
                        variant="soft",
                        color_scheme="gray",
                        flex="1"
                    ),
                    rx.button(
                        rx.cond(AdminState.is_editing, "Update", "Create"),
                        on_click=AdminState.save_material,
                        variant="solid",
                        color_scheme="blue",
                        flex="1"
                    ),
                    width="100%",
                    spacing="3"
                ),
                
                width="100%",
                spacing="4",
                padding="1.5rem",
                bg="white",
                border="1px solid #e2e8f0",
                border_radius="8px",
                box_shadow="0 4px 12px rgba(0,0,0,0.1)"
            ),
            position="fixed",
            inset="0",
            bg="rgba(15, 23, 42, 0.35)",
            z_index="100",
            display="flex",
            align_items="center",
            justify_content="center",
            padding="1.5rem"
        ),
        rx.fragment()
    )


def hardware_form() -> rx.Component:
    """Form for adding/editing hardware"""
    return rx.cond(
        AdminState.show_hardware_form,
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.heading(
                        rx.cond(AdminState.is_editing, "Edit Hardware", "New Hardware"),
                        size="5"
                    ),
                    rx.spacer(),
                    rx.icon(
                        tag="x",
                        cursor="pointer",
                        on_click=AdminState.cancel_form
                    ),
                    width="100%",
                    align_items="center"
                ),
                
                rx.vstack(
                    rx.text("Brand", font_size="0.75rem", font_weight="bold"),
                    rx.input(
                        value=AdminState.edit_hardware_brand,
                        on_change=AdminState.set_edit_hardware_brand,
                        placeholder="e.g., Blum, Hettich"
                    ),
                    width="100%",
                    spacing="1"
                ),
                
                rx.vstack(
                    rx.text("Name", font_size="0.75rem", font_weight="bold"),
                    rx.input(
                        value=AdminState.edit_hardware_name,
                        on_change=AdminState.set_edit_hardware_name,
                        placeholder="e.g., Clip Top Hinge"
                    ),
                    width="100%",
                    spacing="1"
                ),
                
                rx.vstack(
                    rx.text("Price per Set (zł)", font_size="0.75rem", font_weight="bold"),
                    rx.input(
                        type="number",
                        value=AdminState.edit_hardware_price.to_string(),
                        on_change=AdminState.set_edit_hardware_price,
                        placeholder="2.50"
                    ),
                    width="100%",
                    spacing="1"
                ),
                
                rx.hstack(
                    rx.button(
                        "Cancel",
                        on_click=AdminState.cancel_form,
                        variant="soft",
                        color_scheme="gray",
                        flex="1"
                    ),
                    rx.button(
                        rx.cond(AdminState.is_editing, "Update", "Create"),
                        on_click=AdminState.save_hardware,
                        variant="solid",
                        color_scheme="blue",
                        flex="1"
                    ),
                    width="100%",
                    spacing="3"
                ),
                
                width="100%",
                spacing="4",
                padding="1.5rem",
                bg="white",
                border="1px solid #e2e8f0",
                border_radius="8px",
                box_shadow="0 4px 12px rgba(0,0,0,0.1)"
            ),
            position="fixed",
            inset="0",
            bg="rgba(15, 23, 42, 0.35)",
            z_index="100",
            display="flex",
            align_items="center",
            justify_content="center",
            padding="1.5rem"
        ),
        rx.fragment()
    )


def hardware_rule_form() -> rx.Component:
    """Form for adding/editing hardware rules"""
    return rx.cond(
        AdminState.show_rule_form,
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.heading(
                        rx.cond(AdminState.is_editing, "Edit Hardware Rule", "New Hardware Rule"),
                        size="5"
                    ),
                    rx.spacer(),
                    rx.icon(
                        tag="x",
                        cursor="pointer",
                        on_click=AdminState.cancel_form
                    ),
                    width="100%",
                    align_items="center"
                ),
                
                rx.vstack(
                    rx.text("Tag", font_size="0.75rem", font_weight="bold"),
                    rx.select(
                        ["is_base", "is_wall", "has_doors", "has_drawers", "is_pullout", "is_sink", "is_appliance"],
                        value=AdminState.edit_rule_tag,
                        on_change=AdminState.set_edit_rule_tag,
                    ),
                    width="100%",
                    spacing="1"
                ),
                
                rx.vstack(
                    rx.text("Hardware Name", font_size="0.75rem", font_weight="bold"),
                    rx.input(
                        value=AdminState.edit_rule_hardware_name,
                        on_change=AdminState.set_edit_rule_hardware_name,
                        placeholder="e.g., Cabinet legs, Door hinges"
                    ),
                    width="100%",
                    spacing="1"
                ),
                
                rx.hstack(
                    rx.vstack(
                        rx.text("Quantity", font_size="0.75rem", font_weight="bold"),
                        rx.input(
                            type="number",
                            value=AdminState.edit_rule_qty.to_string(),
                            on_change=AdminState.set_edit_rule_qty,
                            placeholder="4"
                        ),
                        flex="1",
                        spacing="1"
                    ),
                    rx.vstack(
                        rx.text("Unit", font_size="0.75rem", font_weight="bold"),
                        rx.select(
                            ["pcs", "sets"],
                            value=AdminState.edit_rule_unit,
                            on_change=AdminState.set_edit_rule_unit,
                        ),
                        flex="1",
                        spacing="1"
                    ),
                    width="100%",
                    spacing="3"
                ),
                
                rx.vstack(
                    rx.text("Price (zł)", font_size="0.75rem", font_weight="bold"),
                    rx.input(
                        type="number",
                        value=AdminState.edit_rule_price.to_string(),
                        on_change=AdminState.set_edit_rule_price,
                        placeholder="1.50"
                    ),
                    width="100%",
                    spacing="1"
                ),
                
                rx.vstack(
                    rx.text("Description (optional)", font_size="0.75rem", font_weight="bold"),
                    rx.text_area(
                        value=AdminState.edit_rule_description,
                        on_change=AdminState.set_edit_rule_description,
                        placeholder="Optional description..."
                    ),
                    width="100%",
                    spacing="1"
                ),
                
                rx.hstack(
                    rx.button(
                        "Cancel",
                        on_click=AdminState.cancel_form,
                        variant="soft",
                        color_scheme="gray",
                        flex="1"
                    ),
                    rx.button(
                        rx.cond(AdminState.is_editing, "Update", "Create"),
                        on_click=AdminState.save_hardware_rule,
                        variant="solid",
                        color_scheme="blue",
                        flex="1"
                    ),
                    width="100%",
                    spacing="3"
                ),
                
                width="100%",
                spacing="4",
                padding="1.5rem",
                bg="white",
                border="1px solid #e2e8f0",
                border_radius="8px",
                box_shadow="0 4px 12px rgba(0,0,0,0.1)",
                max_width="500px"
            ),
            position="fixed",
            inset="0",
            bg="rgba(15, 23, 42, 0.35)",
            z_index="100",
            display="flex",
            align_items="center",
            justify_content="center",
            padding="1.5rem"
        ),
        rx.fragment()
    )


def admin_page() -> rx.Component:
    """Main admin panel page"""
    return rx.vstack(
        # Header
        rx.hstack(
            rx.heading("Admin Panel - Price Management", size="7"),
            rx.spacer(),
            rx.link(
                rx.button(
                    rx.icon(tag="arrow-left", size=16),
                    "Back to Kitchen",
                    variant="soft",
                    color_scheme="gray"
                ),
                href="/"
            ),
            width="100%",
            padding="1.5rem 2rem",
            bg="white",
            border_bottom="1px solid #e2e8f0",
            align_items="center"
        ),
        
        # Hardware Rules Section (Full Width)
        rx.vstack(
            rx.hstack(
                rx.heading("Tag-Based Hardware Rules", size="5"),
                rx.spacer(),
                rx.button(
                    rx.icon(tag="database", size=16),
                    "Initialize Defaults",
                    on_click=AdminState.initialize_default_rules,
                    color_scheme="gray",
                    variant="soft",
                    margin_right="2"
                ),
                rx.button(
                    rx.icon(tag="plus", size=16),
                    "Add Rule",
                    on_click=AdminState.open_new_rule_form,
                    color_scheme="blue"
                ),
                width="100%",
                align_items="center",
                padding_bottom="1rem"
            ),
            
            # Tag filter
            rx.hstack(
                rx.text("Filter by tag:", font_size="0.85rem", font_weight="bold"),
                rx.select(
                    ["all", "is_base", "is_wall", "has_doors", "has_drawers", "is_pullout", "is_sink", "is_appliance"],
                    value=AdminState.rule_filter,
                    on_change=AdminState.set_rule_filter,
                ),
                spacing="2",
                padding_bottom="1rem"
            ),
            
            # Rules table
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Tag"),
                        rx.table.column_header_cell("Hardware Name"),
                        rx.table.column_header_cell("Quantity"),
                        rx.table.column_header_cell("Price"),
                        rx.table.column_header_cell("Description"),
                        rx.table.column_header_cell("Actions"),
                    ),
                ),
                rx.table.body(
                    rx.foreach(AdminState.hardware_rules, hardware_rule_row)
                ),
                width="100%",
                variant="surface"
            ),
            
            width="100%",
            padding="1.5rem 2rem",
            bg="white",
            border="1px solid #e2e8f0",
            border_radius="8px",
            margin="0 2rem"
        ),
        
        # Main content
        rx.hstack(
            # Materials Section
            rx.vstack(
                rx.hstack(
                    rx.heading("Materials", size="5"),
                    rx.spacer(),
                    rx.button(
                        rx.icon(tag="plus", size=16),
                        "Add Material",
                        on_click=AdminState.open_new_material_form,
                        color_scheme="blue"
                    ),
                    width="100%",
                    align_items="center",
                    padding_bottom="1rem"
                ),
                
                # Category filter
                rx.hstack(
                    rx.text("Category:", font_size="0.85rem", font_weight="bold"),
                    rx.select(
                        ["Board", "Panel", "Edge", "Countertop", "Back"],
                        value=AdminState.material_filter,
                        on_change=AdminState.set_material_filter,
                    ),
                    spacing="2",
                    padding_bottom="1rem"
                ),
                
                # Materials table
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Brand"),
                            rx.table.column_header_cell("Name"),
                            rx.table.column_header_cell("Price"),
                            rx.table.column_header_cell("Unit"),
                            rx.table.column_header_cell("Actions"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(AdminState.materials, material_row)
                    ),
                    width="100%",
                    variant="surface"
                ),
                
                flex="1",
                width="100%",
                padding="1.5rem",
                bg="white",
                border="1px solid #e2e8f0",
                border_radius="8px"
            ),
            
            # Hardware Section
            rx.vstack(
                rx.hstack(
                    rx.heading("Hardware", size="5"),
                    rx.spacer(),
                    rx.button(
                        rx.icon(tag="plus", size=16),
                        "Add Hardware",
                        on_click=AdminState.open_new_hardware_form,
                        color_scheme="blue"
                    ),
                    width="100%",
                    align_items="center",
                    padding_bottom="1rem"
                ),
                
                # Hardware table
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Brand"),
                            rx.table.column_header_cell("Name"),
                            rx.table.column_header_cell("Price per Set"),
                            rx.table.column_header_cell("Actions"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(AdminState.hardware_sets, hardware_row)
                    ),
                    width="100%",
                    variant="surface"
                ),
                
                flex="1",
                width="100%",
                padding="1.5rem",
                bg="white",
                border="1px solid #e2e8f0",
                border_radius="8px"
            ),
            
            width="100%",
            padding="2rem",
            spacing="4",
            align_items="flex-start"
        ),
        
        # Forms (modals)
        material_form(),
        hardware_form(),
        hardware_rule_form(),
        
        width="100%",
        min_height="100vh",
        bg="#f8fafc",
        spacing="0"
    )
