// build.js
// Validate YAML + generate JSON (Decor + Variant model)
// Run: node data/materials/build.js

const yaml = require('js-yaml');
const fs = require('fs');
const path = require('path');
const { DecorsFileSchema } = require('./shared/schema');

const MATERIALS_DIR = __dirname;
const DIST_DIR = path.join(__dirname, '..', 'dist');
const CATALOG_PUBLIC = path.join(__dirname, '..', '..', 'public');

const PRODUCERS = ['kronospan', 'swiss-krono', 'egger'];

let errors = 0;
let warnings = 0;

function error(msg) { console.error(`  ERROR: ${msg}`); errors++; }
function warn(msg) { console.warn(`  WARN:  ${msg}`); warnings++; }
function ok(msg) { console.log(`  OK:    ${msg}`); }

// ── Validate one producer ──
function validateProducer(producer) {
    const dir = path.join(MATERIALS_DIR, producer);

    if (!fs.existsSync(dir)) {
        warn(`Producer ${producer} not found, skipping`);
        return null;
    }

    console.log(`\n${'='.repeat(50)}`);
    console.log(`Producer: ${producer}`);
    console.log('='.repeat(50));

    // 1. Load collections.yaml
    const collectionsPath = path.join(dir, 'collections.yaml');
    if (!fs.existsSync(collectionsPath)) {
        warn(`${producer}: missing collections.yaml, skipping`);
        return null;
    }

    const collections = yaml.load(fs.readFileSync(collectionsPath, 'utf8'));
    const producerData = collections[producer];
    if (!producerData) {
        error(`${producer}: no data for "${producer}" in collections.yaml`);
        return null;
    }

    const validStructures = Object.keys(producerData.structures || {});

    // 2. Load decors.yaml
    const decorsPath = path.join(dir, 'decors.yaml');

    if (!fs.existsSync(decorsPath)) {
        warn(`${producer}: no decors.yaml found`);
        return null;
    }

    let content;
    try {
        content = yaml.load(fs.readFileSync(decorsPath, 'utf8'));
    } catch (e) {
        error(`YAML parse error: ${e.message}`);
        return null;
    }

    console.log(`\n  File: decors.yaml`);

    const result = DecorsFileSchema.safeParse(content);
    if (!result.success) {
        error(`Schema validation failed:`);
        result.error.issues.forEach((i) => {
            error(`    ${i.path.join('.')}: ${i.message}`);
        });
        return null;
    }

    // Validate structures against collections.yaml
    content.decors.forEach((decor) => {
        decor.variants.forEach((variant) => {
            if (!validStructures.includes(variant.structure)) {
                warn(
                    `Decor ${decor.id}, variant ${variant.id}: unknown structure "${variant.structure}". Valid: ${validStructures.join(', ')}`
                );
            }
        });

        // Img check
        if (decor.img) {
            const imgInPublic = path.join(CATALOG_PUBLIC, producer, 'img', decor.img);
            if (!fs.existsSync(imgInPublic)) {
                warn(`Decor ${decor.id}: missing img file "${decor.img}"`);
            }
        }
    });

    // Uniqueness checks
    const decorIds = content.decors.map((d) => d.id);
    const dupes = decorIds.filter((id, i) => decorIds.indexOf(id) !== i);
    if (dupes.length > 0) {
        error(`Duplicate decor IDs: ${dupes.join(', ')}`);
    }

    const variantIds = content.decors.flatMap((d) => d.variants.map((v) => v.id));
    const vDupes = variantIds.filter((id, i) => variantIds.indexOf(id) !== i);
    if (vDupes.length > 0) {
        error(`Duplicate variant IDs: ${vDupes.join(', ')}`);
    }

    ok(`${content.decors.length} decors, ${content.decors.reduce((s, d) => s + d.variants.length, 0)} variants in decors.yaml`);

    return { producer, collections: producerData, decors: content.decors };
}

// ── Main build ──
function build() {
    console.log('Building catalog...\n');

    const catalog = {
        _generated: new Date().toISOString(),
        producers: {},
        shared: {},
        stats: {}
    };

    PRODUCERS.forEach((producer) => {
        const result = validateProducer(producer);
        if (result) {
            catalog.producers[producer] = {
                collections: result.collections,
                decors: result.decors
            };
            catalog.stats[producer] = {
                decors: result.decors.length,
                variants: result.decors.reduce((s, d) => s + d.variants.length, 0)
            };
        }
    });

    // Load shared concepts
    const conceptsPath = path.join(MATERIALS_DIR, 'shared', 'concepts.yaml');
    if (fs.existsSync(conceptsPath)) {
        catalog.shared = yaml.load(fs.readFileSync(conceptsPath, 'utf8'));
        ok('Loaded shared/concepts.yaml');
    }

    // Load substitutions (optional)
    const subsPath = path.join(MATERIALS_DIR, 'substitutions.yaml');
    if (fs.existsSync(subsPath)) {
        catalog.substitutions = yaml.load(fs.readFileSync(subsPath, 'utf8'));
        ok('Loaded substitutions.yaml');
    }

    // ── Write JSON ──
    if (!fs.existsSync(DIST_DIR)) {
        fs.mkdirSync(DIST_DIR, { recursive: true });
    }

    const catalogPath = path.join(DIST_DIR, 'catalog.json');
    fs.writeFileSync(catalogPath, JSON.stringify(catalog, null, 2));
    ok(`Written ${catalogPath}`);

    Object.entries(catalog.producers).forEach(([producer, data]) => {
        const producerPath = path.join(DIST_DIR, `${producer}.json`);
        fs.writeFileSync(producerPath, JSON.stringify(data, null, 2));
        ok(`Written ${producerPath}`);
    });

    if (fs.existsSync(CATALOG_PUBLIC)) {
        const publicCatalogPath = path.join(CATALOG_PUBLIC, 'catalog.json');
        fs.writeFileSync(publicCatalogPath, JSON.stringify(catalog, null, 2));
        ok(`Written ${publicCatalogPath}`);
    }

    // ── Summary ──
    console.log('\n' + '='.repeat(50));
    console.log('SUMMARY');
    console.log('='.repeat(50));

    Object.entries(catalog.stats).forEach(([producer, stats]) => {
        console.log(`  ${producer}: ${stats.decors} decors, ${stats.variants} variants`);
    });

    const totalDecors = Object.values(catalog.stats).reduce((a, b) => a + b.decors, 0);
    const totalVariants = Object.values(catalog.stats).reduce((a, b) => a + b.variants, 0);
    console.log(`  TOTAL: ${totalDecors} decors, ${totalVariants} variants`);

    if (errors > 0) {
        console.error(`\nFAILED: ${errors} errors, ${warnings} warnings`);
        process.exit(1);
    } else {
        console.log(`\nSUCCESS: ${warnings} warnings`);
    }
}

build();
