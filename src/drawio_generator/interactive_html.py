"""Self-contained animated route-journey viewer for Diagram models.

The draw.io artifact remains the editable source. This module reuses the exact
layout engine and SVG preview geometry to produce a dependency-free HTML
companion that can highlight and animate explicitly authored routes.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from html import escape
import json
from pathlib import Path
import re
from typing import Any

from .diagram_model import Diagram, Route
from .layout_engine import apply_layout, infer_layer
from .model_io import ModelValidationError, load_model
from .preview import _edge_route, build_scene, render_page_svg


def route_node_sequence(diagram: Diagram, route: Route) -> list[str]:
    """Return the ordered node journey implied by ``route.edge_ids``.

    Consecutive edges can be traversed forward or backward. The first edge is
    oriented toward the endpoint it shares with the second edge; a one-edge
    route follows the authored source -> target direction.
    """

    edge_lookup = {edge.id: edge for edge in diagram.edges}
    missing = [edge_id for edge_id in route.edge_ids if edge_id not in edge_lookup]
    if missing:
        raise ValueError(f"Route {route.id!r} references missing edges: {', '.join(missing)}")
    if not route.edge_ids:
        raise ValueError(f"Route {route.id!r} has no edges")

    first = edge_lookup[route.edge_ids[0]]
    if len(route.edge_ids) == 1:
        return [first.source, first.target]

    second = edge_lookup[route.edge_ids[1]]
    shared = {first.source, first.target} & {second.source, second.target}
    if not shared:
        raise ValueError(
            f"Route {route.id!r} is not contiguous between {first.id!r} and {second.id!r}"
        )

    current = first.target if first.target in shared else sorted(shared)[0]
    start = first.source if current == first.target else first.target
    nodes = [start, current]

    for edge_id in route.edge_ids[1:]:
        edge = edge_lookup[edge_id]
        if current == edge.source:
            current = edge.target
        elif current == edge.target:
            current = edge.source
        else:
            raise ValueError(
                f"Route {route.id!r} edge {edge.id!r} does not continue from {current!r}"
            )
        nodes.append(current)
    return nodes


def build_route_payload(diagram: Diagram) -> list[dict[str, Any]]:
    """Build browser-safe semantic route data from a laid-out diagram."""

    edge_lookup = {edge.id: edge for edge in diagram.edges}
    node_lookup = {node.id: node for node in diagram.nodes}
    payload: list[dict[str, Any]] = []
    for route in diagram.routes:
        node_ids = route_node_sequence(diagram, route)
        steps: list[dict[str, Any]] = []
        for index, edge_id in enumerate(route.edge_ids):
            edge = edge_lookup[edge_id]
            from_id, to_id = node_ids[index], node_ids[index + 1]
            steps.append(
                {
                    "edge_id": edge.id,
                    "from": from_id,
                    "to": to_id,
                    "reverse": from_id == edge.target and to_id == edge.source,
                    "label": edge.label,
                    "protocol": edge.protocol or "",
                    "security_control": edge.security_control or "",
                    "data_classification": edge.data_classification or "",
                }
            )
        payload.append(
            {
                "id": route.id,
                "label": route.label,
                "description": route.description or "",
                "node_ids": node_ids,
                "node_labels": [node_lookup[node_id].label for node_id in node_ids],
                "steps": steps,
                "animation": {
                    "style": route.animation.style,
                    "speed": route.animation.speed,
                    "dwell_ms": route.animation.dwell_ms,
                    "loop": route.animation.loop,
                },
            }
        )
    return payload


def render_interactive_html(diagram: Diagram) -> str:
    """Render one dependency-free HTML architecture route viewer."""

    laid_out = deepcopy(diagram)
    for node in laid_out.nodes:
        if not node.layer:
            node.layer = infer_layer(node)
    laid_out = apply_layout(laid_out)

    scene = build_scene(laid_out.title, laid_out)
    base_svg = render_page_svg(scene).replace(
        "<svg ",
        '<svg class="base-diagram" role="img" aria-label="Architecture diagram" ',
        1,
    )
    overlay = _render_semantic_overlay(laid_out, scene.width, scene.height)
    route_payload = build_route_payload(laid_out)
    route_json = json.dumps(route_payload, ensure_ascii=False).replace("</", "<\\/")

    route_options = "\n".join(
        f'<option value="{escape(route.id, quote=True)}">{escape(route.label)}</option>'
        for route in laid_out.routes
    )
    empty_note = (
        ""
        if laid_out.routes
        else '<p class="empty-note">No routes are defined in this model. Add <code>routes</code> to enable route tracing.</p>'
    )

    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(laid_out.title)} — Interactive Route Journey</title>
<style>
:root {{
  color-scheme: light dark;
  --surface: #ffffff;
  --surface-muted: #f8fafc;
  --text: #172033;
  --muted: #64748b;
  --border: #cbd5e1;
  --accent: #2563eb;
  --accent-strong: #1d4ed8;
  --past: #0f766e;
  --future: #94a3b8;
  --shadow: 0 10px 30px rgba(15, 23, 42, .12);
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: #eef2f7;
  color: var(--text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
.viewer {{
  max-width: 1800px;
  margin: 0 auto;
  padding: 18px;
}}
.viewer-toolbar {{
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: end;
  padding: 12px;
  margin-bottom: 14px;
  background: rgba(255,255,255,.96);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow);
  backdrop-filter: blur(10px);
}}
.control-group {{ display: grid; gap: 4px; }}
.control-group label {{ font-size: 12px; font-weight: 700; color: #475569; }}
select, button {{
  min-height: 42px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text);
  font: inherit;
}}
select {{ padding: 0 34px 0 10px; }}
button {{
  padding: 0 13px;
  cursor: pointer;
  font-weight: 700;
}}
button:hover:not(:disabled) {{ border-color: var(--accent); }}
button:focus-visible, select:focus-visible {{
  outline: 3px solid rgba(37,99,235,.28);
  outline-offset: 2px;
}}
button:disabled {{ opacity: .45; cursor: default; }}
.play[aria-pressed="true"] {{
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}}
.transport {{ display: flex; gap: 6px; }}
.main-grid {{
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  gap: 14px;
  align-items: start;
}}
.diagram-card, .route-panel {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow);
}}
.diagram-card {{ padding: 10px; overflow: auto; }}
.diagram-stage {{
  position: relative;
  width: 100%;
  min-width: 700px;
  line-height: 0;
}}
.base-diagram {{
  display: block;
  width: 100%;
  height: auto;
}}
.route-overlay {{
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  overflow: visible;
}}
.route-dimmer {{
  fill: #ffffff;
  opacity: 0;
  transition: opacity .2s ease;
}}
.diagram-stage[data-route-active="true"] .route-dimmer {{ opacity: .58; }}
.route-edge {{
  fill: none;
  stroke: var(--future);
  stroke-width: 5;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0;
  transition: opacity .18s ease, stroke .18s ease, stroke-width .18s ease;
}}
.route-edge.active {{ opacity: .72; }}
.route-edge.past {{ stroke: var(--past); opacity: .78; }}
.route-edge.current {{
  stroke: var(--accent);
  stroke-width: 7;
  opacity: 1;
}}
.diagram-stage[data-animation-style="both"] .route-edge.current,
.diagram-stage[data-animation-style="flow"] .route-edge.current {{
  stroke-dasharray: 16 12;
  animation: route-flow var(--flow-duration, .8s) linear infinite;
}}
.route-edge.current[data-route-reverse="true"] {{ animation-direction: reverse; }}
@keyframes route-flow {{ to {{ stroke-dashoffset: -28; }} }}
.route-node {{
  fill: rgba(255,255,255,.94);
  stroke: var(--future);
  stroke-width: 3;
  rx: 8;
  opacity: 0;
  transition: opacity .18s ease, stroke .18s ease, filter .18s ease;
}}
.route-node-label {{
  fill: #0f172a;
  font-size: 12px;
  font-weight: 800;
  text-anchor: middle;
  dominant-baseline: middle;
  opacity: 0;
}}
.route-node.active, .route-node-label.active {{ opacity: 1; }}
.route-node.past {{ stroke: var(--past); }}
.route-node.current {{
  stroke: var(--accent);
  stroke-width: 5;
  filter: drop-shadow(0 0 8px rgba(37,99,235,.45));
}}
.route-node.pulse {{ animation: node-pulse .42s ease-out 1; }}
@keyframes node-pulse {{
  0% {{ stroke-width: 5; filter: drop-shadow(0 0 2px rgba(37,99,235,.3)); }}
  50% {{ stroke-width: 9; filter: drop-shadow(0 0 16px rgba(37,99,235,.7)); }}
  100% {{ stroke-width: 5; filter: drop-shadow(0 0 8px rgba(37,99,235,.45)); }}
}}
.route-packet {{
  fill: #ffffff;
  stroke: var(--accent);
  stroke-width: 5;
  filter: drop-shadow(0 0 7px rgba(37,99,235,.8));
  opacity: 0;
}}
.diagram-stage[data-animation-style="flow"] .route-packet {{ display: none; }}
.route-panel {{
  position: sticky;
  top: 86px;
  padding: 14px;
  max-height: calc(100vh - 110px);
  overflow: auto;
}}
.route-panel h2 {{ margin: 0 0 6px; font-size: 18px; }}
.route-panel p {{ margin: 0 0 12px; color: var(--muted); line-height: 1.45; }}
.route-steps {{ display: grid; gap: 8px; }}
.route-step {{
  width: 100%;
  min-height: 0;
  padding: 9px 10px;
  text-align: left;
  border-radius: 9px;
  background: var(--surface-muted);
}}
.route-step[aria-current="step"] {{
  border-color: var(--accent);
  background: #eff6ff;
  box-shadow: inset 3px 0 0 var(--accent);
}}
.route-step .route-step-title {{ display: block; font-weight: 800; }}
.route-step .route-step-meta {{
  display: block;
  margin-top: 3px;
  font-size: 12px;
  font-weight: 500;
  color: var(--muted);
}}
.route-progress {{
  margin-left: auto;
  min-width: 74px;
  text-align: right;
  font-variant-numeric: tabular-nums;
  font-weight: 800;
  color: #475569;
}}
.keyboard-hint {{
  margin-top: 12px !important;
  font-size: 12px;
}}
.empty-note {{ padding: 12px; }}
@media (max-width: 1000px) {{
  .main-grid {{ grid-template-columns: 1fr; }}
  .route-panel {{ position: static; max-height: none; }}
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{
    scroll-behavior: auto !important;
    animation-duration: .001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .001ms !important;
  }}
  .route-edge.current {{ stroke-dasharray: none !important; }}
}}
@media print {{
  body {{ background: white; }}
  .viewer {{ max-width: none; padding: 0; }}
  .viewer-toolbar, .route-panel, .route-overlay {{ display: none !important; }}
  .diagram-card {{ border: 0; box-shadow: none; padding: 0; }}
  .diagram-stage {{ min-width: 0; }}
}}
</style>
</head>
<body>
<main class="viewer">
  <div class="viewer-toolbar" role="group" aria-label="Route journey controls">
    <div class="control-group">
      <label for="route-select">Route</label>
      <select id="route-select">
        <option value="">Choose a route…</option>
        {route_options}
      </select>
    </div>
    <div class="control-group">
      <label>Journey</label>
      <div class="transport">
        <button id="route-prev" type="button" aria-label="Previous route position" disabled>◀</button>
        <button id="route-play" class="play" type="button" aria-label="Play route journey" aria-pressed="false" disabled>▶ Play</button>
        <button id="route-next" type="button" aria-label="Next route position" disabled>▶</button>
        <button id="route-overview" type="button" aria-label="Show complete route overview" disabled>Overview</button>
      </div>
    </div>
    <div class="control-group">
      <label for="route-speed">Speed</label>
      <select id="route-speed" disabled>
        <option value="0.5">0.5×</option>
        <option value="1" selected>1×</option>
        <option value="2">2×</option>
      </select>
    </div>
    <div id="route-progress" class="route-progress" aria-live="polite">—</div>
  </div>
  {empty_note}
  <div class="main-grid">
    <section class="diagram-card" aria-label="Interactive architecture diagram">
      <div id="diagram-stage" class="diagram-stage" data-route-active="false" data-animation-style="both">
        {base_svg}
        {overlay}
      </div>
    </section>
    <aside id="route-panel" class="route-panel" aria-live="polite">
      <h2>Route Journey</h2>
      <p>Select a route to highlight its complete architecture path.</p>
      <div id="route-steps" class="route-steps"></div>
      <p class="keyboard-hint">Keyboard: ←/→ step, Home/End jump, Space play/pause, Esc pause → overview → clear.</p>
    </aside>
  </div>
</main>
<script>
(() => {{
  "use strict";
  const routes = {route_json};
  const routeById = new Map(routes.map(route => [route.id, route]));
  const stage = document.getElementById("diagram-stage");
  const routeSelect = document.getElementById("route-select");
  const speedSelect = document.getElementById("route-speed");
  const prevButton = document.getElementById("route-prev");
  const playButton = document.getElementById("route-play");
  const nextButton = document.getElementById("route-next");
  const overviewButton = document.getElementById("route-overview");
  const progress = document.getElementById("route-progress");
  const panel = document.getElementById("route-panel");
  const stepsContainer = document.getElementById("route-steps");
  const packet = document.querySelector(".route-packet");
  const edgeElements = new Map(
    [...document.querySelectorAll(".route-edge")].map(el => [el.dataset.edgeId, el])
  );
  const nodeElements = new Map(
    [...document.querySelectorAll(".route-node")].map(el => [el.dataset.nodeId, el])
  );
  const nodeLabelElements = new Map(
    [...document.querySelectorAll(".route-node-label")].map(el => [el.dataset.nodeId, el])
  );
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  let activeRoute = null;
  let journeyIndex = -1;
  let playing = false;
  let generation = 0;
  let frameHandle = 0;
  let edgeProgress = 0;

  function setControlsEnabled(enabled) {{
    prevButton.disabled = !enabled;
    playButton.disabled = !enabled;
    nextButton.disabled = !enabled;
    overviewButton.disabled = !enabled;
    speedSelect.disabled = !enabled;
  }}

  function clearClasses() {{
    for (const edge of edgeElements.values()) {{
      edge.classList.remove("active", "past", "current", "future");
      edge.removeAttribute("data-route-reverse");
      edge.style.removeProperty("--flow-duration");
    }}
    for (const node of nodeElements.values()) {{
      node.classList.remove("active", "past", "current", "future", "pulse");
    }}
    for (const label of nodeLabelElements.values()) {{
      label.classList.remove("active");
    }}
    packet.style.opacity = "0";
  }}

  function routeSpeed() {{
    if (!activeRoute) return 1;
    return Math.max(0.05, Number(activeRoute.animation.speed || 1) * Number(speedSelect.value || 1));
  }}

  function setEdgeMotion(edge, step) {{
    edge.dataset.routeReverse = step.reverse ? "true" : "false";
    edge.style.setProperty("--flow-duration", `${{Math.max(0.14, 0.8 / routeSpeed())}}s`);
  }}

  function markRouteNode(nodeId, state) {{
    const node = nodeElements.get(nodeId);
    const label = nodeLabelElements.get(nodeId);
    if (node) {{
      node.classList.add("active");
      if (state) node.classList.add(state);
    }}
    if (label) label.classList.add("active");
  }}

  function applyOverview() {{
    if (!activeRoute) return;
    pauseJourney({{ preserveProgress: false }});
    journeyIndex = -1;
    edgeProgress = 0;
    clearClasses();
    stage.dataset.routeActive = "true";
    stage.dataset.animationStyle = activeRoute.animation.style || "both";
    activeRoute.steps.forEach(step => {{
      const edge = edgeElements.get(step.edge_id);
      if (edge) {{
        edge.classList.add("active");
        setEdgeMotion(edge, step);
      }}
    }});
    activeRoute.node_ids.forEach(nodeId => markRouteNode(nodeId, ""));
    updateStepButtons();
    updateProgress();
  }}

  function applyStep(index, options = {{}}) {{
    if (!activeRoute) return;
    const max = activeRoute.node_ids.length - 1;
    journeyIndex = Math.max(0, Math.min(max, index));
    if (!options.preserveProgress) edgeProgress = 0;
    clearClasses();
    stage.dataset.routeActive = "true";
    stage.dataset.animationStyle = activeRoute.animation.style || "both";

    activeRoute.steps.forEach((step, edgeIndex) => {{
      const edge = edgeElements.get(step.edge_id);
      if (!edge) return;
      edge.classList.add("active");
      setEdgeMotion(edge, step);
      if (edgeIndex < journeyIndex) edge.classList.add("past");
      else if (edgeIndex === journeyIndex && journeyIndex < max && edgeProgress > 0) edge.classList.add("current");
      else edge.classList.add("future");
    }});

    activeRoute.node_ids.forEach((nodeId, nodeIndex) => {{
      if (nodeIndex < journeyIndex) markRouteNode(nodeId, "past");
      else if (nodeIndex === journeyIndex) markRouteNode(nodeId, "current");
      else markRouteNode(nodeId, "future");
    }});

    positionPacketAtNode(activeRoute.node_ids[journeyIndex]);
    updateStepButtons();
    updateProgress();
  }}

  function positionPacketAtNode(nodeId) {{
    const node = nodeElements.get(nodeId);
    if (!node || stage.dataset.animationStyle === "flow") {{
      packet.style.opacity = "0";
      return;
    }}
    const x = Number(node.getAttribute("x")) + Number(node.getAttribute("width")) / 2;
    const y = Number(node.getAttribute("y")) + Number(node.getAttribute("height")) / 2;
    packet.setAttribute("cx", String(x));
    packet.setAttribute("cy", String(y));
    packet.style.opacity = "1";
  }}

  function pulseNode(nodeId) {{
    const node = nodeElements.get(nodeId);
    if (!node || reducedMotion.matches) return;
    node.classList.remove("pulse");
    void node.getBoundingClientRect();
    node.classList.add("pulse");
  }}

  function positionPacketOnEdge(edge, step, value) {{
    if (stage.dataset.animationStyle === "flow") {{
      packet.style.opacity = "0";
      return;
    }}
    const length = edge.getTotalLength();
    const logical = step.reverse ? 1 - value : value;
    const point = edge.getPointAtLength(length * logical);
    packet.setAttribute("cx", String(point.x));
    packet.setAttribute("cy", String(point.y));
    packet.style.opacity = "1";
  }}

  function animateEdge(edgeIndex) {{
    return new Promise(resolve => {{
      if (!activeRoute || edgeIndex >= activeRoute.steps.length) {{
        resolve(false);
        return;
      }}
      const step = activeRoute.steps[edgeIndex];
      const edge = edgeElements.get(step.edge_id);
      if (!edge) {{
        resolve(false);
        return;
      }}
      clearClasses();
      activeRoute.steps.forEach((candidate, index) => {{
        const element = edgeElements.get(candidate.edge_id);
        if (!element) return;
        element.classList.add("active");
        setEdgeMotion(element, candidate);
        if (index < edgeIndex) element.classList.add("past");
        else if (index === edgeIndex) element.classList.add("current");
        else element.classList.add("future");
      }});
      activeRoute.node_ids.forEach((nodeId, index) => {{
        if (index <= edgeIndex) markRouteNode(nodeId, index === edgeIndex ? "current" : "past");
        else markRouteNode(nodeId, "future");
      }});

      const localGeneration = generation;
      if (reducedMotion.matches) {{
        edgeProgress = 1;
        positionPacketOnEdge(edge, step, 1);
        resolve(true);
        return;
      }}
      const duration = 1100 / routeSpeed();
      const started = performance.now() - edgeProgress * duration;
      function frame(now) {{
        if (!playing || localGeneration !== generation) {{
          resolve(false);
          return;
        }}
        edgeProgress = Math.min(1, Math.max(0, (now - started) / duration));
        positionPacketOnEdge(edge, step, edgeProgress);
        if (edgeProgress >= 1) {{
          resolve(true);
          return;
        }}
        frameHandle = requestAnimationFrame(frame);
      }}
      frameHandle = requestAnimationFrame(frame);
    }});
  }}

  function delay(ms, localGeneration) {{
    return new Promise(resolve => {{
      if (ms <= 0 || reducedMotion.matches) {{
        resolve(playing && localGeneration === generation);
        return;
      }}
      window.setTimeout(() => resolve(playing && localGeneration === generation), ms);
    }});
  }}

  async function playJourney() {{
    if (!activeRoute || playing) return;
    if (journeyIndex < 0) applyStep(0);
    if (journeyIndex >= activeRoute.node_ids.length - 1 && edgeProgress === 0) {{
      applyStep(0);
    }}
    playing = true;
    generation += 1;
    const localGeneration = generation;
    updatePlayButton();

    while (playing && localGeneration === generation && activeRoute) {{
      const lastNode = activeRoute.node_ids.length - 1;
      if (journeyIndex >= lastNode) {{
        if (activeRoute.animation.loop) {{
          applyStep(0);
          continue;
        }}
        pauseJourney({{ preserveProgress: false, complete: true }});
        break;
      }}

      const completed = await animateEdge(journeyIndex);
      if (!completed || !playing || localGeneration !== generation) break;
      edgeProgress = 0;
      journeyIndex += 1;
      applyStep(journeyIndex);
      pulseNode(activeRoute.node_ids[journeyIndex]);
      const dwell = Number(activeRoute.animation.dwell_ms || 0) / routeSpeed();
      const continued = await delay(dwell, localGeneration);
      if (!continued) break;
    }}
  }}

  function pauseJourney(options = {{}}) {{
    const wasPlaying = playing;
    playing = false;
    generation += 1;
    if (frameHandle) cancelAnimationFrame(frameHandle);
    frameHandle = 0;
    if (!options.preserveProgress) edgeProgress = 0;
    if (wasPlaying || options.complete) updatePlayButton();
  }}

  function updatePlayButton() {{
    playButton.setAttribute("aria-pressed", playing ? "true" : "false");
    playButton.textContent = playing ? "Ⅱ Pause" : "▶ Play";
  }}

  function togglePlay() {{
    if (playing) pauseJourney({{ preserveProgress: true }});
    else playJourney();
  }}

  function updateProgress() {{
    if (!activeRoute) {{
      progress.textContent = "—";
      return;
    }}
    progress.textContent = journeyIndex < 0
      ? `${{activeRoute.node_ids.length}} nodes`
      : `${{journeyIndex + 1}} / ${{activeRoute.node_ids.length}}`;
  }}

  function buildRoutePanel() {{
    stepsContainer.replaceChildren();
    if (!activeRoute) {{
      panel.querySelector("h2").textContent = "Route Journey";
      panel.querySelector("p").textContent = "Select a route to highlight its complete architecture path.";
      return;
    }}
    panel.querySelector("h2").textContent = activeRoute.label;
    panel.querySelector("p").textContent =
      activeRoute.description || `${{activeRoute.node_ids.length}} nodes · ${{activeRoute.steps.length}} connections`;

    activeRoute.node_ids.forEach((nodeId, index) => {{
      const button = document.createElement("button");
      button.type = "button";
      button.className = "route-step";
      button.dataset.routeJourneyIndex = String(index);
      button.tabIndex = index === 0 ? 0 : -1;
      const title = document.createElement("span");
      title.className = "route-step-title";
      title.textContent = `${{index + 1}}. ${{activeRoute.node_labels[index]}}`;
      button.appendChild(title);
      if (index > 0) {{
        const edge = activeRoute.steps[index - 1];
        const meta = document.createElement("span");
        meta.className = "route-step-meta";
        const parts = [edge.protocol, edge.label, edge.security_control, edge.data_classification].filter(Boolean);
        meta.textContent = parts.join(" · ");
        button.appendChild(meta);
      }}
      button.addEventListener("click", () => {{
        pauseJourney({{ preserveProgress: false }});
        applyStep(index);
      }});
      button.addEventListener("keydown", event => {{
        let next = index;
        if (event.key === "ArrowRight" || event.key === "ArrowDown") next = Math.min(activeRoute.node_ids.length - 1, index + 1);
        else if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = Math.max(0, index - 1);
        else if (event.key === "Home") next = 0;
        else if (event.key === "End") next = activeRoute.node_ids.length - 1;
        else if (event.key === "Enter" || event.key === " ") {{
          event.preventDefault();
          button.click();
          return;
        }} else return;
        event.preventDefault();
        const target = stepsContainer.querySelector(`[data-route-journey-index="${{next}}"]`);
        if (target) target.focus();
      }});
      stepsContainer.appendChild(button);
    }});
    updateStepButtons();
  }}

  function updateStepButtons() {{
    const buttons = [...stepsContainer.querySelectorAll(".route-step")];
    buttons.forEach((button, index) => {{
      const current = journeyIndex === index;
      button.tabIndex = current || (journeyIndex < 0 && index === 0) ? 0 : -1;
      if (current) button.setAttribute("aria-current", "step");
      else button.removeAttribute("aria-current");
    }});
  }}

  function selectRoute(id, options = {{ updateUrl: true }}) {{
    pauseJourney({{ preserveProgress: false }});
    activeRoute = routeById.get(id) || null;
    journeyIndex = -1;
    edgeProgress = 0;
    clearClasses();
    setControlsEnabled(Boolean(activeRoute));
    if (!activeRoute) {{
      stage.dataset.routeActive = "false";
      routeSelect.value = "";
      buildRoutePanel();
      updateProgress();
      if (options.updateUrl) history.replaceState(null, "", location.pathname + location.search);
      return;
    }}
    routeSelect.value = activeRoute.id;
    stage.dataset.routeActive = "true";
    stage.dataset.animationStyle = activeRoute.animation.style || "both";
    buildRoutePanel();
    applyOverview();
    if (options.updateUrl) {{
      history.replaceState(null, "", `#route=${{encodeURIComponent(activeRoute.id)}}`);
    }}
  }}

  function step(delta) {{
    if (!activeRoute) return;
    pauseJourney({{ preserveProgress: false }});
    if (journeyIndex < 0) applyStep(delta > 0 ? 0 : activeRoute.node_ids.length - 1);
    else applyStep(journeyIndex + delta);
  }}

  function escapeRoute() {{
    if (playing) {{
      pauseJourney({{ preserveProgress: true }});
      return "paused";
    }}
    if (activeRoute && journeyIndex >= 0) {{
      applyOverview();
      return "overview";
    }}
    if (activeRoute) {{
      selectRoute("");
      return "cleared";
    }}
    return "noop";
  }}

  function syncFromHash() {{
    const match = location.hash.match(/^#route=(.*)$/);
    if (!match) return;
    try {{
      const id = decodeURIComponent(match[1]);
      if (routeById.has(id)) selectRoute(id, {{ updateUrl: false }});
    }} catch (_) {{}}
  }}

  routeSelect.addEventListener("change", () => selectRoute(routeSelect.value));
  prevButton.addEventListener("click", () => step(-1));
  nextButton.addEventListener("click", () => step(1));
  playButton.addEventListener("click", togglePlay);
  overviewButton.addEventListener("click", applyOverview);
  speedSelect.addEventListener("change", () => {{
    if (activeRoute && journeyIndex < 0) applyOverview();
    else if (activeRoute) applyStep(journeyIndex, {{ preserveProgress: true }});
  }});
  window.addEventListener("beforeprint", () => pauseJourney({{ preserveProgress: true }}));
  window.addEventListener("hashchange", syncFromHash);
  document.addEventListener("keydown", event => {{
    if (event.target.closest("select, input, textarea, button")) return;
    if (event.key === "ArrowLeft") {{ event.preventDefault(); step(-1); }}
    else if (event.key === "ArrowRight") {{ event.preventDefault(); step(1); }}
    else if (event.key === "Home" && activeRoute) {{ event.preventDefault(); pauseJourney({{ preserveProgress: false }}); applyStep(0); }}
    else if (event.key === "End" && activeRoute) {{ event.preventDefault(); pauseJourney({{ preserveProgress: false }}); applyStep(activeRoute.node_ids.length - 1); }}
    else if (event.key === " ") {{ event.preventDefault(); togglePlay(); }}
    else if (event.key === "Escape") {{ event.preventDefault(); escapeRoute(); }}
  }});

  setControlsEnabled(false);
  updatePlayButton();
  syncFromHash();
}})();
</script>
</body>
</html>
'''


def _render_semantic_overlay(diagram: Diagram, width: int, height: int) -> str:
    nodes_by_id = {node.id: node for node in diagram.nodes}
    parts = [
        f'<svg class="route-overlay" viewBox="0 0 {width} {height}" aria-hidden="true">',
        f'<rect class="route-dimmer" x="0" y="0" width="{width}" height="{height}"/>',
        '<g class="route-edge-layer">',
    ]
    for edge in diagram.edges:
        points = _edge_route(edge, nodes_by_id)
        if not points:
            continue
        encoded_points = " ".join(f"{x:g},{y:g}" for x, y in points)
        parts.append(
            f'<polyline id="route-edge-{_dom_token(edge.id)}" class="route-edge" '
            f'data-edge-id="{escape(edge.id, quote=True)}" '
            f'data-source="{escape(edge.source, quote=True)}" '
            f'data-target="{escape(edge.target, quote=True)}" '
            f'points="{encoded_points}"/>'
        )
    parts.append('</g><g class="route-node-layer">')
    for node in diagram.nodes:
        x, y = float(node.x or 0), float(node.y or 0)
        cx, cy = x + node.width / 2.0, y + node.height / 2.0
        parts.append(
            f'<rect id="route-node-{_dom_token(node.id)}" class="route-node" '
            f'data-node-id="{escape(node.id, quote=True)}" '
            f'x="{x:g}" y="{y:g}" width="{node.width}" height="{node.height}"/>'
        )
        parts.append(
            f'<text class="route-node-label" data-node-id="{escape(node.id, quote=True)}" '
            f'x="{cx:g}" y="{cy:g}">{escape(node.label)}</text>'
        )
    parts.append(
        '<circle class="route-packet" cx="0" cy="0" r="7"/>'
        '</svg>'
    )
    return "\n".join(parts)


def _dom_token(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")
    return clean or "item"


def write_interactive(diagram: Diagram, output_path: Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_interactive_html(diagram), encoding="utf-8")
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a self-contained animated route-journey HTML companion from a Diagram model."
    )
    parser.add_argument("--model", required=True, help="Diagram model JSON (or YAML when PyYAML is importable).")
    parser.add_argument(
        "--output",
        help="Output HTML path. Defaults to <model-stem>.interactive.html beside the model.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    model_path = Path(args.model)
    try:
        diagram = load_model(model_path)
    except ModelValidationError as exc:
        for error in exc.errors:
            print(f"model validation error: {error}")
        return 2
    output = Path(args.output) if args.output else model_path.with_suffix(".interactive.html")
    write_interactive(diagram, output)
    print(f"Wrote interactive route viewer to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
