<style lang="scss" scoped>
  #options-menu {
    box-sizing: border-box;
    position: absolute;
    right: 0;
    bottom: -295px;
    width: 300px;
    height: 300px;
    background-color: #fdfdfd;
    padding: 10px;
    border-radius: 5px;
    border: solid 1px #ccc;
    box-shadow: 5px 5px 25px 5px #efefef;
    font-family: "system-ui";
  }
  .relay {
    display: block;
    font-size: 0.9em;
  }
  span.online, span.offline {
    width: 10px;
    height: 10px;
    display: inline-block;
    border-radius: 50%;
  }
  span.online {
    background-color: green;
  }
  span.offline {
    background-color: red;
  }
</style>

<template>
  <div v-click-outside="hideMenuIfVisible">
    <div id="options" :class="activeClass" v-on:click="toggleMenu">
      <i class="fa fa-ellipsis-v" aria-hidden="true"></i>
    </div>
    <div id="options-menu" v-if="showMenu">
      <h2>Relays</h2>
      <span class="relay" v-for="relay in relays" :key="relay.address">
        <span :class="relay.status"></span>
        <b>{{ relay.address }}</b>
      </span>
      <h2>Connections</h2>
      <select v-model="nodeCount">
        <option v-for="count in relayCounts" :key="count">{{count}}</option>
      </select>
    </div>
  </div>
</template>

<script>
import { mapState } from 'vuex';

export default {
  name: 'SettingsComponent',
  computed: mapState({
    relays: state => state.status.relays,
    relayCounts: (state) => {
      if (state.status.relays.length <= 3) {
        return [3];
      }
      return Array(state.status.relays.length - 2).fill().map((_, i) => i + 3);
    },
  }),
  methods: {
    toggleMenu() {
      this.showMenu = !this.showMenu;
      if (this.showMenu) {
        this.activeClass = 'action-button active';
        this.$store.dispatch('status/pingDirectoryStatus');
      } else {
        this.activeClass = 'action-button';
      }
    },
    hideMenuIfVisible() {
      if (this.showMenu) {
        this.activeClass = 'action-button';
        this.showMenu = false;
      }
    },
  },
  watch: {
    nodeCount(newVal, _) {
      this.$store.dispatch('query/setNodeCount', newVal);
    },
  },
  data() {
    return {
      showMenu: false,
      nodeCount: 3,
      activeClass: 'action-button',
    };
  },
};
</script>
