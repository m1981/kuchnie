// tests/validate.test.js
// Walidacja YAML + porownanie z danymi referencyjnymi
// Uruchomienie: cd data/materials && node --test tests/validate.test.js

const { describe, it, before } = require('node:test');
const assert = require('node:assert/strict');
const yaml = require('js-yaml');
const fs = require('fs');
const path = require('path');
const { CollectionFileSchema } = require('../shared/schema');

const MATERIALS_DIR = path.join(__dirname, '..');
const KRONOSPAN_DIR = path.join(MATERIALS_DIR, 'kronospan');

// ── Helper: wczytaj YAML ──
function loadYaml(filePath) {
    return yaml.load(fs.readFileSync(filePath, 'utf8'));
}

// ── Helper: znajdz dekor po ID ──
function findDecor(decors, id) {
    return decors.find((d) => d.id === id);
}

// ════════════════════════════════════════════════════════
// TEST 1: Walidacja struktury YAML
// ════════════════════════════════════════════════════════

describe('YAML Schema Validation', () => {
    it('acrylic-gloss.yaml passes schema validation', () => {
        const content = loadYaml(path.join(KRONOSPAN_DIR, 'acrylic-gloss.yaml'));
        const result = CollectionFileSchema.safeParse(content);
        assert.equal(result.success, true, JSON.stringify(result.error?.issues, null, 2));
    });

    it('acrylic-gloss.yaml has correct collection name', () => {
        const content = loadYaml(path.join(KRONOSPAN_DIR, 'acrylic-gloss.yaml'));
        assert.equal(content.collection, 'acrylic_gloss');
    });

    it('acrylic-gloss.yaml has 6 decors', () => {
        const content = loadYaml(path.join(KRONOSPAN_DIR, 'acrylic-gloss.yaml'));
        assert.equal(content.decors.length, 6);
    });

    it('all decors have required fields', () => {
        const content = loadYaml(path.join(KRONOSPAN_DIR, 'acrylic-gloss.yaml'));
        content.decors.forEach((decor) => {
            assert.ok(decor.id, `Decor missing id`);
            assert.ok(decor.name, `Decor ${decor.id} missing name`);
            assert.ok(decor.structure, `Decor ${decor.id} missing structure`);
            assert.ok(decor.edge, `Decor ${decor.id} missing edge`);
            assert.ok(decor.edge.code, `Decor ${decor.id} missing edge.code`);
            assert.ok(decor.thickness_mm, `Decor ${decor.id} missing thickness_mm`);
            assert.ok(decor.format, `Decor ${decor.id} missing format`);
        });
    });
});

// ════════════════════════════════════════════════════════
// TEST 2: Porownanie z danymi referencyjnymi (MD)
// ════════════════════════════════════════════════════════

describe('Reference Data Comparison (acrylic-gloss.md)', () => {
    const ref = require('../tests/fixtures/acrylic-gloss-ref');
    let decors;

    before(() => {
        const content = loadYaml(path.join(KRONOSPAN_DIR, 'acrylic-gloss.yaml'));
        decors = content.decors;
    });

    it(`has exactly ${ref.expected_count} decors`, () => {
        assert.equal(decors.length, ref.expected_count);
    });

    it('all reference decors are present in YAML', () => {
        const ids = decors.map((d) => d.id);
        ref.decors.forEach((expected) => {
            assert.ok(ids.includes(expected.id), `Missing decor ${expected.id} (${expected.name})`);
        });
    });

    it('no extra decors in YAML (not in reference)', () => {
        const refIds = ref.decors.map((d) => d.id);
        decors.forEach((decor) => {
            assert.ok(
                refIds.includes(decor.id),
                `Extra decor in YAML: ${decor.id} (${decor.name}) - not in reference MD`
            );
        });
    });

    // Testy per dekor
    ref.decors.forEach((expected) => {
        describe(`Decor ${expected.id} (${expected.name})`, () => {
            let decor;
            before(() => {
                decor = findDecor(decors, expected.id);
            });

            it('exists in YAML', () => {
                assert.ok(decor, `Decor ${expected.id} not found`);
            });

            it(`name matches: "${expected.name}"`, () => {
                assert.equal(decor.name, expected.name);
            });

            it(`structure matches: "${expected.structure}"`, () => {
                assert.equal(decor.structure, expected.structure);
            });

            it(`edge code matches: "${expected.edge_code}"`, () => {
                assert.equal(decor.edge.code, expected.edge_code);
            });

            it(`edge finish matches: "${expected.edge_finish}"`, () => {
                assert.equal(decor.edge.finish, expected.edge_finish);
            });

            it('thickness is 18.3mm', () => {
                assert.equal(decor.thickness_mm, ref.expected_thickness);
            });

            it('format is [2800, 1300]', () => {
                assert.deepEqual(decor.format, ref.expected_format);
            });

            it(`color_family matches: "${expected.color_family}"`, () => {
                assert.equal(decor.color_family, expected.color_family);
            });
        });
    });
});

