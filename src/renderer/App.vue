<style lang="scss" scoped>
  #navigation {
    width: 100%;
    display: flex;
    div {
      display: inline-block;
      margin-right: 15px;
    }
    #omnibox {
      flex: 1;
      width: 100%;
      input {
        width: inherit;
      }
    }
  }
</style>

<template>
  <nav id="navigation">
    <div id="back">
      <i class="fa fa-arrow-left" aria-hidden="true"></i>
    </div>
    <div id="forward">
      <i class="fa fa-arrow-right" aria-hidden="true"></i>
    </div>
    <div id="refresh">
      <i class="fa fa-sync" aria-hidden="true"></i>
    </div>
    <div id="omnibox">
      <input type="text" id="url">
    </div>
  </nav>
</template>

<script>
  export default {
    name: 'app'
  }
</script>