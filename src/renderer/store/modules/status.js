// eslint-disable-next-line import/no-unresolved
import { seconds, spawnClientAndServers } from 'common/util';

const electron = require('electron');

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
  startServers({ commit }) {
    // TODO: check that directory and servers are up.
    // find a better way to instantiate the servers
    spawnClientAndServers().then(() => {
      commit('connected');
    }).catch(() => {
      electron.ipcRenderer.send('clear-pids');
      commit('decerementDelay');
    });
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
