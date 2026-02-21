<template>
    <div id="channels">
        <template v-for="(group, gidx) in channelGroups" :key="gidx">
            <div class="channel-group">
                <div class="group-title">{{ group.title }}</div>
                <div class="group-channels">
                    <div v-for="channel in group.channels" :key="channel.cc" class="channel">
                        <div class="channel-label">{{ channel.title }}</div>
                        <div class="fader-container" :class="{ 'dragging': dragState[channel.cc] }">
                            <input
                                ref="faders"
                                class="fader"
                                type="range"
                                min="0"
                                max="127"
                                v-model.number="values[channel.cc]"
                                @input="onInput(channel.cc)"
                                @pointerdown="onPointerDown(channel.cc, $event)"
                            />
                        </div>
                        <!-- Editable numeric value: on change/blur/enter send value like slider -->
                        <input
                            class="value-display"
                            type="number"
                            min="0"
                            max="127"
                            :value="values[channel.cc] ?? 0"
                            @change="onValueEdit(channel.cc, $event)"
                            @blur="onValueEdit(channel.cc, $event)"
                            @keydown.enter.prevent="onValueEdit(channel.cc, $event)"
                        />
                        <div class="cc-number">CC {{ channel.cc }}</div>
                    </div>
                </div>
            </div>
                <div v-if="gidx < channelGroups.length - 1" class="group-divider"></div>
        </template>
    </div>
</template>

<script>
import { useRelativeDrag } from '../composables/useRelativeDrag'

export default {
  data() {
    return {
      channelGroups: [],
      ws: null,
      values: {},
      // per-cc drag state for visual feedback
      dragState: {},
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
    onPointerDown(cc, e) {
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
        this.setValueAndSend(cc, value)
        return
      }

      // Start relative drag using the composable
      if (this.$set) this.$set(this.dragState, cc, true)
      else this.dragState[cc] = true

      const stop = this._dragComposable.start(e, this.values[cc], input, (newVal) => {
        this.setValueAndSend(cc, newVal)
      }, () => {
        if (this.$set) this.$set(this.dragState, cc, false)
        else this.dragState[cc] = false
      })

      this._dragComposableStop = stop && stop.stop ? stop.stop : null
    },

    async initialize() {
      try {
        const response = await fetch('/config')
        const cfg = await response.json()
        if (cfg.error) {
          console.error('Config error', cfg.error)
          return
        }
        this.channelGroups = cfg.channel_groups || []
        // initialize values
        this.channelGroups.forEach(group => {
          group.channels.forEach(ch => {
            if (this.$set) this.$set(this.values, ch.cc, 0)
            else this.values[ch.cc] = 0
          })
        })
        this.connectWs()
      } catch (e) {
        console.error('Failed to load config', e)
      }
    },

    connectWs() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/ws`
      this.ws = new WebSocket(wsUrl)
      this.ws.onopen = () => { this.$emit('connection', true) }
      this.ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data)
          if (data.type === 'midi_cc_update') {
            const cc = data.cc
            const value = data.value
            if (this.$set) this.$set(this.values, cc, value)
            else this.values[cc] = value
          }
        } catch (_) {
          // ignore non-json
        }
      }
      this.ws.onclose = () => {
        this.$emit('connection', false);
        setTimeout(() => this.connectWs(), 1500)
      }
      this.ws.onerror = (err) => console.error('ws error', err)
    },

    onInput(cc) {
      // slider moved — ensure we use the same sending path
      const value = parseInt(this.values[cc])
      this.setValueAndSend(cc, value)
    },

    onValueEdit(cc, event) {
      // user edited the numeric input: parse, clamp, set and send
      const raw = event && event.target ? event.target.value : event
      const parsed = parseInt(raw)
      this.setValueAndSend(cc, parsed)
    },

    setValueAndSend(cc, parsedValue) {
      let value = Number.isFinite(parsedValue) ? parseInt(parsedValue) : NaN
      if (Number.isNaN(value)) {
        // invalid input, reset to current stored value or 0
        value = this.values[cc] ?? 0
      }
      // clamp
      if (value < 0) value = 0
      if (value > 127) value = 127
      // update reactive value
      if (this.$set) this.$set(this.values, cc, value)
      else this.values[cc] = value

      // send via ws if open
      const msg = JSON.stringify({ type: 'cc', cc, value })
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
        gap: 40px;
        align-items: center;
        justify-content: center;
        height: 100%;
        max-height: 600px;
        column-gap: 40px;
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
        gap: 40px;
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
        min-width: 80px;
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
        width: 60px;
        margin: 10px 0;
        padding: 10px 0;
        border-radius: 6px;

        box-shadow: 0 0 0 3px rgba(255,255,255,0.03) inset, 0 4px 14px rgba(0,0,0,0.4);
    }

    /* Drag feedback */
    .fader-container.dragging {
        box-shadow: 0 0 0 3px rgba(255,255,255,0.1) inset, 0 4px 14px rgba(0,0,0,0.5);
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
        width: 50px;
        height: 30px;
        background: lightgray;
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
        border: 1px solid rgba(255,255,255,0.08);
        padding: 4px 6px;
        border-radius: 4px;
        /* define standard and vendor appearance properties together */
        appearance: textfield;
        -webkit-appearance: textfield;
    }

    .value-display:focus {
        outline: none;
        border-color: rgba(255,255,255,0.2);
        background: rgba(255,255,255,0.02);
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
</style>
