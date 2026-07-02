# Project Structure

## krono-compositor-mvp/gen_kitchen.py
```python
import bpy
import json
import os
import math

def hex_to_rgb(hex_str)

def setup_front_materials(obj, hex_color)

def configure_engine_for_art()

def configure_engine_for_math()

def switch_front_materials(pass_name)

def set_handles_visibility(visible)

def set_shadow_catchers(active)

def set_floor_visibility(visible)
```

## krono-compositor-mvp/main.py
```python
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from compositor.presentation.api import router

def serve_frontend()
```

## krono-compositor-mvp/src/compositor/application/scene_compositor.py
```python
from typing import List
import cv2
from compositor.domain.interfaces import ImageReader, ImageWriter, TextureTiler, UVWarper, MaskExtractor, ImageBlender, ZoneConfig

class SceneCompositor
    def __init__(self, reader: ImageReader, writer: ImageWriter, tiler: TextureTiler, warper: UVWarper, masker: MaskExtractor, blender: ImageBlender)
    def render_scene(self, base_path: str, uv_path: str, mask_path: str, zones: List[ZoneConfig], out_path: str=None, uv_scale_mm: float=1000.0, reflection_path: str=None, handle_path: str=None)

```

## krono-compositor-mvp/src/compositor/infrastructure/opencv_impl.py
```python
import os
import cv2
import numpy
from typing import Tuple
from compositor.domain.interfaces import Image, UVMap, Mask, ColorBGR

class OpenCVImageIO
    def read_color(self, path: str) -> Image
    def read_rgba(self, path: str) -> Image
    def read_uv(self, path: str) -> UVMap
    def write(self, path: str, image: Image) -> None

class OpenCVTextureTiler
    def tile(self, texture: Image, target_shape: Tuple[int, int], scale: float) -> Image

class OpenCVUVWarper
    def warp(self, texture: Image, uv_map: UVMap, repetition_factor: float=1.0) -> Image

class OpenCVMaskExtractor
    def extract(self, id_mask: Image, target_color: ColorBGR) -> Mask

class OpenCVImageBlender
    def multiply(self, base: Image, layer: Image, mask: Mask) -> Image
    def screen(self, base: Image, layer: Image) -> Image
    def alpha_composite(self, base: Image, rgba_layer: Image) -> Image

```

## krono-compositor-mvp/src/compositor/domain/interfaces.py
```python
import numpy
from typing import Protocol, Tuple
from dataclasses import dataclass

class ImageReader(Protocol)
    def read_color(self, path: str) -> Image
    def read_rgba(self, path: str) -> Image
    def read_uv(self, path: str) -> UVMap

class ImageWriter(Protocol)
    def write(self, path: str, image: Image) -> None

class TextureTiler(Protocol)
    def tile(self, texture: Image, target_shape: Tuple[int, int], scale: float) -> Image

class UVWarper(Protocol)
    def warp(self, texture: Image, uv_map: UVMap) -> Image

class MaskExtractor(Protocol)
    def extract(self, id_mask: Image, target_color: ColorBGR) -> Mask

class ImageBlender(Protocol)
    def multiply(self, base: Image, layer: Image, mask: Mask) -> Image
    def screen(self, base: Image, layer: Image) -> Image
    def alpha_composite(self, base: Image, rgba_layer: Image) -> Image

class ZoneConfig
    pass

```

## krono-compositor-mvp/src/compositor/presentation/api.py
```python
import os
import cv2
import logging
from fastapi import APIRouter, Depends, HTTPException, Response
from typing import List
from compositor.application.scene_compositor import SceneCompositor
from compositor.domain.interfaces import ZoneConfig
from compositor.infrastructure.opencv_impl import OpenCVImageIO, OpenCVTextureTiler, OpenCVUVWarper, OpenCVMaskExtractor, OpenCVImageBlender
from compositor.presentation.schemas import RenderRequest, ZoneType, AllowedZone
from compositor.presentation.catalog_db import CATALOG

def get_compositor() -> SceneCompositor

def get_catalog()

def render_image(request: RenderRequest, compositor: SceneCompositor=Depends())
```

## krono-compositor-mvp/src/compositor/presentation/schemas.py
```python
from pydantic import BaseModel, Field
from typing import List, Tuple
from enum import Enum

class ZoneType(str, Enum)
    pass

class AllowedZone(str, Enum)
    pass

class ZoneRequest(BaseModel)
    def get_bgr_tuple(self) -> Tuple[int, int, int]

class RenderRequest(BaseModel)
    pass

```

## catalog/repositories/pairing_repo.py
```python
from __future__ import annotations
import sqlite3
from typing import Optional
from catalog.models.domain import PairingOut

class PairingRepository
    def __init__(self, db: sqlite3.Connection)
    def get_for_decor(self, business_id: str) -> list[PairingOut]

```

## catalog/repositories/decor_repo.py
```python
from __future__ import annotations
import sqlite3
from typing import Optional
from catalog.models.domain import DecorSummary, DecorWithVariants, VariantOut

class DecorRepository
    def __init__(self, db: sqlite3.Connection)
    def list_filtered(self) -> tuple[list[DecorSummary], int]
    def get_by_id(self, business_id: str) -> Optional[DecorWithVariants]
    def get_variants(self, business_id: str) -> list[VariantOut]
    def _build_where() -> tuple[str, list]

```

## catalog/repositories/worktop_repo.py
```python
from __future__ import annotations
import sqlite3
from typing import Optional
from catalog.models.domain import WorktopOut

class WorktopRepository
    def __init__(self, db: sqlite3.Connection)
    def list_filtered(self) -> list[WorktopOut]

```

## catalog/repositories/configurator.py
```python
from __future__ import annotations
import json
import sqlite3
import uuid

class ConfiguratorRepository
    def __init__(self, db: sqlite3.Connection)
    def create_session(self) -> dict
    def get_session(self, token: str) -> dict | None
    def update_step(self, token: str, step: str, column: str, value) -> None
    def front_options(self, color_family: str | None=None, style: str | None=None) -> list[dict]
    def carcass_options(self, front_variant_id: str) -> list[dict]
    def worktop_options(self) -> list[dict]
    def edge_options(self, front_variant_id: str) -> list[dict]
    def side_panel_options(self) -> list[dict]
    def plinth_options(self) -> list[dict]
    def build_bom(self, session: dict) -> dict
    def _fallback_options(self, role: str) -> list[dict]
    def _option_from_row(self, row) -> dict
    def compare_variants(self, variant_ids: list[str]) -> list[dict]

def _next_step(step: str) -> str | None

def _variant_step_column(step: str) -> str
```

## catalog/repositories/availability_repo.py
```python
from __future__ import annotations
import sqlite3
from typing import Optional
from catalog.models.domain import AvailabilityOut

class AvailabilityRepository
    def __init__(self, db: sqlite3.Connection)
    def list_filtered(self) -> list[AvailabilityOut]

```

## catalog/models/domain.py
```python
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel

class ProducerOut(BaseModel)
    pass

class DecorSummary(BaseModel)
    pass

class VariantOut(BaseModel)
    pass

class DecorWithVariants(BaseModel)
    pass

class PairingOut(BaseModel)
    pass

class WorktopOut(BaseModel)
    pass

class AvailabilityOut(BaseModel)
    pass

class PaginatedResponse(BaseModel)
    pass

class StatsOut(BaseModel)
    pass

class SessionOut(BaseModel)
    pass

class SelectRequest(BaseModel)
    pass

class ConfiguratorOption(BaseModel)
    pass

class ConfiguratorStepOut(BaseModel)
    pass

class BOMItem(BaseModel)
    pass

class BOMOut(BaseModel)
    pass

class TemplateOut(BaseModel)
    pass

class FromTemplateRequest(BaseModel)
    pass

```

