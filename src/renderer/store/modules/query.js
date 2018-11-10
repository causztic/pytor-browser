// initial state
const state = {
  history: [],
  actualURL: null,
  status: null,
};

// getters
const getters = {};

// actions
const actions = {
  getWebsite({
    commit, dispatch, rootState,
  }, website) {
    // TODO: unsure whether creating multiple callbacks will be inefficient.
    if (rootState.status.connected) {
      dispatch('status/load', { website }, { root: true });
      commit('setActualURL', website);
      commit('addQueryToHistory', website);
    }
  },
};

// mutations
const mutations = {
  addQueryToHistory(state, website) {
    state.history.push(website);
  },
  setActualURL(state, website) {
    state.actualURL = `http://localhost:27182?${website}`;
  },
};

export default {
  namespaced: true,
  state,
  getters,
  actions,
  mutations,
};
