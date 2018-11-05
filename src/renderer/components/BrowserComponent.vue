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
    <iframe :srcdoc="response" />
  </div>
</template>

<script>
  import fs from "fs";
  import { mapState, mapActions } from 'vuex';

  export default {
    name: "browser-component",
    computed: mapState({
      response: state => state.query.response
    }),
    created() {
      this.$store.dispatch('query/getWebsite', 'https://www.motherfuckingwebsite.com');
    },
    data() {
      return {
        initialHTML: require('../503.html'),
      }
    }
  }
</script>