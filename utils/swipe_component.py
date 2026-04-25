SWIPE_CARD_HTML = """\
<div id="swipe-container" style="
  position: relative;
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
  height: 420px;
  perspective: 1000px;
  user-select: none;
">
  <div id="swipe-card" style="
    position: absolute;
    inset: 0;
    border-radius: 16px;
    background: var(--st-secondary-background-color, #1a1a2e);
    border: 1px solid rgba(99,102,241,0.3);
    padding: 24px;
    overflow-y: auto;
    cursor: grab;
    transition: box-shadow 0.2s ease;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    display: flex;
    flex-direction: column;
    gap: 8px;
  ">
    <div id="swipe-hint" style="
      position: absolute;
      top: 12px;
      width: 100%;
      text-align: center;
      font-size: 1.1em;
      font-weight: 700;
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.15s ease;
      z-index: 10;
    "></div>
    <div id="card-content" style="flex:1; display:flex; flex-direction:column; gap:8px;"></div>
  </div>
  <div id="nav-hint" style="
    text-align: center;
    margin-top: 8px;
    padding-top: 8px;
    font-size: 0.85em;
    opacity: 0.6;
    color: var(--st-text-color, #e2e8f0);
  ">Drag left to skip, right to save. Use arrow keys for keyboard.</div>
</div>
"""

SWIPE_CARD_CSS = """\
#swipe-card:active { cursor: grabbing; }
#swipe-card.dragging { transition: none; }
#swipe-card.fly-out {
  transition: transform 0.4s ease, opacity 0.4s ease;
}
#card-content h2 { margin: 0 0 4px 0; color: var(--st-text-color, #e2e8f0); }
#card-content .badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 0.8em;
  font-weight: 600;
  margin-bottom: 4px;
}
#card-content p { margin: 4px 0; line-height: 1.5; color: var(--st-text-color, #e2e8f0); }
#card-content .meta { font-size: 0.85em; opacity: 0.8; }
#card-content .why-matters {
  background: rgba(99,102,241,0.15);
  border-left: 3px solid #6366f1;
  padding: 8px 12px;
  border-radius: 4px;
  margin: 6px 0;
}
#card-content .facts-list { margin: 4px 0; padding-left: 16px; }
#card-content .facts-list li { margin: 4px 0; line-height: 1.4; color: var(--st-text-color, #e2e8f0); }
#card-content .quiz-q { font-weight: 600; margin-top: 8px; }
"""

