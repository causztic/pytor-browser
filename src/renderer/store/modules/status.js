// eslint-disable-next-line import/no-unresolved
import { spawnServers } from 'common/util';

const state = {
  message: 'You are not connected to the network.',
  connected: false,
  connectionState: 'not_connected',
};

const actions = {
  load({ commit }, { website }) {
    commit('loading', website);
  },
  connected({ commit }) {
    commit('connected');
  },
  startServers({ commit, state }) {
    if (!state.connected) {
      const instances = spawnServers();
      commit('connecting');
      return new Promise((resolve, _) => {
        // TODO: check for server timeouts
        // TODO: update to check for exact server startup
        instances.forEach((instance) => {
          instance.stdout.on('data', (data) => {
            console.log(`stdin: ${data}`);
          });

          instance.stderr.on('data', (data) => {
            console.log(`stderr: ${data}`);
          });

          instance.on('close', (code) => {
            console.log(`child process exited with code ${code}`);
          });
        });

        setTimeout(() => {
          commit('connected');
          resolve();
        }, 300);
      });
    }
    return new Promise((resolve, _) => {
      resolve();
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
};

export default {
  namespaced: true,
  state,
  actions,
  mutations,
};