## catalog/scripts/generate_kronoswiss_yaml.py
```python
from pathlib import Path
import yaml

def _build_swiss_variants(decors: list[dict], primary_map: dict) -> list[dict]

def generate_kronoswiss_yaml() -> dict

def _build_swiss_decor_structures(decors: list[dict]) -> list[dict]
```

## catalog/scripts/importer.py
```python
from __future__ import annotations
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
import yaml
import json
import json

class ImportStats
    def total(self) -> int
    def __repr__(self) -> str

class CatalogImporter
    def __init__(self, db: sqlite3.Connection)
    def _lookup_id(self, table: str, column: str, value: str | int) -> int | None
    def _require_id(self, table: str, column: str, value: str | int, context: str) -> int
    def import_all(self, data: dict) -> ImportStats
    def import_producers(self, items: list[dict]) -> int
    def import_structures(self, items: list[dict]) -> int
    def import_collections(self, items: list[dict]) -> int
    def import_materials(self, items: list[dict]) -> int
    def import_decors(self, items: list[dict]) -> int
    def import_variants(self, items: list[dict]) -> int
    def import_worktops(self, items: list[dict]) -> int
    def import_decor_structures(self, items: list[dict]) -> int
    def import_pairings(self, items: list[dict]) -> int
    def import_edges(self, items: list[dict]) -> tuple[int, int]
    def import_availability(self, items: list[dict]) -> int
    def import_property_flags(self, items: list[dict]) -> int

def load_yaml(path: str | Path) -> dict

def _require(item: dict, key: str, section: str)
```

## catalog/scripts/generate_variants.py
```python
from __future__ import annotations
from pathlib import Path
import yaml

def main() -> None
```

## catalog/scripts/seed_pairings_edges.py
```python
from __future__ import annotations
import sqlite3
from pathlib import Path
import yaml

def get_db() -> sqlite3.Connection

def seed_carcass_pairings(db: sqlite3.Connection) -> int

def seed_edges(db: sqlite3.Connection) -> tuple[int, int]

def main() -> None
```

## catalog/scripts/seed.py
```python
from __future__ import annotations
import sys
from pathlib import Path
from catalog.db.engine import get_connection, init_schema
from catalog.scripts.importer import CatalogImporter, load_yaml

def main() -> None
```

## catalog/scripts/merge_global_collection.py
```python
from __future__ import annotations
from pathlib import Path
import yaml

def _find_image(business_id: str) -> str | None

def _group_to_color_family(group: str) -> str | None

def _infer_color_family(name: str, group: str) -> str | None

def main() -> None
```

## catalog/scripts/generate_kronospan_yaml.py
```python
import json
from pathlib import Path
import yaml

def generate_kronospan_yaml() -> dict

def _build_variants(decors: list[dict], primary_map: dict) -> list[dict]

def _build_decor_structures(decors: list[dict]) -> list[dict]

def write_yaml(data: dict, path: Path)
```

## catalog/scripts/seed_worktop_compat.py
```python
from __future__ import annotations
import sqlite3
from pathlib import Path

def get_db() -> sqlite3.Connection

def seed_worktop_compatibility(db: sqlite3.Connection) -> int

def main() -> None
```

## catalog/scripts/build_image_map.py
```python
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
import yaml

def _extract_digits(s: str) -> str

def _find_image(business_id: str, img_dir: Path) -> str | None

def _load_yaml(path: Path) -> dict

def _save_yaml(path: Path, data: dict) -> None

def build_mapping(yaml_path: Path) -> dict[str, str | None]

def apply_mapping(yaml_path: Path, mapping: dict[str, str | None]) -> int

def main() -> None
```

## catalog/scripts/seed_decor_style_tags.py
```python
from __future__ import annotations
import sqlite3
from pathlib import Path

def get_db() -> sqlite3.Connection

def seed_decor_style_tags(db: sqlite3.Connection) -> int

def main() -> None
```

## catalog/scripts/seed_curated_kitchens.py
```python
from __future__ import annotations
import sqlite3
from pathlib import Path

def get_db() -> sqlite3.Connection

def seed_style_tags(db: sqlite3.Connection) -> int

def seed_curated_kitchens(db: sqlite3.Connection) -> int

def main() -> None
```

## catalog/db/engine.py
```python
from __future__ import annotations
import sqlite3
from pathlib import Path

def get_connection(db_path: str=':memory:') -> sqlite3.Connection

def init_schema(db: sqlite3.Connection) -> None
```

## catalog/api/routers/producers.py
```python
from __future__ import annotations
import sqlite3
from typing import Annotated
from fastapi import APIRouter, Depends
from catalog.api.deps import get_db
from catalog.models.domain import ProducerOut

def list_producers(db: Annotated[sqlite3.Connection, Any]) -> list[dict]
```

## catalog/api/routers/worktops.py
```python
from __future__ import annotations
import sqlite3
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query
from catalog.api.deps import get_db
from catalog.models.domain import WorktopOut
from catalog.repositories.worktop_repo import WorktopRepository

def list_worktops(db: Annotated[sqlite3.Connection, Any], construction: Optional[str]=Query(), producer: Optional[str]=Query()) -> list[WorktopOut]
```

## catalog/api/routers/decors.py
```python
from __future__ import annotations
import sqlite3
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from catalog.api.deps import get_db
from catalog.models.domain import DecorSummary, DecorWithVariants, PaginatedResponse, PairingOut, VariantOut
from catalog.repositories.decor_repo import DecorRepository
from catalog.repositories.pairing_repo import PairingRepository

def list_decors(db: Annotated[sqlite3.Connection, Any], producer: Optional[str]=Query(), color_family: Optional[str]=Query(), material_type: Optional[str]=Query(), structure: Optional[str]=Query(), role: Optional[str]=Query(), search: Optional[str]=Query(), page: int=Query(), page_size: int=Query()) -> PaginatedResponse

def get_decor(decor_id: str, db: Annotated[sqlite3.Connection, Any]) -> DecorWithVariants

def get_decor_variants(decor_id: str, db: Annotated[sqlite3.Connection, Any], material_type: Optional[str]=Query()) -> list[VariantOut]

def get_decor_pairings(decor_id: str, db: Annotated[sqlite3.Connection, Any], pairing_type: Optional[str]=Query()) -> list[PairingOut]
```

## catalog/api/routers/admin.py
```python
from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends
from catalog.api.deps import get_db
from catalog.models.domain import StatsOut

def get_stats(db: Annotated[sqlite3.Connection, Any]) -> dict

def get_full_catalog(db: Annotated[sqlite3.Connection, Any]) -> dict
```

## catalog/api/routers/configurator.py
```python
from __future__ import annotations
import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from catalog.api.deps import get_db
from catalog.models.domain import BOMOut, ConfiguratorOption, ConfiguratorStepOut, FromTemplateRequest, SelectRequest, SessionOut, TemplateOut
from catalog.repositories.configurator import STEPS, VARIANT_STEPS, ConfiguratorRepository

def create_session(db: sqlite3.Connection=Depends()) -> SessionOut

def get_session(token: str, db: sqlite3.Connection=Depends()) -> SessionOut

def get_options(token: str, color_family: str | None=None, style: str | None=None, db: sqlite3.Connection=Depends()) -> ConfiguratorStepOut

def select(token: str, req: SelectRequest, db: sqlite3.Connection=Depends()) -> SessionOut

def get_bom(token: str, db: sqlite3.Connection=Depends()) -> BOMOut

def compare_variants(ids: str, db: sqlite3.Connection=Depends()) -> list[dict]

def list_templates(db: sqlite3.Connection=Depends()) -> list[TemplateOut]

def from_template(token: str, req: FromTemplateRequest, db: sqlite3.Connection=Depends()) -> SessionOut

def _next_step_or_done(current: str) -> str
```

