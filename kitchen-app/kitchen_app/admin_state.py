import reflex as rx
from pydantic import BaseModel
from sqlmodel import select
from kitchen_erp.database import get_session
from kitchen_erp.models import Material, HardwareSet, HardwareRule


class MaterialUI(BaseModel):
    """ViewModel for material editing"""
    id: int
    name: str
    brand: str
    category: str
    price_per_unit: float
    unit: str


class HardwareUI(BaseModel):
    """ViewModel for hardware editing"""
    id: int
    name: str
    brand: str
    price_per_set: float


class HardwareRuleUI(BaseModel):
    """ViewModel for hardware rule editing"""
    id: int
    tag: str
    hardware_name: str
    qty_per_unit: int
    unit: str
    price: float
    description: str


class AdminState(rx.State):
    """Admin panel state for managing prices and catalog"""
    
    # Materials
    materials: list[MaterialUI] = []
    selected_material_id: int | None = None
    material_filter: str = "Board"  # Filter by category
    
    # Hardware
    hardware_sets: list[HardwareUI] = []
    selected_hardware_id: int | None = None
    
    # Hardware Rules (Tag-based)
    hardware_rules: list[HardwareRuleUI] = []
    selected_rule_id: int | None = None
    rule_filter: str = "all"  # Filter by tag
    
    # Edit forms
    edit_material_name: str = ""
    edit_material_brand: str = ""
    edit_material_price: float = 0.0
    edit_material_unit: str = "m2"
    edit_material_category: str = "Board"
    
    edit_hardware_name: str = ""
    edit_hardware_brand: str = ""
    edit_hardware_price: float = 0.0
    
    edit_rule_tag: str = "is_base"
    edit_rule_hardware_name: str = ""
    edit_rule_qty: int = 1
    edit_rule_unit: str = "pcs"
    edit_rule_price: float = 0.0
    edit_rule_description: str = ""
    
    # UI state
    show_material_form: bool = False
    show_hardware_form: bool = False
    show_rule_form: bool = False
    is_editing: bool = False
    
    def load_materials(self):
        """Load all materials from database"""
        with next(get_session()) as session:
            materials = session.exec(
                select(Material).where(Material.category == self.material_filter)
            ).all()
            
            self.materials = [
                MaterialUI(
                    id=m.id,
                    name=m.name,
                    brand=m.brand or "Generic",
                    category=m.category or "Board",
                    price_per_unit=m.price_per_unit,
                    unit=m.unit
                )
                for m in materials
            ]
    
    def load_hardware(self):
        """Load all hardware from database"""
        with next(get_session()) as session:
            hardware = session.exec(select(HardwareSet)).all()
            
            self.hardware_sets = [
                HardwareUI(
                    id=h.id,
                    name=h.name,
                    brand=h.brand or "Generic",
                    price_per_set=h.price_per_set
                )
                for h in hardware
            ]
    
    def load_hardware_rules(self):
        """Load all hardware rules from database"""
        with next(get_session()) as session:
            query = select(HardwareRule)
            if self.rule_filter != "all":
                query = query.where(HardwareRule.tag == self.rule_filter)
            
            rules = session.exec(query).all()
            
            self.hardware_rules = [
                HardwareRuleUI(
                    id=r.id,
                    tag=r.tag,
                    hardware_name=r.hardware_name,
                    qty_per_unit=r.qty_per_unit,
                    unit=r.unit,
                    price=r.price,
                    description=r.description or ""
                )
                for r in rules
            ]
    
    def set_material_filter(self, category: str):
        """Filter materials by category"""
        self.material_filter = category
        self.load_materials()
    
    # Material form setters
    def set_edit_material_name(self, value: str):
        self.edit_material_name = value
    
    def set_edit_material_brand(self, value: str):
        self.edit_material_brand = value
    
    def set_edit_material_price(self, value: str):
        try:
            self.edit_material_price = float(value) if value else 0.0
        except ValueError:
            self.edit_material_price = 0.0
    
    def set_edit_material_unit(self, value: str):
        self.edit_material_unit = value
    
    def set_edit_material_category(self, value: str):
        self.edit_material_category = value
    
    # Hardware form setters
    def set_edit_hardware_name(self, value: str):
        self.edit_hardware_name = value
    
    def set_edit_hardware_brand(self, value: str):
        self.edit_hardware_brand = value
    
    def set_edit_hardware_price(self, value: str):
        try:
            self.edit_hardware_price = float(value) if value else 0.0
        except ValueError:
            self.edit_hardware_price = 0.0
    
    # Hardware rule form setters
    def set_edit_rule_tag(self, value: str):
        self.edit_rule_tag = value
    
    def set_edit_rule_hardware_name(self, value: str):
        self.edit_rule_hardware_name = value
    
    def set_edit_rule_qty(self, value: str):
        try:
            self.edit_rule_qty = int(value) if value else 1
        except ValueError:
            self.edit_rule_qty = 1
    
    def set_edit_rule_unit(self, value: str):
        self.edit_rule_unit = value
    
    def set_edit_rule_price(self, value: str):
        try:
            self.edit_rule_price = float(value) if value else 0.0
        except ValueError:
            self.edit_rule_price = 0.0
    
    def set_edit_rule_description(self, value: str):
        self.edit_rule_description = value
    
    def set_rule_filter(self, tag: str):
        """Filter rules by tag"""
        self.rule_filter = tag
        self.load_hardware_rules()
    
    def open_new_material_form(self):
        """Open form to add new material"""
        self.is_editing = False
        self.edit_material_name = ""
        self.edit_material_brand = ""
        self.edit_material_price = 0.0
        self.edit_material_unit = "m2"
        self.edit_material_category = self.material_filter
        self.show_material_form = True
    
    def open_edit_material_form(self, material_id: int):
        """Open form to edit existing material"""
        with next(get_session()) as session:
            material = session.get(Material, material_id)
            if material:
                self.is_editing = True
                self.selected_material_id = material_id
                self.edit_material_name = material.name
                self.edit_material_brand = material.brand or ""
                self.edit_material_price = material.price_per_unit
                self.edit_material_unit = material.unit
                self.edit_material_category = material.category or "Board"
                self.show_material_form = True
    
    def save_material(self):
        """Save material (create or update)"""
        with next(get_session()) as session:
            if self.is_editing and self.selected_material_id:
                # Update existing
                material = session.get(Material, self.selected_material_id)
                if material:
                    material.name = self.edit_material_name
                    material.brand = self.edit_material_brand
                    material.price_per_unit = self.edit_material_price
                    material.unit = self.edit_material_unit
                    material.category = self.edit_material_category
            else:
                # Create new
                material = Material(
                    name=self.edit_material_name,
                    brand=self.edit_material_brand,
                    category=self.edit_material_category,
                    price_per_unit=self.edit_material_price,
                    unit=self.edit_material_unit
                )
                session.add(material)
            
            session.commit()
        
        self.show_material_form = False
        self.load_materials()
    
    def delete_material(self, material_id: int):
        """Delete a material"""
        with next(get_session()) as session:
            material = session.get(Material, material_id)
            if material:
                session.delete(material)
                session.commit()
        
        self.load_materials()
    
    def open_new_hardware_form(self):
        """Open form to add new hardware"""
        self.is_editing = False
        self.edit_hardware_name = ""
        self.edit_hardware_brand = ""
        self.edit_hardware_price = 0.0
        self.show_hardware_form = True
    
    def open_edit_hardware_form(self, hardware_id: int):
        """Open form to edit existing hardware"""
        with next(get_session()) as session:
            hardware = session.get(HardwareSet, hardware_id)
            if hardware:
                self.is_editing = True
                self.selected_hardware_id = hardware_id
                self.edit_hardware_name = hardware.name
                self.edit_hardware_brand = hardware.brand or ""
                self.edit_hardware_price = hardware.price_per_set
                self.show_hardware_form = True
    
    def save_hardware(self):
        """Save hardware (create or update)"""
        with next(get_session()) as session:
            if self.is_editing and self.selected_hardware_id:
                # Update existing
                hardware = session.get(HardwareSet, self.selected_hardware_id)
                if hardware:
                    hardware.name = self.edit_hardware_name
                    hardware.brand = self.edit_hardware_brand
                    hardware.price_per_set = self.edit_hardware_price
            else:
                # Create new
                hardware = HardwareSet(
                    name=self.edit_hardware_name,
                    brand=self.edit_hardware_brand,
                    price_per_set=self.edit_hardware_price
                )
                session.add(hardware)
            
            session.commit()
        
        self.show_hardware_form = False
        self.load_hardware()
    
    def delete_hardware(self, hardware_id: int):
        """Delete a hardware set"""
        with next(get_session()) as session:
            hardware = session.get(HardwareSet, hardware_id)
            if hardware:
                session.delete(hardware)
                session.commit()
        
        self.load_hardware()
    
    def open_new_rule_form(self):
        """Open form to add new hardware rule"""
        self.is_editing = False
        self.edit_rule_tag = "is_base"
        self.edit_rule_hardware_name = ""
        self.edit_rule_qty = 1
        self.edit_rule_unit = "pcs"
        self.edit_rule_price = 0.0
        self.edit_rule_description = ""
        self.show_rule_form = True
    
    def open_edit_rule_form(self, rule_id: int):
        """Open form to edit existing hardware rule"""
        with next(get_session()) as session:
            rule = session.get(HardwareRule, rule_id)
            if rule:
                self.is_editing = True
                self.selected_rule_id = rule_id
                self.edit_rule_tag = rule.tag
                self.edit_rule_hardware_name = rule.hardware_name
                self.edit_rule_qty = rule.qty_per_unit
                self.edit_rule_unit = rule.unit
                self.edit_rule_price = rule.price
                self.edit_rule_description = rule.description or ""
                self.show_rule_form = True
    
    def save_hardware_rule(self):
        """Save hardware rule (create or update)"""
        with next(get_session()) as session:
            if self.is_editing and self.selected_rule_id:
                # Update existing
                rule = session.get(HardwareRule, self.selected_rule_id)
                if rule:
                    rule.tag = self.edit_rule_tag
                    rule.hardware_name = self.edit_rule_hardware_name
                    rule.qty_per_unit = self.edit_rule_qty
                    rule.unit = self.edit_rule_unit
                    rule.price = self.edit_rule_price
                    rule.description = self.edit_rule_description
            else:
                # Create new
                rule = HardwareRule(
                    tag=self.edit_rule_tag,
                    hardware_name=self.edit_rule_hardware_name,
                    qty_per_unit=self.edit_rule_qty,
                    unit=self.edit_rule_unit,
                    price=self.edit_rule_price,
                    description=self.edit_rule_description
                )
                session.add(rule)
            
            session.commit()
        
        self.show_rule_form = False
        self.load_hardware_rules()
    
    def delete_hardware_rule(self, rule_id: int):
        """Delete a hardware rule"""
        with next(get_session()) as session:
            rule = session.get(HardwareRule, rule_id)
            if rule:
                session.delete(rule)
                session.commit()
        
        self.load_hardware_rules()
    
    def initialize_default_rules(self):
        """Initialize database with default hardware rules"""
        from kitchen_erp.rules_engine import get_default_hardware_rules
        
        with next(get_session()) as session:
            # Check if rules already exist
            existing = session.exec(select(HardwareRule)).first()
            if existing:
                return  # Don't overwrite existing rules
            
            # Load defaults
            default_rules = get_default_hardware_rules()
            
            for tag, rules_list in default_rules.items():
                for rule_data in rules_list:
                    rule = HardwareRule(
                        tag=tag,
                        hardware_name=rule_data["name"],
                        qty_per_unit=rule_data["qty_per_unit"],
                        unit=rule_data["unit"],
                        price=rule_data["price"],
                        description=f"Auto-added for {tag}"
                    )
                    session.add(rule)
            
            session.commit()
        
        self.load_hardware_rules()
    
    def cancel_form(self):
        """Close any open form"""
        self.show_material_form = False
        self.show_hardware_form = False
        self.show_rule_form = False
