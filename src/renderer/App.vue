<style lang="scss">
  body {
    margin: 0;
  }
  #navigation {
    padding: 8px;
    width: 100%;
    display: flex;
    align-items: center;
    background-color: #fafafa;
    div {
      display: inline-block;
      margin-right: 15px;
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
      color: #bbb;
      width: 16px;
      &.active {
        color: #777;
      }
    }
  }
</style>

<template>
  <nav id="navigation">
    <div id="back" class="action-button">
      <i class="fa fa-arrow-left" aria-hidden="true"></i>
    </div>
    <div id="forward" class="action-button">
      <i class="fa fa-arrow-right" aria-hidden="true"></i>
    </div>
    <div id="refresh" class="action-button">
      <i class="fa fa-sync" aria-hidden="true"></i>
    </div>
    <div id="omnibox">
      <input type="text" id="url">
    </div>
    <div id="options" class="action-button active">
      <i class="fa fa-ellipsis-v" aria-hidden="true"></i>
    </div>
  </nav>
</template>

<script>
  export default {
    name: 'app'
  }
</script>