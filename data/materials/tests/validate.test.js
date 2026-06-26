// tests/validate.test.js
// Validation tests for Decor + Variant model
// Run: cd data/materials && node --test tests/validate.test.js

const { describe, it, before } = require('node:test');
const assert = require('node:assert/strict');
const yaml = require('js-yaml');
const fs = require('fs');
const path = require('path');
const { DecorsFileSchema, COLOR_FAMILIES, MATERIAL_TYPES, ROLES } = require('../shared/schema');

const KRONOSPAN_DIR = path.join(__dirname, '..', 'kronospan');

function loadYaml(filePath) {
    return yaml.load(fs.readFileSync(filePath, 'utf8'));
}

function loadDecors() {
    const content = loadYaml(path.join(KRONOSPAN_DIR, 'decors.yaml'));
    return content.decors;
}

// ════════════════════════════════════════════════════════
// TEST 1: Schema validation
// ════════════════════════════════════════════════════════

describe('Schema Validation', () => {
    it('decors.yaml passes DecorsFileSchema', () => {
        const content = loadYaml(path.join(KRONOSPAN_DIR, 'decors.yaml'));
        const result = DecorsFileSchema.safeParse(content);
        assert.equal(result.success, true, JSON.stringify(result.error?.issues, null, 2));
    });

    it('all decors have at least one variant', () => {
        const decors = loadDecors();
        decors.forEach((d) => {
            assert.ok(d.variants.length >= 1, `Decor ${d.id}: no variants`);
        });
    });

    it('all variants have valid material type', () => {
        const decors = loadDecors();
        decors.forEach((d) => {
            d.variants.forEach((v) => {
                assert.ok(
                    MATERIAL_TYPES.includes(v.material),
                    `Decor ${d.id}, variant ${v.id}: invalid material "${v.material}"`
                );
            });
        });
    });

    it('all variants have valid roles', () => {
        const decors = loadDecors();
        decors.forEach((d) => {
            d.variants.forEach((v) => {
                v.roles.forEach((r) => {
                    assert.ok(
                        ROLES.includes(r),
                        `Decor ${d.id}, variant ${v.id}: invalid role "${r}"`
                    );
                });
            });
        });
    });
});

// ════════════════════════════════════════════════════════
// TEST 2: Identity model — K-prefix
// ════════════════════════════════════════════════════════

describe('Identity Model', () => {
    it('all decor IDs start with K', () => {
        const decors = loadDecors();
        decors.forEach((d) => {
            assert.ok(d.id.startsWith('K'), `Decor id="${d.id}" does not start with K`);
        });
    });

    it('all variant IDs follow {decor_id}-{material_suffix} pattern', () => {
        const decors = loadDecors();
        decors.forEach((d) => {
            d.variants.forEach((v) => {
                assert.ok(
                    v.id.startsWith(d.id + '-'),
                    `Variant ${v.id}: should start with ${d.id}-`
                );
                const suffix = v.id.slice(d.id.length + 1);
                assert.ok(
                    suffix.length >= 2,
                    `Variant ${v.id}: missing material suffix`
                );
            });
        });
    });

    it('no duplicate decor IDs', () => {
        const decors = loadDecors();
        const ids = decors.map((d) => d.id);
        const unique = new Set(ids);
        assert.equal(ids.length, unique.size, `Duplicate decor IDs found`);
    });

    it('no duplicate variant IDs across all decors', () => {
        const decors = loadDecors();
        const allVariantIds = decors.flatMap((d) => d.variants.map((v) => v.id));
        const unique = new Set(allVariantIds);
        assert.equal(
            allVariantIds.length,
            unique.size,
            `Duplicate variant IDs found: ${allVariantIds.filter((id, i) => allVariantIds.indexOf(id) !== i).join(', ')}`
        );
    });
});

// ════════════════════════════════════════════════════════
// TEST 3: Color family
// ════════════════════════════════════════════════════════