## catalog/api/routers/availability.py
```python
from __future__ import annotations
import sqlite3
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query
from catalog.api.deps import get_db
from catalog.models.domain import AvailabilityOut
from catalog.repositories.availability_repo import AvailabilityRepository

def list_availability(db: Annotated[sqlite3.Connection, Any], channel: Optional[str]=Query(), producer: Optional[str]=Query()) -> list[AvailabilityOut]
```

## catalog/api/deps.py
```python
from __future__ import annotations
import sqlite3
from typing import Generator

def set_db(conn: sqlite3.Connection) -> None

def get_db() -> Generator[sqlite3.Connection, None, None]
```

## catalog/api/main.py
```python
from __future__ import annotations
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from catalog.api import deps
from catalog.api.routers import admin, availability, configurator, decors, producers, worktops
from catalog.db.engine import get_connection, init_schema

async def lifespan(app: FastAPI)
```

## kitchen-erp/rxconfig.py
```python
import reflex

```

## kitchen-erp/kitchen_erp/ui/admin_ui.py
```python
import reflex
from admin_state import AdminState, MaterialUI, HardwareUI, HardwareRuleUI

def material_row(material: MaterialUI) -> rx.Component

def hardware_row(hardware: HardwareUI) -> rx.Component

def hardware_rule_row(rule: HardwareRuleUI) -> rx.Component

def material_form() -> rx.Component

def hardware_form() -> rx.Component

def hardware_rule_form() -> rx.Component

def admin_page() -> rx.Component
```

## kitchen-erp/kitchen_erp/ui/admin_state.py
```python
import reflex
from pydantic import BaseModel
from sqlmodel import select
from core.database import get_session
from core.models import Material, HardwareSet, HardwareRule
from core.rules_engine import get_default_hardware_rules

class MaterialUI(BaseModel)
    pass

class HardwareUI(BaseModel)
    pass

class HardwareRuleUI(BaseModel)
    pass

class AdminState(rx.State)
    def load_materials(self)
    def load_hardware(self)
    def load_hardware_rules(self)
    def set_material_filter(self, category: str)
    def set_edit_material_name(self, value: str)
    def set_edit_material_brand(self, value: str)
    def set_edit_material_price(self, value: str)
    def set_edit_material_sheet_size(self, value: str)
    def set_edit_material_has_woodgrain(self, value: bool)
    def set_edit_material_unit(self, value: str)
    def set_edit_material_category(self, value: str)
    def set_edit_hardware_name(self, value: str)
    def set_edit_hardware_brand(self, value: str)
    def set_edit_hardware_price(self, value: str)
    def set_edit_rule_tag(self, value: str)
    def set_edit_rule_hardware_name(self, value: str)
    def set_edit_rule_qty(self, value: str)
    def set_edit_rule_unit(self, value: str)
    def set_edit_rule_price(self, value: str)
    def set_edit_rule_description(self, value: str)
    def set_rule_filter(self, tag: str)
    def open_new_material_form(self)
    def open_edit_material_form(self, material_id: int)
    def save_material(self)
    def delete_material(self, material_id: int)
    def open_new_hardware_form(self)
    def open_edit_hardware_form(self, hardware_id: int)
    def save_hardware(self)
    def delete_hardware(self, hardware_id: int)
    def open_new_rule_form(self)
    def open_edit_rule_form(self, rule_id: int)
    def save_hardware_rule(self)
    def delete_hardware_rule(self, rule_id: int)
    def initialize_default_rules(self)
    def cancel_form(self)

```

## kitchen-erp/kitchen_erp/ui/state.py
```python
import re
import reflex
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import select
from core.database import get_session, engine, SQLModel
from core.models import Project, Cabinet, Material, HardwareSet, ProjectDefaults, HardwareRule
from core.schemas import CostTraceLine
from core.bom_generator import BOMGenerator
from core.bom_generator import BOMGenerator
from core.purchasing import get_strategy_for_material
from core.bom_generator import BOMGenerator

class CabinetUI(BaseModel)
    pass

class CostTraceLineUI(BaseModel)
    pass

class KitchenState(rx.State)
    def _ensure_cabinet_schema(self, session)
    def local_material_options(self) -> list[str]
    def _format_cost_trace_line(self, line: CostTraceLine) -> CostTraceLineUI
    def _is_row_module(self, cab: Cabinet) -> bool
    def _row_key(self, cab: Cabinet) -> str | None
    def _row_siblings(self, project: Project, cab: Cabinet) -> list[Cabinet]
    def _relayout_ordered_row(self, siblings: list[Cabinet])
    def _anchor_overlays(self, project: Project)
    def _relayout_project(self, project: Project)
    def _module_ui(self, cab: Cabinet, cost: float) -> CabinetUI
    def load_ikea_layout(self)
    def clear_layout(self)
    def set_use_new_bom(self, value: bool)
    def close_cost_trace(self)
    def open_selected_cabinet_cost_trace(self)
    def open_selected_cabinet_cost_trace_new(self)
    def open_project_cost_trace(self)
    def open_project_cost_trace_new(self)
    def change_global_front(self, formatted_name: str)
    def change_local_front(self, formatted_name: str)
    def _parse_number(self, raw_value: str, is_float: bool) -> float | int | None
    def _apply_cabinet_constraints(self, cab: Cabinet, field: str, raw_value: str)
    def update_cabinet_field(self, field: str, value: str)
    def add_cabinet(self, cab_type: str)
    def add_equipment(self, equipment_name: str)
    def move_cabinet(self, cab_id: int, direction: int)
    def move_selected_cabinet(self, direction: int)
    def delete_cabinet(self)
    def select_cabinet(self, cab_id: int)
    def close_sidebar(self)
    def _update_selected_cabinet_ui(self)
    def load_mock_data(self)

```

## kitchen-erp/kitchen_erp/core/recipe_loader.py
```python
import json
from pathlib import Path
from typing import Any

def load_recipes() -> dict[str, dict]

def get_recipe(recipe_id: str) -> dict[str, Any]

def get_recipe_tags(recipe_id: str) -> list[str]

def eval_formula(formula: str, cabinet_dims: dict[str, float]) -> float

def clear_recipe_cache()
```

## kitchen-erp/kitchen_erp/core/models.py
```python
from sqlmodel import SQLModel, Field, Relationship
from schemas import CabinetCostResult, CostTraceLine
from bom_generator import BOMGenerator
from purchasing import get_strategy_for_material

class Material(SQLModel)
    pass

class HardwareSet(SQLModel)
    pass

class HardwareRule(SQLModel)
    pass

class ProjectDefaults(SQLModel)
    pass

class Cabinet(SQLModel)
    def has_custom_front(self) -> bool
    def local_front_mat(self) -> Material | None
    def calculate_cost(self, defaults: ProjectDefaults, waste_factor: float) -> CabinetCostResult

class Project(SQLModel)
    def generate_project_bom(self)

```

