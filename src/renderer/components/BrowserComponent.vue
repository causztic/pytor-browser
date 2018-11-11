<style lang="scss" scoped>
  .content {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .icon {
    width: 75px;
    height: 75px;
    opacity: 0.25;
  }
  webview {
    flex-grow: 1;
    border: none;
    width: 100%;
    height: 100%;
  }
</style>

<template>
  <div class="content">
    <img class="icon" src="./../onion.png" v-show="actualURL === null" />
    <webview v-show="actualURL !== null" :src="actualURL"
      @did-stop-loading="loadStop"></webview>
  </div>
</template>

<script>
import { mapState } from 'vuex';

export default {
  name: 'BrowserComponent',
  props: ['url', 'fired'],
  computed: mapState({
    actualURL: state => state.query.actualURL,
    connected: state => state.status.connected,
  }),
  methods: {
    loadStop() {
      this.$store.dispatch('status/connected');
    },
  },
  watch: {
    fired(newVal, _) {
      if (newVal && this.connected) {
        this.$store.dispatch('query/getWebsite', this.url);
        this.$emit('update:fired', false);
      }
    },
  },
  created() {
    this.$store.dispatch('status/startServers');
  },
};
</script>
