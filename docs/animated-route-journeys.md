# Animated Route Journeys

Animated Route Journeys add a presentation layer to the existing editable draw.io workflow. The `.drawio` file remains the source artifact; the interactive viewer reuses the same intermediate model, layout engine, and routed edge geometry.

## Author a route

Add `routes` to the diagram model:

```json
{
  "routes": [
    {
      "id": "user-request",
      "label": "User Request",
      "edge_ids": [
        "user-frontdoor",
        "frontdoor-ingress",
        "ingress-app",
        "app-sql"
      ],
      "description": "Trace an end-user request to the application database.",
      "animation": {
        "style": "both",
        "speed": 1.0,
        "dwell_ms": 350,
        "loop": false
      }
    }
  ]
}
```

`edge_ids` are authoritative and ordered. Adjacent edges must form a contiguous chain. The viewer can traverse an existing edge backward when the ordered chain requires it, so bidirectional infrastructure relationships do not need duplicate presentation-only edges.

Animation styles:

- `both` — moving flow stroke plus traveling packet.
- `packet` — traveling packet without the moving dash effect.
- `flow` — moving flow stroke without the packet.

Playback is finite by default. Set `loop: true` only when continuous playback is actually wanted.

## Generate the viewer

After installing the package:

```bash
drawio-interactive --model architecture.json --output architecture.interactive.html
```

Or directly from the source tree:

```bash
python -m drawio_generator.interactive_html --model architecture.json --output architecture.interactive.html
```

The generated HTML is self-contained and has no runtime dependencies or network calls.

## Viewer behavior

The viewer provides:

- route selection;
- complete-route overview;
- Previous / Play-Pause / Next controls;
- 0.5x, 1x, and 2x viewer speed multipliers;
- route-specific speed and dwell settings;
- highlighted past/current/future route state;
- moving packet animation using the actual SVG edge geometry;
- node-arrival pulse;
- route details including protocol, edge label, security control, and data classification;
- keyboard navigation with Arrow keys, Home, End, Space, and layered Escape behavior;
- resumable pause while an edge is in flight;
- `prefers-reduced-motion` support;
- print behavior that strips the transient interactive overlay;
- stable `data-node-id`, `data-edge-id`, `data-source`, and `data-target` semantic hooks;
- shareable `#route=<id>` links without leaking transient journey position into the URL.

## Design boundary

The interactive HTML is deliberately a companion artifact, not a replacement for diagrams.net. Editing remains in `.drawio`; route playback remains in HTML. This keeps presentation behavior out of the editable XML and avoids creating two independent layout engines.
