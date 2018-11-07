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
    display: flex;
    min-width: 150px;
    align-items: center;
    justify-content: flex-end;
  }
  #status {
    margin-left: 5px;
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
    <span id="status" :class="connectionState" />
  </div>
</template>

<script>
import { mapState } from 'vuex';

export default {
  name: 'LoadingComponent',
  computed: mapState({
    connectionState: state => state.status.connectionState,
    message: state => state.status.message,
  }),
};
</script>
