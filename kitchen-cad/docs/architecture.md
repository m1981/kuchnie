classDiagram
class PanelRole { + LEFT_SIDE + RIGHT_SIDE + BOTTOM + TOP + SHELF + BACK + FRONT_DOOR + FRONT_DRAWER
}
class EdgeSide { + TOP + BOTTOM + LEFT + RIGHT
}
class DrillFace { + INSIDE + OUTSIDE + FRONT + BACK
}
class DrillType { + SYSTEM_32 + HINGE_CUP + HINGE_SCREW + HINGE_DOWEL + DOWEL_CONNECTOR + MINIFIX + HANDLE + SHELF_PIN
}
class EdgeBand { + EdgeSide side + str material
}
class DrillPoint { + float x + float y + float diameter + float depth + DrillFace face + DrillType drill_type + str label
}
class Panel { + str id + PanelRole role + float width + float height + float thickness + str material + int quantity + list[EdgeBand] edges + list[DrillPoint] drill_points
}
class HingeSpec { + str type + float cup_diameter + float cup_depth + float screw_spacing + float screw_offset_x + float screw_diameter + float screw_depth + float edge_to_cup_centre + int count + float first_position
}
class DrawerSpec { + float internal_height + str runner_type
}
class HandleSpec { + str type + float spacing + str position + float hole_diameter
}
class CorpusSpec { + str id + str name + str corpus_type + float width + float height + float depth + float panel_thickness + float back_thickness + float back_groove_depth + str material_corpus + str material_back + str material_front + str edge_material + list[float] shelves + list[DrawerSpec] drawers + list[int] doors + HingeSpec | None hinges + HandleSpec | None handles + float shelf_pin_diameter + float shelf_pin_depth + float shelf_pin_front_offset + float shelf_pin_back_offset + int shelf_pin_max_per_row + float front_gap
}

    EdgeBand *-- EdgeSide : side
    DrillPoint *-- DrillFace : face
    DrillPoint *-- DrillType : drill_type
    Panel *-- PanelRole : role
    Panel *-- EdgeBand : edges
    Panel *-- DrillPoint : drill_points
    CorpusSpec *-- DrawerSpec : drawers
    CorpusSpec *-- HingeSpec : hinges
    CorpusSpec *-- HandleSpec : handles

    class kitchen_cad_csv_generator_module {
        <<module>>
        +_edge_length(Panel panel, EdgeBand edge) float
        +generate_cutting_csv(list[Panel] panels, Path path) Path
        +generate_edging_csv(list[Panel] panels, Path path) Path
    }
    class kitchen_cad_drill_engine_module {
        <<module>>
        +system32_y_positions(float height) list[float]
        +_shelf_pin_offsets(int max_per_row, float raster) list[float]
        +apply_system32(list[Panel] panels, CorpusSpec spec) list[Panel]
        +_default_hinge() HingeSpec
        +_hinge_positions(float front_height, int count, float first_pos) list[float]
        +apply_hinges(list[Panel] panels, CorpusSpec spec) list[Panel]
        +apply_handles(list[Panel] panels, CorpusSpec spec) list[Panel]
        +apply_all_drilling(list[Panel] panels, CorpusSpec spec) list[Panel]
    }
    class kitchen_cad_panel_calculator_module {
        <<module>>
        +_edge_material(CorpusSpec spec) str
        +_side_panels(CorpusSpec spec) list[Panel]
        +_horizontal_panels(CorpusSpec spec) list[Panel]
        +_shelf_panels(CorpusSpec spec) list[Panel]
        +_back_panel(CorpusSpec spec) Panel
        +_door_fronts(CorpusSpec spec) list[Panel]
        +_drawer_fronts(CorpusSpec spec) list[Panel]
        +calculate_panels(CorpusSpec spec) list[Panel]
    }