## kitchen-erp/kitchen_erp/core/database.py
```python
from sqlmodel import create_engine, SQLModel, Session
from  import models

def create_db_and_tables()

def get_session()
```

## kitchen-erp/kitchen_erp/core/bom_generator.py
```python
from schemas import BOMAssembly, BOMPart
from recipe_loader import get_recipe, eval_formula
from rules_engine import RulesEngine
from models import Cabinet, ProjectDefaults
from schemas import CostTraceLine

class BOMGenerator
    def __init__(self, cabinet: Cabinet, defaults: ProjectDefaults)
    def generate(self) -> BOMAssembly
    def generate_cost_trace_lines(self)

```

## kitchen-erp/kitchen_erp/core/schemas.py
```python
from pydantic import BaseModel, Field
from typing import Literal

class BOMNode(BaseModel)
    def calculate(self) -> float

class BOMPart(BOMNode)
    def calculate(self) -> float

class BOMAssembly(BOMNode)
    def calculate(self) -> float
    def add_child(self, child: BOMNode)
    def get_all_parts(self) -> list[BOMPart]

class CostTraceLine(BaseModel)
    pass

class CabinetCostResult(BaseModel)
    pass

```

## kitchen-erp/kitchen_erp/core/purchasing.py
```python
from abc import ABC, abstractmethod
from math import ceil

class PurchasingStrategy(ABC)
    def calculate_purchase_quantity(self, net_quantity: float) -> float
    def get_waste_factor(self, net_quantity: float) -> float

class SheetMaterialStrategy(PurchasingStrategy)
    def __init__(self, sheet_size_m2: float=5.796, has_woodgrain: bool=False)
    def calculate_purchase_quantity(self, net_quantity: float) -> float
    def get_waste_factor(self, net_quantity: float) -> float

class LinearMaterialStrategy(PurchasingStrategy)
    def __init__(self, roll_length_m: float=50.0, waste_factor: float=1.1)
    def calculate_purchase_quantity(self, net_quantity: float) -> float
    def get_waste_factor(self, net_quantity: float) -> float

class CountertopStrategy(PurchasingStrategy)
    def __init__(self, standard_length_mm: float=4100.0, width_mm: float=600.0)
    def calculate_purchase_quantity(self, net_quantity: float) -> float
    def get_waste_factor(self, net_quantity: float) -> float

class ExactQuantityStrategy(PurchasingStrategy)
    def __init__(self, waste_factor: float=1.05)
    def calculate_purchase_quantity(self, net_quantity: float) -> float
    def get_waste_factor(self, net_quantity: float) -> float

def get_strategy_for_material(material_category: str) -> PurchasingStrategy
```

## kitchen-erp/kitchen_erp/core/rules_engine.py
```python
from typing import Any
from schemas import BOMPart, BOMAssembly
from database import engine
from models import HardwareRule
from sqlmodel import Session, select
from sqlalchemy.exc import OperationalError

class RulesEngine
    def __init__(self, rules: dict[str, list[dict]] | None=None)
    def clear_cache(cls)
    def apply_rules(self, tags: list[str], assembly: BOMAssembly, multipliers: dict[str, int] | None=None) -> BOMAssembly
    def get_required_hardware_for_tags(self, tags: list[str]) -> list[dict[str, Any]]

def get_default_hardware_rules()

def load_hardware_rules_from_db()
```

## kitchen-erp/kitchen_erp/kitchen_erp.py
```python
import reflex
from ui.state import KitchenState, CabinetUI, CostTraceLineUI
from ui.admin_ui import admin_page
from ui.admin_state import AdminState

def top_bar() -> rx.Component

def cost_trace_row(line: CostTraceLineUI) -> rx.Component

def cost_trace_panel() -> rx.Component

def cabinet_2d_box(cabinet: CabinetUI) -> rx.Component

def module_front(cabinet: CabinetUI) -> rx.Component

def plan_module_box(cabinet: CabinetUI) -> rx.Component

def main_canvas() -> rx.Component

def action_bar() -> rx.Component

def form_input_group(label: str, field_name: str, default_val: str) -> rx.Component

def sidebar() -> rx.Component

def index() -> rx.Component
```

## kitchen-erp/examples/demo_bom_system.py
```python
from sqlmodel import Session, create_engine, SQLModel, select
from kitchen_erp.core.models import Cabinet, Material, HardwareSet, ProjectDefaults, Project
from kitchen_erp.core.bom_generator import BOMGenerator
from kitchen_erp.core.purchasing import get_strategy_for_material
from kitchen_erp.core.recipe_loader import get_recipe
from kitchen_erp.core.recipe_loader import load_recipes
from kitchen_erp.core.rules_engine import RulesEngine

def create_demo_database()

def demo_recipe_system()

def demo_bom_generation(engine, project_id)

def demo_rules_engine(engine, cabinet_id)

def demo_purchasing_strategies(engine, project_id)

def demo_old_vs_new_comparison(engine, cabinet_id)

def main()
```

## kitchen-erp/scripts/validate_migration.py
```python
import sys
from pathlib import Path
from sqlmodel import Session, select, func
from kitchen_erp.core.database import get_session, create_db_and_tables
from kitchen_erp.core.models import Cabinet, Project, ProjectDefaults
from kitchen_erp.core.bom_generator import BOMGenerator
from kitchen_erp.core.recipe_loader import load_recipes

def check_recipe_coverage()

def compare_costs()

def generate_report()

def main()
```

## scripts/export_pdf_pages.py
```python
import argparse
import os
import sys
from pathlib import Path
import fitz

def export_pdf_pages(pdf_path: str, output_dir: str=None, dpi: int=150, page_range: str=None) -> list[str]

def parse_page_range(range_str: str, total_pages: int) -> list[int]

def main()
```

## kitchen-cam/src/kitchen_cam/panel_calculator.py
```python
from __future__ import annotations
from kitchen_cam.models import SYSTEM32_OFFSET, BaseDoorConfig, BaseDrawerConfig, CabinetConfig, CargoConfig, CornerBlindConfig, CornerInternalConfig, CorpusSpec, EdgeBand, EdgeSide, OvenConfig, Panel, PanelRole, SinkConfig
import math

def _edge_material(spec: CorpusSpec) -> str

def _side_panels(spec: CorpusSpec) -> list[Panel]

def _horizontal_panels(spec: CorpusSpec) -> list[Panel]

def _shelf_panels(spec: CorpusSpec, shelf_positions: list[float]) -> list[Panel]

def _back_panel(spec: CorpusSpec) -> Panel

def _door_fronts(spec: CorpusSpec, door_hinge_counts: list[int]) -> list[Panel]

def _drawer_fronts(spec: CorpusSpec, drawer_count: int) -> list[Panel]

def _calculate_base_door(spec: CorpusSpec, config: BaseDoorConfig) -> list[Panel]

def _calculate_base_drawer(spec: CorpusSpec, config: BaseDrawerConfig) -> list[Panel]

def _calculate_corner_blind(spec: CorpusSpec, config: CornerBlindConfig) -> list[Panel]

def _calculate_corner_internal(spec: CorpusSpec, config: CornerInternalConfig) -> list[Panel]

def _calculate_sink(spec: CorpusSpec, config: SinkConfig) -> list[Panel]

def _calculate_cargo(spec: CorpusSpec, config: CargoConfig) -> list[Panel]

def _calculate_oven(spec: CorpusSpec, config: OvenConfig) -> list[Panel]

def calculate_panels(spec: CorpusSpec) -> list[Panel]
```

