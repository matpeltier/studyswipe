import uuid

import streamlit.components.v2 as components

_SESSION_JS = """\
export default function(component) {
  const { setStateValue } = component
  setTimeout(() => {
    const sid = localStorage.getItem('studyswipe_session_id');
    if (!sid) {
      const newId = crypto.randomUUID ? crypto.randomUUID()
          : ([1e7]+-1e3+-4e3+-1e4+-1e3+-2e11).replace(/[018]/g,
              c => (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16));
      localStorage.setItem('studyswipe_session_id', newId);
      setStateValue("session_id", newId);
    } else {
      setStateValue("session_id", sid);
    }
  }, 50);
}
"""

_session_component = components.component(
    "session_manager",
    html="<div style='display:none'></div>",
    js=_SESSION_JS,
)


def get_session_id() -> str:
    result = _session_component(key="studyswipe_session")
    if result and hasattr(result, "session_id") and result.session_id:
        return result.session_id
    return str(uuid.uuid4())
