<template>
  <div id="channels">
    <template v-for="(group, gidx) in channelGroups" :key="gidx">
      <div class="channel-group">
        <div class="group-title">{{ group.title }}</div>
        <div class="group-channels">
          <div v-for="channel in group.channels" :key="channel.volume_cc || channel.title" class="channel">
            <div class="channel-label">{{ channel.title }}</div>
            <div class="fader-container" :class="{ 'dragging': dragState[channel.volume_cc] }">
              <input
                  ref="faders"
                  class="fader"
                  type="range"
                  min="0"
                  max="127"
                  v-model.number="values[channel.volume_cc]"
                  @input="onInput(channel.volume_cc)"
                  @pointerdown="onPointerDown(channel.volume_cc, $event)"
              />
            </div>

            <!-- Mute button: toggles mute state for channel.mute_cc -->
            <button
                class="mute-btn"
                :class="{ active: muteState[channel.mute_cc] > 0 }"
                @click="toggleMute(channel.mute_cc)"
                title="Toggle mute"
            >
              M
            </button>

            <!-- Editable numeric value: on change/blur/enter send value like slider -->
            <input
                class="value-display"
                type="number"
                min="0"
                max="127"
                :value="values[channel.volume_cc] ?? 0"
                @change="onValueEdit(channel.volume_cc, $event)"
                @blur="onValueEdit(channel.volume_cc, $event)"
                @keydown.enter.prevent="onValueEdit(channel.volume_cc, $event)"
            />

            <div class="cc-number">VCC {{ channel.volume_cc }} &nbsp; MuteCC {{ channel.mute_cc }}</div>
          </div>
        </div>
      </div>
      <div v-if="gidx < channelGroups.length - 1" class="group-divider"></div>
    </template>
  </div>
</template>

<script>
import {useRelativeDrag} from "../composables/useRelativeDrag"

