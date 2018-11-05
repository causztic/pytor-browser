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
</style>

<template>
  <div v-click-outside="hideMenuIfVisible">
    <div id="options" :class="activeClass" v-on:click="toggleMenu">
      <i class="fa fa-ellipsis-v" aria-hidden="true"></i>
    </div>
    <div id="options-menu" v-if="showMenu">
    </div>
  </div>
</template>

<script>
  export default {
    name: "settings-component",
    data() {
      return {
        showMenu: false,
        nodeCount: 0,
        activeClass: 'action-button',
      };
    },
    methods: {
      toggleMenu() {
        this.showMenu = !this.showMenu;
        if (this.showMenu)
          this.activeClass = 'action-button active';
        else
          this.activeClass = 'action-button';
      },
      hideMenuIfVisible() {
        if (this.showMenu) {
          this.activeClass = 'action-button';
          this.showMenu = false;
        }
      },
    }
  }
</script>