// shared/schema.js
// Schematy walidacji YAML per producent
// Uzycie: const { CollectionFileSchema } = require('./shared/schema');

const { z } = require('zod');

// ── Obrzeze ──
const EdgeSchema = z.object({
    code: z.string().min(1, 'Edge code is required'),
    supplier: z.string().optional(),
    finish: z.string().optional(),
    material: z.string().optional(),
    thickness_mm: z.number().optional(),
    width_mm: z.number().optional()
});

// ── Dekor w Global Collection (chipboard) ──
const GlobalDecorSchema = z.object({
    id: z.string().min(1, 'Decor ID is required'),
    name: z.string().min(1, 'Decor name is required'),
    group: z.string(),
    structure: z.string().min(2).max(3),
    tags: z.array(z.string()).optional(),
    color_family: z.string().optional(),
    ncs: z.string().optional(),
    ral: z.string().optional(),
    pantone: z.string().optional(),
    express: z.array(z.number()).optional(),
    konfekcja: z.boolean(),
    countertop: z.string().nullable().optional(),
    hdf_laminate: z.boolean().optional(),
    cross_collections: z.array(z.string()).optional(),
    edge: EdgeSchema,
    notes: z.string().optional(),
    img: z.string().nullable().optional()
});

// ── Dekor w kolekcji specjalistycznej (MDF, Compact) ──
const SpecializedDecorSchema = z.object({
    id: z.string().min(1, 'Decor ID is required'),
    name: z.string().min(1, 'Decor name is required'),
    group: z.string(),
    structure: z.string().min(2).max(3),
    thickness_mm: z.number(),
    format: z.tuple([z.number(), z.number()]),
    sidedness: z.enum(['one_sided', 'two_sided_same', 'two_sided_different']),
    konfekcja: z.boolean(),
    global_decor_id: z.string().nullable(),
    edge: EdgeSchema,
    notes: z.string().optional(),
    img: z.string().nullable().optional()
});

// ── Plik kolekcji (dowolny typ dekoru) ──
const CollectionFileSchema = z.object({
    collection: z.string().min(1, 'Collection name is required'),
    decors: z.array(z.union([GlobalDecorSchema, SpecializedDecorSchema]))
});

module.exports = {
    EdgeSchema,
    GlobalDecorSchema,
    SpecializedDecorSchema,
    CollectionFileSchema
};
