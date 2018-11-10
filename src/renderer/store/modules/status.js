// eslint-disable-next-line import/no-unresolved
import { seconds } from 'common/util';

const state = {
  message: 'You are not connected to the network.',
  connected: false,
  connectionState: 'not_connected',
  serverNodes: [],
  directoryQueryDelay: 1000,
  directoryQueryDelayCounter: 1000,
};

const actions = {
  load({ commit }, { website }) {
    commit('loading', website);
  },
  connected({ commit }) {
    commit('connected');
  },
  decrementDelay({ commit, dispatch }) {
    // try again after a certain time.
    setTimeout(() => {
      commit('decrementDelay');
      if (state.directoryQueryDelayCounter === 0) {
        dispatch('startServers');
      } else {
        dispatch('decrementDelay');
      }
    }, 1000);
  },
  startServers({ commit, dispatch }) {
    // prepare for Directory, use placeholder wait
    commit('connecting');
    // simulate a connection to the Directory.
    setTimeout(() => {
      commit('connectionFailed');
      dispatch('decrementDelay');
    }, 3000);
  },
};

const mutations = {
  connecting(state) {
    state.message = 'Connecting..';
    state.connectionState = 'connecting';
    state.connected = false;
  },
  loading(state, website) {
    state.message = `Loading ${website}..`;
    state.connectionState = 'connecting';
  },
  connected(state) {
    state.message = 'Connected to network.';
    state.connectionState = 'connected';
    state.connected = true;
  },
  connectionFailed(state) {
    state.directoryQueryDelay *= 2;
    state.directoryQueryDelayCounter = state.directoryQueryDelay;
    state.message = `Failed to connect to Directory. Retry in ${seconds(state.directoryQueryDelayCounter)}..`;
    state.connectionState = 'not-connected';
    state.connected = false;
  },
  decrementDelay(state) {
    state.directoryQueryDelayCounter -= 1000;
    state.message = `Failed to connect to Directory. Retry in ${seconds(state.directoryQueryDelayCounter)}..`;
    state.connectionState = 'not-connected';
  },
};

export default {
  namespaced: true,
  state,
  actions,
  mutations,
};
