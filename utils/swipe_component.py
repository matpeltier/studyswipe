SWIPE_CARD_HTML = """\
<div id="swipe-container" style="
  position: relative;
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
  height: min(70vh, 520px);
  perspective: 1000px;
  overflow: hidden;
">
  <div id="swipe-card" style="
    position: absolute;
    inset: 0;
    border-radius: 16px;
    background: var(--st-secondary-background-color, #1a1a2e);
    border: 1px solid rgba(99,102,241,0.3);
    padding: 20px 24px;
    overflow: hidden;
    transition: box-shadow 0.2s ease;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    display: flex;
    flex-direction: column;
    gap: 6px;
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
    <div id="card-content" style="flex:1; overflow-y:auto; overflow-x:hidden; display:flex; flex-direction:column; gap:6px; min-height:0;"></div>
    <div id="swipe-arrows" style="
      display:none;
      justify-content:space-between; align-items:center;
      padding-top:4px; font-size:0.8em; opacity:0.5;
      color: var(--st-text-color, #e2e8f0); flex-shrink:0;
    ">
      <span>\\u2B05 Skip</span>
      <span style="font-size:0.75em; opacity:0.7">Swipe to navigate</span>
      <span>Save \\u27A1</span>
    </div>
  </div>
</div>
"""

SWIPE_CARD_CSS = """\
#swipe-card.dragging { transition: none; }
#swipe-card.fly-out {
  transition: transform 0.4s ease, opacity 0.4s ease;
}
#card-content::-webkit-scrollbar { width: 4px; }
#card-content::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.3); border-radius: 2px; }
#card-content h2 { margin: 0 0 2px 0; color: var(--st-text-color, #e2e8f0); font-size: 1.3em; }
#card-content .badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 0.75em;
  font-weight: 600;
  margin-bottom: 2px;
}
#card-content .meta { font-size: 0.8em; opacity: 0.8; margin: 0; color: var(--st-text-color, #e2e8f0); }
#card-content p { margin: 4px 0; line-height: 1.4; color: var(--st-text-color, #e2e8f0); font-size: 0.92em; }
#card-content .why-matters {
  background: rgba(99,102,241,0.12);
  border-left: 3px solid #6366f1;
  padding: 6px 10px;
  border-radius: 4px;
  margin: 4px 0;
  font-size: 0.88em;
}
#card-content .facts-list { margin: 2px 0; padding-left: 14px; }
#card-content .facts-list li { margin: 2px 0; line-height: 1.3; font-size: 0.88em; color: var(--st-text-color, #e2e8f0); }

@media (pointer: coarse) {
  #swipe-card { cursor: grab; user-select: none; touch-action: pan-y; }
  #swipe-card:active { cursor: grabbing; }
  #swipe-arrows { display: flex !important; }
}
@media (max-width: 640px) {
  #swipe-container { height: min(65vh, 420px); }
  #card-content h2 { font-size: 1.1em; }
  #card-content p { font-size: 0.85em; }
}
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
    if (t.difficulty) html += ` \\u00B7 ${t.difficulty}`
    if (t.pageviews) html += ` \\u00B7 ${t.pageviews.toLocaleString()} views/wk`
    html += `</div>`
  }

  const summary = t.summary
  html += `<p>${summary}</p>`

  if (t.why_matters) {
    html += `<div class="why-matters">\\u{1F4A1} <strong>Why this matters:</strong> ${t.why_matters}</div>`
  }

  if (t.facts && t.facts.length > 0) {
    html += `<strong style="font-size:0.9em">Key facts:</strong><ul class="facts-list">`
    const maxFacts = t.facts.length > 3 ? 3 : t.facts.length
    for (let i = 0; i < maxFacts; i++) {
      html += `<li>${t.facts[i]}</li>`
    }
    html += `</ul>`
  }

  content.innerHTML = html

  const isTouchDevice = window.matchMedia("(pointer: coarse)").matches

  let startX = 0, startY = 0, currentX = 0, isDragging = false, isScrolling = false
  const THRESHOLD = 100

  function updateCard(dx) {
    const rot = dx * 0.06
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

  if (!isTouchDevice) return

  const shadow = card.getRootNode()

  const onTouchStart = (e) => {
    startX = e.touches[0].clientX; startY = e.touches[0].clientY
    isDragging = false; isScrolling = false; currentX = 0
    card.classList.add("dragging")
  }
  shadow.addEventListener("touchstart", onTouchStart, true)

  const onTouchMove = (e) => {
    const dx = e.touches[0].clientX - startX
    const dy = e.touches[0].clientY - startY
    if (!isDragging && !isScrolling) {
      if (Math.abs(dy) > Math.abs(dx) && Math.abs(dy) > 5) { isScrolling = true; return }
      if (Math.abs(dx) > 5) { isDragging = true }
    }
    if (!isDragging) return
    currentX = dx
    updateCard(currentX)
  }
  shadow.addEventListener("touchmove", onTouchMove, {passive:true})

  const onTouchEnd = () => {
    if (!isDragging && !isScrolling) return
    isDragging = false; isScrolling = false
    card.classList.remove("dragging")
    if (currentX !== 0 && Math.abs(currentX) > THRESHOLD) {
      flyOut(currentX > 0 ? 1 : -1)
    } else {
      updateCard(0)
    }
    currentX = 0
  }
  shadow.addEventListener("touchend", onTouchEnd)
  parentElement.addEventListener("touchend", onTouchEnd)

  return () => {
    shadow.removeEventListener("touchstart", onTouchStart, true)
    shadow.removeEventListener("touchmove", onTouchMove)
    shadow.removeEventListener("touchend", onTouchEnd)
    parentElement.removeEventListener("touchend", onTouchEnd)
  }
}
"""
