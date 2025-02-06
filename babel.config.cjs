/*
 * Babel Configuration File
 * ========================
 * This file configures how Jest should transform JavaScript code.
 * Here, we target the current Node.js environment and apply the 
 * '@babel/preset-env' for ES6+ features.
 */
module.exports = {
  presets: [
    [
      "@babel/preset-env",
      {
        // Indicate which versions of Node.js or browsers to support
        targets: {
          node: "current", // Match the Node version in which the tests run
        },
      },
    ],
  ],
};
