"use strict";

import Vue from "vue";
import * as vClickOutside from "v-click-outside-x";

import store from "./store";
import App from "./App.vue";

const style = document.createElement("link");
style.setAttribute("rel", "stylesheet");
style.setAttribute("href", "https://use.fontawesome.com/releases/v5.4.2/css/all.css");
document.head.appendChild(style);

Vue.use(vClickOutside);

new Vue({
  el: "#app",
  store,
  data: {
    versions: {
      electron: process.versions.electron,
      electronWebpack: require("electron-webpack/package.json").version
    }
  },
  components: { App },
  template: "<App />"
});

