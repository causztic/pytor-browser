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
  pingDirectoryStatus({ commit }) {
    getDirectoryStatus().then((relays) => {
      commit('updateRelays', relays);
    });
  },
};

const relayAddresses = relays => relays.map(relay => relay.address);

const mutations = {
  setRelays(state, relays) {
    state.relays = relays.map((relay) => {
      const updatedRelay = {};
      updatedRelay.address = relay;
      updatedRelay.status = 'online';
      return updatedRelay;
    });
  },
  updateRelays(state, relays) {
    const tempRelays = state.relays.map((relay) => {
      if (!relays.includes(relay.address)) {
        relay.status = 'offline';
      }
      return relay;
    });

    // add new relays
    relays.forEach((newRelay) => {
      if (!relayAddresses(tempRelays).includes(newRelay)) {
        const updatedRelay = {};
        updatedRelay.address = newRelay;
        updatedRelay.status = 'online';
        tempRelays.push(newRelay);
      }
    });

    state.relays = tempRelays;
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
