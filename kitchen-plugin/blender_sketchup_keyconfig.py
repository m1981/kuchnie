"""
SketchUp-Style Keyconfig for Blender 4+ (macOS)
===============================================
Mimics SketchUp navigation in Blender's 3D Viewport.

macOS US keyboard layout assumed.
User physical remaps:
  - CapsLock  → acts as Left Shift (system-level)
  - RCmd      → acts as Right Option/Alt (system-level)

Install:
  1. Run in Blender's Scripting workspace, or
  2. Copy to: ~/Library/Application Support/Blender/4.x/scripts/startup/

Activate:
  Edit → Preferences → Keymap → "SketchUp" dropdown
"""

bl_info = {
    "name": "SketchUp Navigation",
    "author": "Interior Designer",
    "version": (1, 0, 0),
    "blender": (5, 1, 0),
    "location": "Edit > Preferences > Keymap",
    "description": "SketchUp-style viewport navigation for Blender",
    "category": "User Interface",
}

import bpy


# =============================================================================
# CONFIG — Change these to customize
# =============================================================================

KEYCONFIG_NAME = "SketchUp"

# Modifier keys (set True/False to match your system)
MOD_CTRL = False      # ⌃ Control
MOD_SHIFT = False     # ⇧ Shift (or CapsLock with your remap)
MOD_ALT = False       # ⌥ Option (or RCmd with your remap)
MOD_OSKEY = False     # ⌘ Command (left)

# Navigation keys
KEY_ORBIT = 'MIDDLEMOUSE'
KEY_PAN = 'MIDDLEMOUSE'
KEY_PAN_MOD_SHIFT = True    # Shift + MMB for pan
KEY_ZOOM = 'WHEELUPMOUSE'   # Scroll wheel (handled via enum)
KEY_ZOOM_IN = 'WHEELUPMOUSE'
KEY_ZOOM_OUT = 'WHEELDOWNMOUSE'

# SketchUp-style tool keys
KEY_ORBIT_TOOL = 'O'        # Temp orbit (hold)
KEY_PAN_TOOL = 'H'          # Temp pan (hold)
KEY_ZOOM_TOOL = 'Z'         # Temp zoom (hold+drag)

# Zoom Extents / Frame Selected
KEY_ZOOM_EXTENTS = 'HOME'   # No default in SketchUp; HOME is conventional
KEY_FRAME_SELECTED = 'NUMPAD_PERIOD'  # or use '.' 


# =============================================================================
# HELPERS
# =============================================================================

addon_keymaps = []


def remove_conflicting_items(km, keys_to_remove):
    """Remove existing keymap items that conflict with our bindings."""
    to_remove = []
    for kmi in km.keymap_items:
        for check in keys_to_remove:
            if (kmi.type == check.get('type', kmi.type) and
                kmi.shift == check.get('shift', kmi.shift) and
                kmi.ctrl == check.get('ctrl', kmi.ctrl) and
                kmi.alt == check.get('alt', kmi.alt) and
                kmi.oskey == check.get('oskey', kmi.oskey)):
                to_remove.append(kmi)
                break
    for kmi in to_remove:
        km.keymap_items.remove(kmi)


def add_key(km, idname, key, value='PRESS',
            ctrl=False, shift=False, alt=False, oskey=False,
            properties=None, head=False):
    """Add a keymap item and track it for cleanup."""
    kmi = km.keymap_items.new(
        idname=idname,
        type=key,
        value=value,
        ctrl=ctrl,
        shift=shift,
        alt=alt,
        oskey=oskey,
        head=head,
    )
    if properties:
        for attr, val in properties.items():
            setattr(kmi.properties, attr, val)
    addon_keymaps.append((km, kmi))
    return kmi


# =============================================================================
# 3D VIEWPORT NAVIGATION
# =============================================================================

