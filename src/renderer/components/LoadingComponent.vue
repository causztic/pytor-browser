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

    &.not-connected {
       background-color: red;
    };
    &.connected {
      background-color: green;
    };
    &.connecting {
      background-color: green;
      animation: blink-animation 1.5s steps(5, start) infinite;
    };
  }
</style>

<template>
  <div class="loading-messages">
    <span>{{ message }}</span>
    <span id="status" :class="connection_state"></span>
  </div>
</template>

<script>
  import { mapState, mapActions } from 'vuex';

  export default {
    name: 'loading-component',
    computed: mapState({
      connection_state: state => state.status.connection_state,
      message: state => state.status.message,
    }),
  }
</script>