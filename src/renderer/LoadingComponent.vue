<style lang="scss" scoped>
  .loading {
    color: #777;
    background-color: rgba(225, 225, 225, 0.5);
    padding: 5px 20px 5px 10px;
    font-size: 0.75rem;
    font-family: sans-serif;
    position: absolute;
    right: 0;
    bottom: 0;
  }
</style>

<template>
  <div class="loading" v-if="message">{{ message }}</div>
</template>

<script>
  export default {
    name: 'loading-component',
    data() {
      return {
        message: '',
      }
    },
  }
</script>