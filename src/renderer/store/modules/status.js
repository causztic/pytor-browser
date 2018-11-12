// eslint-disable-next-line import/no-unresolved
import { seconds, spawnClient, getDirectoryStatus } from 'common/util';

const state = {
  realMessage: '',
  message: 'You are not connected to the network.',
  connected: false,
  connectionState: 'not_connected',
  relays: [],
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
        dispatch('startProxy');
      } else {
        dispatch('decrementDelay');
      }
    }, 1000);
  },
  startProxy({ commit, dispatch }) {
    commit('connecting');
    getDirectoryStatus().then((relays) => {
      commit('setRelays', relays);
      spawnClient().then(() => {
        commit('connected');
      });
    }).catch((message) => {
      commit('connectionFailed', message);
      dispatch('decrementDelay');
    });
  },
};

const mutations = {
  setRelays(state, relays) {
    state.relays = relays;
  },
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
  connectionFailed(state, message) {
    state.directoryQueryDelay *= 2;
    state.directoryQueryDelayCounter = state.directoryQueryDelay;
    state.realMessage = message;
    state.message = `${message}. Retry in ${seconds(state.directoryQueryDelayCounter)}..`;
    state.connectionState = 'not-connected';
    state.connected = false;
  },
  decrementDelay(state) {
    state.directoryQueryDelayCounter -= 1000;
    state.message = `${state.realMessage}. Retry in ${seconds(state.directoryQueryDelayCounter)}..`;
    state.connectionState = 'not-connected';
  },
};

export default {
  namespaced: true,
  state,
  actions,
  mutations,
};