describe('Color Family', () => {
    it('all decors have valid color_family', () => {
        const decors = loadDecors();
        decors.forEach((d) => {
            assert.ok(d.color_family, `Decor ${d.id}: missing color_family`);
            assert.ok(
                COLOR_FAMILIES.includes(d.color_family),
                `Decor ${d.id}: invalid color_family "${d.color_family}"`
            );
        });
    });

    it('at least 15 distinct color families used', () => {
        const decors = loadDecors();
        const families = new Set(decors.map((d) => d.color_family));
        assert.ok(
            families.size >= 15,
            `Only ${families.size} color families used (expected ≥15)`
        );
    });
});

// ════════════════════════════════════════════════════════
// TEST 4: Multi-variant decor merging
// K8685, K0514, K7045 exist in both Global Collection
// (chipboard) and Acrylic Gloss (MDF). They must appear
// as ONE decor with TWO variants, not two separate decors.
// ════════════════════════════════════════════════════════

describe('Multi-variant Decors', () => {
    const MULTI_VARIANT_IDS = ['K8685', 'K0514', 'K7045'];
    let decors;

    before(() => {
        decors = loadDecors();
    });

    MULTI_VARIANT_IDS.forEach((id) => {
        it(`${id} has exactly 2 variants (chipboard + mdf_acrylic)`, () => {
            const decor = decors.find((d) => d.id === id);
            assert.ok(decor, `Decor ${id} not found`);
            assert.equal(decor.variants.length, 2, `Expected 2 variants for ${id}`);

            const materials = decor.variants.map((v) => v.material).sort();
            assert.deepEqual(materials, ['chipboard', 'mdf_acrylic']);
        });
    });

    it('total decors is 177 (not 180 — 3 merged)', () => {
        assert.equal(decors.length, 177);
    });

    it('total variants is 180 (same as before migration)', () => {
        const total = decors.reduce((s, d) => s + d.variants.length, 0);
        assert.equal(total, 180);
    });
});

// ════════════════════════════════════════════════════════
// TEST 5: Variant completeness
// ════════════════════════════════════════════════════════

describe('Variant Completeness', () => {
    let decors;

    before(() => {
        decors = loadDecors();
    });

    it('only K110 has carcass-only chipboard role', () => {
        const carcassOnly = decors.filter(d =>
            d.variants.some(v =>
                v.material === 'chipboard' &&
                v.roles.includes('carcass') &&
                !v.roles.includes('front')
            )
        );
        assert.equal(carcassOnly.length, 1, 'Expected exactly 1 carcass-only chipboard decor');
        assert.equal(carcassOnly[0].id, 'K110');
    });

    it('all other chipboard decors are front-only', () => {
        const wrongRoles = decors.filter(d =>
            d.id !== 'K110' &&
            d.variants.some(v =>
                v.material === 'chipboard' &&
                v.roles.includes('carcass')
            )
        );
        assert.deepEqual(
            wrongRoles.map(d => d.id),
            [],
            `These chipboard decors should not have carcass role: ${wrongRoles.map(d => d.id).join(', ')}`
        );
    });

    it('all mdf_acrylic variants are front-only', () => {
        const wrongRoles = decors.filter(d =>
            d.variants.some(v =>
                v.material === 'mdf_acrylic' &&
                !v.roles.includes('front')
            )
        );
        assert.deepEqual(wrongRoles.map(d => d.id), []);
    });

    it('all chipboard variants have edge banding', () => {
        const missing = [];
        decors.forEach((d) => {
            d.variants.filter((v) => v.material === 'chipboard').forEach((v) => {
                if (!v.edge || !v.edge.code) {
                    missing.push(`${d.id}/${v.id}`);
                }
            });
        });
        assert.deepEqual(missing, [], `Chipboard variants missing edge: ${missing.join(', ')}`);
    });

    it('all mdf_acrylic variants have thickness_mm and format', () => {
        const missing = [];
        decors.forEach((d) => {
            d.variants.filter((v) => v.material === 'mdf_acrylic').forEach((v) => {
                if (!v.thickness_mm) missing.push(`${d.id}/${v.id} (thickness_mm)`);
                if (!v.format) missing.push(`${d.id}/${v.id} (format)`);
            });
        });
        assert.deepEqual(missing, [], `MDF variants missing fields: ${missing.join(', ')}`);
    });

    it('all variants have at least one role', () => {
        decors.forEach((d) => {
            d.variants.forEach((v) => {
                assert.ok(v.roles.length >= 1, `Decor ${d.id}, variant ${v.id}: no roles`);
            });
        });
    });

    it('all edge codes start with K-', () => {
        decors.forEach((d) => {
            d.variants.forEach((v) => {
                if (v.edge) {
                    assert.ok(
                        v.edge.code.startsWith('K-'),
                        `Decor ${d.id}, variant ${v.id}: edge code "${v.edge.code}" does not start with K-`
                    );
                }
            });
        });
    });
});

