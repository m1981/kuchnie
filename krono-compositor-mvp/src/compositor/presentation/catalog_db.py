# src/compositor/presentation/catalog_db.py

CATALOG = {
    "price_groups": [
        {"id": 1, "name": "Grupa Cenowa 1"},
        {"id": 2, "name": "Grupa Cenowa 2"}
    ],
    "materials": [
        # GRUPA 1
        {"id": "dab_szlachetny", "name": "Dąb Szlachetny", "price_group": 1, "allowed_zone": "ANY",
         "texture_width_mm": 1200.0, "hex_color": "#A88B68"},
        {"id": "zielony_kamienny", "name": "Zielony Kamienny", "price_group": 1, "allowed_zone": "FRONT_ONLY",
         "texture_width_mm": 1000.0, "hex_color": "#4A5D5E"},
        {"id": "marmur_bianco", "name": "Marmur Bianco", "price_group": 1, "allowed_zone": "ANY",
         "texture_width_mm": 2000.0, "hex_color": "#F5F5F5"},
        {"id": "czarny_strukturalny", "name": "Czarny Strukturalny", "price_group": 1,
         "allowed_zone": "COUNTERTOP_ONLY", "texture_width_mm": 2000.0, "hex_color": "#222222"},

        # GRUPA 2
        {"id": "dab_casella_jasny", "name": "Dąb Casella Jasny", "price_group": 2, "allowed_zone": "ANY",
         "texture_width_mm": 1200.0, "hex_color": "#D4B895"},
        {"id": "alabast", "name": "Alabast", "price_group": 2, "allowed_zone": "FRONT_ONLY", "texture_width_mm": 1000.0,
         "hex_color": "#EAE8DC"}
    ],
    "scenes": [
        {
            "scene_id": "kitchen_01",
            "name": "Nowoczesna Kuchnia (Modern)",
            "angles": [
                {"angle_id": "main", "name": "Widok Główny (Front View)"},
                {"angle_id": "detail", "name": "Zbliżenie (Detail View)"}
            ]
        }
    ]
}