## kitchen-cam/src/kitchen_cam/models.py
```python
from __future__ import annotations
from enum import Enum
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field, model_validator

class CorpusType(str, Enum)
    pass

class PanelRole(str, Enum)
    pass

class EdgeSide(str, Enum)
    pass

class DrillFace(str, Enum)
    pass

class DrillType(str, Enum)
    pass

class CornerSide(str, Enum)
    pass

class CarouselType(str, Enum)
    pass

class CargoType(str, Enum)
    pass

class EdgeBand(BaseModel)
    pass

class DrillPoint(BaseModel)
    pass

class HingeSpec(BaseModel)
    pass

class DrawerSpec(BaseModel)
    pass

class HandleSpec(BaseModel)
    pass

class BaseDoorConfig(BaseModel)
    pass

class BaseDrawerConfig(BaseModel)
    pass

class CornerBlindConfig(BaseModel)
    pass

class CornerInternalConfig(BaseModel)
    pass

class SinkConfig(BaseModel)
    pass

class CargoConfig(BaseModel)
    pass

class OvenConfig(BaseModel)
    pass

class Panel(BaseModel)
    pass

class CorpusSpec(BaseModel)
    def _sync_config_from_legacy(self) -> 'CorpusSpec'
    def corpus_type_resolved(self) -> str
    def shelves_resolved(self) -> list[float]
    def drawers_resolved(self) -> list[DrawerSpec]
    def doors_resolved(self) -> list[int]

```

## kitchen-cam/src/kitchen_cam/dxf/legrabox_side_panel.py
```python
import ezdxf
import argparse
import math
import os
from pathlib import Path

def create_dxf_layers(doc)

def add_circle(msp, layer, center, diameter)

def add_outline(msp, width, height)

def add_system32_holes(msp, width, height, panel_thickness=PANEL_THICKNESS)

def add_legarabox_profile_holes(msp, width, height, drawer_config, panel_thickness=PANEL_THICKNESS)

def add_dowel_holes(msp, width, height, drawer_config)

def add_edgebanding_marks(msp, width, height)

def add_dimensions_and_notes(msp, width, height, drawer_config)

def calculate_drawer_openings(cabinet_height, drawer_types)

def generate_side_panel_dxf(cabinet_depth=510, cabinet_height=720, drawer_types=None, output_dir=None, side='left')

def main()
```

## kitchen-cam/src/kitchen_cam/machining.py
```python
from __future__ import annotations
import copy
from kitchen_cam.models import SYSTEM32_OFFSET, SYSTEM32_SPACING, BaseDoorConfig, BaseDrawerConfig, CargoConfig, CornerBlindConfig, CornerInternalConfig, CorpusSpec, DrillFace, DrillPoint, DrillType, HingeSpec, OvenConfig, Panel, PanelRole, SinkConfig

def system32_y_positions(height: float) -> list[float]

def _shelf_pin_offsets(max_per_row: int, raster: float=SYSTEM32_SPACING) -> list[float]

def _get_shelf_positions(spec: CorpusSpec) -> list[float]

def _get_door_hinge_counts(spec: CorpusSpec) -> list[int]

def apply_system32(panels: list[Panel], spec: CorpusSpec) -> list[Panel]

def _hinge_positions(front_height: float, count: int, first_pos: float) -> list[float]

def apply_hinges(panels: list[Panel], spec: CorpusSpec) -> list[Panel]

def apply_handles(panels: list[Panel], spec: CorpusSpec) -> list[Panel]

def apply_all_drilling(panels: list[Panel], spec: CorpusSpec) -> list[Panel]
```

## kitchen-cam/src/kitchen_cam/csv_generator.py
```python
from __future__ import annotations
import csv
from pathlib import Path
from kitchen_cam.models import EdgeBand, EdgeSide, Panel

def _edge_length(panel: Panel, edge: EdgeBand) -> float

def generate_cutting_csv(panels: list[Panel], path: Path) -> Path

def generate_edging_csv(panels: list[Panel], path: Path) -> Path
```

## home-builder-adapter/scripts/summarize_manifest.py
```python
import json
import sys
from pathlib import Path

def summarize_manifest(manifest: dict) -> str

def main()
```

## home-builder-adapter/scripts/validate_manifest.py
```python
import json
import sys
from pathlib import Path
from manifest_validator import validate_manifest, print_validation_report
import jsonschema

def main()
```

## home-builder-adapter/scripts/blender_sketchup_keyconfig.py
```python
import bpy
import traceback
import os

def remove_conflicting_items(km, keys_to_remove)

def add_key(km, idname, key, value='PRESS', ctrl=False, shift=False, alt=False, oskey=False, properties=None, head=False)

def setup_3dview_navigation(kc)

def setup_object_mode(kc)

def setup_mesh_edit(kc)

def setup_window(kc)

def register()

def unregister()
```

## home-builder-adapter/src/cli.py
```python
from __future__ import annotations
import json
import sys
from extract import extract_cabinets_from_scene, cabinets_to_kitchen
from kuchnie_core.serialize import kitchen_to_dict

def main() -> None
```

## home-builder-adapter/src/extract.py
```python
from __future__ import annotations
from typing import Any
from kuchnie_core.model import CabinetInstance, Kitchen, Row
import bpy

def _m_to_mm(m: float) -> int

def _extract_cabinet(obj: Any) -> dict[str, Any] | None

def _count_shelves(obj: Any) -> int

def extract_cabinets_from_scene() -> list[dict[str, Any]]

def cabinets_to_kitchen(cabinets: list[dict[str, Any]]) -> Kitchen

def extract_kitchen_from_blend() -> Kitchen
```

## src/kuchnie_core/validator.py
```python
from dataclasses import dataclass, field
from typing import List, Optional
import math

class Issue
    def to_dict(self) -> dict

class ValidationResult
    def is_valid(self) -> bool
    def add_issue(self, issue: Issue) -> None
    def to_dict(self) -> dict

def validate_manifest(manifest: dict, dimension_tolerance_mm: float=DEFAULT_DIMENSION_TOLERANCE_MM, overlap_tolerance_mm: float=DEFAULT_OVERLAP_TOLERANCE_MM, min_clearance_mm: float=MIN_WALKWAY_CLEARANCE_MM) -> ValidationResult

def check_dimensions(obj: dict, tolerance_mm: float) -> List[Issue]

def check_overlaps(objects: List[dict], tolerance_mm: float, min_overlap_mm: float=50.0) -> List[Issue]

def _compute_overlap(bounds_a: dict, bounds_b: dict, tolerance_mm: float) -> Optional[tuple]

def check_vertex_face_counts(obj: dict) -> List[Issue]

def check_standard_widths(obj: dict, settings: dict) -> List[Issue]

def check_run_continuity(layout: dict) -> List[Issue]

def check_construction(obj: dict, settings: dict) -> List[Issue]

def print_validation_report(result: ValidationResult) -> None
```

## src/kuchnie_core/catalog.py
```python
from __future__ import annotations
from construction import ConstructionMethod
from model import Accessory, CabinetInstance, DecompositionResult, EdgeBand, HandleSpec, MachiningOp, Panel, PanelRole
from legrabox import decompose_drawer_box, make_runner_accessory, validate_height_nl

def _handle_accessory_name(spec: HandleSpec) -> str

def _method_from_cab(cab: CabinetInstance) -> ConstructionMethod

def _normalize_edge_material(edge_type: str, board_material: str) -> str

def _body_eb(cab: CabinetInstance, length_mm: float) -> EdgeBand

def _front_eb(cab: CabinetInstance, length_mm: float) -> EdgeBand

def decompose_dolna_szufladowa(cab: CabinetInstance) -> DecompositionResult

def decompose_gorna_drzwiowa(cab: CabinetInstance) -> DecompositionResult

def decompose_dolna_drzwiowa(cab: CabinetInstance) -> DecompositionResult

def decompose_dolna_legrabox(cab: CabinetInstance) -> DecompositionResult
```