// ════════════════════════════════════════════════════════
// TEST 3: Cross-reference walidacja
// ════════════════════════════════════════════════════════

describe('Cross-reference Validation', () => {
    let collections;
    let acrylicDecors;

    before(() => {
        collections = loadYaml(path.join(KRONOSPAN_DIR, 'collections.yaml'));
        const acrylic = loadYaml(path.join(KRONOSPAN_DIR, 'acrylic-gloss.yaml'));
        acrylicDecors = acrylic.decors;
    });

    it('all structures exist in collections.yaml', () => {
        const validStructures = Object.keys(collections.kronospan.structures);
        acrylicDecors.forEach((decor) => {
            assert.ok(
                validStructures.includes(decor.structure),
                `Decor ${decor.id}: structure "${decor.structure}" not in collections.yaml. Valid: ${validStructures.join(', ')}`
            );
        });
    });

    it('all decors have global_decor_id (link to Global Collection)', () => {
        acrylicDecors.forEach((decor) => {
            assert.ok(decor.global_decor_id, `Decor ${decor.id}: missing global_decor_id`);
        });
    });

    it('edge codes follow Kronospan pattern K-*', () => {
        acrylicDecors.forEach((decor) => {
            assert.ok(
                decor.edge.code.startsWith('K-'),
                `Decor ${decor.id}: edge code "${decor.edge.code}" doesn't start with K-`
            );
        });
    });

    it('edge supplier is Schilsner', () => {
        acrylicDecors.forEach((decor) => {
            assert.equal(
                decor.edge.supplier,
                'Schilsner',
                `Decor ${decor.id}: edge supplier should be Schilsner`
            );
        });
    });
});

// ════════════════════════════════════════════════════════
// TEST 4: Unikalnosc
// ════════════════════════════════════════════════════════

describe('Uniqueness Checks', () => {
    it('no duplicate IDs in acrylic-gloss', () => {
        const content = loadYaml(path.join(KRONOSPAN_DIR, 'acrylic-gloss.yaml'));
        const ids = content.decors.map((d) => d.id);
        const uniqueIds = [...new Set(ids)];
        assert.equal(
            ids.length,
            uniqueIds.length,
            `Duplicate IDs found: ${ids.filter((id, i) => ids.indexOf(id) !== i).join(', ')}`
        );
    });

    it('no duplicate edge codes in acrylic-gloss', () => {
        const content = loadYaml(path.join(KRONOSPAN_DIR, 'acrylic-gloss.yaml'));
        const codes = content.decors.map((d) => d.edge.code);
        const uniqueCodes = [...new Set(codes)];
        assert.equal(codes.length, uniqueCodes.length, `Duplicate edge codes found`);
    });
});

// ════════════════════════════════════════════════════════
// TEST 5: Identity Model — K-prefix convention
// All Kronospan decor IDs must start with 'K' prefix
// to ensure global uniqueness across collections.
// ════════════════════════════════════════════════════════

describe('Identity Model — K-prefix convention', () => {
    it('all global-collection IDs start with K', () => {
        const content = loadYaml(path.join(KRONOSPAN_DIR, 'global-collection.yaml'));
        content.decors.forEach((decor) => {
            assert.ok(
                decor.id.startsWith('K'),
                `Global Collection decor id="${decor.id}" does not start with K. All Kronospan IDs must use K-prefix.`
            );
        });
    });

    it('all acrylic-gloss IDs start with K', () => {
        const content = loadYaml(path.join(KRONOSPAN_DIR, 'acrylic-gloss.yaml'));
        content.decors.forEach((decor) => {
            assert.ok(
                decor.id.startsWith('K'),
                `Acrylic Gloss decor id="${decor.id}" does not start with K. All Kronospan IDs must use K-prefix.`
            );
        });
    });

    it('all global_decor_id values start with K', () => {
        const content = loadYaml(path.join(KRONOSPAN_DIR, 'acrylic-gloss.yaml'));
        content.decors.forEach((decor) => {
            if (decor.global_decor_id) {
                assert.ok(
                    decor.global_decor_id.startsWith('K'),
                    `Decor ${decor.id}: global_decor_id="${decor.global_decor_id}" does not start with K.`
                );
            }
        });
    });
});

