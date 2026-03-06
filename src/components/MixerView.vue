<template>
  <div id="channels">
    <!-- Clear button in the top-left corner -->
    <div class="clear-button">
      <button class="clear-btn" @click="onClearClick">Clear</button>
    </div>

    <!-- Preset dropdown in the top-right corner -->
    <div class="preset-dropdown">
      <label for="preset-select">Presets</label>
      <div class="preset-controls">
        <select id="preset-select" v-model="selectedPreset" @change="onPresetChange">
          <option :value="SAVE_SENTINEL">Save preset...</option>
          <option disabled>────────</option>
          <option v-for="name in presets" :key="name" :value="name">{{ name }}</option>
        </select>

        <!-- Visible list of presets with small delete buttons beside each -->
        <div class="preset-list" v-if="presets.length">
          <div class="preset-item" v-for="name in presets" :key="name">
            <button class="preset-delete" @click.prevent="deletePreset(name)" title="Delete preset">✕</button>
            <span class="preset-name">{{ name }}</span>
          </div>
        </div>
      </div>
    </div>

    <template v-for="(group, gidx) in channelGroups" :key="gidx">
      <div class="channel-group">
        <div class="group-title">{{ group.title }}</div>
        <div class="group-channels">
          <template v-for="channel in group.channels" :key="channel.volume_cc || channel.title">
            <div v-if="channel.hide !== true" class="channel">
              <div class="channel-label">{{ channel.title }}</div>

              <!-- Faders: render one or two faders centered horizontally -->
              <div class="faders-wrapper" :class="`faders-${fadersForChannel(channel).length}`">
                <template v-for="(fader, faderIndex) in fadersForChannel(channel)" :key="fader.cc">
                  <div class="fader-column" :class="`fader-column-${faderIndex}`">
                    <div class="fader-container"
                         :class="{ 'dragging': dragState[fader.cc], [fader.classNameSuffix]: true }" :key="faderIndex">
                      <input
                          ref="faders"
                          class="fader"
                          :class="`${fader.classNameSuffix}`"
                          type="range"
                          min="0"
                          max="127"
                          v-model.number="values[fader.cc]"
                          @input="onInput(fader.cc)"
                          @pointerdown="onPointerDown(fader.cc, $event)"
                      />
                    </div>

                    <!-- Editable numeric value per fader -->
                    <input
                        class="value-display"
                        type="number"
                        min="0"
                        max="127"
                        :value="values[fader.cc] ?? 0"
                        @change="onValueEdit(fader.cc, $event)"
                        @blur="onValueEdit(fader.cc, $event)"
                        @keydown.enter.prevent="onValueEdit(fader.cc, $event)"
                    />

                    <div class="cc-number">{{ fader.label }} {{ fader.cc }}</div>
                  </div>
                  <div class="fader-ticks" :class="`fader-ticks-${faderIndex}`"
                       v-if="fadersForChannel(channel).length === 1 || faderIndex < fadersForChannel(channel).length - 1">
                    <div v-for="number in tick_values" class="fader-tick" :key="number">
                      <div class="tick-mark"/>
                      <div class="tick-number">{{ number }}</div>
                      <div v-if="fadersForChannel(channel).length !== 1" class="tick-mark"/>
                    </div>
                  </div>

                </template>
              </div>

              <!-- Mute button: toggles mute state for channel.mute_cc (one per channel, below the faders) -->
              <button
                  class="mute-btn"
                  :class="{ active: muteState[channel.mute_cc] > 0 }"
                  @click="toggleMute(channel.mute_cc)"
                  title="Toggle mute"
              >M
              </button>
            </div>
          </template>
        </div>
      </div>
      <div v-if="gidx < channelGroups.length - 1" class="group-divider"></div>
    </template>
  </div>
</template>

<script>
import {useRelativeDrag} from "../composables/useRelativeDrag";

