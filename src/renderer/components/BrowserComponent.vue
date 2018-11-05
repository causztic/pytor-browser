<style lang="scss" scoped>
  .content {
    width: 100%;
    height: 100%;
    display: flex;
  }
  iframe {
    flex-grow: 1;
    border: none;
  }
</style>

<template>
  <div class="content">
    <iframe :srcdoc="initialHTML" />
  </div>
</template>

<script>
  export default {
    name: "browser-component",
    data() {
      return {
        initialHTML: require(`${__static}/503.html`)
      }
    }
  }
</script>