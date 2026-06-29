Please analzye my use cases and help me rethink scope and boundaries and in/out
based on feateure and best workflow patterns from Polyboard, PRO100, Winner Flex, TopSolid'Wood, PaletteCAD.


1. The first visit app can be disconnected from the system and I can manage decors separately to the catalog app right now.

2.  The output from First visit is not complicated just few decors I have to note. Thats it. 

3. Easy kitchen cost estimation and BOM was my  
idea to help user take smarter expensive decision. 
4. Drawers are costly more than simple cabinets. 
5. Corner cabinet can be cheeper or  expensive. 
6. Egger boards are more expensive than KronoSwiss.
7. So  I thought system could roughly generate BOM with costs estimation.  

8. When customer settles on core decisions I move to the next stage. 
9. I have to layout kitchen and add all cabinets to match space constraints and customer decisions,
10. Add table tops with proper locks,
11.  add handles, 
12. add splash back 
13. it all affects renders.
14. then I will generate renders for approval.

15. Then I need to be able to make CAM enrichments (maybe Blender home 5 extension or export in some format from it)
16. Enrichment phase (I need to be able to set cabinet construction type, grooves, drilling holes to hinges and Blum drawers (many options) 

17. Then I should be able to:
18.  make CAM level validation 
19. I have to have all board materials with right codes including edge banding.
20. Then to produce Cut list artifact (just CSV list since CNC has own nesting tool)
21. Then to have DXF drilling files for each board
22. BOM for hinges, handles, screws, Blum rides 


——

I know that plugin solve some GUI concerns that I would like to address. I'm not good in GUI. There are a lot of nice kitchen layout and drawing features.  
I know that plugin is on license but I'm going to use it as personal project anyway. Please analyze where is the best places to implement best patterns:

                                                                    
---                                                                                                                                                         
                                                                                                                                                            
## What each system does best                                                                                                                               
                                                                                                                                                            
| Software | Key pattern you should steal |                                                                                                                 
|---|---|  
| **PRO100** | Cabinet "macros" — template + parametric overrides. Visual drag-drop. Polish market knows this UX. |                                         
| **Polyboard** | **Construction Method** as a first-class entity, separate from cabinet definition. This is the cleanest architecture of all five. |       
| **Winner Flex** | Sub-product hierarchy (drawer is a sub-product of a cabinet). Material assignment decoupled from construction. |                        
| **TopSolid'Wood** | Feature-based operations (drill, groove, rabbet) as associative objects that survive dimension changes. |                             
| **PaletteCAD** | Object-in-room model. Render-ready placement separate from engineering data. |                                                           
                                                                                                                                                            
---                                                                                                                                                         
                                                                                                                                                            
## The convergent pattern (common to all five)                                                                                                              
                                                                                                                                                            
All five systems decompose the same way. The hierarchy is universal: 

```                                                                                                                                                         
Kitchen                                                                                                                                                     
 └─ Wall / Row                                                                                                                                              
     └─ Cabinet Instance          ← your "placed cabinet"                                                                                                   
         └─ Sub-assembly          ← drawer box, door group                                                                                                  
             └─ Panel             ← THE atomic unit                                                                                                         
                 ├─ Edge (front/back/left/right)                                                                                                            
                 └─ Machining Operations (holes, grooves, rabbets)                                                                                          
```                                                                                                                                                         
         
                                                                                                                                                            
**The atomic manufacturing unit is the Panel — not the cabinet.** Everything above panels is organizational. Everything below panels is decoration on that  
physical piece.                                                                                                                                             
                                                                                                                                                            
---                                                                                                                                                         
                                                                                                                                                            
## The three patterns that matter most for you                                                                                                              
                                                                                                                                                            
### Pattern 1 — Construction Method (from Polyboard) 
This is the one that will save you the most pain. Polyboard separates:                                                                                      
                                                                                                                                                            
- **What** a cabinet is (its role: base, tall, wall, corner)                                                                                                
- **How** it's built (its construction method: dowel, cam-lock, dado, glue)                                                                                 
                                                                                                                                                            
```                                                                                                                                                         
Cabinet Type = Role + Construction Method + Default Accessories                                                                                             
                                                                                                                                                            
  role:           "base_standard"                                                                                                                           
  construction:   "dowel_camlock_18mm"    ← reusable across many types                                                                                      
  accessories:    [hinges, shelf_pins, ...]                                                                                                                 
``` 
                                                                                                                                                            
Why this matters: if you change from cam-lock to dowel construction, you swap the method — you don't rewrite every cabinet type. One method change          
cascades correctly to all panels.                                                                                                                           
                                                                                                                                                            
**My recommendation:** Extract construction rules into a `ConstructionMethod` object. Your cabinet types reference a method, they don't embed the rules.    
                                                                                                                                                            
### Pattern 2 — Panel Derivation Formulas (from all five)                                                                                                   
                                                                                                                                                            
Every system uses formulas, not hardcoded values. Each panel's dimensions are expressions: 

```python                                                                                                                                                   
# NOT this:                                                                                                                                                 
shelf.width = 556  # hardcoded                                                                                                                              
                                                                                                                                                            
# THIS:                                                                                                                                                     
shelf.width = cabinet.width - 2 * side.thickness - 2 * back.recess                                                                                          
```                                                                                                                                                         
                                                                                                                                                            
The formula graph looks like:                                                                                                                               
                                                                                                                                                            
``` 
cabinet.width (600)                                                                                                                                         
  │                                                                                                                                                         
  ├─► side.width  = cabinet.depth                                                                                                                           
  │     └─► side.height = cabinet.height - plinth.height                                                                                                    
  │                                                                                                                                                         
  ├─► top.width   = cabinet.width - 2×side.thickness                                                                                                        
  │     └─► top.depth = cabinet.depth - back.thickness - back.recess                                                                                        
  │                                                                                                                                                         
  ├─► shelf.width = top.width - shelf_clearance                                                                                                             
  │     └─► shelf.depth = top.depth - shelf_clearance                                                                                                       
  │                                                                                                                                                         
  ├─► back.width  = cabinet.width - 2×side.thickness + 2×back.recess (fits in groove)  
  │                                                                                                                                                         
  └─► door.width  = (cabinet.width - gap) / door_count                                                                                                      
```                                                                                                                                                         
                                                                                                                                                            
**My recommendation:** Store formulas as data, not code. This is how Polyboard and Winner Flex do it — the formula tree is part of the cabinet type         
definition. Makes validation and UI preview possible.                                                                                                       
                                                                                                                                                            
### Pattern 3 — Material ≠ Construction (from Winner Flex)                                                                                                  
                                                                                                                                                            
Winner Flex's key insight: you can swap all materials (oak → white gloss) without touching construction. And you can change construction (dowel →           
cam-lock) without touching materials. 
```                                                                                                                                                         
Cabinet Instance                                                                                                                                            
  ├─ construction_ref  →  ConstructionMethod + dimensions                                                                                                   
  └─ material_ref      →  { body: "K001", front: "U702", ... }                                                                                              
```                                                                                                                                                         
                                                                                                                                                             
---                                                                                                                                                         
                                                                                                                                                            
## Validation (where TopSolid'Wood excels)  
                                                                                                                                                            
TopSolid validates at every level. For your system, the minimal validation gates:                                                                           
                                                                                                                                                            
| Gate | Checks |                                                                                                                                           
|------|--------|                                                                                                                                           
| **Cabinet valid** | Dimensions within type's min/max, required accessories assigned |                                                                     
| **Row valid** | Total cabinet widths ≤ wall width, no overlaps, gaps accounted |                                                                          
| **Kitchen valid** | No row conflicts, worktop segments cover all rows, plumbing/hob placed |                                                              
| **CAM ready** | All panels have positive dimensions, all edges assigned, all holes defined, cutouts don't exceed worktop bounds |                         
                                                                                                                                                            
---   
