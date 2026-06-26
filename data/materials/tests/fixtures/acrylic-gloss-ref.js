// tests/fixtures/acrylic-gloss-ref.js
// Dane referencyjne z plyty-mdf-acrylic-gloss.pdf, str. 114-118
//
// Porownujemy z variantami mdf_acrylic w decors.yaml.

module.exports = {
    collection: 'acrylic_gloss',
    source: 'plyty-mdf-acrylic-gloss.pdf, str. 114-118',
    expected_count: 6,
    expected_thickness: 18.3,
    expected_format: [2800, 1300],
    decors: [
        {
            id: 'K8685',
            name: 'Biel Alpejska',
            group: 'XXI Color Basic',
            structure: 'AG',
            color_family: 'bialy',
            edge_code: 'K-8685-HG/AG',
            edge_finish: 'HG'
        },
        {
            id: 'K0112',
            name: 'Jasny Szary',
            group: 'XXIII Color Special',
            structure: 'AG',
            color_family: 'szary',
            edge_code: 'K-0112-HG/AG',
            edge_finish: 'HG'
        },
        {
            id: 'K0164',
            name: 'Antracyt',
            group: 'XXIII Color Special',
            structure: 'AG',
            color_family: 'czarny',
            edge_code: 'K-0164-HG/AG',
            edge_finish: 'HG'
        },
        {
            id: 'K0190',
            name: 'Czarny',
            group: 'XXIII Color Special',
            structure: 'AG',
            color_family: 'czarny',
            edge_code: 'K-0190-HG/AG',
            edge_finish: 'HG'
        },
        {
            id: 'K0514',
            name: 'Kość Słoniowa',
            group: 'XXIII Color Special',
            structure: 'AG',
            color_family: 'bezowy',
            edge_code: 'K-0514-UM/AG',
            edge_finish: 'UM' // UWAGA: UM nie HG!
        },
        {
            id: 'K7045',
            name: 'Szampański',
            group: 'XXIII Color Special',
            structure: 'AG',
            color_family: 'bezowy',
            edge_code: 'K-7045-HG/AG',
            edge_finish: 'HG'
        }
    ]
};
