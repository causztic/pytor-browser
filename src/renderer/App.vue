<style lang="scss">
  body {
    margin: 0;
  }
  #navigation {
    padding: 8px 0;
    width: 100%;
    display: flex;
    position: relative;
    align-items: center;
    background-color: #fafafa;
    .action-button, #omnibox {
      display: inline-block;
      margin-right: 5px;
    }
    #omnibox {
      flex: 1;
      width: 100%;
      input {
        box-sizing: border-box;
        width: inherit;
        border: 1px solid #fff;
        outline: none;
        background-color: #eee;
        padding: 5px 5px;
        border-radius: 10px;
        &:active, &:focus {
          background-color: #fff;
          border: 1px solid #aaf;
        }
      }
    }
    .action-button {
      color: #777;
      height: 32px;
      width: 32px;
      line-height: 32px;
      text-align: center;
      cursor: pointer;
      border-radius: 50%;
      transition: all 0.3s;
      &.active {
        background-color: #eee;
      }
      &:hover {
        background-color: #dadada;
      }
      &.disabled {
        color: #bbb;
        cursor: initial;
        &:hover {
          background-color: initial;
        }
      }
    }
  }
</style>

<template>
  <div class="main">
    <nav id="navigation">
      <div id="back" class="action-button disabled">
        <i class="fa fa-arrow-left" aria-hidden="true"></i>
      </div>
      <div id="forward" class="action-button disabled">
        <i class="fa fa-arrow-right" aria-hidden="true"></i>
      </div>
      <div id="refresh" class="action-button disabled">
        <i class="fa fa-sync" aria-hidden="true"></i>
      </div>
      <div id="omnibox">
        <input type="text" id="url">
      </div>
      <SettingsComponent />
    </nav>
    <div class="body">
      <LoadingComponent />
    </div>
  </div>
</template>

<script>
  import LoadingComponent from './LoadingComponent.vue';
  import SettingsComponent from './SettingsComponent.vue';
  export default {
    name: 'app',
    components: { LoadingComponent, SettingsComponent }
  }
</script>