// scripts/convert-global-collection.js
// Konwertuje global-collection-decory.yaml → global-collection.yaml (nowy format)

const yaml = require('js-yaml');
const fs = require('fs');
const path = require('path');

const INPUT = path.join(__dirname, '..', 'docs', 'materials', 'Kronospan', 'global-collection-decory.yaml');
const OUTPUT = path.join(__dirname, '..', 'data', 'materials', 'kronospan', 'global-collection.yaml');
const IMG_DIR = path.join(__dirname, '..', 'public', 'kronospan', 'img');

const raw = yaml.load(fs.readFileSync(INPUT, 'utf8'));

// Wczytaj listę istniejących plików img
const existingImages = new Set(fs.readdirSync(IMG_DIR).filter(f => f.endsWith('.jpg')));

// Sprawdź czy plik img istnieje dla danego ID
// ID moze byc K110, K096, 0514, 8685 itp.
// Pliki moga byc K0110.jpg, K096.jpg, K0514.jpg itp.
function findImgFile(id) {
  // Exact match
  if (existingImages.has(`${id}.jpg`)) return `${id}.jpg`;
  // Dodaj leading zero (K110 → K0110)
  const num = id.replace(/^K/, '');
  const padded = `K${num.padStart(4, '0')}`;
  if (existingImages.has(`${padded}.jpg`)) return `${padded}.jpg`;
  return null;
}

// Mapowanie dopasowanie → cross_collections
const CROSS_MAP = {
  'AG': 'acrylic_gloss',
  'AM': 'acrylic_matt',
  'MG': 'mirror_gloss',
  'CI': 'compact_interior',
  'KA': 'kronoart',
  'Compact Interior': 'compact_interior',
};

function parseCrossCollections(str) {
  if (!str) return [];
  const results = [];
  // Match patterns like "AG", "AM", "MG", "KA", "CI (BS)", "Compact Interior (BS)"
  const parts = str.split(',').map(s => s.trim());
  for (const part of parts) {
    const clean = part.replace(/\(.*?\)/g, '').trim();
    if (CROSS_MAP[clean]) {
      results.push(CROSS_MAP[clean]);
    }
  }
  return results;
}

// Parsowanie uwagi → NCS, RAL, Pantone
function parseColors(uwagi) {
  if (!uwagi) return {};
  const result = {};
  const ncsMatch = uwagi.match(/NCS\s+([\w\s.-]+)/);
  if (ncsMatch) result.ncs = ncsMatch[1].trim();
  const ralMatch = uwagi.match(/RAL\s+([\w\s.]+)/);
  if (ralMatch) result.ral = ralMatch[1].trim().split(',')[0].trim();
  const pantoneMatch = uwagi.match(/Pantone\s+([\w\s.]+)/);
  if (pantoneMatch) result.pantone = pantoneMatch[1].trim().split(',')[0].trim();
  return result;
}

