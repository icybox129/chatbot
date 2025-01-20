module.exports = {
  testEnvironment: "jest-environment-jsdom",
  setupFiles: ["<rootDir>/jest.setup.js"],
  transform: {
    "^.+\\.js$": "babel-jest",
  },
};
