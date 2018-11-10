/* eslint-disable no-undef */
import Vue from 'vue';
import * as vClickOutside from 'v-click-outside-x';

import store from './store';
import App from './App.vue';

Vue.use(vClickOutside);

// eslint-disable-next-line no-new
new Vue({
  el: '#app',
  store,
  data: {
    versions: {
      electron: process.versions.electron,
      // eslint-disable-next-line global-require
      electronWebpack: require('electron-webpack/package.json').version,
    }
  },
  components: { App },
  template: '<App />',
});
