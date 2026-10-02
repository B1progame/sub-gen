# V2 visual system

## Direction

Apple Liquid Glass inspired, dark graphite studio. The implemented palette uses near-black graphite canvases, cool cyan/blue focus and controls, violet accents for motion, and the supplied amber brand mark/caption emphasis. Keep the video surface visually open and editing panels calm and opaque enough for sustained work. Glass is reserved for the header and transient or floating surfaces.

## Layout and hierarchy

The desktop workspace places timed, searchable captions and transcription controls on the left, the video preview with transport and caption timeline in the center, and a scrollable inspector on the right. The inspector contains caption text/timing, appearance and placement controls, motion presets/gallery, translation, dubbing, and delivery. Import/export and the Dub audio entry point live in the header. Transcription and dubbing are both first-class workflows; preserve similarly direct access to each as the workspace evolves.

At widths below 940px, the inspector becomes a fixed slide-in panel opened by the Style & motion control or Dub audio entry point. Below 650px, the header and stage tighten, the inspector and effect gallery use viewport-bounded widths, and the gallery changes to two columns. The current layout adapts these regions; it does not replace the caption list with a separate mobile navigation model.

## Surfaces, type, and motion

- Use graphite gradients for the page and opaque work panels. The video stage has a subtle radial light and vignette; caption selection uses a restrained cyan-to-violet highlight.
- The header uses a translucent dark fill, fine light edge, blur, and inset highlight. The mobile inspector, effect dialog, toast, and delivery dialog use darker glass-like layers. Preserve readable text and a clear media canvas.
- Use the native system sans-serif stack (`-apple-system`, BlinkMacSystemFont, Segoe UI). Headings, compact uppercase pane labels, muted supporting text, and clear form labels establish hierarchy. Interface icons are inline SVG; the app mark comes from the supplied asset.
- Short transitions and caption effects signal focus, playback, panel entry, and effect previews. Keep them interruptible and avoid animating the whole workspace during routine edits.

## Accessibility and fallback behavior

Keyboard focus has a visible cyan outline, native controls inherit a dark color scheme, and dynamic transcription/dubbing statuses use live regions. Dialogs use modal semantics and labeled headings. Honor `prefers-reduced-motion`: CSS transitions/animations are suppressed and scripted GSAP motion and smooth scrolling are disabled or made immediate. Honor `prefers-reduced-transparency` by removing backdrop filters from the header and floating/transient panels and giving the header and inspector solid graphite fills. Maintain contrast if blur is unavailable; glass must not be required for content separation.

## Implemented scope and aspirations

Implemented: local video/caption editing, transcription, caption styling and motion, translation controls, local dubbing controls, SRT import/export, and a delivery flow for caption files or a burned MP4. Dubbing is surfaced as an inspector section reached from the header; translation and dubbing remain distinct operations. Playback and caption selection share the same preview and timing context.

Product direction: keep subtitle and dubbing workflows equally prominent and coherent across desktop and phone-sized screens, with the inspector adapting as a mobile sheet. Treat any additional localization or delivery concepts as aspirations until present in the interface and backed by working behavior. The direction contract in `index.html` is the north star; this document describes the current implementation where it is concrete.