SWIPE_CARD_JS = """\
export default function(component) {
  const { data, parentElement, setStateValue, setTriggerValue } = component
  if (!data || !data.topic) return

  const container = parentElement.querySelector("#swipe-container")
  const card = parentElement.querySelector("#swipe-card")
  const hint = parentElement.querySelector("#swipe-hint")
  const content = parentElement.querySelector("#card-content")
  if (!container || !card || !content) return

  const t = data.topic
  const badgeColors = { Science:"#22c55e", History:"#3b82f6", Politics:"#f97316", Culture:"#8b5cf6", Technology:"#ef4444" }
  const popIcons = { Trending:"\\u{1F4C8}", Popular:"\\u{1F525}", Moderate:"\\u{1F441}", Niche:"\\u{1F9ED}" }

  let html = `<span class="badge" style="background:${badgeColors[t.category] || '#888'}; color:#fff">${t.category}</span>`
  html += `<h2>${t.title}</h2>`

  if (t.popularity || t.difficulty) {
    html += `<div class="meta">`
    html += `${popIcons[t.popularity] || ''} ${t.popularity || ''}`
    if (t.difficulty) html += ` &middot; ${t.difficulty}`
    if (t.pageviews) html += ` &middot; ${t.pageviews.toLocaleString()} views/wk`
    html += `</div>`
  }

  html += `<p>${t.summary}</p>`

  if (t.why_matters) {
    html += `<div class="why-matters">\\u{1F4A1} <strong>Why this matters:</strong> ${t.why_matters}</div>`
  }

  if (t.facts && t.facts.length > 0) {
    html += `<strong>Key facts:</strong><ul class="facts-list">`
    t.facts.forEach(f => { html += `<li>${f}</li>` })
    html += `</ul>`
  }

  if (t.quiz_question) {
    html += `<div class="quiz-q">\\u{1F4DD} ${t.quiz_question}</div>`
    if (t.quiz_options) {
      t.quiz_options.forEach(o => { html += `<div class="meta" style="padding:2px 0">\\u{25CB} ${o}</div>` })
    }
  }

  content.innerHTML = html

  let startX = 0, currentX = 0, isDragging = false
  const THRESHOLD = 120

  function updateCard(dx) {
    const rot = dx * 0.08
    card.style.transform = `translateX(${dx}px) rotate(${rot}deg)`
    const progress = Math.min(Math.abs(dx) / THRESHOLD, 1)
    if (dx > 0) {
      hint.textContent = "\\u{1F4BE} SAVE"
      hint.style.color = "#22c55e"
      hint.style.opacity = progress
      card.style.boxShadow = `${dx * 0.3}px 4px 24px rgba(34,197,94,${progress * 0.5})`
    } else if (dx < 0) {
      hint.textContent = "\\u{23ED} SKIP"
      hint.style.color = "#ef4444"
      hint.style.opacity = progress
      card.style.boxShadow = `${dx * 0.3}px 4px 24px rgba(239,68,68,${progress * 0.5})`
    } else {
      hint.style.opacity = 0
      card.style.boxShadow = "0 4px 24px rgba(0,0,0,0.4)"
    }
  }

  function flyOut(direction) {
    const flyX = direction * 800
    card.classList.add("fly-out")
    card.style.transform = `translateX(${flyX}px) rotate(${direction * 30}deg)`
    card.style.opacity = "0"
    const action = direction > 0 ? "save" : "skip"
    setStateValue("swipe_value", action)
    setTriggerValue("swiped", action)
  }

  function resetCard() {
    card.classList.remove("fly-out", "dragging")
    card.style.transform = ""
    card.style.opacity = ""
    card.style.boxShadow = "0 4px 24px rgba(0,0,0,0.4)"
    hint.style.opacity = 0
  }

  if (data.reset === true) {
    setTimeout(resetCard, 50)
  }

  card.addEventListener("mousedown", e => { isDragging = true; startX = e.clientX; card.classList.add("dragging"); e.preventDefault() })
  card.addEventListener("touchstart", e => { isDragging = true; startX = e.touches[0].clientX; card.classList.add("dragging") }, {passive:true})

  const onMove = (clientX) => {
    if (!isDragging) return
    currentX = clientX - startX
    updateCard(currentX)
  }
  document.addEventListener("mousemove", e => onMove(e.clientX))
  document.addEventListener("touchmove", e => onMove(e.touches[0].clientX), {passive:true})

  const onEnd = () => {
    if (!isDragging) return
    isDragging = false
    card.classList.remove("dragging")
    if (Math.abs(currentX) > THRESHOLD) {
      flyOut(currentX > 0 ? 1 : -1)
    } else {
      updateCard(0)
    }
    currentX = 0
  }
  document.addEventListener("mouseup", onEnd)
  document.addEventListener("touchend", onEnd)

  const onKey = (e) => {
    if (e.key === "ArrowRight") flyOut(1)
    else if (e.key === "ArrowLeft") flyOut(-1)
  }
  document.addEventListener("keydown", onKey)

  return () => {
    document.removeEventListener("mousemove", onMove)
    document.removeEventListener("mouseup", onEnd)
    document.removeEventListener("touchmove", onMove)
    document.removeEventListener("touchend", onEnd)
    document.removeEventListener("keydown", onKey)
  }
}
"""
