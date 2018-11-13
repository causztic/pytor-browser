<style lang="scss">
  @import '~@fortawesome/fontawesome-free/css/all.css';

  body {
    margin: 0;
    height: 100vh;
  }
  .main {
    display: flex;
    width: 100%;
    height: 100%;
    flex-direction: column;
  }
  #navigation {
    padding: 8px 0;
    width: 100%;
    display: flex;
    position: relative;
    align-items: center;
    background-color: #fafafa;
    .action-button, #omnibox {
      display: inline-block;
      margin-right: 5px;
    }
    #omnibox {
      position: relative;
      flex: 1;
      width: 100%;
      input {
        box-sizing: border-box;
        width: inherit;
        border: 1px solid #fff;
        outline: none;
        background-color: #eee;
        padding: 5px 5px;
        border-radius: 10px;
        &:active, &:focus {
          background-color: #fff;
          border: 1px solid #aaf;
        }
      }
      .autocomplete-results {
        padding: 0;
        margin: 0;
        border: 1px solid #eeeeee;
        height: 120px;
        overflow: auto;
        background-color: #fff;
        border-radius: 0 0 10px 10px;
        filter: drop-shadow(2px 2px rgba(220, 220, 220, 0.2));
        position: absolute;
        width: 100%;
      }

      .autocomplete-result {
        font-family: sans-serif;
        list-style: none;
        text-align: left;
        padding: 4px 2px;
        cursor: pointer;
      }

      .autocomplete-result:hover {
        background-color: #4AAE9B;
        color: white;
      }
    }
    .action-button {
      color: #777;
      height: 32px;
      width: 32px;
      line-height: 32px;
      text-align: center;
      cursor: pointer;
      border-radius: 50%;
      transition: all 0.3s;
      &.active {
        background-color: #eee;
      }
      &:hover {
        background-color: #dadada;
      }
      &.disabled {
        color: #bbb;
        cursor: initial;
        &:hover {
          background-color: initial;
        }
      }
    }
  }
</style>

<template>
  <div class="main">
    <nav id="navigation">
      <div id="back" class="action-button" :class="{disabled: backDisabled}"
        @click="navigateHistory(-1, backDisabled)">
        <i class="fa fa-arrow-left" aria-hidden="true"></i>
      </div>
      <div id="forward" class="action-button" :class="{disabled: forwardDisabled}"
        @click="navigateHistory(1, forwardDisabled)">
        <i class="fa fa-arrow-right" aria-hidden="true"></i>
      </div>
      <div id="refresh" class="action-button disabled">
        <i class="fa fa-sync" aria-hidden="true"></i>
      </div>
      <div id="omnibox">
        <input v-model="url" type="text" id="url" @keyup.enter="navigate" @input="onChange">
        <ul class="autocomplete-results" v-show="isOpen">
          <li class="autocomplete-result"
            v-for="(result, i) in results" :key="i" @click="setURLFromResult(result)">
            {{ result }}
          </li>
        </ul>
      </div>
      <SettingsComponent />
    </nav>
    <BrowserComponent v-bind:url="url" v-bind:fired.sync="fired" v-on:linkClick="updateURL"/>
    <StatusComponent />
  </div>
</template>

<script>
import { mapState } from 'vuex';

import StatusComponent from './components/StatusComponent.vue';
import SettingsComponent from './components/SettingsComponent.vue';
import BrowserComponent from './components/BrowserComponent.vue';

export default {
  name: 'app',
  components: { StatusComponent, SettingsComponent, BrowserComponent },
  computed: mapState({
    history: state => [...new Set(state.query.history)],
    backDisabled: state => (state.query.historyIndex <= 0),
    forwardDisabled: state => (state.query.historyIndex + 1 === state.query.history.length),
  }),
  methods: {
    onChange() {
      this.isOpen = true;
      this.filterResults();
    },
    filterResults() {
      this.results = this.history.filter(item => item.toLowerCase()
        .indexOf(this.url.toLowerCase()) > -1);
    },
    setURLFromResult(url) {
      this.updateURL(url);
      this.navigate();
    },
    updateURL(url) {
      this.url = url;
    },
    navigate() {
      this.fired = true;
      this.isOpen = false;
    },
    navigateHistory(diff, disabled) {
      if (!disabled) {
        this.$store.dispatch('query/navigateHistory', diff).then((website) => {
          this.url = website;
        });
      }
    },
  },
  data() {
    return {
      url: 'http://www.example.com',
      fired: false,
      isOpen: false,
      results: [],
    };
  },
};
</script>