## src/kuchnie_core/serialize.py
```python
from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path
from model import CabinetInstance, Kitchen, Row, WorktopSegment

def kitchen_to_dict(kitchen: Kitchen) -> dict

def kitchen_to_json(kitchen: Kitchen, path: str | Path) -> Path

def kitchen_to_json_str(kitchen: Kitchen) -> str

def _build_cabinet(d: dict) -> CabinetInstance

def _build_row(d: dict) -> Row

def _build_worktop(d: dict) -> WorktopSegment

def kitchen_from_dict(data: dict) -> Kitchen

def kitchen_from_json(path: str | Path) -> Kitchen

def kitchen_from_json_str(text: str) -> Kitchen
```

## src/kuchnie_core/materials/sqlite_repository.py
```python
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from exceptions import CatalogUnavailableError
from models import EdgeInfo, VariantInfo, WorktopInfo
from protocol import MaterialCatalog

class SqliteMaterialCatalog
    def __init__(self, db_path: str | Path)
    def _connect(self) -> sqlite3.Connection
    def close(self) -> None
    def get_variant(self, code: str) -> VariantInfo | None
    def get_edge(self, code: str) -> EdgeInfo | None
    def find_worktops(self, decor_code: str) -> list[WorktopInfo]
    def find_edges_for_variant(self, variant_code: str) -> list[EdgeInfo]

```

## src/kuchnie_core/materials/models.py
```python
from __future__ import annotations
from dataclasses import dataclass, field

class VariantInfo
    pass

class EdgeInfo
    pass

class WorktopInfo
    pass

class PropertyFlag
    pass

class AvailabilityInfo
    pass

```

## src/kuchnie_core/materials/protocol.py
```python
from __future__ import annotations
from typing import Protocol, runtime_checkable
from models import EdgeInfo, VariantInfo, WorktopInfo

class MaterialCatalog(Protocol)
    def get_variant(self, code: str) -> VariantInfo | None
    def get_edge(self, code: str) -> EdgeInfo | None
    def find_worktops(self, decor_code: str) -> list[WorktopInfo]
    def find_edges_for_variant(self, variant_code: str) -> list[EdgeInfo]

```

## src/kuchnie_core/materials/__init__.py
```python
from exceptions import CatalogUnavailableError, EdgeNotFoundError, MaterialCatalogError, MaterialNotFoundError
from models import AvailabilityInfo, EdgeInfo, PropertyFlag, VariantInfo, WorktopInfo
from protocol import MaterialCatalog
from resolver import MaterialResolver
from sqlite_repository import SqliteMaterialCatalog

```

## src/kuchnie_core/materials/resolver.py
```python
from __future__ import annotations
from exceptions import MaterialNotFoundError
from models import EdgeInfo, VariantInfo, WorktopInfo
from protocol import MaterialCatalog

class MaterialResolver
    def __init__(self, catalog: MaterialCatalog, cache_size: int=512)
    def resolve(self, code: str) -> VariantInfo
    def try_resolve(self, code: str) -> VariantInfo | None
    def _put_variant(self, code: str, variant: VariantInfo) -> None
    def resolve_edge(self, code: str) -> EdgeInfo
    def resolve_edges(self, variant_code: str) -> list[EdgeInfo]
    def resolve_worktops(self, decor_code: str) -> list[WorktopInfo]
    def cache_stats(self) -> dict[str, int]
    def clear_cache(self) -> None

```

## src/kuchnie_core/materials/exceptions.py
```python
class MaterialCatalogError(Exception)
    pass

class MaterialNotFoundError(MaterialCatalogError)
    def __init__(self, code: str)

class EdgeNotFoundError(MaterialCatalogError)
    def __init__(self, code: str)

class CatalogUnavailableError(MaterialCatalogError)
    def __init__(self, path: str, cause: Exception | None=None)

```

## src/kuchnie_core/construction.py
```python
from __future__ import annotations
from dataclasses import dataclass

class ConstructionMethod
    def carcass_bottom_width(self, cabinet_width_mm: int) -> int
    def back_panel_width(self, cabinet_width_mm: int) -> int
    def back_panel_height(self, side_height_mm: int) -> int
    def shelf_width(self, cabinet_width_mm: int) -> int
    def door_width(self, cabinet_width_mm: int, door_count: int=1) -> float
    def door_height(self, cabinet_height_mm: int) -> int
    def drawer_front_width(self, cabinet_width_mm: int, margin_mm: int=3) -> int
    def validate_cabinet_width(self, cabinet_width_mm: int) -> list[str]

class ConstructionMethodRegistry
    def __init__(self) -> None
    def __len__(self) -> int
    def register(self, method: ConstructionMethod) -> None
    def get(self, method_id: str) -> ConstructionMethod
    def list_ids(self) -> list[str]
    def default(cls) -> ConstructionMethodRegistry

class CabinetGeometry
    def internal_width(self) -> float
    def internal_depth(self) -> float
    def internal_height(self) -> float
    def side_panel_width(self) -> float
    def side_panel_height(self) -> float
    def bottom_panel_width(self) -> float
    def bottom_panel_depth(self) -> float
    def back_panel_width(self) -> float
    def back_panel_height(self) -> float
    def front_dimensions(self, overlay_side: float=DEFAULT_OVERLAY_SIDE, overlay_top: float=DEFAULT_OVERLAY_TOP, overlay_bottom: float=DEFAULT_OVERLAY_BOTTOM) -> tuple
    def front_position(self, overlay_side: float=DEFAULT_OVERLAY_SIDE, overlay_top: float=DEFAULT_OVERLAY_TOP, overlay_bottom: float=DEFAULT_OVERLAY_BOTTOM) -> tuple

```

## src/kuchnie_core/legrabox.py
```python
from __future__ import annotations
from dataclasses import dataclass
from model import Accessory, MachiningOp, Panel

class LegraboxHeight
    pass

def lw(kb: int, side_thickness: int=0) -> int

def back_panel_width(lw_val: int) -> int

def base_panel_width(lw_val: int) -> int

def runner_screw_first_offset() -> int

def base_panel_depth(nl: int) -> int

def drawer_internal_width(lw_val: int) -> int

def drawer_internal_depth(nl: int) -> int

def validate_height_nl(height_code: str, nl: int) -> list[str]

def validate_capacity(nl: int, capacity_kg: int) -> list[str]

def decompose_drawer_box(cabinet_id: str, drawer_id: str, kb: int, nl: int, height_code: str, side_thickness: int, base_material: str='plyta_16mm', back_material: str='plyta_16mm', base_thickness: int=16, back_thickness: int=16) -> tuple[list[Panel], list[MachiningOp]]

def make_runner_accessory(cabinet_id: str, drawer_id: str, height_code: str, nl: int, capacity_kg: int=40, colour: str='SW-M', motion: str='BLUMOTION S') -> Accessory
```

