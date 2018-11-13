// initial state
const state = {
  history: [],
  historyIndex: -1,
  actualURL: null,
  status: null,
  nodeCount: 3,
};

// actions
const actions = {
  getWebsite({
    commit, dispatch, rootState,
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
  navigateHistory({
    commit, rootState, dispatch, state,
  }, diff) {
    return new Promise((resolve, _) => {
      const website = state.history[state.historyIndex + diff];
      if (rootState.status.connected) {
        commit('updateHistory', diff);
        dispatch('status/load', { website }, { root: true });
        commit('setActualURL', website);
      }
      resolve(website);
    });
  },
  setNodeCount({ commit }, nodeCount) {
    commit('setNodeCount', nodeCount);
  },
};

// mutations
const mutations = {
  addQueryToHistory(state, website) {
    state.historyIndex += 1;
    state.history.length = state.historyIndex;
    state.history.push(website);
  },
  setActualURL(state, website) {
    state.actualURL = `http://localhost:27182?url=${website}&count=${state.nodeCount}`;
  },
  setNodeCount(state, nodeCount) {
    state.nodeCount = nodeCount;
  },
  updateHistory(state, diff) {
    if (state.historyIndex > -1) {
      state.historyIndex += diff;
    }
  },
};

export default {
  namespaced: true,
  state,
  actions,
  mutations,
};
