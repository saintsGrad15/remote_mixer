import { ref } from 'vue'

// Composable to manage a single relative pointer drag session.
// API: const d = useRelativeDrag();
// const { stop } = d.start(event, startValue, element, onChange, onEnd)
// d.isDragging is a ref boolean
export function useRelativeDrag() {
  const isDragging = ref(false)
  let _move = null
  let _up = null
  let _state = null

  function start(e, startValue, element, onChange, onEnd) {
    if (!element || !e) return { stop: () => {} }
    e.preventDefault()

    const rect = element.getBoundingClientRect()
    const isVertical = rect.height > rect.width
    const clientPos = isVertical
      ? e.clientY
      : e.clientX
    const size = isVertical
      ? rect.height
      : rect.width

    _state = {
      startClient: clientPos,
      startValue: Number(startValue) || 0,
      size: Math.max(size, 1),
      isVertical,
      pointerId: e.pointerId,
      element
    }

    isDragging.value = true

    _move = function (ev) {
      if (!_state) return
      if (typeof _state.pointerId === 'number' && ev.pointerId !== _state.pointerId) return

      const pos = _state.isVertical
        ? ev.clientY
        : ev.clientX
      const delta = pos - _state.startClient
      const ratio = _state.isVertical
        ? ( -delta / _state.size )
        : ( delta / _state.size )
      const valueDelta = Math.round(ratio * 127)
      const newValue = _state.startValue + valueDelta
      onChange && onChange(newValue)
    }

    _up = function () {
      cleanup()
      onEnd && onEnd()
    }

    window.addEventListener('pointermove', _move)
    window.addEventListener('pointerup', _up)
    window.addEventListener('pointercancel', _up)
    try { element.setPointerCapture && element.setPointerCapture(e.pointerId) } catch (_) {}

    function cleanup() {
      if (!_state) return
      isDragging.value = false
      window.removeEventListener('pointermove', _move)
      window.removeEventListener('pointerup', _up)
      window.removeEventListener('pointercancel', _up)
      try { _state.element && _state.element.releasePointerCapture && _state.element.releasePointerCapture(_state.pointerId) } catch (_) {}
      _state = null
      _move = null
      _up = null
    }

    return { stop: cleanup }
  }

  return {
    start,
    isDragging
  }
}