## src/kuchnie_core/__init__.py
```python
from model import Accessory, BaseDoorConfig, BaseDrawerConfig, CabinetConfig, CabinetInstance, CargoConfig, CornerBlindConfig, CornerInternalConfig, DecompositionResult, DrawerSlot, EdgeBand, HandleSpec, Kitchen, OvenConfig, Panel, PanelRole, Row, ShelfPinSpec, SinkConfig, WorktopSegment
from construction import ConstructionMethod, ConstructionMethodRegistry
from blum_drawers import DrawerSystem, DrawerSystemFactory, TandemboxAntaro, Merivobox, Legrabox
from blum_hinges import BlumHinge, BlumClipTop110, BlumClipTop95, BlumClipTop155, HingeFactory, HingeGeometry, calculate_hinge_count
from recipe import PanelRecipe, RecipeSchema, evaluate_formula, RecipeValidationError
from decomposer import decompose
from bom import BOM, BOMItem, calculate_bom
from loader import load_cabinet, load_kitchen
from kitchen import all_panels, all_accessories, kitchen_bom, validate_rows
from serialize import kitchen_to_dict, kitchen_to_json, kitchen_to_json_str, kitchen_from_dict, kitchen_from_json, kitchen_from_json_str
from export.cutlist_csv import export_cutlist_csv, aggregate_panels
from export.edging_csv import export_edging_csv, collect_edging_rows
from geometry import Vector2D, Vector3D, BoundingBox, Transform2D, mm_to_m
from standards import KitchenStandards
from types import Direction, CabinetLevel, CabinetType, HandleType, DoorSide, Dimensions

```

## src/kuchnie_core/standards.py
```python
from dataclasses import dataclass
from typing import List, Set
from kuchnie_core.types import Dimensions

class KitchenStandards
    def base_total_height(self) -> float
    def standard_widths(self) -> Set[float]
    def is_standard_width(self, width: float) -> bool
    def get_dimensions(self, level: str) -> Dimensions

```

## src/kuchnie_core/types.py
```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import math

class Direction(Enum)
    def dx(self) -> float
    def dy(self) -> float
    def angle_rad(self) -> float
    def turn(self, turn_direction: str) -> 'Direction'

class CabinetLevel(Enum)
    pass

class CabinetType(Enum)
    def level(self) -> CabinetLevel
    def is_corner(self) -> bool

class HandleType(Enum)
    pass

class DoorSide(Enum)
    pass

class Dimensions
    def with_offsets(self, depth_offset: float=0, height_offset: float=0) -> 'Dimensions'

```

## src/kuchnie_core/kitchen.py
```python
from __future__ import annotations
from collections import defaultdict
from bom import BOM, calculate_bom
from decomposer import decompose
from model import Accessory, CabinetInstance, DecompositionResult, Kitchen, Panel, Row

def decompose_kitchen(kitchen: Kitchen) -> dict[str, DecompositionResult]

def all_panels(kitchen: Kitchen) -> list[Panel]

def all_accessories(kitchen: Kitchen) -> list[Accessory]

def kitchen_bom(kitchen: Kitchen, board_prices: dict[str, float] | None=None, edge_prices: dict[str, float] | None=None) -> BOM

def validate_rows(kitchen: Kitchen) -> list[str]
```

## src/kuchnie_core/model.py
```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Union

class PanelRole(str, Enum)
    pass

class MachiningOp
    pass

class EdgeBand
    pass

class Panel
    pass

class ShelfPinSpec
    pass

class HandleSpec
    pass

class DrawerSlot
    pass

class BaseDoorConfig
    pass

class BaseDrawerConfig
    pass

class CornerBlindConfig
    pass

class CornerInternalConfig
    pass

class SinkConfig
    pass

class CargoConfig
    pass

class OvenConfig
    pass

class Accessory
    pass

class CabinetInstance
    def __post_init__(self) -> None
    def validate(self) -> list[str]

class DecompositionResult
    pass

class Row
    def used_width_mm(self) -> float
    def remaining_mm(self) -> float

class GrainAxis
    pass

class WorktopSegment
    pass

class Kitchen
    pass

```

## src/kuchnie_core/blum_drawers.py
```python
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from model import Accessory, MachiningOp, Panel

class DrawerSystem(ABC)
    def height_codes(self) -> list[str]
    def side_height(self, code: str) -> float
    def back_panel_height(self, code: str) -> float
    def runner_clearance_per_side_mm(self) -> float
    def valid_nl(self) -> list[int]
    def is_valid_combo(self, code: str, nl: int) -> bool
    def lw(self, kb: int) -> int
    def base_panel_width(self, lw: int) -> int
    def back_panel_width(self, lw: int) -> int
    def base_panel_depth(self, nl: int) -> int
    def decompose_drawer_box(self, cabinet_id: str, drawer_id: str, kb: int, nl: int, height_code: str, base_material: str='plyta_16mm', back_material: str='plyta_16mm', base_thickness: int=16, back_thickness: int=16) -> tuple[list[Panel], list[MachiningOp]]
    def _runner_screw_ops(self, cabinet_id: str, drawer_id: str, nl: int) -> list[MachiningOp]
    def make_runner_accessory(self, cabinet_id: str, drawer_id: str, height_code: str, nl: int, capacity_kg: int=40, colour: str='SW-M', motion: str='BLUMOTION S') -> Accessory

class _TandemboxHeight
    pass

class TandemboxAntaro(DrawerSystem)
    def height_codes(self) -> list[str]
    def side_height(self, code: str) -> float
    def back_panel_height(self, code: str) -> float
    def runner_clearance_per_side_mm(self) -> float
    def valid_nl(self) -> list[int]
    def is_valid_combo(self, code: str, nl: int) -> bool

class Merivobox(DrawerSystem)
    def height_codes(self) -> list[str]
    def side_height(self, code: str) -> float
    def back_panel_height(self, code: str) -> float
    def runner_clearance_per_side_mm(self) -> float
    def valid_nl(self) -> list[int]
    def is_valid_combo(self, code: str, nl: int) -> bool

class Legrabox(DrawerSystem)
    def height_codes(self) -> list[str]
    def side_height(self, code: str) -> float
    def back_panel_height(self, code: str) -> float
    def runner_clearance_per_side_mm(self) -> float
    def valid_nl(self) -> list[int]
    def is_valid_combo(self, code: str, nl: int) -> bool

class DrawerSystemFactory
    def get(system_id: str) -> DrawerSystem
    def list_ids() -> list[str]

```

## src/kuchnie_core/loader.py
```python
from pathlib import Path
import yaml
from model import BaseDoorConfig, BaseDrawerConfig, CabinetConfig, CabinetInstance, CargoConfig, CornerBlindConfig, CornerInternalConfig, DrawerSlot, HandleSpec, Kitchen, OvenConfig, Row, ShelfPinSpec, SinkConfig, WorktopSegment

def _handle_spec_from_polish(d: dict | None) -> HandleSpec | None

def _shelf_pins_from_polish(d: dict | None) -> ShelfPinSpec

def _shelf_pins_from_schema(d: dict | None) -> ShelfPinSpec

def _handle_spec_from_schema(d: dict | None) -> HandleSpec | None

def _shelf_positions(cab: CabinetInstance) -> list[float]

def _door_hinge_counts(cab: CabinetInstance) -> list[int]

def _drawer_slot_from_dict(d: dict) -> DrawerSlot

def _synthesise_config(cab: CabinetInstance) -> CabinetConfig | None

def _apply_synthesised_config(cab: CabinetInstance) -> CabinetInstance

def load_cabinet(yaml_path: str | Path) -> CabinetInstance

def _cabinet_from_schema(cab_data: dict) -> CabinetInstance

def load_kitchen(yaml_path: str | Path) -> Kitchen

def load_kitchen_from_schema(yaml_path: str | Path) -> Kitchen

def _load_schema_format(data: dict, path: Path) -> Kitchen
```