// ════════════════════════════════════════════════════════
// TEST 6: Reference comparison (acrylic-gloss)
// Verify that acrylic-gloss variant data matches the
// PDF reference fixture.
// ════════════════════════════════════════════════════════

describe('Reference Data (acrylic-gloss)', () => {
    const ref = require('../tests/fixtures/acrylic-gloss-ref');
    let decors;

    before(() => {
        decors = loadDecors();
    });

    ref.decors.forEach((expected) => {
        describe(`${expected.id} (${expected.name})`, () => {
            let decor;
            let variant;

            before(() => {
                decor = decors.find((d) => d.id === expected.id);
                variant = decor?.variants.find((v) => v.material === 'mdf_acrylic');
            });

            it('decor exists', () => {
                assert.ok(decor, `Decor ${expected.id} not found`);
            });

            it('name matches', () => {
                assert.equal(decor.name, expected.name);
            });

            it('color_family matches', () => {
                assert.equal(decor.color_family, expected.color_family);
            });

            it('has mdf_acrylic variant', () => {
                assert.ok(variant, `No mdf_acrylic variant for ${expected.id}`);
            });

            it('variant structure matches', () => {
                assert.equal(variant.structure, expected.structure);
            });

            it('variant edge code matches', () => {
                assert.equal(variant.edge.code, expected.edge_code);
            });

            it('variant edge finish matches', () => {
                assert.equal(variant.edge.finish, expected.edge_finish);
            });

            it('variant thickness is 18.3mm', () => {
                assert.equal(variant.thickness_mm, ref.expected_thickness);
            });

            it('variant format is [2800, 1300]', () => {
                assert.deepEqual(variant.format, ref.expected_format);
            });
        });
    });
});

// ════════════════════════════════════════════════════════
// TEST 7: Cross-reference — structures in collections.yaml
// ════════════════════════════════════════════════════════

describe('Cross-reference: collections.yaml', () => {
    let collections;
    let decors;

    before(() => {
        collections = loadYaml(path.join(KRONOSPAN_DIR, 'collections.yaml'));
        decors = loadDecors();
    });

    it('all variant structures exist in collections.yaml', () => {
        const validStructures = Object.keys(collections.kronospan.structures);
        const invalid = [];
        decors.forEach((d) => {
            d.variants.forEach((v) => {
                if (!validStructures.includes(v.structure)) {
                    invalid.push(`${d.id}/${v.id}: "${v.structure}"`);
                }
            });
        });
        assert.deepEqual(invalid, [], `Invalid structures: ${invalid.join(', ')}`);
    });

    it('all variant collections exist in collections.yaml', () => {
        const validCollections = Object.keys(collections.kronospan.collections);
        const invalid = [];
        decors.forEach((d) => {
            d.variants.forEach((v) => {
                if (!validCollections.includes(v.collection)) {
                    invalid.push(`${d.id}/${v.id}: "${v.collection}"`);
                }
            });
        });
        assert.deepEqual(invalid, [], `Invalid collections: ${invalid.join(', ')}`);
    });
});
