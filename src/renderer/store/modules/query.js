// eslint-disable-next-line import/no-unresolved
import { spawnClient } from 'common/util';

// initial state
const state = {
  history: [],
  response: null,
  status: null,
};

// getters
const getters = {};

// actions
const actions = {
  getWebsite({ dispatch, commit }, website) {
    dispatch('status/load', { website }, { root: true });
    commit('setResponse', null);
    const result = spawnClient(website);

    console.log(result);

    result.stdout.on('data', (data) => {
      console.log(`stdout: ${data}`);

      commit('addQueryToHistory', website);
      commit('setResponse', data);
    });

    result.stderr.on('data', (data) => {
      console.log(`stderr: ${data}`);
      commit('setResponse', null);
    });

    result.on('close', (code) => {
      console.log(`child process exited with code ${code}`);
      dispatch('status/connected', null, { root: true });
    });
  },
};

// mutations
const mutations = {
  addQueryToHistory(state, website) {
    state.history.push(website);
  },
  setResponse(state, response) {
    state.response = response;
  },
};

export default {
  namespaced: true,
  state,
  getters,
  actions,
  mutations,
};
