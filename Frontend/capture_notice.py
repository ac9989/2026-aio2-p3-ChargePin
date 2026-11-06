"""Best-effort browser notice when a general user presses Print Screen."""
from __future__ import annotations

import streamlit as st


def install_capture_notice(is_general_user: bool) -> None:
    # Operating systems and browsers may consume the key; this cannot block capture.
    enabled = "true" if is_general_user else "false"
    script = r"""
<script>
(() => {
  const previous = window.__chargepinCaptureGuard;
  if (previous) {
    document.removeEventListener("keydown", previous.onKey, true);
    document.removeEventListener("keyup", previous.onKey, true);
    window.removeEventListener("message", previous.onMessage);
    delete window.__chargepinCaptureGuard;
  }
  const oldDialog = document.getElementById("chargepin-capture-dialog");
  if (!__ENABLED__) { if (oldDialog) oldDialog.remove(); return; }

  function showNotice() {
    if (document.getElementById("chargepin-capture-dialog")) return;
    const dialog = document.createElement("dialog");
    dialog.id = "chargepin-capture-dialog";
    dialog.className = "cp-capture-dialog";
    dialog.setAttribute("aria-labelledby", "cp-capture-title");
    dialog.innerHTML = '<div class="cp-capture-mark">!</div><h2 id="cp-capture-title">화면 캡처 안내</h2>'
      + '<p>화면에 표시된 정보를 공유하기 전에 내용을 확인해 주세요.</p>'
      + '<button type="button" class="cp-capture-confirm">확인</button>';
    dialog.addEventListener("close", () => dialog.remove());
    dialog.querySelector("button").addEventListener("click", () => dialog.close());
    document.body.appendChild(dialog);
    dialog.showModal();
  }
  function onKey(event) {
    if (event.key === "PrintScreen" || event.code === "PrintScreen" || event.keyCode === 44) showNotice();
  }
  function onMessage(event) {
    if (!event.data || event.data.type !== "chargepin:printscreen") return;
    const isFrame = Array.from(document.querySelectorAll("iframe")).some(frame => frame.contentWindow === event.source);
    if (isFrame) showNotice();
  }
  window.__chargepinCaptureGuard = {onKey, onMessage};
  document.addEventListener("keydown", onKey, true);
  document.addEventListener("keyup", onKey, true);
  window.addEventListener("message", onMessage);
})();
</script>
"""
    # Render in the mounted main area, even when Streamlit's sidebar is collapsed.
    with st.container(key="capture_listener"):
        st.html(script.replace("__ENABLED__", enabled), unsafe_allow_javascript=True)