export default {
  data() {
    return {
      channelGroups: [],
      ws: null,
      values: {},
      // per-cc drag state for visual feedback (keyed by cc number)
      dragState: {},
      // current mute state keyed by mute_cc (0 or 1)
      muteState: {},
      // the composable handles global pointer listeners
      _dragComposable: null,
      _dragComposableStop: null,
      tick_values: [127, 111, 95, 79, 63, 47, 31, 15, 0],
      // Throttling support for outgoing CC messages
      _throttleIntervalMs: 20,
      _throttleTimer: null,
      _lastSentAt: 0,
      _pendingMessages: {},

      // Preset support
      presets: [],
      selectedPreset: null,
      SAVE_SENTINEL: '__save__',
      _storageKey: 'remote_mixer_presets'
    };
  },
  computed: {
    nonHiddenChannels() {
      const channels = [];

      for (const channelGroup of this.channelGroups) {
        for (const channel of channelGroup.channels) {
          if (channel.hide !== true) {
            channels.push(channel);
          }
        }
      }

      return channels;
    }
  },
  mounted() {
    this.initialize();
    this._dragComposable = useRelativeDrag();
    // load presets from localStorage after initialization started
    this.loadPresetsFromStorage();
  },
  methods: {
    // returns an array of faders to render for a channel (volume always first, optional verb)
    fadersForChannel(channel) {
      const arr = [];

      if (channel.volume_cc !== undefined) arr.push({cc: channel.volume_cc, label: 'Vol', classNameSuffix: "volume"});
      if (channel.mon_cc !== undefined) arr.push({cc: channel.mon_cc, label: 'Mon', classNameSuffix: "monitor"});
      if (channel.verb_cc !== undefined) arr.push({cc: channel.verb_cc, label: 'Verb', classNameSuffix: "reverb"});

      return arr;
    },

    onPointerDown(cc, e) {
      // Support command/meta-click for jump-to-click behavior
      const input = e.target;
      if (e.metaKey || e.ctrlKey) {
        // compute jump location as native behavior: calculate value from click
        const rect = input.getBoundingClientRect();
        const isVertical = rect.height > rect.width;
        const pos = isVertical ? e.clientY : e.clientX;
        const offset = isVertical ? (rect.bottom - pos) : (pos - rect.left);
        const ratio = offset / (isVertical ? rect.height : rect.width);
        const value = Math.round(Math.min(1, Math.max(0, ratio)) * 127);
        this.setValueAndSend(cc, value);
        return;
      }

      // Start relative drag using the composable
      if (this.$set) this.$set(this.dragState, cc, true);
      else this.dragState[cc] = true;

      const stop = this._dragComposable.start(e, this.values[cc], input, (newVal) => {
        this.setValueAndSend(cc, newVal);
      }, () => {
        if (this.$set) this.$set(this.dragState, cc, false);
        else this.dragState[cc] = false;
      });

      this._dragComposableStop = stop && stop.stop ? stop.stop : null;
    },

    async initialize() {
      try {
        const response = await fetch("/config");
        const cfg = await response.json();
        if (cfg.error) {
          console.error("Config error", cfg.error);
          return;
        }

        // Expect config.channel_groups each with channels that contain volume_cc and mute_cc
        this.channelGroups = cfg.channel_groups || [];

        // initialize values and muteState keyed by CC numbers
        this.nonHiddenChannels.forEach(ch => {
          const volCc = ch.volume_cc ?? (ch.cc ?? undefined);
          const muteCc = ch.mute_cc;
          const verbCc = ch.verb_cc;
          const monCc = ch.mon_cc;

          if (volCc !== undefined) {
            if (this.$set) this.$set(this.values, volCc, 0);
            else this.values[volCc] = 0;
          }
          if (verbCc !== undefined) {
            if (this.$set) this.$set(this.values, verbCc, 0);
            else this.values[verbCc] = 0;
          }
          if (monCc !== undefined) {
            if (this.$set) this.$set(this.values, monCc, 0);
            else this.values[monCc] = 0;
          }

          if (muteCc !== undefined) {
            if (this.$set) this.$set(this.muteState, muteCc, 0);
            else this.muteState[muteCc] = 0;
          }

          // ensure channel has both fields (if backend sent old 'cc' rename, support fallback)
          // if (ch.cc && !ch.volume_cc) ch.volume_cc = ch.cc;
          // if (ch.mute_cc === undefined) ch.mute_cc = 0;
          // if (ch.mon_cc === undefined) ch.mon_cc = 0;
        });

        this.connectWs();
      } catch (e) {
        console.error("Failed to load config", e);
      }
    },

    connectWs() {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/ws`;
      this.ws = new WebSocket(wsUrl);
      this.ws.onopen = () => {
        this.$emit("connection", true);
      };
      this.ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.type === "midi_cc_update") {
            const cc = data.cc;
            const value = data.value;

            // If this CC corresponds to a volume/verb CC, update values; if it's a mute CC, update muteState
            if (this.values.hasOwnProperty(cc)) {
              if (this.$set) this.$set(this.values, cc, value);
              else this.values[cc] = value;
            }
            if (this.muteState.hasOwnProperty(cc)) {
              // treat nonzero as muted (1), zero as unmuted (0)
              const m = value ? 127 : 0;
              if (this.$set) this.$set(this.muteState, cc, m);
              else this.muteState[cc] = m;
            }
          }
        } catch (_) {
          // ignore non-json
        }
      };
      this.ws.onclose = () => {
        this.$emit("connection", false);
        setTimeout(() => this.connectWs(), 1500);
      };
      this.ws.onerror = (err) => console.error("ws error", err);
    },

    onInput(cc) {
      const value = parseInt(this.values[cc]);
      this.setValueAndSend(cc, value);
    },

    onValueEdit(cc, event) {
      const raw = event && event.target ? event.target.value : event;
      const parsed = parseInt(raw);
      this.setValueAndSend(cc, parsed);
    },

    toggleMute(muteCc) {
      // toggle current mute state (0/1)
      const current = this.muteState[muteCc] || 0;
      const newState = current ? 0 : 127;
      if (this.$set) this.$set(this.muteState, muteCc, newState);
      else this.muteState[muteCc] = newState;

      // send CC message: 1 for muted, 0 for unmuted
      const msg = JSON.stringify({type: 'cc', cc: muteCc, value: newState});
      if (this.ws && this.ws.readyState === WebSocket.OPEN) this.ws.send(msg);
    },

    setValueAndSend(cc, parsedValue) {
      let value = Number.isFinite(parsedValue) ? parseInt(parsedValue) : NaN;
      if (Number.isNaN(value)) {
        value = this.values[cc] ?? 0;
      }
      if (value < 0) value = 0;
      if (value > 127) value = 127;
      if (this.$set) this.$set(this.values, cc, value);
      else this.values[cc] = value;

      this.sendWSCCMessage(cc, value);
    },

    sendWSCCMessage(cc, value) {
      // Store the latest value for this CC in the pending map
      this._pendingMessages[cc] = value;

      const sendPending = () => {
        const entries = Object.entries(this._pendingMessages);
        if (entries.length === 0) return;

        // Clear pending map before sending to avoid re-entrancy issues
        this._pendingMessages = {};
        this._lastSentAt = Date.now();

        // Send each pending cc message as individual CC messages (preserves previous behavior)
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          for (const [pcc, pval] of entries) {
            try {
              this.ws.send(JSON.stringify({type: "cc", cc: Number(pcc), value: pval}));
            } catch (e) {
              // ignore send errors; will not retry for now
            }
          }
        }
      };

      const now = Date.now();

      // If enough time has passed since last send, send immediately
      if (!this._lastSentAt || (now - this._lastSentAt) >= this._throttleIntervalMs) {
        sendPending();
      }

      // Ensure a periodic timer exists while there are pending messages that arrive faster than interval
      if (!this._throttleTimer) {
        // Start timer which will flush pending messages every _throttleIntervalMs
        this._throttleTimer = setInterval(() => {
          if (Object.keys(this._pendingMessages).length === 0) {
            // nothing left to send -> stop the timer
            clearInterval(this._throttleTimer);
            this._throttleTimer = null;
            return;
          }

          // send latest pending batch
          sendPending();
        }, this._throttleIntervalMs);
      }
    },

    // Preset storage helpers
    loadPresetsFromStorage() {
      try {
        const raw = localStorage.getItem(this._storageKey);
        if (!raw) {
          this.presets = [];
          // no presets -> clear any restored selection
          this.selectedPreset = null;
          return;
        }
        const obj = JSON.parse(raw) || {};
        this.presets = Object.keys(obj).sort((a, b) => a.localeCompare(b));

        // Restore last selected preset (persisted separately) if it still exists
        // try {
        //   const lastKey = this._storageKey + '_last';
        //   const last = localStorage.getItem(lastKey);
        //   if (last && this.presets.includes(last)) {
        //     this.selectedPreset = last;
        //   } else {
        //     this.selectedPreset = null;
        //   }
        // } catch (e) {
        //   // ignore restore errors and leave selection cleared
        //   this.selectedPreset = null;
        // }
      } catch (e) {
        console.error('Failed to load presets', e);
        this.presets = [];
      }
    },

    savePresetWithName(name) {
      if (!name || !name.trim()) return;
      const trimmed = name.trim();

      // read existing
      let obj = {};
      try {
        const raw = localStorage.getItem(this._storageKey);
        obj = raw ? (JSON.parse(raw) || {}) : {};
      } catch (e) {
        obj = {};
      }

      // deep copy current values and muteState
      const copyValues = {};
      for (const [k, v] of Object.entries(this.values)) copyValues[k] = v;
      const copyMute = {};
      for (const [k, v] of Object.entries(this.muteState)) copyMute[k] = v;

      obj[trimmed] = {values: copyValues, muteState: copyMute};

      try {
        localStorage.setItem(this._storageKey, JSON.stringify(obj));
      } catch (e) {
        console.error('Failed to save preset', e);
        return;
      }

      this.loadPresetsFromStorage();
      // select the newly created preset in the dropdown
      this.selectedPreset = trimmed;
      // persist last selected preset
      // try { localStorage.setItem(this._storageKey + '_last', trimmed); } catch (e) { /* ignore */ }
    },

    applyPresetByName(name) {
      if (!name) return;
      let obj = {};
      try {
        const raw = localStorage.getItem(this._storageKey);
        obj = raw ? (JSON.parse(raw) || {}) : {};
      } catch (e) {
        console.error('Failed to read presets', e);
        return;
      }

      const preset = obj[name];
      if (!preset) return;

      // Ask for confirmation
      const ok = window.confirm('Are you sure?');
      if (!ok) {
        // revert selection
        // keep prior selection (don't force clear) — preserve user's last selection
        return;
      }

      // Apply values and muteState
      const pvals = preset.values || {};
      const pmute = preset.muteState || {};

      // Update values store reactively
      for (const [k, v] of Object.entries(pvals)) {
        const nkey = isNaN(Number(k)) ? k : Number(k);
        if (this.$set) this.$set(this.values, nkey, v);
        else this.values[nkey] = v;
      }

      for (const [k, v] of Object.entries(pmute)) {
        const nkey = isNaN(Number(k)) ? k : Number(k);
        if (this.$set) this.$set(this.muteState, nkey, v);
        else this.muteState[nkey] = v;
      }

      // After loading, keep the selection visible and persist it as the last selected
      // this.selectedPreset = name;
      // try { localStorage.setItem(this._storageKey + '_last', name); } catch (e) { /* ignore */ }
    },

    onPresetChange() {
      const sel = this.selectedPreset;
      if (sel === this.SAVE_SENTINEL) {
        const name = window.prompt('Enter a preset name:');
        if (name && name.trim()) {
          this.savePresetWithName(name);
        }
        // reset selection
        this.selectedPreset = null;
        return;
      }

      // otherwise a real preset was chosen -> apply
      if (sel) {
        this.applyPresetByName(sel);
      }
    },

    deletePreset(name) {
      if (!name) return;
      const confirmDel = window.confirm(`Are you sure you want to delete ${name}?`);
      if (!confirmDel) return;

      try {
        const raw = localStorage.getItem(this._storageKey);
        const obj = raw ? (JSON.parse(raw) || {}) : {};
        if (obj.hasOwnProperty(name)) {
          delete obj[name];
          localStorage.setItem(this._storageKey, JSON.stringify(obj));
        }
        // If the deleted preset was the persisted last selection, remove that too
        // try {
        // const lastKey = this._storageKey + '_last';
        // const last = localStorage.getItem(lastKey);
        // if (last === name) localStorage.removeItem(lastKey);
        // } catch (e) { /* ignore */ }
      } catch (e) {
        console.error('Failed to delete preset', e);
      }

      // reload preset list and clear selection if it was the deleted one
      this.loadPresetsFromStorage();
      if (this.selectedPreset === name) this.selectedPreset = null;
    },

    // Handler that prompts then clears all mixer values and mutes
    onClearClick() {
      const ok = window.confirm('Are you sure?');
      if (!ok) return;
      this.clearAll();
    },

    clearAll() {
      // Set every fader value to 0 and send CCs
      try {
        for (const key of Object.keys(this.values)) {
          const cc = isNaN(Number(key)) ? key : Number(key);
          // update state and send
          if (this.$set) this.$set(this.values, cc, 0);
          else this.values[cc] = 0;
          this.sendWSCCMessage(cc, 0);
        }

        // Set every mute to 'on' (127) and send CCs
        for (const key of Object.keys(this.muteState)) {
          const cc = isNaN(Number(key)) ? key : Number(key);
          if (this.$set) this.$set(this.muteState, cc, 127);
          else this.muteState[cc] = 127;
          this.sendWSCCMessage(cc, 127);
        }
      } catch (e) {
        console.error('Failed to clear mixers', e);
      }
    },
  }
};
</script>

<style lang="scss" scoped>
/* Variable for ticks width */
$ticks-width: 30px;

#channels {
  display: flex;
  //gap: 20px;
  align-items: center;
  justify-content: center;
  height: 100%;
  max-height: 600px;
  column-gap: 20px;
}

/* Clear button (top-left) */
.clear-button {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 50;
}

.clear-btn {
  background: rgba(250, 7, 7, 0.4);
  color: #e0e0e0;
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 6px 10px;
  border-radius: 4px;
  cursor: pointer;

  font-size: x-large;
}

.clear-btn:hover {
  background: rgba(255, 255, 255, 0.12);
}

/* Preset dropdown styling (top-right) */
.preset-dropdown {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 40;

  display: flex;
  flex-direction: row;
  column-gap: 10px;
  align-items: center;

  font-size: x-large;
}

/* New preset list and delete button styles */
.preset-controls {
  display: flex;
  flex-direction: row;
  column-gap: 10px;
  align-items: center;
}

#preset-select {
  font-size: x-large;
}

.preset-list {
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 240px;
  overflow: auto;
  background: rgba(0, 0, 0, 0.05);
  padding: 6px;
  border-radius: 4px;
}

.preset-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.preset-delete {
  background: #ff4d4f;
  color: white;
  border: none;
  padding: 2px 6px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
  line-height: 1;
}

.preset-delete:hover {
  opacity: 0.9;
}

.preset-name {
  color: white;
  font-size: 13px;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
  max-width: 160px;
}

.channel-group {
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
}

.group-title {
  font-size: 24px;
  font-weight: bold;
  color: #e0e0e0;
  text-align: center;
  margin-bottom: 10px;
  min-height: 5vh;
}

.group-channels {
  display: flex;
  gap: 20px;
  align-items: center;
  height: 100%;
  position: relative;
}

.group-divider {
  width: 2px;
  height: 100%;
  background: black;
}

.channel {
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  min-width: 60px;

  padding: 10px;
}

.channel:nth-child(even) {
  background-color: #363636;
  color: #2a2a2a;
  margin: 10px -10px;
}

.channel-label {
  display: flex;
  flex-direction: column;
  justify-content: center;

  font-size: 14px;
  font-weight: bold;
  color: #e0e0e0;
  text-align: center;
  min-height: 5vh;
}

/* New wrapper to horizontally center one or two faders */
.faders-wrapper {
  display: grid;

  align-items: center;
  justify-content: center;
  height: 100%;
}

.faders-wrapper.faders-1 {
  grid-template-columns: 1fr repeat(2, calc($ticks-width / 2));
}

.faders-wrapper.faders-2 {
  grid-template-columns: 1fr repeat(2, calc($ticks-width / 2)) 1fr;
}

.faders-wrapper.faders-3 {
  grid-template-columns: 1fr repeat(2, calc($ticks-width / 2)) 1fr repeat(2, calc($ticks-width / 2)) 1fr;
}

.fader-column {
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;

  row-gap: 10px;
  grid-row: 1;
}

.fader-column.fader-column-0 {
  grid-column: 1 / span 2;
}

.fader-column.fader-column-0 > .fader-container,
.fader-column.fader-column-0 > .value-display,
.fader-column.fader-column-0 > .cc-number {
  margin-right: calc($ticks-width / 2);
}

.fader-column.fader-column-1 {
  grid-column: 3 / span 3;
}

.fader-column.fader-column-2 {
  grid-column: 6 / span 2;
  grid-row: 1;
  //margin-left: -1px;
}

.fader-column.fader-column-2 > .fader-container,
.fader-column.fader-column-2 > .value-display,
.fader-column.fader-column-2 > .cc-number {
  margin-left: calc($ticks-width / 2);
}

.fader-ticks {
  height: 100%;

  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;

  color: darkgray;
  font-size: xx-small;
  padding-top: 37px;
  padding-bottom: 102px;

  grid-row: 1;
}

.fader-ticks-0 {
  grid-column: 2 / span 2;
}

.fader-ticks-1 {
  grid-column: 5 / span 2;
}

.fader-tick {
  display: grid;
  grid-template-columns: 1fr max-content 1fr;
  align-items: center;
  column-gap: 3px;

  width: 100%;

  text-wrap: nowrap;
}

.tick-mark {
  background-color: #999999;
  height: 1px;
  width: 100%;
}

.tick-number {
  color: #999999;
}

.fader-container {
  /* keep a fixed width for the vertical slider column */
  display: flex;
  justify-content: center;
  align-items: stretch;
  position: relative;
  width: 30px;
  margin: 10px 0;
  padding: 10px 0;
  border-radius: 6px;
  flex-grow: 1;

  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.03) inset, 0 4px 14px rgba(0, 0, 0, 0.4);
}

/* Drag feedback */
.fader-container.dragging {
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.1) inset, 0 4px 14px rgba(0, 0, 0, 0.5);
}

.fader-container.volume {
  background-color: #806a40;
}

.fader-container.reverb {
  background: transparent;
}

.fader-container.monitor {
  background: transparent;
}

.fader {
  -webkit-appearance: none;
  appearance: none;
  accent-color: lightgray;
  writing-mode: vertical-rl;
  direction: rtl;
  border-radius: 4px;
  width: 10px;
  border: 2px solid black;
  /* cursor moved to above rules */
  z-index: 2;
  margin: 0 auto;
}

.fader-container.volume > .fader {
  background: linear-gradient(to top, #490000 0%, #cc6666 100%);
}

.fader-container.reverb > .fader {
  background: linear-gradient(to top, #00214a 0%, #6694cc 100%);
}

.fader-container.monitor > .fader {
  background: linear-gradient(to top, #004a01 0%, #66cc68 100%);
}

.fader:active, .fader.grabbing {
  cursor: grabbing;
}

.fader::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 20px;
  height: 40px;
  background-color: lightgray; /* fallback */
  background-image: linear-gradient(to bottom,
      lightgray 6px, #919191 7px, lightgray 8px,
      lightgray 17px, #737373 18px, lightgray 19px,
      lightgray 28px, #919191 29px, lightgray 30px);
  border: 2px solid #505050;
  border-radius: 4px;
  cursor: pointer;
}

/* Numeric input (value-display) styling */
.value-display {
  //margin-top: 10px;
  font-size: 16px;
  font-weight: bold;
  /* keep a readable color for numeric text */
  color: #e8f5e9;
  height: 30px;
  font-family: 'Courier New', monospace;
  text-align: center;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 4px 6px;
  //border-radius: 4px;
  /* define standard and vendor appearance properties together */
  appearance: textfield;
  -webkit-appearance: textfield;
}

.value-display:focus {
  outline: none;
  border-color: rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.02);
}

/* Remove spinner arrows in WebKit (Chrome, Edge, Safari) */
.value-display::-webkit-outer-spin-button,
.value-display::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

/* For older Firefox compatibility we already set -moz-appearance above in the main selector */

.cc-number {
  font-size: 11px;
  color: #999;
  height: 15px;
  //margin-top: 5px;
}

/* Mute button styling */
.mute-btn {
  background-color: transparent;
  border: 2px solid #505050;
  color: #e0e0e0;
  font-size: 14px;
  font-weight: bold;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 10px;
  transition: background-color 0.2s, color 0.2s;
}

.mute-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.mute-btn.active {
  background-color: #F44336;
  color: white;
}
</style>
