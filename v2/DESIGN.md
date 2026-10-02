# V2 visual system

## Direction

Apple Liquid Glass inspired, charcoal graphite studio. Use cool ice-blue focus and controls, light gray text, and restrained amber/coral pulled from the app mark. Keep the video surface visually open and editing panels calm and opaque enough for sustained work. Glass is reserved for navigation and transient or floating surfaces; the main work panels remain solid graphite.

## Layout and hierarchy

The desktop workspace places timed, searchable captions and transcription controls on the left, the video preview with transport and caption timeline in the center, and a scrollable inspector on the right. The inspector contains caption text/timing, appearance and placement controls, motion presets/gallery, translation, dubbing, and delivery. Import/export and the Dub audio entry point live in the header. Transcription and dubbing are both first-class workflows; preserve similarly direct access to each as the workspace evolves.

At widths below 940px, the inspector becomes a fixed slide-in panel opened by the Style & motion control or Dub audio entry point. Below 650px, the header and stage tighten, the inspector and effect gallery use viewport-bounded widths, the gallery changes to two columns, and transcription remains directly available below the caption list. Subtitle editing and dubbing remain reachable from the same workspace.

Inspector sections are keyboard-operable foldouts. Keep caption text and Video Look open by default; model, translation, dubbing, appearance, motion, placement, and delivery panels can be opened when needed. Video Look exposes Light, Color, Color grading, Detail & Optics, and Geometry adjustments, previews them on the canvas, and sends the same values to the local burned-video renderer.

## Surfaces, type, and motion

- Use charcoal gradients for the page and graphite work panels. The video stage has a subtle radial light and vignette; caption selection and transport use restrained ice blue.
- The header uses a translucent charcoal fill, fine light edge, blur, and inset highlight. The effect dialog and mobile inspector use floating glass materials; preserve readable text and a clear media canvas.
- Use the native system sans-serif stack (`-apple-system`, BlinkMacSystemFont, Segoe UI). Headings, compact uppercase pane labels, muted supporting text, and clear form labels establish hierarchy. Interface icons are inline SVG; the app mark comes from the supplied asset.
- Short transitions and caption effects signal focus, playback, panel entry, and effect previews. Keep them interruptible and avoid animating the whole workspace during routine edits. The effect library filters by treatment family, previews a selected treatment, and applies it explicitly to the globally styled caption track.
- Type-on reveal follows Whisper word timestamps when available; imported captions without word-level timing fall back to cue-time character reveal.

## Accessibility and fallback behavior

Keyboard focus has a visible cyan outline, native controls inherit a dark color scheme, and dynamic transcription/dubbing statuses use live regions. Dialogs use modal semantics and labeled headings. Honor `prefers-reduced-motion`: CSS transitions/animations are suppressed and scripted GSAP motion and smooth scrolling are disabled or made immediate. Honor `prefers-reduced-transparency` by removing backdrop filters from the header and floating/transient panels and giving the header and inspector solid graphite fills. Maintain contrast if blur is unavailable; glass must not be required for content separation.

## Implemented scope and aspirations

Implemented: local video/caption editing, transcription, caption styling and motion, translation controls, local dubbing controls, SRT import/export, and a delivery flow for caption files or a burned MP4. Dubbing is surfaced as an inspector section reached from the header; translation and dubbing remain distinct operations. Playback and caption selection share the same preview and timing context.

Product direction: keep subtitle and dubbing workflows equally prominent and coherent across desktop and phone-sized screens, with the inspector adapting as a mobile sheet. Treat any additional localization or delivery concepts as aspirations until present in the interface and backed by working behavior. The direction contract in `index.html` is the north star; this document describes the current implementation where it is concrete.
