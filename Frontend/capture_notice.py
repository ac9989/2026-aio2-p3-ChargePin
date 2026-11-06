"""Browser-only capture notice for the demo's general-user role."""
from __future__ import annotations

import streamlit as st


def install_capture_notice(is_general_user: bool) -> None:
    # A key event is only a notice, not a screenshot prevention mechanism.
    enabled = "true" if is_general_user else "false"
    script = r"""
<script>
(() => {
  const enabled = __ENABLED__;
  if (window.__chargepinPrintScreenHandler) {
    document.removeEventListener("keyup", window.__chargepinPrintScreenHandler, true);
    delete window.__chargepinPrintScreenHandler;
  }
  const existing = document.getElementById("chargepin-capture-dialog");
  if (!enabled) { if (existing) existing.remove(); return; }
  const handler = (event) => {
    if (event.key !== "PrintScreen" && event.code !== "PrintScreen") return;
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
  };
  window.__chargepinPrintScreenHandler = handler;
  document.addEventListener("keyup", handler, true);
})();
</script>
"""
    # Sidebar is hidden; executing the static script there does not move the header.
    st.sidebar.html(script.replace("__ENABLED__", enabled), unsafe_allow_javascript=True)
