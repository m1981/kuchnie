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
