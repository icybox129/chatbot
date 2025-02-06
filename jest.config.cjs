/*
 * Jest Configuration File
 * =======================
 * This file tells Jest what environment to use (jsdom), 
 * and how to transform JavaScript modules (via babel-jest).
 * It also specifies a setup file (`jest.setup.js`) 
 * to run before test execution for global mocking.
 */
module.exports = {
  testEnvironment: "jest-environment-jsdom",
  setupFiles: ["<rootDir>/jest.setup.js"],
  transform: {
    "^.+\\.js$": "babel-jest",
  },
};