def setup_3dview_navigation(kc):
    """
    Configure 3D Viewport to match SketchUp navigation.
    
    Blender defaults already match SketchUp for basic nav:
      - MMB drag       = Orbit       (same as SketchUp)
      - Shift+MMB drag = Pan         (same as SketchUp)
      - Scroll wheel   = Zoom        (same as SketchUp)
    
    We override the tool keys (O, H, Z) to be temporary navigation.
    """
    
    km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
    
    # -----------------------------------------------------------------
    # Remove Blender defaults for O, H, Z that would conflict
    # -----------------------------------------------------------------
    # O → default is "Proportional Editing" toggle in some contexts
    # H → default is "Hide Selected" (Object mode)
    # Z → default is "Shading" pie menu
    
    conflicts = [
        {'type': 'O', 'shift': False, 'ctrl': False, 'alt': False, 'oskey': False},
        {'type': 'H', 'shift': False, 'ctrl': False, 'alt': False, 'oskey': False},
        {'type': 'Z', 'shift': False, 'ctrl': False, 'alt': False, 'oskey': False},
    ]
    remove_conflicting_items(km, conflicts)
    
    # Also remove Z with Shift (Zoom Extents custom) if it exists
    conflicts_z = [
        {'type': 'Z', 'shift': True, 'ctrl': False, 'alt': False, 'oskey': False},
    ]
    remove_conflicting_items(km, conflicts_z)
    
    # -----------------------------------------------------------------
    # O → Toggle NDOF orbit mode / use view3d.rotate for temp orbit
    # -----------------------------------------------------------------
    # Blender 5.x view3d.view_orbit expects: ORBITLEFT/RIGHT/UP/DOWN
    # For SketchUp-style temp orbit, use view3d.rotate (free orbit)
    # User holds O then LMB+drag to orbit
    add_key(km,
        idname='view3d.rotate',
        key='O',
        value='PRESS',
        head=True,
    )
    
    # -----------------------------------------------------------------
    # H → Temp Pan (hold to pan, release to return)
    # -----------------------------------------------------------------
    add_key(km,
        idname='view3d.view_pan',
        key='H',
        value='PRESS',
        head=True,
    )
    
    # -----------------------------------------------------------------
    # Z → Temp Zoom (hold + drag up/down to zoom)
    # -----------------------------------------------------------------
    # Blender doesn't have a single "temp zoom" operator,
    # so we use view3d.zoom with a mapped input.
    # Alternative: bind to 'wm.call_menu_pie' for shading pie on Shift+Z
    
    add_key(km,
        idname='view3d.zoom',
        key='Z',
        value='PRESS',
        head=True,
    )
    
    # -----------------------------------------------------------------
    # Shift+Z → Zoom Extents (SketchUp custom)
    # -----------------------------------------------------------------
    add_key(km,
        idname='view3d.view_all',
        key='Z',
        value='PRESS',
        shift=True,
        properties={'center': False},
        head=True,
    )
    
    # -----------------------------------------------------------------
    # Zoom to Selected (very useful for interior detail work)
    # -----------------------------------------------------------------
    # Numpad . or just period
    add_key(km,
        idname='view3d.view_selected',
        key='NUMPAD_PERIOD',
        value='PRESS',
        head=True,
    )
    
    # -----------------------------------------------------------------
    # Home → View All (Zoom Extents equivalent)
    # -----------------------------------------------------------------
    # Blender already has this by default, but ensure it's there
    add_key(km,
        idname='view3d.view_all',
        key='HOME',
        value='PRESS',
        head=True,
    )
    
    return km


# =============================================================================
# OBJECT MODE — Remove conflicting H (hide) default
# =============================================================================

def setup_object_mode(kc):
    """Object mode tweaks to avoid conflicts with H = Pan."""
    
    km = kc.keymaps.new(name='Object Mode', space_type='EMPTY')
    
    # H → default is "Hide Selected" in Object mode — remove it
    conflicts = [
        {'type': 'H', 'shift': False, 'ctrl': False, 'alt': False, 'oskey': False},
    ]
    remove_conflicting_items(km, conflicts)
    
    # Rebind hide to something else if needed (e.g., Ctrl+H)
    add_key(km,
        idname='object.hide_view_set',
        key='H',
        value='PRESS',
        ctrl=True,
        properties={'unselected': False},
    )
    
    # Ctrl+Shift+H → Hide Unselected
    add_key(km,
        idname='object.hide_view_set',
        key='H',
        value='PRESS',
        ctrl=True,
        shift=True,
        properties={'unselected': True},
    )
    
    # Alt+H → Unhide All (keep Blender default, just verify)
    add_key(km,
        idname='object.hide_view_clear',
        key='H',
        value='PRESS',
        alt=True,
    )
    
    return km


