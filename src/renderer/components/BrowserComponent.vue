<style lang="scss" scoped>
  .content {
    width: 100%;
    height: 100%;
    display: flex;
  }
  iframe, webview {
    flex-grow: 1;
    border: none;
  }
</style>

<template>
  <div class="content">
    <iframe :srcdoc="initialHTML" v-if="actualURL === null" />
    <webview v-else :src="actualURL"></webview>
  </div>
</template>

<script>
import { mapState } from 'vuex';

const initialHTML = require('../503.html');

export default {
  name: 'BrowserComponent',
  props: ['url', 'fired'],
  data() {
    return {
      initialHTML,
    };
  },
  computed: mapState({
    // response: state => state.query.response,
    actualURL: state => state.query.actualURL,
    connected: state => state.status.connected,
  }),
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