export default {
  data() {
    return {
      channelGroups: [],
      ws: null,
      values: {},
      // per-cc drag state for visual feedback (keyed by volume_cc)
      dragState: {},
      // current mute state keyed by mute_cc (0 or 1)
      muteState: {},
      // the composable handles global pointer listeners
      _dragComposable: null,
      _dragComposableStop: null
    }
  },
  mounted() {
    this.initialize()
    this._dragComposable = useRelativeDrag()
  },
  methods: {
    onPointerDown(volumeCc, e) {
      // Support command/meta-click for jump-to-click behavior
      const input = e.target
      if (e.metaKey || e.ctrlKey) {
        // compute jump location as native behavior: calculate value from click
        const rect = input.getBoundingClientRect()
        const isVertical = rect.height > rect.width
        const pos = isVertical ? e.clientY : e.clientX
        const offset = isVertical ? (rect.bottom - pos) : (pos - rect.left)
        const ratio = offset / (isVertical ? rect.height : rect.width)
        const value = Math.round(Math.min(1, Math.max(0, ratio)) * 127)
        this.setValueAndSend(volumeCc, value)
        return
      }

      // Start relative drag using the composable
      if (this.$set) this.$set(this.dragState, volumeCc, true)
      else this.dragState[volumeCc] = true

      const stop = this._dragComposable.start(e, this.values[volumeCc], input, (newVal) => {
        this.setValueAndSend(volumeCc, newVal)
      }, () => {
        if (this.$set) this.$set(this.dragState, volumeCc, false)
        else this.dragState[volumeCc] = false
      })

      this._dragComposableStop = stop && stop.stop ? stop.stop : null
    },

    async initialize() {
      try {
        const response = await fetch("/config")
        const cfg = await response.json()
        if (cfg.error) {
          console.error("Config error", cfg.error)
          return
        }

        // Expect config.channel_groups each with channels that contain volume_cc and mute_cc
        this.channelGroups = cfg.channel_groups || []

        // initialize values and muteState keyed by CC numbers
        this.channelGroups.forEach(group => {
          group.channels.forEach(ch => {
            const vol = ch.volume_cc ?? 0
            const mute = ch.mute_cc ?? 0
            if (this.$set) {
              this.$set(this.values, vol, 0)
              this.$set(this.muteState, mute, 0)
            } else {
              this.values[vol] = 0
              this.muteState[mute] = 0
            }

            // ensure channel has both fields (if backend sent old 'cc' rename, support fallback)
            if (ch.cc && !ch.volume_cc) ch.volume_cc = ch.cc
            if (ch.mute_cc === undefined) ch.mute_cc = 0
          })
        })

        this.connectWs()
      } catch (e) {
        console.error("Failed to load config", e)
      }
    },

    connectWs() {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
      const wsUrl = `${protocol}//${window.location.host}/ws`
      this.ws = new WebSocket(wsUrl)
      this.ws.onopen = () => {
        this.$emit("connection", true)
      }
      this.ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data)
          if (data.type === "midi_cc_update") {
            const cc = data.cc
            const value = data.value
            // If this CC corresponds to a volume CC, update values; if it's a mute CC, update muteState
            if (this.values.hasOwnProperty(cc)) {
              if (this.$set) this.$set(this.values, cc, value)
              else this.values[cc] = value
            }
            if (this.muteState.hasOwnProperty(cc)) {
              // treat nonzero as muted (1), zero as unmuted (0)
              const m = value ? 1 : 0
              if (this.$set) this.$set(this.muteState, cc, m)
              else this.muteState[cc] = m
            }
          }
        } catch (_) {
          // ignore non-json
        }
      }
      this.ws.onclose = () => {
        this.$emit("connection", false);
        setTimeout(() => this.connectWs(), 1500)
      }
      this.ws.onerror = (err) => console.error("ws error", err)
    },

    onInput(volumeCc) {
      const value = parseInt(this.values[volumeCc])
      this.setValueAndSend(volumeCc, value)
    },

    onValueEdit(volumeCc, event) {
      const raw = event && event.target ? event.target.value : event
      const parsed = parseInt(raw)
      this.setValueAndSend(volumeCc, parsed)
    },

    toggleMute(muteCc) {
      // toggle current mute state (0/1)
      const current = this.muteState[muteCc] || 0
      const newState = current ? 0 : 127
      if (this.$set) this.$set(this.muteState, muteCc, newState)
      else this.muteState[muteCc] = newState

      // send CC message: 1 for muted, 0 for unmuted
      const msg = JSON.stringify({type: 'cc', cc: muteCc, value: newState})
      if (this.ws && this.ws.readyState === WebSocket.OPEN) this.ws.send(msg)
    },

    setValueAndSend(cc, parsedValue) {
      let value = Number.isFinite(parsedValue) ? parseInt(parsedValue) : NaN
      if (Number.isNaN(value)) {
        value = this.values[cc] ?? 0
      }
      if (value < 0) value = 0
      if (value > 127) value = 127
      if (this.$set) this.$set(this.values, cc, value)
      else this.values[cc] = value

      const msg = JSON.stringify({type: "cc", cc, value})
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(msg)
      }
    }
  }
}
</script>

<style lang="scss" scoped>
#channels {
  display: flex;
  //gap: 20px;
  align-items: center;
  justify-content: center;
  height: 100%;
  max-height: 600px;
  column-gap: 20px;
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

.fader-container {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: stretch;
  position: relative;
  width: 30px;
  margin: 10px 0;
  padding: 10px 0;
  border-radius: 6px;

  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.03) inset, 0 4px 14px rgba(0, 0, 0, 0.4);
}

/* Drag feedback */
.fader-container.dragging {
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.1) inset, 0 4px 14px rgba(0, 0, 0, 0.5);
}

.fader {
  -webkit-appearance: none;
  appearance: none;
  accent-color: lightgray;
  writing-mode: vertical-rl;
  direction: rtl;
  background: linear-gradient(to top, #4CAF50 0%, #FFC107 50%, #F44336 100%);
  border-radius: 4px;
  width: 10px;
  border: 2px solid black;
  /* cursor moved to above rules */
  z-index: 2;
  margin: 0 auto;
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
  margin-top: 10px;
  font-size: 16px;
  font-weight: bold;
  /* keep a readable color for numeric text */
  color: #e8f5e9;
  min-height: 24px;
  font-family: 'Courier New', monospace;
  width: 64px;
  text-align: center;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 4px 6px;
  border-radius: 4px;
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
  margin-top: 5px;
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
