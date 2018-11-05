'use strict';
const isDevelopment = process.env.NODE_ENV !== "production";
const staticPath = isDevelopment ? __static : __dirname.replace(/app\.asar$/, 'static');

export { isDevelopment, staticPath };