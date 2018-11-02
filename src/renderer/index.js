"use strict";
import Vue from 'vue';
import App from "./App.vue";
// <link rel="stylesheet" href="https://use.fontawesome.com/releases/v5.4.2/css/all.css" integrity="sha384-/rXc/GQVaYpyDdyxK+ecHPVYJSN9bmVFBvjA/9eOB+pb3F2w2N6fc5qB9Ew5yIns" crossorigin="anonymous">
const style = document.createElement("link");
style.setAttribute("rel", "stylesheet");
style.setAttribute("href", "https://use.fontawesome.com/releases/v5.4.2/css/all.css");
document.head.appendChild(style);

new Vue({
  el: "#app",
  data: {
    versions: {
      electron: process.versions.electron,
      electronWebpack: require("electron-webpack/package.json").version
    }
  },
  components: { App },
  template: `<App />`
})
