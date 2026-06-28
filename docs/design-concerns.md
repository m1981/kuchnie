 Analysis: Kitchen Design System Architecture                                                                                                               
                                                                                                                                                            
 As a commercial Python developer in the kitchen industry, here's my analysis of your system:                                                               
                                                                                                                                                            
 ────────────────────────────────────────────────────────────────────────────────                                                                           
                                                                                                                                                            
 🏗️ System Overview                                                                                                                                         
                                                                                                                                                            
 You have 6 distinct applications that form a kitchen design ecosystem:                                                                                     
                                                                                                                                                            
 ┌───────────────────────┬─────────────────────────────────────┬──────────────────────────────────┐                                                         
 │ Application           │ Purpose                             │ Tech Stack                       │                                                         
 ├───────────────────────┼─────────────────────────────────────┼──────────────────────────────────┤                                                         
 │ catalog/              │ Material/decor database management  │ Python, SQLite, YAML, FastAPI    │                                                         
 ├───────────────────────┼─────────────────────────────────────┼──────────────────────────────────┤                                                         
 │ kitchen-app/          │ Kitchen configurator UI (web)       │ Reflex (React wrapper), SQLModel │                                                         
 ├───────────────────────┼─────────────────────────────────────┼──────────────────────────────────┤                                                         
 │ kitchen-cad/          │ Panel cutting/drilling calculations │ Python, Pydantic, DXF export     │                                                         
 ├───────────────────────┼─────────────────────────────────────┼──────────────────────────────────┤                                                         
 │ kitchen-plugin/       │ 3D visualization                    │ Blender Python API               │                                                         
 ├───────────────────────┼─────────────────────────────────────┼──────────────────────────────────┤                                                         
 │ krono-compositor-mvp/ │ Material texture compositing        │ FastAPI, OpenCV                  │                                                         
 ├───────────────────────┼─────────────────────────────────────┼──────────────────────────────────┤                                                         
 │ src/kuchnie_core/     │ Core domain model                   │ Pure Python, dataclasses         │                                                         
 └───────────────────────┴─────────────────────────────────────┴──────────────────────────────────┘                                                         
                                                                                                                                                            
 ────────────────────────────────────────────────────────────────────────────────                                                                           
                                                                                                                                                            
 📦 Application Breakdown                                                                                                                                   
                                                                                                                                                            
 ### 1. catalog/ — Material Catalog Manager                                                                                                                 
                                                                                                                                                            
 What it does:                                                                                                                                              
 - Manages producers (Kronospan, Kronoswiss, etc.)                                                                                                          
 - Stores materials, decors, variants, edges                                                                                                                
 - Handles pairings (which decor goes with which edge)                                                                                                      
 - Imports from YAML → SQLite                                                                                                                               
 - Provides FastAPI endpoints for querying                                                                                                                  
                                                                                                                                                            
 Domain concepts:                                                                                                                                           
 - Producer → MaterialType → Collection → Material → Decor → Variant                                                                                        
 - Pairings (decor + edge combinations)                                                                                                                     
 - Structures (finish types: ST10, SM, etc.)                                                                                                                
                                                                                                                                                            
 Boundaries:                                                                                                                                                
 - ✅ Clean separation: domain models → importer → API                                                                                                      
 - ⚠️ Tightly coupled to SQLite (no repository abstraction)                                                                                                 
 - ⚠️ YAML generators per-producer (Kronospan, Kronoswiss) — not pluggable                                                                                  
                                                                                                                                                            
 ────────────────────────────────────────────────────────────────────────────────                                                                           
                                                                                                                                                            
 ### 2. kitchen-app/ — Kitchen Configurator (Reflex Web App)                                                                                                
                                                                                                                                                            
 What it does:                                                                                                                                              
 - Interactive kitchen layout editor                                                                                                                        
 - Cabinet placement on runs/walls                                                                                                                          
 - BOM (Bill of Materials) generation                                                                                                                       
 - Cost calculation with trace                                                                                                                              
 - Admin panel for materials/hardware/rules                                                                                                                 
 - IKEA layout import                                                                                                                                       
                                                                                                                                                            
 Domain concepts:                                                                                                                                           
 - Project → Cabinet → Material + HardwareSet                                                                                                               
 - BOMGenerator: decomposes cabinet into parts                                                                                                              
 - RulesEngine: applies hardware rules based on tags                                                                                                        
 - PurchasingStrategy: calculates material needs (sheets, linear, countertop)                                                                               
                                                                                                                                                            
 Boundaries:                                                                                                                                                
 - ✅ Good separation: models.py, bom_generator.py, rules_engine.py, purchasing.py                                                                          
 - ✅ Recipe-based BOM generation (JSON recipes)                                                                                                            
 - ⚠️ State management in Reflex is complex (KitchenState has 30+ methods)                                                                                  
 - ⚠️ Circular imports visible (models.py imports bom_generator, bom_generator imports models)                                                              
                                                                                                                                                            
 Concerns:                                                                                                                                                  
                                                                                                                                                            
 ```python                                                                                                                                                  
   # Circular dependency pattern:                                                                                                                           
   # models.py → bom_generator.py → models.py                                                                                                               
   class Cabinet(SQLModel):                                                                                                                                 
       def calculate_cost(self, defaults, waste_factor):                                                                                                    
           from kitchen_erp.bom_generator import BOMGenerator  # Lazy import to break cycle                                                                 
 ```                                                                                                                                                        
                                                                                                                                                            
 ────────────────────────────────────────────────────────────────────────────────                                                                           
                                                                                                                                                            
 ### 3. kitchen-cad/ — Panel Calculator & DXF Generator                                                                                                     
                                                                                                                                                            
 What it does:                                                                                                                                              
 - Calculates panel dimensions from cabinet specs                                                                                                           
 - Generates System 32 drilling patterns                                                                                                                    
 - Exports cutting lists (CSV)                                                                                                                              
 - Exports edging lists (CSV)                                                                                                                               
 - Generates DXF files for CNC machines (Legrabox side panels)                                                                                              
                                                                                                                                                            
 Domain concepts:                                                                                                                                           
 - CorpusSpec → Panel[] (with DrillPoint[], EdgeBand[])                                                                                                     
 - Cabinet types: Base, Drawer, CornerBlind, CornerInternal, Sink, Cargo, Oven                                                                              
 - System 32: 32mm grid, offset from edge                                                                                                                   
                                                                                                                                                            
 Boundaries:                                                                                                                                                
 - ✅ Pure calculation layer (no UI dependencies)                                                                                                           
 - ✅ Pydantic models for validation                                                                                                                        
 - ✅ Clean separation: models → panel_calculator → drill_engine → csv_generator                                                                            
 - ⚠️ DXF generation in separate script (legrabox_side_panel.py) — not integrated                                                                           
                                                                                                                                                            
 Concerns:                                                                                                                                                  
 - Panel calculator uses math.ceil for drawer fronts — rounding errors?                                                                                     
 - No validation that drawer specs fit within cabinet height                                                                                                
                                                                                                                                                            
 ────────────────────────────────────────────────────────────────────────────────                                                                           
                                                                                                                                                            
 ### 4. kitchen-plugin/ — Blender 3D Plugin                                                                                                                 
                                                                                                                                                            
 What it does:                                                                                                                                              
 - Builds 3D kitchen geometry in Blender                                                                                                                    
 - Exports wireframe renders                                                                                                                                
 - Generates geometry manifest (JSON) for validation                                                                                                        
 - Validates dimensions, overlaps, clearances                                                                                                               
                                                                                                                                                            
 Domain concepts:                                                                                                                                           
 - Config (YAML) → Layout → CabinetPlacement → Blender Objects                                                                                              
 - Wall/Room geometry with corner detection                                                                                                                 
 - CabinetGeometry: internal/external dimensions with overlays                                                                                              
                                                                                                                                                            
 Boundaries:                                                                                                                                                
 - ✅ Good domain separation: core/ (geometry, types) → kitchen/ (domain) → src/ (Blender)                                                                  
 - ✅ Validation layer (manifest_validator.py, validators.py)                                                                                               
 - ⚠️ Blender API coupling in geometry_builder.py                                                                                                           
                                                                                                                                                            
 Concerns:                                                                                                                                                  
                                                                                                                                                            
 ```python                                                                                                                                                  
   # geometry_manifest.py — Complex object classification                                                                                                   
   def _classify_object(name: str) -> str:                                                                                                                  
       # String-based classification — fragile                                                                                                              
       # Should use Blender custom properties instead                                                                                                       
 ```                                                                                                                                                        
                                                                                                                                                            
 ────────────────────────────────────────────────────────────────────────────────                                                                           
                                                                                                                                                            
 ### 5. krono-compositor-mvp/ — Material Texture Compositor                                                                                                 
                                                                                                                                                            
 What it does:                                                                                                                                              
 - Composites material textures onto 3D renders                                                                                                             
 - UV warping for perspective correction                                                                                                                    
 - Zone-based material application (front, carcass, countertop)                                                                                             
 - FastAPI endpoint for render requests                                                                                                                     
                                                                                                                                                            
 Domain concepts:                                                                                                                                           
 - RenderRequest → ZoneConfig[] → SceneCompositor.render_scene()                                                                                            
 - UV maps, masks, texture tiling                                                                                                                           
                                                                                                                                                            
 Boundaries:                                                                                                                                                
 - ✅ Clean hexagonal architecture (domain/interfaces.py → infrastructure/opencv_impl.py)                                                                   
 - ✅ Protocol-based interfaces (testable)                                                                                                                  
 - ⚠️ Hardcoded catalog in presentation/catalog_db.py                                                                                                       
                                                                                                                                                            
 ────────────────────────────────────────────────────────────────────────────────                                                                           
                                                                                                                                                            
 ### 6. src/kuchnie_core/ — Core Domain Library                                                                                                             
                                                                                                                                                            
 What it does:                                                                                                                                              
 - Pure domain model (Kitchen, Cabinet, Panel, Accessory)                                                                                                   
 - Cabinet decomposition (type → panels + accessories)                                                                                                      
 - BOM calculation                                                                                                                                          
 - Legrabox drawer box calculations                                                                                                                         
 - YAML/JSON serialization                                                                                                                                  
 - Cut list CSV export                                                                                                                                      
                                                                                                                                                            
 Domain concepts:                                                                                                                                           
 - Kitchen → Row[] → CabinetInstance[]                                                                                                                      
 - CabinetInstance → DecompositionResult → Panel[] + Accessory[]                                                                                            
 - Legrabox: NL (length), height codes (S, M, C)                                                                                                            
                                                                                                                                                            
 Boundaries:                                                                                                                                                
 - ✅ Pure Python, no external dependencies                                                                                                                 
 - ✅ Dataclass-based models (lightweight)                                                                                                                  
 - ✅ Clean decomposition catalog pattern                                                                                                                   
                                                                                                                                                            
 Concerns:                                                                                                                                                  
                                                                                                                                                            
 ```python                                                                                                                                                  
   # loader.py — Relative imports without package context                                                                                                   
   from model import Accessory, CabinetInstance  # Will fail if not in sys.path                                                                             
 ```                                                                                                                                                        
                                                                                                                                                            
 ────────────────────────────────────────────────────────────────────────────────                                                                           
                                                                                                                                                            
 🔴 Critical Issues                                                                                                                                         
                                                                                                                                                            
 ### 1. Duplicate Domain Models                                                                                                                             
                                                                                                                                                            
 You have 3 separate cabinet/panel models:                                                                                                                  
                                                                                                                                                            
 ┌───────────────────────────────────┬────────────────────┬──────────────────────┐                                                                          
 │ Location                          │ Model Type         │ Notes                │                                                                          
 ├───────────────────────────────────┼────────────────────┼──────────────────────┤                                                                          
 │ kitchen-cad/models.py             │ Pydantic BaseModel │ For CAD calculations │                                                                          
 ├───────────────────────────────────┼────────────────────┼──────────────────────┤                                                                          
 │ kitchen-app/kitchen_erp/models.py │ SQLModel           │ For database + UI    │                                                                          
 ├───────────────────────────────────┼────────────────────┼──────────────────────┤                                                                          
 │ src/kuchnie_core/model.py         │ Dataclass          │ For core domain      │                                                                          
 └───────────────────────────────────┴────────────────────┴──────────────────────┘                                                                          
                                                                                                                                                            
 Problem: Same concepts (Panel, Cabinet, Material) defined 3 times with different structures. Any change requires 3 updates.                                
                                                                                                                                                            
 Recommendation: Use kuchnie_core as the single source of truth. Other apps import from it.                                                                 
                                                                                                                                                            
 ────────────────────────────────────────────────────────────────────────────────                                                                           
                                                                                                                                                            
 ### 2. Circular Dependencies in kitchen-app                                                                                                                
                                                                                                                                                            
 ```                                                                                                                                                        
   models.py → bom_generator.py → models.py                                                                                                                 
   models.py → purchasing.py → models.py                                                                                                                    
 ```                                                                                                                                                        
                                                                                                                                                            
 Problem: Lazy imports used as workaround. This indicates architecture smell.                                                                               
                                                                                                                                                            
 Fix: Extract interfaces:                                                                                                                                   
                                                                                                                                                            
 ```python                                                                                                                                                  
   # interfaces.py                                                                                                                                          
   from abc import ABC, abstractmethod                                                                                                                      
                                                                                                                                                            
   class CostCalculator(ABC):                                                                                                                               
       @abstractmethod                                                                                                                                      
       def calculate(self, cabinet: 'CabinetProtocol') -> float: ...                                                                                        
 ```                                                                                                                                                        
                                                                                                                                                            
 ────────────────────────────────────────────────────────────────────────────────                                                                           
                                                                                                                                                            
 ### 3. Unit Inconsistencies                                                                                                                                
                                                                                                                                                            
 ┌─────────────────────┬─────────────────────────────────┬──────────┐                                                                                       
 │ Component           │ Units Used                      │ Expected │                                                                                       
 ├─────────────────────┼─────────────────────────────────┼──────────┤                                                                                       
 │ kitchen-cad         │ mm (float)                      │ mm ✓     │                                                                                       
 ├─────────────────────┼─────────────────────────────────┼──────────┤                                                                                       
 │ kitchen-plugin      │ mm (converted to m for Blender) │ mm ✓     │                                                                                       
 ├─────────────────────┼─────────────────────────────────┼──────────┤                                                                                       
 │ kitchen-app         │ Mixed (cm in UI, mm in DB?)     │ mm       │                                                                                       
 ├─────────────────────┼─────────────────────────────────┼──────────┤                                                                                       
 │ CABINET-VARIANTS.md │ cm (was) → mm (now)             │ mm ✓     │                                                                                       
 └─────────────────────┴─────────────────────────────────┴──────────┘                                                                                       
                                                                                                                                                            
 Problem: Any mm/cm mismatch will cause 10x errors in production.                                                                                           
                                                                                                                                                            
 ────────────────────────────────────────────────────────────────────────────────                                                                           
                                                                                                                                                            
 ### 4. No Shared Validation Layer                                                                                                                          
                                                                                                                                                            
 Each app validates independently:                                                                                                                          
 - kitchen-cad/models.py — Pydantic validators                                                                                                              
 - kitchen-plugin/src/validators.py — Custom validators                                                                                                     
 - kitchen-app/kitchen_erp/ — No visible validation                                                                                                         
                                                                                                                                                            
 Concern: A cabinet width validated in CAD might fail in Blender or vice versa.                                                                             
                                                                                                                                                            
 ────────────────────────────────────────────────────────────────────────────────                                                                           
                                                                                                                                                            
 🟡 Architectural Concerns                                                                                                                                  
                                                                                                                                                            
 ### 1. Technology Fragmentation                                                                                                                            
                                                                                                                                                            
 ┌──────────────────┬───────────────────────────────────┬───────────────────────────────────────────────────┐                                               
 │ Concern          │ Current State                     │ Risk                                              │                                               
 ├──────────────────┼───────────────────────────────────┼───────────────────────────────────────────────────┤                                               
 │ Web framework    │ Reflex (immature)                 │ Vendor lock-in, limited ecosystem                 │                                               
 ├──────────────────┼───────────────────────────────────┼───────────────────────────────────────────────────┤                                               
 │ Database         │ SQLite (catalog) + SQLModel (app) │ No migration strategy visible                     │                                               
 ├──────────────────┼───────────────────────────────────┼───────────────────────────────────────────────────┤                                               
 │ 3D Engine        │ Blender (GPL)                     │ Cannot distribute commercially without compliance │                                               
 ├──────────────────┼───────────────────────────────────┼───────────────────────────────────────────────────┤                                               
 │ Image processing │ OpenCV                            │ Good choice ✓                                     │                                               
 └──────────────────┴───────────────────────────────────┴───────────────────────────────────────────────────┘                                               
                                                                                                                                                            
 ### 2. Missing Service Layer                                                                                                                               
                                                                                                                                                            
 kitchen-app has:                                                                                                                                           
 - state.py (30+ methods in KitchenState)                                                                                                                   
 - No service layer between state and database                                                                                                              
                                                                                                                                                            
 Problem: Business logic mixed with UI state management.                                                                                                    
                                                                                                                                                            
 Fix:                                                                                                                                                       
                                                                                                                                                            
 ```python                                                                                                                                                  
   # kitchen_service.py                                                                                                                                     
   class KitchenService:                                                                                                                                    
       def __init__(self, session: Session):                                                                                                                
           self.session = session                                                                                                                           
                                                                                                                                                            
       def add_cabinet(self, project_id: int, cab_type: str) -> Cabinet:                                                                                    
           # Business logic here, not in state.py                                                                                                           
 ```                                                                                                                                                        
                                                                                                                                                            
 ────────────────────────────────────────────────────────────────────────────────                                                                           
                                                                                                                                                            
 ### 3. Recipe System Fragility                                                                                                                             
                                                                                                                                                            
 ```python                                                                                                                                                  
   # recipe_loader.py                                                                                                                                       
   def eval_formula(formula: str, cabinet_dims: dict[str, float]) -> float:                                                                                 
       # eval() usage — security risk if recipes from external sources                                                                                      
 ```                                                                                                                                                        
                                                                                                                                                            
 Concern: JSON recipes with eval() — potential code injection if recipes are user-generated.                                                                
                                                                                                                                                            
 ────────────────────────────────────────────────────────────────────────────────                                                                           
                                                                                                                                                            
 ### 4. No Event Sourcing / Audit Trail                                                                                                                     
                                                                                                                                                            
 For commercial kitchen manufacturing:                                                                                                                      
 - No traceability of design changes                                                                                                                        
 - No version control on BOMs                                                                                                                               
 - No audit log for cost changes                                                                                                                            
                                                                                                                                                            
 ────────────────────────────────────────────────────────────────────────────────                                                                           
                                                                                                                                                            
 📊 Dependency Graph (Current)                                                                                                                              
                                                                                                                                                            
 ```                                                                                                                                                        
   ┌─────────────────────────────────────────────────────────────────┐                                                                                      
   │                        Blender Plugin                           │                                                                                      
   │  (3D visualization, manifest export)                            │                                                                                      
   └─────────────────────────────────────────────────────────────────┘                                                                                      
                                 │                                                                                                                          
                                 ▼ (optional: reads manifest)                                                                                               
   ┌─────────────────────────────────────────────────────────────────┐                                                                                      
   │                     krono-compositor-mvp                        │                                                                                      
   │  (texture compositing on renders)                               │                                                                                      
   └─────────────────────────────────────────────────────────────────┘                                                                                      
                                                                                                                                                            
   ┌─────────────────────────────────────────────────────────────────┐                                                                                      
   │                        kitchen-cad                              │                                                                                      
   │  (panel calculations, DXF export)                               │                                                                                      
   └─────────────────────────────────────────────────────────────────┘                                                                                      
                                 │                                                                                                                          
                                 ▼ (shares models??)                                                                                                        
   ┌─────────────────────────────────────────────────────────────────┐                                                                                      
   │                        kitchen-app                              │                                                                                      
   │  (configurator UI, BOM, costing)                                │                                                                                      
   └─────────────────────────────────────────────────────────────────┘                                                                                      
                                 │                                                                                                                          
                                 ▼ (imports)                                                                                                                
   ┌─────────────────────────────────────────────────────────────────┐                                                                                      
   │                       kuchnie_core                              │                                                                                      
   │  (domain model, decomposition, BOM)                             │                                                                                      
   └─────────────────────────────────────────────────────────────────┘                                                                                      
                                                                                                                                                            
   ┌─────────────────────────────────────────────────────────────────┐                                                                                      
   │                         catalog                                 │                                                                                      
   │  (material database, YAML import)                               │                                                                                      
   └─────────────────────────────────────────────────────────────────┘                                                                                      
 ```                                                                                                                                                        
                                                                                                                                                            
 ────────────────────────────────────────────────────────────────────────────────                                                                           
                                                                                                                                                            
 🎯 Recommendations                                                                                                                                         
                                                                                                                                                            
 ### Immediate Fixes                                                                                                                                        
                                                                                                                                                            
 1. Unify domain models — single kuchnie_core package                                                                                                       
 2. Break circular deps — extract interfaces in kitchen-app                                                                                                 
 3. Standardize units — enforce mm everywhere with Pydantic confloat(gt=0)                                                                                  
 4. Replace eval() — use a safe expression evaluator (e.g., asteval)                                                                                        
                                                                                                                                                            
 ### Architecture Improvements                                                                                                                              
                                                                                                                                                            
 5. Add service layer to kitchen-app                                                                                                                        
 6. Repository pattern for catalog database access                                                                                                          
 7. Event sourcing for BOM/cost changes (commercial requirement)                                                                                            
 8. Plugin system for producers (instead of hardcoded Kronospan/Kronoswiss)                                                                                 
                                                                                                                                                            
 ### Technical Debt                                                                                                                                         
                                                                                                                                                            
 9. Type hints — many functions lack return types                                                                                                           
 10. Tests — no test files visible in the structure                                                                                                         
 11. CI/CD — no pipeline configuration                                                                                                                      
 12. Documentation — architecture docs exist but incomplete                                                                                                 
                                                                                                                                                            
 ────────────────────────────────────────────────────────────────────────────────                                                                           
                                                                                                                                                            
 💡 Industry-Specific Concerns                                                                                                                              
                                                                                                                                                            
 ┌────────────────────────────────────┬─────────────┬────────────────────────────────────────────────────────┐                                              
 │ Concern                            │ Your Status │ Industry Requirement                                   │                                              
 ├────────────────────────────────────┼─────────────┼────────────────────────────────────────────────────────┤                                              
 │ EGGER/Kronospan catalog compliance │ ✓ Partial   │ Must match official decor codes exactly                │                                              
 ├────────────────────────────────────┼─────────────┼────────────────────────────────────────────────────────┤                                              
 │ Blum hardware integration          │ ✓ Legrabox  │ Need full Blum catalog (Tandembox, Merivobox, Aventos) │                                              
 ├────────────────────────────────────┼─────────────┼────────────────────────────────────────────────────────┤                                              
 │ CNC machine output                 │ ✓ DXF       │ May need HOMOM/Biesse native format support            │                                              
 ├────────────────────────────────────┼─────────────┼────────────────────────────────────────────────────────┤                                              
 │ Edge banding tracking              │ ✓ Basic     │ Need supplier-specific edge codes                      │                                              
 ├────────────────────────────────────┼─────────────┼────────────────────────────────────────────────────────┤                                              
 │ Grain direction                    │ ✓ Modeled   │ Critical for wood decors — good                        │                                              
 ├────────────────────────────────────┼─────────────┼────────────────────────────────────────────────────────┤                                              
 │ Panel optimization                 │ ✗ Missing   │ Commercial requirement: nesting software integration   │                                              
 ├────────────────────────────────────┼─────────────┼────────────────────────────────────────────────────────┤                                                                             
 └────────────────────────────────────┴─────────────┴────────────────────────────────────────────────────────┘    