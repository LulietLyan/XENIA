const postcssPresetEnv = require("postcss-preset-env");

module.exports = {
  plugins: [
    require('postcss-extend-rule')(),
    require("@csstools/postcss-global-data")({
      files: [
        "./src/styles/_extends.css",
        "./src/styles/_media.css",
      ],
    }),
    postcssPresetEnv({
      features: {
        "logical-properties-and-values": false,
        "custom-properties": false,
      },
    }),
    require("cssnano"),
  ],
};
