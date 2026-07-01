I'm solo developer and want to design and assembly kitchen cabinets for Wroclaw's customers. I'm going to develop and integrate system to be able to fulfill such usecase:

Use case: First visit

1.  I visit customer with at this new investment with decors from Kronospan, Egger.
2.  To help customer choose the initial material I open web app
3.  A few predefined 2.5D kitchen layouts popup
4.  I chose one
5.  I have a sidebar where I can change decors for ground cabinets, tall cabinets, wall cabinets, counter top, and splashback
6.  System is connection with backend to provide me 2.5D high quality image
7.  I repeat steps 6 and seven and doing screenshots (handled by ipad screenshot NO other feature needed) for all two setups customer likes most.
8.  I take measurement of the kitchen space for leter work

Use case: Easy kitchen cost estimation with BOM

1. I open web app
2. I use simple 2d layout system to make rows based on measurements (I don’t handle slants and difficult shapes and island in version 1.0)
3. I can easily add typical cabinet types from sidebar and use simple arrow system to move them left or right in rows
4. I can globally setup important dimensions
5. I can customize single cabinets to override dimensions or configuration
6. System knows board and accessory pricing so automatically update estimated cost (no nesting or any optimization at this point)
7. When I decided configuration is ready to send to customer feedback I click generate renders
8. System send rows and cabinets configuration with decor names to backend using (not CAD ready)
9. Backend generates blender files based on intermediate with proper textures based on decor names (Kronospan, Egger, etc)
10. I can import living setup to the scene and generate renders for customer to acceptation

Use case: CAM preparation

1. Customer accepted layout and decors.
2. I can tweak configuration in intermediate format too ensure every obstacle is addressed and vent wholes are present, grooves for led are added.
3. I runs CLI app to use intermediate format to generate cut list in CVS files compatible with e-rozrys, e-rozkroj I can upload them for nesting.
4. I run CLI app to use intermediate format to generate construction holes / dowel holes, hinge boring, panel rabbet, etc.
5. At this point system is able to provide estimated cost with accessories and nesting applied on our end (this is still estimation by let me tweak the configuration before sending to CNC. Important: CNC company enforces me to buy material and serve after getting pricing so I can’t use their system back and forth for cost calculation!
6. I send DXF files or similar to my CNC company to get pricing and after my acceptance they start the manufacturing
7. End
