// shared/schema.js
// Validation schemas for Decor + Variant model.
// Usage: const { DecorsFileSchema } = require('./shared/schema');

const { z } = require('zod');

// ── Edge banding ──
const EdgeSchema = z.object({
    code: z.string().min(1, 'Edge code is required'),
    supplier: z.string().optional(),
    finish: z.string().optional(),
    material: z.string().optional(),
    thickness_mm: z.number().optional(),
    width_mm: z.number().optional()
});

// ── Color families ──
const COLOR_FAMILIES = [
    'bialy', 'bezowy', 'szary', 'czarny', 'brazowy', 'kremowy',
    'dab', 'orzech', 'jesion', 'buk', 'brzoza', 'olcha',
    'wisnia', 'klon', 'wenge', 'wiaz',
    'marmur', 'beton', 'lupek',
    'niebieski', 'zielony', 'czerwony', 'rozowy', 'zloty', 'srebrny',
    'metal', 'unikolor'
];

// ── Material types ──
const MATERIAL_TYPES = [
    'chipboard',      // płyta wiórowa laminowana
    'mdf_acrylic',    // MDF z powłoką akrylową
    'mdf_lacquered',  // MDF lakierowany
    'mdf_foil',       // MDF foliowany
    'compact',        // compact HPL
    'hpl',            // HPL na chipboard
    'worktop',        // blat roboczy
    'splashback',     // panel ścienny (splashback)
];

// ── Roles (element types) ──
const ROLES = [
    'carcass',     // korpus (boki, półki, dno)
    'front',       // front (drzwi, szufronty)
    'worktop',     // blat roboczy
    'splashback',  // panel ścienny
    'plinth',      // cokół
    'side_panel',  // panel boczny zabudowy
    'housing',     // maskownica (lodówka, zmywarka)
];

// ── Variant: specific material + format ──
const VariantSchema = z.object({
    id: z.string().min(1),
    material: z.enum(MATERIAL_TYPES),
    collection: z.string().min(1),
    structure: z.string().min(2).max(3),
    roles: z.array(z.enum(ROLES)).min(1),

    // Physical properties (optional — varies by material type)
    thickness_mm: z.number().optional(),
    format: z.array(z.number()).optional(),
    sidedness: z.enum(['one_sided', 'two_sided_same', 'two_sided_different']).optional(),

    // Availability
    express: z.array(z.number()).optional(),
    konfekcja: z.boolean().optional(),
    hdf_laminate: z.boolean().optional(),
    countertop: z.string().nullable().optional(),

    // Edge banding
    edge: EdgeSchema.optional(),

    // Multi-structure (e.g. "SM, BS, PD")
    multi_structures: z.string().optional(),

    notes: z.string().optional()
});

// ── Decor: abstract visual identity ──
const DecorSchema = z.object({
    id: z.string().min(1, 'Decor ID is required'),
    name: z.string().min(1, 'Decor name is required'),
    group: z.string(),
    color_family: z.enum(COLOR_FAMILIES),
    tags: z.array(z.string()).optional(),
    ncs: z.string().optional(),
    ral: z.string().optional(),
    pantone: z.string().optional(),
    img: z.string().optional(),
    notes: z.string().optional(),
    variants: z.array(VariantSchema).min(1, 'Decor must have at least one variant')
});

// ── Top-level file schema ──
const DecorsFileSchema = z.object({
    _comment: z.string().optional(),
    _generated: z.string().optional(),
    decors: z.array(DecorSchema)
});

module.exports = {
    COLOR_FAMILIES,
    MATERIAL_TYPES,
    ROLES,
    EdgeSchema,
    VariantSchema,
    DecorSchema,
    DecorsFileSchema
};
