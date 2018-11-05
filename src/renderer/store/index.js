import Vue from "vue";
import Vuex from "vuex";

import query from "./modules/query";
import status from "./modules/status";
import { isDevelopment } from "common/util";

Vue.use(Vuex);

export default new Vuex.Store({
  modules: {
    query,
    status
  },
  strict: isDevelopment
});