# =============================================================================
# MESH EDIT MODE — Remove O (proportional) if needed
# =============================================================================

def setup_mesh_edit(kc):
    """Mesh edit mode tweaks to avoid conflicts with O = Orbit."""
    
    km = kc.keymaps.new(name='Mesh', space_type='EMPTY')
    
    # O → default is "Proportional Editing" toggle
    # Rebind to Alt+O instead
    conflicts = [
        {'type': 'O', 'shift': False, 'ctrl': False, 'alt': False, 'oskey': False},
    ]
    remove_conflicting_items(km, conflicts)
    
    add_key(km,
        idname='wm.context_toggle',
        key='O',
        value='PRESS',
        alt=True,
        properties={'data_path': 'tool_settings.use_proportional_edit'},
    )
    
    return km


# =============================================================================
# WINDOW (Global) — Additional useful shortcuts
# =============================================================================

def setup_window(kc):
    """Global shortcuts that work everywhere."""
    
    km = kc.keymaps.new(name='Window', space_type='EMPTY')
    
    # F6 → Quick render (viewport)
    add_key(km,
        idname='render.render',
        key='F6',
        value='PRESS',
        properties={'use_viewport': True},
    )
    
    # Ctrl+Z → Undo (should already exist, but ensure)
    # Ctrl+Shift+Z → Redo (should already exist)
    
    return km


# =============================================================================
# REGISTRATION
# =============================================================================

def register():
    """Create the SketchUp keyconfig."""
    wm = bpy.context.window_manager
    
    # Remove existing if re-registering
    if KEYCONFIG_NAME in wm.keyconfigs:
        kc_old = wm.keyconfigs[KEYCONFIG_NAME]
        # Can't easily remove keyconfigs, just clear and recreate
        for km in kc_old.keymaps:
            for kmi in km.keymap_items:
                km.keymap_items.remove(kmi)
    
    # Create new keyconfig (don't set as active — crashes during startup)
    kc = wm.keyconfigs.new(name=KEYCONFIG_NAME)
    
    # Setup each keymap area
    setup_3dview_navigation(kc)
    setup_object_mode(kc)
    setup_mesh_edit(kc)
    setup_window(kc)
    
    print(f"[{KEYCONFIG_NAME}] Keyconfig registered.")
    print(f"[{KEYCONFIG_NAME}] Activate: Edit → Preferences → Keymap → '{KEYCONFIG_NAME}'")


def unregister():
    """Remove all custom keymap items."""
    for km, kmi in addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    addon_keymaps.clear()
    
    print(f"[{KEYCONFIG_NAME}] Keyconfig unregistered.")


# =============================================================================
# RUN AS SCRIPT (for testing in Scripting workspace)
# =============================================================================

if __name__ == "__main__":
    # Clean up if re-running
    try:
        unregister()
    except Exception:
        pass
    
    register()
    
    print("\n" + "=" * 60)
    print("  SKETCHUP KEYCONFIG ACTIVE")
    print("=" * 60)
    print(f"  Keyconfig: {KEYCONFIG_NAME}")
    print(f"  Orbit:     MMB drag")
    print(f"  Pan:       Shift + MMB drag")
    print(f"  Zoom:      Scroll wheel")
    print(f"  O key:     Temp orbit")
    print(f"  H key:     Temp pan")
    print(f"  Z key:     Temp zoom")
    print(f"  Shift+Z:   Zoom Extents")
    print(f"  Home:      View All")
    print(f"  . (numpad): Frame Selected")
    print("=" * 60)
    print("\nActivate in: Edit → Preferences → Keymap → 'SketchUp'")
