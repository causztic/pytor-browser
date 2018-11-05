import Vue from "vue";
import Vuex from "vuex";

import query from "./modules/query";
import { isDevelopment } from "common/util";

Vue.use(Vuex);

export default new Vuex.Store({
  modules: {
    query
  },
  strict: isDevelopment
});