## src/kuchnie_core/bom.py
```python
from dataclasses import dataclass, field
from model import DecompositionResult

class BOMItem
    pass

class BOM
    pass

def calculate_bom(result: DecompositionResult, board_prices: dict[str, float] | None=None, edge_prices: dict[str, float] | None=None) -> BOM
```

## src/kuchnie_core/geometry.py
```python
from dataclasses import dataclass
from typing import Tuple
import math

class Vector2D
    def __add__(self, other: 'Vector2D') -> 'Vector2D'
    def __sub__(self, other: 'Vector2D') -> 'Vector2D'
    def __mul__(self, scalar: float) -> 'Vector2D'
    def __rmul__(self, scalar: float) -> 'Vector2D'
    def dot(self, other: 'Vector2D') -> float
    def length(self) -> float
    def normalized(self) -> 'Vector2D'
    def perpendicular(self) -> 'Vector2D'
    def to_tuple(self) -> Tuple[float, float]

class Vector3D
    def __add__(self, other: 'Vector3D') -> 'Vector3D'
    def __sub__(self, other: 'Vector3D') -> 'Vector3D'
    def __mul__(self, scalar: float) -> 'Vector3D'
    def __rmul__(self, scalar: float) -> 'Vector3D'
    def dot(self, other: 'Vector3D') -> float
    def cross(self, other: 'Vector3D') -> 'Vector3D'
    def length(self) -> float
    def normalized(self) -> 'Vector3D'
    def to_tuple(self) -> Tuple[float, float, float]
    def to_mm(self) -> 'Vector3D'
    def to_m(self) -> 'Vector3D'

class BoundingBox
    def width(self) -> float
    def depth(self) -> float
    def height(self) -> float
    def center(self) -> Vector3D
    def contains_point(self, point: Vector3D) -> bool
    def intersects(self, other: 'BoundingBox') -> bool

class Transform2D
    def from_rotation(cls, angle_rad: float) -> 'Transform2D'
    def from_translation(cls, tx: float, ty: float) -> 'Transform2D'
    def from_position_and_direction(cls, x: float, y: float, dx: float, dy: float) -> 'Transform2D'
    def apply_to_point(self, point: Vector2D) -> Vector2D
    def apply_to_vector(self, vec: Vector2D) -> Vector2D

def mm_to_m(mm: float) -> float
```

## src/kuchnie_core/decomposer.py
```python
from model import CabinetInstance, DecompositionResult
from catalog import TYPE_REGISTRY

def decompose(cab: CabinetInstance) -> DecompositionResult
```

## src/kuchnie_core/recipe.py
```python
from __future__ import annotations
import ast
import operator
from dataclasses import dataclass, field
from typing import Any

class RecipeValidationError(Exception)
    pass

class PanelRecipe
    def compute_width(self, context: dict[str, float]) -> float
    def compute_height(self, context: dict[str, float]) -> float
    def compute_thickness(self, context: dict[str, float]) -> float

class RecipeSchema
    def from_dict(cls, data: dict[str, Any]) -> RecipeSchema

def evaluate_formula(formula: str, context: dict[str, float]) -> float

def _eval_node(node: ast.AST, ctx: dict[str, float]) -> float
```

## src/kuchnie_core/export/cutlist_csv.py
```python
from __future__ import annotations
import csv
import io
from dataclasses import dataclass
from pathlib import Path
from kitchen import all_panels
from model import Kitchen, Panel

class CutPiece
    pass

def _edge_key(panel: Panel) -> tuple[bool, bool, bool, bool]

def aggregate_panels(panels: list[Panel]) -> list[CutPiece]

def _yn(b: bool) -> str

def pieces_to_csv(pieces: list[CutPiece]) -> str

def export_cutlist_csv(kitchen: Kitchen, path: str | Path) -> Path
```

## src/kuchnie_core/export/edging_csv.py
```python
from __future__ import annotations
import csv
import io
from dataclasses import dataclass
from pathlib import Path
from kitchen import all_panels
from model import Kitchen, Panel

class EdgingRow
    pass

def _edge_length_mm(panel: Panel, side: str) -> float

def collect_edging_rows(panels: list[Panel]) -> list[EdgingRow]

def rows_to_csv(rows: list[EdgingRow]) -> str

def export_edging_csv(kitchen: Kitchen, path: str | Path) -> Path
```

## src/kuchnie_core/blum_hinges.py
```python
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from model import Accessory

class HingeGeometry
    pass

class BlumHinge(ABC)
    def id(self) -> str
    def name(self) -> str
    def opening_angle_deg(self) -> int
    def cup_diameter_mm(self) -> int
    def cup_drill_depth_mm(self) -> int
    def mounting_type(self) -> str
    def overlay_types(self) -> list[str]
    def closing_type(self) -> str
    def is_default(self) -> bool
    def to_accessory(self, cabinet_id: str, door_id: str, quantity: int=2) -> Accessory
    def geometry(self) -> HingeGeometry

class BlumClipTop110(BlumHinge)
    def id(self) -> str
    def name(self) -> str
    def opening_angle_deg(self) -> int
    def cup_diameter_mm(self) -> int
    def cup_drill_depth_mm(self) -> int
    def mounting_type(self) -> str
    def overlay_types(self) -> list[str]
    def closing_type(self) -> str
    def is_default(self) -> bool

class BlumClipTop95(BlumHinge)
    def id(self) -> str
    def name(self) -> str
    def opening_angle_deg(self) -> int
    def cup_diameter_mm(self) -> int
    def cup_drill_depth_mm(self) -> int
    def mounting_type(self) -> str
    def overlay_types(self) -> list[str]
    def closing_type(self) -> str
    def is_default(self) -> bool

class BlumClipTop155(BlumHinge)
    def id(self) -> str
    def name(self) -> str
    def opening_angle_deg(self) -> int
    def cup_diameter_mm(self) -> int
    def cup_drill_depth_mm(self) -> int
    def mounting_type(self) -> str
    def overlay_types(self) -> list[str]
    def closing_type(self) -> str
    def is_default(self) -> bool

class HingeFactory
    def get(hinge_id: str) -> BlumHinge
    def get_default() -> BlumHinge
    def list_ids() -> list[str]

def calculate_hinge_count(door_height_mm: int) -> int
```

## src/kuchnie_core/schema.py
```python
from __future__ import annotations
from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

class DrawerSpec(BaseModel)
    def valid_height_code(cls, v: str) -> str
    def valid_nl(cls, v: int) -> int
    def valid_system(cls, v: str) -> str
    def valid_capacity(cls, v: int) -> int

class ShelfSpec(BaseModel)
    pass

class FrontSpec(BaseModel)
    def valid_front_type(cls, v: str) -> str
    def valid_side(cls, v: Optional[str]) -> Optional[str]

class HandleSpec(BaseModel)
    pass

class CabinetSpec(BaseModel)
    def valid_cabinet_type(cls, v: str) -> str
    def width_exceeds_sides(self) -> 'CabinetSpec'

class RowSpec(BaseModel)
    def cabinets_fit_in_wall(self) -> 'RowSpec'

class MaterialSpec(BaseModel)
    pass

class SettingsSpec(BaseModel)
    pass

class WorktopSpec(BaseModel)
    pass

class KitchenSchema(BaseModel)
    def from_yaml(cls, path: str | Path) -> KitchenSchema
    def to_yaml(self, path: str | Path) -> Path

```

