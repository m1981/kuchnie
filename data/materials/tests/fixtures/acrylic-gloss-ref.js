// tests/fixtures/acrylic-gloss-ref.js
// Dane referencyjne z acrylic-gloss.md
// rdlo: plyty-mdf-acrylic-gloss.pdf, str. 114-118
//
// TO jest "source of truth" z katalogu papierowego.
// Porownujemy z tym co jest w YAML.

module.exports = {
    collection: 'acrylic_gloss',
    source: 'plyty-mdf-acrylic-gloss.pdf, str. 114-118',
    expected_count: 6,
    expected_thickness: 18.3,
    expected_format: [2800, 1300],
    decors: [
        {
            id: '8685',
            name: 'Biel Alpejska',
            group: 'XXI Color Basic',
            structure: 'AG',
            edge_code: 'K-8685-HG/AG',
            edge_finish: 'HG'
        },
        {
            id: '0112',
            name: 'Jasny Szary',
            group: 'XXIII Color Special',
            structure: 'AG',
            edge_code: 'K-0112-HG/AG',
            edge_finish: 'HG'
        },
        {
            id: '0164',
            name: 'Antracyt',
            group: 'XXIII Color Special',
            structure: 'AG',
            edge_code: 'K-0164-HG/AG',
            edge_finish: 'HG'
        },
        {
            id: '0190',
            name: 'Czarny',
            group: 'XXIII Color Special',
            structure: 'AG',
            edge_code: 'K-0190-HG/AG',
            edge_finish: 'HG'
        },
        {
            id: '0514',
            name: 'Kość Słoniowa',
            group: 'XXIII Color Special',
            structure: 'AG',
            edge_code: 'K-0514-UM/AG',
            edge_finish: 'UM' // UWAGA: UM nie HG!
        },
        {
            id: '7045',
            name: 'Szampański',
            group: 'XXIII Color Special',
            structure: 'AG',
            edge_code: 'K-7045-HG/AG',
            edge_finish: 'HG'
        }
    ]
};
