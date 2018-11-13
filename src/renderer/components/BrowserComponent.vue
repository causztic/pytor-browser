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
      @did-stop-loading="loadStop" @will-navigate="injectURL"></webview>
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
    currentURL: state => state.query.history.slice(-1)[0],
  }),
  methods: {
    loadStop() {
      this.$store.dispatch('status/connected');
    },
    injectURL(event) {
      event.preventDefault();
      let { url } = event;
      if (event.url.startsWith('http://localhost:27182')) {
        // relative link, append current website
        // eslint-disable-next-line no-unused-vars
        const [protocol, _, host] = this.currentURL.split('/');
        url = `${protocol}//${host}${event.url.split('http://localhost:27182')[1]}`;
      }
      console.log(url);
      this.$emit('linkClick', url);
      this.$store.dispatch('query/getWebsite', url);
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
    this.$store.dispatch('status/startProxy');
  },
};
</script>
