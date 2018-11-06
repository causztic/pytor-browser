// initial state
import { spawnServers } from 'common/util';

const state = {
  message: 'You are not connected to the network.',
  connected: false,
  connectionState: 'not_connected',
};

const actions = {
  load({ commit }) {
    commit('loading');
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
        for (let instance of instances) {
          instance.stdout.on('data', data => {
            console.log(`stdin: ${data}`);
          });

          instance.stderr.on('data', data => {
            console.log(`stderr: ${data}`);
          });

          instance.on('close', code => {
            console.log(`child process exited with code ${code}`);
          });
        }

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
    PopStateEvent.connected = false;
  },
  loading(state) {
    state.message = 'Loading page..';
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
