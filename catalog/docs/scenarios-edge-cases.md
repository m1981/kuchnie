# Kitchen Builder — Scenarios & Edge Cases

## Scenarios

### S1: Browse → Assign (happy path)
```
User sees grid → clicks card → card appears in active sidebar slot
→ slot advances to next empty → user clicks another card → repeat
→ all required slots filled → "Zapisz jako szablon" enabled
```

### S2: Two-tone kitchen
```
User assigns K003 (oak) to "Front dolny"
→ sidebar auto-opens "Front górny" slot (highlighted)
→ user clicks K101 (white) → assigned to "Front górny"
→ result: oak bottoms + white tops
```

### S3: Single-tone kitchen
```
User assigns K8685 (white) to "Front dolny"
→ "Front górny" slot shows "pomiń" button
→ user clicks "pomiń" → slot collapses
→ kitchen uses same front for top and bottom
```

### S4: Start from template
```
User clicks "Dąb Craft + Biel" template in sidebar
→ all slots fill instantly
→ user swaps K093 (marble) for K200 (concrete) by clicking card
→ "Zapisz jako szablon" creates a new template
```

### S5: Change a slot
```
User clicks ✕ on "Blat" slot
→ slot empties
→ grid filters to show only worktop-role variants
→ user picks new worktop
```

### S6: Filter while building
```
User has 3 slots filled
→ types "dębowy" in search
→ grid filters to oak decors
→ assigns new front to "Front dolny" (replaces previous)
```

---

## Edge Cases

### E1: Discontinued decor
- Card shows "wycofany" badge (red)
- Can still be assigned (for existing kitchens)
- Warning in compatibility check: "Ten dekor jest wycofany"

### E2: No image
- Card shows "brak zdjęcia" placeholder (already implemented)
- No impact on assignment

### E3: Decor with no variants for selected role
- Example: decor has "front" role but no "blat" variant
- Card is grayed out for that role
- Tooltip: "Brak wariantu w roli 'blat'"

### E4: Incompatible combo
- Example: front K003 (oak) + worktop K8984 (navy)
- Compatibility check shows: "⚠️ Kontrast: dab + niebieski — odważne zestawienie"
- Still allowed (user might want bold)

### E5: Same decor for front + worktop
- Example: K8685 as front + 868S as worktop (same visual, different material)
- Allowed — monochromatic kitchen
- Compatibility: "✓ Monochromatyczna kuchnia — ten sam dekor"

### E6: Producer mismatch
- Example: Kronospan front + Swiss Krono worktop
- Allowed — cross-producer combo
- Info: "Dwóch producentów: KP + SK — sprawdź dostępność"

### E7: Empty required slot
- "Zapisz jako szablon" button is disabled
- Missing slots highlighted in red
- Tooltip: "Uzupełnij: Front dolny, Korpus, Blat"

### E8: Replacing an assigned slot
- User clicks a new card while a slot is filled
- Old assignment is replaced (not added)
- Card badge updates on both old and new cards

### E9: Worktop-only browsing
- User clicks "Blat" role tab in grid
→ grid shows only worktop variants
→ all worktop cards are clickable
→ clicking assigns to "Blat" slot specifically

### E10: Session persistence
- Sidebar state saved to localStorage
- Refresh preserves assignments
- "Wyczyść wszystko" clears localStorage + slots

---

## UI Interactions

### Click card → assign
1. Check which slot is active (highlighted)
2. If no active slot → default to first empty required slot
3. Assign variant to that slot
4. Update card badge (DÓŁ/GÓRA/KORPUS/BLAT)
5. Advance active slot to next empty

### Click ✕ on slot → clear
1. Remove assignment
2. Remove card badge in grid
3. Set this slot as active

### Click template → fill all
1. Fill all slots from template data
2. Update all card badges
3. Set first empty optional slot as active

### Role tab filter
1. "Wszystkie" → show all
2. "Front" → show only cards with front role
3. "Blat" → show only worktop variants
4. Active tab affects which slot clicking assigns to