// Generowanie tagów na podstawie nazwy
function generateTags(name, group) {
  const tags = [];
  const lower = name.toLowerCase();

  // Drewno
  if (lower.includes('dąb') || lower.includes('dab')) tags.push('dab');
  if (lower.includes('orzech')) tags.push('orzech');
  if (lower.includes('jesion')) tags.push('jesion');
  if (lower.includes('buk')) tags.push('buk');
  if (lower.includes('brzoza')) tags.push('brzoza');
  if (lower.includes('olcha')) tags.push('olcha');
  if (lower.includes('wenge')) tags.push('wenge');
  if (lower.includes('wiśnia') || lower.includes('wisnia')) tags.push('wisnia');
  if (lower.includes('klon')) tags.push('klon');
  if (lower.includes('sosna')) tags.push('sosna');
  if (lower.includes('wiąz') || lower.includes('wiaz')) tags.push('wiaz');
  if (lower.includes('drewno') || lower.includes('wood')) tags.push('drewno');
  if (lower.includes('marine')) tags.push('drewno');

  // Kamień
  if (lower.includes('beton')) tags.push('beton');
  if (lower.includes('marmur')) tags.push('marmur');
  if (lower.includes('łupek') || lower.includes('lupek')) tags.push('lupek');
  if (lower.includes('kamień') || lower.includes('kamien') || lower.includes('stone')) tags.push('kamien');
  if (lower.includes('kwarcyt')) tags.push('kwarcyt');
  if (lower.includes('granada')) tags.push('kamien');

  // Kolory
  if (lower.includes('biały') || lower.includes('bialy') || lower.includes('alpejska') || lower.includes('brylantowy') || lower.includes('perłowy biały')) tags.push('bialy');
  if (lower.includes('czarny')) tags.push('czarny');
  if (lower.includes('szary') || lower.includes('grafit') || lower.includes('mouse grey')) tags.push('szary');
  if (lower.includes('beżowy') || lower.includes('bezowy') || lower.includes('piaskow')) tags.push('bezowy');
  if (lower.includes('złoty') || lower.includes('zlota') || lower.includes('gold')) tags.push('zloty');
  if (lower.includes('srebrny') || lower.includes('silver') || lower.includes('platinium')) tags.push('srebrny');
  if (lower.includes('brązowy') || lower.includes('brazowy') || lower.includes('brąz')) tags.push('brazowy');
  if (lower.includes('krem') || lower.includes('ivory') || lower.includes('kość słoniowa')) tags.push('kremowy');
  if (lower.includes('niebieski') || lower.includes('blue') || lower.includes('błękit')) tags.push('niebieski');
  if (lower.includes('zielony') || lower.includes('green') || lower.includes('zieleń')) tags.push('zielony');
  if (lower.includes('czerwon') || lower.includes('red') || lower.includes('chilli')) tags.push('czerwony');
  if (lower.includes('róż') || lower.includes('pink') || lower.includes('pudrowy')) tags.push('rozowy');
  if (lower.includes('antracyt')) tags.push('czarny');
  if (lower.includes('bazalt')) tags.push('szary');

  // Style
  if (lower.includes('craft') || lower.includes('urban') || lower.includes('vintage')) tags.push('rustykalny');
  if (lower.includes('barokow') || lower.includes('castello') || lower.includes('harbor')) tags.push('klasyczny');

  // Specjalne
  if (group.includes('CORPUS')) tags.push('korpusowy');
  if (group.includes('FRONT')) tags.push('frontowy');

  return [...new Set(tags)];
}

// Konwersja
const decors = raw.dekory.map(d => {
  const colors = parseColors(d.uwagi);
  const structures = d.struktura.includes('/') ? d.struktura.split('/').map(s => s.trim()) : [d.struktura];
  const structure = structures[0];
  const multiStructures = structures.length > 1 ? structures.slice(1).join(', ') : null;
  const express = [];
  if (d.ex_12) express.push(12);
  if (d.ex_16) express.push(16);
  if (d.ex_18) express.push(18);

  return {
    id: String(d.dekor),
    name: d.nazwa,
    group: d.grupa,
    structure,
    multi_structures: multiStructures,
    tags: generateTags(d.nazwa, d.grupa),
    ...colors,
    express,
    konfekcja: d.konfekcja === 'K',
    countertop: d.blat || null,
    hdf_laminate: true,
    cross_collections: parseCrossCollections(d.dopasowanie),
    img: findImgFile(String(d.dekor)),
    edge: {
      code: d.obrzeze,
      supplier: 'Schilsner',
    },
  };
});

const output = {
  collection: 'global',
  decors,
};

fs.writeFileSync(OUTPUT, yaml.dump(output, {
  lineWidth: 120,
  noRefs: true,
  quotingType: '"',
  forceQuotes: false,
}));

console.log(`Converted ${decors.length} decors → ${OUTPUT}`);
