<template>
    <div id="channels">
        <template v-for="(group, gidx) in channelGroups" :key="gidx">
            <div class="channel-group">
                <div class="group-title">{{ group.title }}</div>
                <div class="group-channels">
                    <div v-for="channel in group.channels" :key="channel.cc" class="channel">
                        <div class="channel-label">{{ channel.title }}</div>
                        <div class="fader-container">
                            <input class="fader" type="range" min="0" max="127" v-model.number="values[channel.cc]" @input="onInput(channel.cc)">
                        </div>
                        <div class="value-display">{{ values[channel.cc] ?? 0 }}</div>
                        <div class="cc-number">CC {{ channel.cc }}</div>
                    </div>
                </div>
            </div>
                <div v-if="gidx < channelGroups.length - 1" class="group-divider"></div>
        </template>
    </div>
</template>

<script>
    export default {
        data() {
            return {
                channelGroups: [],
                ws: null,
                values: {}
            }
        },
        mounted() {
            this.initialize()
        },
        methods: {
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
                            this.$set
                                ? this.$set(this.values, ch.cc, 0)
                                : ( this.values[ch.cc] = 0 )
                        })
                    })
                    this.connectWs()
                } catch (e) {
                    console.error('Failed to load config', e)
                }
            },
            connectWs() {
                const protocol = window.location.protocol === 'https:'
                    ? 'wss:'
                    : 'ws:'
                const wsUrl = `${ protocol }//${ window.location.host }/ws`
                this.ws = new WebSocket(wsUrl)
                this.ws.onopen = () => { this.$emit('connection', true) }
                this.ws.onmessage = (e) => {
                    try {
                        const data = JSON.parse(e.data)
                        if (data.type === 'midi_cc_update') {
                            const cc = data.cc
                            const value = data.value
                            this.$set
                                ? this.$set(this.values, cc, value)
                                : ( this.values[cc] = value )
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
                const value = parseInt(this.values[cc])
                const msg = JSON.stringify({ type: 'cc', cc, value })
                if (this.ws && this.ws.readyState === WebSocket.OPEN) this.ws.send(msg)
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
        cursor: pointer;
        z-index: 2;
        margin: 0 auto;
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

    .value-display {
        margin-top: 10px;
        font-size: 16px;
        font-weight: bold;
        color: #4CAF50;
        min-height: 24px;
        font-family: 'Courier New', monospace;
    }

    .cc-number {
        font-size: 11px;
        color: #999;
        margin-top: 5px;
    }
</style>
