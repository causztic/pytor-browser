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
</style>

<template>
  <div v-click-outside="hideMenuIfVisible">
    <div id="options" :class="activeClass" v-on:click="toggleMenu">
      <i class="fa fa-ellipsis-v" aria-hidden="true"></i>
    </div>
    <div id="options-menu" v-if="showMenu">
      <h1>Online Relays</h1>
      <span class="relay" v-for="relay in relays" :key="relay">
        {{ relay }}
      </span>
    </div>
  </div>
</template>

<script>
import { mapState } from 'vuex';

export default {
  name: 'SettingsComponent',
  computed: mapState({
    relays: state => state.status.relays,
  }),
  methods: {
    toggleMenu() {
      this.showMenu = !this.showMenu;
      if (this.showMenu) {
        this.activeClass = 'action-button active';
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
  data() {
    return {
      showMenu: false,
      nodeCount: 0,
      activeClass: 'action-button',
    };
  },
};
</script>
