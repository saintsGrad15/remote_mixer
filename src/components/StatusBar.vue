<template>
  <div id="status" :class="connected ? 'connected' : 'disconnected'">
    {{ connected ? 'Connected' : 'Disconnected' }}
  </div>
</template>

<script>
export default {
  props: { connected: { type: Boolean, default: false } }
}
</script>

<style scoped>
#status {
  color: white;
}

.connected {
  background-color: #28a745;
  color: white;
}

.disconnected {
  background-color: #dc3545;
  color: white;
}
</style>
