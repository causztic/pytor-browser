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
    state, commit, dispatch, rootState,
  }, website) {
    if (!website.startsWith('http://') && !website.startsWith('https://')) {
      website = `http://${website}`;
    }

    if (rootState.status.connected) {
      if (state.history.slice(-1)[0] !== website) {
        dispatch('status/load', { website }, { root: true });
      }
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
    state.actualURL = `http://localhost:27182?url=${website}`;
  },
};

export default {
  namespaced: true,
  state,
  getters,
  actions,
  mutations,
};
