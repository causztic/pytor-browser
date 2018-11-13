// initial state
const state = {
  history: [],
  actualURL: null,
  status: null,
  nodeCount: 3,
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
      dispatch('status/load', { website }, { root: true });
      commit('setActualURL', website);
      commit('addQueryToHistory', website);
    }
  },
  setNodeCount({ commit }, nodeCount) {
    commit('setNodeCount', nodeCount);
  },
};

// mutations
const mutations = {
  addQueryToHistory(state, website) {
    state.history.push(website);
  },
  setActualURL(state, website) {
    state.actualURL = `http://localhost:27182?url=${website}&count=${state.nodeCount}`;
  },
  setNodeCount(state, nodeCount) {
    state.nodeCount = nodeCount;
  },
};

export default {
  namespaced: true,
  state,
  getters,
  actions,
  mutations,
};
