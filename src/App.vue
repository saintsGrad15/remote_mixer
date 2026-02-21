<template>
    <div id="remote-mixer">
        <header id="header">Remote Mixer</header>
        <div id="mixer-container">
            <MixerView @connection="onConnection"/>
        </div>
        <StatusBar :connected="connected"/>
    </div>
</template>

<script>
    import MixerView from './components/MixerView.vue'
    import StatusBar from './components/StatusBar.vue'

    export default {
        components: { MixerView, StatusBar },
        data() {
            return { connected: false }
        },
        methods: {
            onConnection(val) {
                this.connected = !!val
            }
        }
    }
</script>

<style lang="scss" scoped>
    /* keep App.vue styles minimal */
    #remote-mixer {
        height: 100vh;

        display: grid;
        grid-template-rows: auto 1fr auto;
    }

    #mixer-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 0; /* allow the grid row to properly constrain children */
        overflow: auto;

        padding-top: 40px;
        padding-bottom: 40px;
    }
</style>
