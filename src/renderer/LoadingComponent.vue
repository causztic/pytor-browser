<style lang="scss" scoped>
  .loading-messages {
    color: #777;
    background-color: rgba(225, 225, 225, 0.5);
    padding: 5px 10px;
    font-size: 0.75rem;
    font-family: sans-serif;
    position: absolute;
    right: 0;
    bottom: 0;
  }
  #status {
    width: 10px;
    height: 10px;
    display: inline-block;
    border-radius: 50%;
    &.inactive {
      background-color: red;
    }
    &.active {
      background-color: green;
    }
    @keyframes blink-animation {
      25% {
        opacity: 0.5;
      }
      50% {
        opacity: 0;
      }
      75% {
        opacity: 0.5;
      }
    }
    &.blinking {
      animation: blink-animation 1.5s steps(5, start) infinite;
    }
  }
</style>

<template>
  <div class="loading-messages">
    <span>{{ message }}</span>
    <span id="status" :class="connected ? 'active' : 'inactive'"></span>
  </div>
</template>

<script>
  export default {
    name: 'loading-component',
    data() {
      return {
        connected: false,
        message: 'You are not connected to the network.',
      }
    },
  }
</script>