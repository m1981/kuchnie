// build.js
// Walidacja YAML + generowanie JSON
// Uruchomienie: node data/materials/build.js

const yaml = require('js-yaml');
const fs = require('fs');
const path = require('path');
const { CollectionFileSchema } = require('./shared/schema');

const MATERIALS_DIR = __dirname;
const DIST_DIR = path.join(__dirname, '..', 'dist');
const CATALOG_PUBLIC = path.join(__dirname, '..', '..', 'catalog', 'public');

// ── Producenci do przetworzenia ──
const PRODUCERS = ['kronospan', 'swiss-krono', 'egger'];

let errors = 0;
let warnings = 0;

function error(msg) {
    console.error(`  ERROR: ${msg}`);
    errors++;
}

function warn(msg) {
    console.warn(`  WARN:  ${msg}`);
    warnings++;
}

function ok(msg) {
    console.log(`  OK:    ${msg}`);
}

// ── Walidacja jednego producenta ──
function validateProducer(producer) {
    const dir = path.join(MATERIALS_DIR, producer);

    if (!fs.existsSync(dir)) {
        warn(`Producer ${producer} not found, skipping`);
        return null;
    }

    console.log(`\n${'='.repeat(50)}`);
    console.log(`Producer: ${producer}`);
    console.log('='.repeat(50));

    // 1. Wczytaj collections.yaml
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

    // 2. Waliduj każdy plik YAML (oprocz collections.yaml)
    const yamlFiles = fs
        .readdirSync(dir)
        .filter((f) => f.endsWith('.yaml') && f !== 'collections.yaml')
        .sort();

    const allDecors = [];

    yamlFiles.forEach((file) => {
        const filePath = path.join(dir, file);
        console.log(`\n  File: ${file}`);

        // Parse YAML
        let content;
        try {
            content = yaml.load(fs.readFileSync(filePath, 'utf8'));
        } catch (e) {
            error(`YAML parse error: ${e.message}`);
            return;
        }

        // Schema validation
        const result = CollectionFileSchema.safeParse(content);
        if (!result.success) {
            error(`Schema validation failed:`);
            result.error.issues.forEach((i) => {
                error(`    ${i.path.join('.')}: ${i.message}`);
            });
            return;
        }

        // Structure validation
        content.decors.forEach((decor) => {
            if (!validStructures.includes(decor.structure)) {
                error(
                    `Decor ${decor.id}: unknown structure "${decor.structure}". Valid: ${validStructures.join(', ')}`
                );
            }

            // Img check (optional warning)
            if (decor.img) {
                const imgPath = path.join(dir, 'img', decor.img);
                if (!fs.existsSync(imgPath)) {
                    warn(`Decor ${decor.id}: missing img file "${decor.img}"`);
                }
            }

            // Edge code pattern check
            if (decor.edge && decor.edge.code) {
                // Kronospan pattern: K-{code}-{finish}/{structure} or similar
                if (!decor.edge.code.match(/^K-/)) {
                    warn(
                        `Decor ${decor.id}: edge code "${decor.edge.code}" doesn't match expected pattern K-*`
                    );
                }
            }
        });

        // Unikalnosc ID w pliku
        const ids = content.decors.map((d) => d.id);
        const duplicates = ids.filter((id, i) => ids.indexOf(id) !== i);
        if (duplicates.length > 0) {
            error(`Duplicate IDs in ${file}: ${duplicates.join(', ')}`);
        }

        allDecors.push(...content.decors);
        ok(`${content.decors.length} decors in ${file}`);
    });

    return { producer, collections: producerData, decors: allDecors };
}

// ── Glowna procedura ──
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
            catalog.stats[producer] = result.decors.length;
        }
    });

    // Wczytaj shared concepts
    const conceptsPath = path.join(MATERIALS_DIR, 'shared', 'concepts.yaml');
    if (fs.existsSync(conceptsPath)) {
        catalog.shared = yaml.load(fs.readFileSync(conceptsPath, 'utf8'));
        ok('Loaded shared/concepts.yaml');
    } else {
        warn('shared/concepts.yaml not found');
    }

    // Wczytaj substitutions (opcjonalnie)
    const subsPath = path.join(MATERIALS_DIR, 'substitutions.yaml');
    if (fs.existsSync(subsPath)) {
        catalog.substitutions = yaml.load(fs.readFileSync(subsPath, 'utf8'));
        ok('Loaded substitutions.yaml');
    }

    // ── Generowanie JSON ──
    if (!fs.existsSync(DIST_DIR)) {
        fs.mkdirSync(DIST_DIR, { recursive: true });
    }

    // Pelen katalog
    const catalogPath = path.join(DIST_DIR, 'catalog.json');
    fs.writeFileSync(catalogPath, JSON.stringify(catalog, null, 2));
    ok(`Written ${catalogPath}`);

    // Per producent
    Object.entries(catalog.producers).forEach(([producer, data]) => {
        const producerPath = path.join(DIST_DIR, `${producer}.json`);
        fs.writeFileSync(producerPath, JSON.stringify(data, null, 2));
        ok(`Written ${producerPath}`);
    });

    // Copy catalog.json to catalog/public/ for Vite dev server
    if (fs.existsSync(CATALOG_PUBLIC)) {
        const publicCatalogPath = path.join(CATALOG_PUBLIC, 'catalog.json');
        fs.writeFileSync(publicCatalogPath, JSON.stringify(catalog, null, 2));
        ok(`Written ${publicCatalogPath}`);
    }

    // ── Podsumowanie ──
    console.log('\n' + '='.repeat(50));
    console.log('SUMMARY');
    console.log('='.repeat(50));

    Object.entries(catalog.stats).forEach(([producer, count]) => {
        console.log(`  ${producer}: ${count} decors`);
    });

    const totalDecors = Object.values(catalog.stats).reduce((a, b) => a + b, 0);
    console.log(`  TOTAL: ${totalDecors} decors`);

    if (errors > 0) {
        console.error(`\nFAILED: ${errors} errors, ${warnings} warnings`);
        process.exit(1);
    } else {
        console.log(`\nSUCCESS: ${warnings} warnings`);
    }
}

build();
