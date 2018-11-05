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
    <iframe :srcdoc="response === null ? initialHTML : response" />
  </div>
</template>

<script>
  import fs from "fs";
  import { mapState, mapActions } from 'vuex';

  export default {
    name: "browser-component",
    props: ["url", "fired"],
    computed: mapState({
      response: state => state.query.response,
      connected: state => state.status.connected,
    }),
    watch: {
      fired: function(newVal, oldVal) {
        if (newVal && this.connected) {
          this.$store.dispatch('query/getWebsite', this.url);
          this.$emit('update:fired', false);
        }
      }
    },
    created() {
      Promise.resolve(this.$store.dispatch('status/startServers'));
    },
    data() {
      return {
        initialHTML: require('../503.html'),
      }
    }
  }
</script>