// ════════════════════════════════════════════════════════
// TEST 6: Cross-collection uniqueness
// No two decors across different collection files may
// share the same ID UNLESS they are the same decor in
// a different material (linked via global_decor_id).
// This allows K8685 to exist in both Global Collection
// (chipboard) and Acrylic Gloss (MDF) as variants.
// ════════════════════════════════════════════════════════

describe('Cross-collection Uniqueness', () => {
    it('no accidental duplicate IDs across collections', () => {
        const global_ = loadYaml(path.join(KRONOSPAN_DIR, 'global-collection.yaml'));
        const acrylic = loadYaml(path.join(KRONOSPAN_DIR, 'acrylic-gloss.yaml'));

        const globalIds = new Set(global_.decors.map((d) => d.id));
        const acrylicIds = acrylic.decors.map((d) => d.id);

        // IDs that appear in both collections
        const overlapping = acrylicIds.filter((id) => globalIds.has(id));

        // Each overlap must be linked via global_decor_id
        overlapping.forEach((id) => {
            const acrylicDecor = acrylic.decors.find((d) => d.id === id);
            assert.ok(
                acrylicDecor.global_decor_id,
                `Decor ${id} exists in both global-collection and acrylic-gloss but has no global_decor_id link.`
            );
            assert.equal(
                acrylicDecor.global_decor_id,
                id,
                `Decor ${id}: global_decor_id should equal its own id (same decor, different material).`
            );
        });

        // IDs in acrylic-gloss that are NOT in global-collection must not collide
        const uniqueToAcrylic = acrylicIds.filter((id) => !globalIds.has(id));
        const uniqueSet = new Set(uniqueToAcrylic);
        assert.equal(
            uniqueToAcrylic.length,
            uniqueSet.size,
            `Duplicate IDs in acrylic-gloss (not in global): ${uniqueToAcrylic.filter((id, i) => uniqueToAcrylic.indexOf(id) !== i).join(', ')}`
        );
    });
});

// ════════════════════════════════════════════════════════
// TEST 7: Cross-reference integrity
// global_decor_id must resolve to an existing decor
// in global-collection.yaml.
// ════════════════════════════════════════════════════════

// ════════════════════════════════════════════════════════
// TEST 8: Color Family
// Every decor must have a color_family assigned.
// This enables cross-vendor color matching.
// ════════════════════════════════════════════════════════

describe('Color Family', () => {
    it('all global-collection decors have color_family', () => {
        const content = loadYaml(path.join(KRONOSPAN_DIR, 'global-collection.yaml'));
        const { COLOR_FAMILIES } = require('../shared/schema');
        content.decors.forEach((decor) => {
            assert.ok(
                decor.color_family,
                `Decor ${decor.id} (${decor.name}): missing color_family`
            );
            assert.ok(
                COLOR_FAMILIES.includes(decor.color_family),
                `Decor ${decor.id}: invalid color_family "${decor.color_family}". Valid: ${COLOR_FAMILIES.join(', ')}`
            );
        });
    });

    it('all acrylic-gloss decors have color_family', () => {
        const content = loadYaml(path.join(KRONOSPAN_DIR, 'acrylic-gloss.yaml'));
        const { COLOR_FAMILIES } = require('../shared/schema');
        content.decors.forEach((decor) => {
            assert.ok(
                decor.color_family,
                `Decor ${decor.id} (${decor.name}): missing color_family`
            );
            assert.ok(
                COLOR_FAMILIES.includes(decor.color_family),
                `Decor ${decor.id}: invalid color_family "${decor.color_family}". Valid: ${COLOR_FAMILIES.join(', ')}`
            );
        });
    });
});

describe('Cross-reference Integrity', () => {
    it('all global_decor_id values resolve to existing global-collection decors', () => {
        const global_ = loadYaml(path.join(KRONOSPAN_DIR, 'global-collection.yaml'));
        const acrylic = loadYaml(path.join(KRONOSPAN_DIR, 'acrylic-gloss.yaml'));

        const globalIdSet = new Set(global_.decors.map((d) => d.id));

        acrylic.decors.forEach((decor) => {
            if (decor.global_decor_id) {
                assert.ok(
                    globalIdSet.has(decor.global_decor_id),
                    `Decor ${decor.id}: global_decor_id="${decor.global_decor_id}" does not exist in global-collection.yaml`
                );
            }
        });
    });
});
