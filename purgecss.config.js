// purgecss.config.js
module.exports = {
    // 1. Tell it where to look for used classes
    content: ['**/*.html', '**/*.js'],

    // 2. Tell it which CSS files to clean
    css: ['common.css'], // Update this if your CSS is in a specific folder, e.g., 'css/**/*.css'

    // 3. Output destination (overwrites the original file)
    output: 'common.css', // If using a folder above, use the folder name here, e.g., 'css/'

    // 4. THE SAFETY NET: Safelisting
    // Add any classes here that are added via JavaScript (like 'active', 'show')
    // or classes you just want to protect from deletion.
    safelist: [
        'active',
        'disabled',
        'show',
        'hidden',
        // You can also use Regular Expressions to protect entire families of classes!
        // e.g., /^nav-/, /^btn-/ will protect ANY class starting with nav- or btn-
        /^node-/,
        /^border-/
    ],

    // Optional: Extractors help PurgeCSS read special characters in class names
    defaultExtractor: (content) => content.match(/[\w-/:]+(?<!:)/g) || []
};
