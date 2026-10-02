/* V2 subtitle design, motion preview, and local translation controls. */
(() => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const safeText = value => { const node = document.createElement('span'); node.textContent = value; return node.innerHTML; };
  const style = state.style;
  Object.assign(style, { effect: 'static', highlight: '#ffbf69', outlineColor: '#10131b', outlineWidth: 2, shadow: 6, radius: 8, letterSpacing: 0, speed: 'balanced', wordsPerBeat: 5, emphasis: 'color' });
  const inspector = $('.inspector');
  const look = style.videoLook ||= { exposure: 0, contrast: 1, saturation: 1, warmth: 0, shadows: 0, midtones: 0, highlights: 0, sharpness: 0, vignette: 0, flipX: false, flipY: false };
  const videoPanel = document.createElement('section');
  videoPanel.className = 'video-look-panel'; videoPanel.id = 'videoLookPanel';
  videoPanel.innerHTML = `<h2>Video look</h2><p class="motion-note">Shape the picture while you edit. These settings carry into Burn captions to MP4.</p>
    <fieldset><legend>Light</legend><label>Exposure <output id="lookExposureValue">0</output><input type="range" min="-2" max="2" step="0.1" value="0" data-look="exposure"></label><label>Contrast <output id="lookContrastValue">100%</output><input type="range" min="50" max="150" step="1" value="100" data-look="contrast"></label></fieldset>
    <fieldset><legend>Color</legend><label>Saturation <output id="lookSaturationValue">100%</output><input type="range" min="0" max="200" step="1" value="100" data-look="saturation"></label><label>Temperature <output id="lookWarmthValue">0</output><input type="range" min="-100" max="100" step="1" value="0" data-look="warmth"></label></fieldset>
    <fieldset><legend>Color grading</legend><p class="look-hint">Shift tone separately in the shadows, midtones, and highlights.</p><label>Shadows <output id="lookShadowsValue">Neutral</output><input type="range" min="-100" max="100" step="1" value="0" data-look="shadows"></label><label>Midtones <output id="lookMidtonesValue">Neutral</output><input type="range" min="-100" max="100" step="1" value="0" data-look="midtones"></label><label>Highlights <output id="lookHighlightsValue">Neutral</output><input type="range" min="-100" max="100" step="1" value="0" data-look="highlights"></label></fieldset>
    <fieldset><legend>Detail &amp; optics</legend><label>Sharpen <output id="lookSharpnessValue">0</output><input type="range" min="0" max="100" step="1" value="0" data-look="sharpness"></label><label>Vignette <output id="lookVignetteValue">0</output><input type="range" min="0" max="100" step="1" value="0" data-look="vignette"></label></fieldset>
    <fieldset><legend>Geometry</legend><div class="look-flips"><label><input type="checkbox" data-look="flipX"> Mirror horizontally</label><label><input type="checkbox" data-look="flipY"> Mirror vertically</label></div></fieldset>
    <button type="button" class="wide ghost" id="resetVideoLook">Reset video adjustments</button>`;
  const appearancePanel = [...inspector.children].find(section => section.querySelector('h2')?.textContent.trim() === 'Appearance');
  inspector.insertBefore(videoPanel, appearancePanel || inspector.children[1] || null);
  const video = $('#video');
  const videoLookOverlay = document.createElement('div');
  videoLookOverlay.className = 'video-look-overlay'; videoLookOverlay.setAttribute('aria-hidden', 'true');
  $('#safeArea').before(videoLookOverlay);
  const paintVideoLook = () => {
    for (const key of ['exposure','contrast','saturation','warmth','shadows','midtones','highlights','sharpness','vignette']) {
      const input = videoPanel.querySelector(`[data-look="${key}"]`), output = $(`#look${key[0].toUpperCase()+key.slice(1)}Value`);
      if (!input || !output) continue;
      const value = Number(input.value); look[key] = key === 'contrast' || key === 'saturation' ? value / 100 : value;
      output.textContent = key === 'contrast' || key === 'saturation' ? `${value}%` : key === 'exposure' ? `${value > 0 ? '+' : ''}${value.toFixed(1)} EV` : ['shadows','midtones','highlights'].includes(key) ? (value === 0 ? 'Neutral' : `${value > 0 ? 'Warm' : 'Cool'} ${Math.abs(value)}`) : String(value);
    }
    look.flipX = videoPanel.querySelector('[data-look="flipX"]').checked;
    look.flipY = videoPanel.querySelector('[data-look="flipY"]').checked;
    const exposure = Math.pow(2, Number(look.exposure) || 0), sharpness = Number(look.sharpness) || 0;
    video.style.filter = `brightness(${exposure}) contrast(${look.contrast * (1 + sharpness / 800)}) saturate(${look.saturation}) sepia(${Math.max(0, Number(look.warmth)) / 750}) hue-rotate(${Math.min(0, Number(look.warmth)) * .12}deg)`;
    video.style.transform = `scale(${look.flipX ? -1 : 1},${look.flipY ? -1 : 1})`;
    const tint = (value, positive, negative) => { const amount=Math.min(1,Math.abs(Number(value)||0)/100*.22); return value===0?'transparent':`${value>0?positive:negative}${amount})`; };
    const warm='rgba(255,150,75,', cool='rgba(80,145,255,';
    const shadow=tint(look.shadows,warm,cool), mid=tint(look.midtones,warm,cool), high=tint(look.highlights,warm,cool);
    const edgeAlpha=Math.min(.72,(Number(look.vignette)||0)/100*.72);
    videoLookOverlay.style.background = `radial-gradient(ellipse at center, transparent ${Math.max(18,70-(Number(look.vignette)||0)*.38)}%, rgba(0,0,0,${edgeAlpha}) 100%), radial-gradient(ellipse 120% 110% at 50% 50%, ${mid}, transparent 75%), radial-gradient(ellipse 90% 100% at 8% 92%, ${shadow}, transparent 72%), radial-gradient(ellipse 90% 100% at 92% 8%, ${high}, transparent 72%)`;
    videoLookOverlay.style.mixBlendMode = 'soft-light';
  };
  videoPanel.querySelectorAll('[data-look]').forEach(input => input.addEventListener('input', paintVideoLook));
  videoPanel.querySelector('#resetVideoLook').addEventListener('click', () => {
    Object.assign(look, { exposure:0, contrast:1, saturation:1, warmth:0, shadows:0, midtones:0, highlights:0, sharpness:0, vignette:0, flipX:false, flipY:false });
    videoPanel.querySelectorAll('[data-look]').forEach(input => { input.checked = false; if (input.type !== 'checkbox') input.value = input.dataset.look === 'contrast' || input.dataset.look === 'saturation' ? '100' : '0'; });
    paintVideoLook();
  });
  paintVideoLook();
  const audioPanel = document.createElement('section');
  audioPanel.className = 'audio-panel'; audioPanel.id = 'audioPanel';
  audioPanel.innerHTML = `<h2>Dub your captions</h2><p class="motion-note">Generate a locally voiced track from the caption text. Translate into the target language first for a full-language dub. The new video replaces source audio with speech only; original music and ambience are not retained. Your source file stays untouched.</p><label>Speech model<select id="dubModel"><option value="chatterbox-multilingual-v3">Chatterbox Multilingual V3 · 23 languages</option></select></label><label>Dub language<select id="dubLanguage"><option value="de">German</option><option value="en">English</option><option value="es">Spanish</option><option value="fr">French</option><option value="it">Italian</option><option value="pt">Portuguese</option><option value="zh">Chinese</option><option value="ja">Japanese</option><option value="ko">Korean</option><option value="ar">Arabic</option><option value="hi">Hindi</option><option value="nl">Dutch</option><option value="pl">Polish</option><option value="ru">Russian</option><option value="sv">Swedish</option><option value="da">Danish</option><option value="fi">Finnish</option><option value="el">Greek</option><option value="he">Hebrew</option><option value="ms">Malay</option><option value="no">Norwegian</option><option value="sw">Swahili</option><option value="tr">Turkish</option></select></label><label>Voice reference <input id="voiceReference" type="file" accept="audio/wav,audio/mpeg,audio/mp4,audio/flac,audio/ogg"><small>Optional · use a voice clip you have permission to reproduce.</small></label><button type="button" id="generateDub" class="wide action">Generate dubbed video</button><p id="audioModelStatus" class="motion-note" aria-live="polite">Checking optional local voice runtime…</p><div id="dubProgress" class="dub-progress" hidden><span id="dubStage">Preparing local dub</span><span id="dubPercent">0%</span><i><b id="dubProgressFill"></b></i></div><p class="audio-caveat">Generated speech starts at each caption's time. Listen through and adjust any lines that overlap or sound rushed.</p>`;
  inspector.insertBefore(audioPanel, inspector.children[1] || null);
  const dubbingWorkspace = $('#dubbingWorkspace');
  dubbingWorkspace?.addEventListener('click', () => {
    if (window.matchMedia('(max-width: 940px)').matches) setInspectorOpen(true);
    expandSection(audioPanel);
    audioPanel.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
    $('#generateDub').focus({ preventScroll: true });
  });
  const audioStatus = $('#audioModelStatus');
  api('/api/audio/status').then(status => { audioStatus.textContent = status.detail || 'Optional Chatterbox model status is unavailable in this preview.'; }).catch(error => { audioStatus.textContent = /404|not found/i.test(error.message) ? 'This running preview server does not expose the V2 dubbing route yet. Restart V2 with start.bat to refresh its audio services.' : `Local voice runtime status unavailable: ${error.message}`; });
  let dubLanguageWasPicked = false;
  $('#dubLanguage').addEventListener('change', () => { dubLanguageWasPicked = true; });
  $('#generateDub').addEventListener('click', async () => {
    const status = $('#audioModelStatus'), button = $('#generateDub'), progress = $('#dubProgress');
    if (!state.file) { status.textContent = 'Open a video before generating a dubbed version.'; $('#openVideo').focus(); return; }
    if (!state.captions.length) { status.textContent = 'Add or transcribe captions before generating a dub.'; return; }
    button.disabled = true; button.textContent = 'Preparing dub…'; progress.hidden = false;
    try {
      const form = new FormData(); form.append('video', state.file); form.append('captions_json', JSON.stringify(state.captions)); form.append('language', $('#dubLanguage').value);
      const reference = $('#voiceReference').files[0]; if (reference) form.append('voice_reference', reference);
      const { job_id } = await api('/api/dub', { method: 'POST', body: form });
      const poll = async () => {
        const job = await api(`/api/jobs/${job_id}`); $('#dubStage').textContent = job.stage || 'Generating locally'; $('#dubPercent').textContent = `${job.progress || 0}%`; $('#dubProgressFill').style.transform = `scaleX(${Math.max(0, Math.min(100, Number(job.progress) || 0)) / 100})`;
        status.textContent = job.detail || job.eta || 'Generating voice locally…';
        if (job.status === 'done') { button.disabled = false; button.textContent = 'Generate another dub'; status.textContent = job.detail; location.href = job.download; return; }
        if (job.status === 'error') { button.disabled = false; button.textContent = 'Try dubbing again'; status.textContent = `${job.stage}: ${job.detail}`; return; }
        setTimeout(poll, 900);
      };
      poll();
    } catch (error) { button.disabled = false; button.textContent = 'Generate dubbed video'; status.textContent = error.message; progress.hidden = true; }
  });
  const gallery = document.createElement('dialog');
  gallery.className = 'effect-gallery';
  gallery.setAttribute('aria-labelledby', 'effectGalleryTitle');
  gallery.innerHTML = '<header class="gallery-head"><div><h2 id="effectGalleryTitle">Caption effects</h2><p>Choose a category, preview a treatment, then apply it across this project.</p></div><button type="button" class="ghost" id="closeEffectGallery" aria-label="Close effect library">Close</button></header><div class="gallery-controls"><label>Effect family<select id="effectCategory"><option value="all">All effects</option><option value="words">Word-synced</option><option value="entrance">Entrance</option><option value="reveal">Reveal</option><option value="clean">Clean captions</option></select></label><label class="gallery-search">Search<input id="effectSearch" type="search" placeholder="Try marker, spring, or glow"></label></div><div class="gallery-count" id="effectCount" aria-live="polite"></div><div class="gallery-body"><div class="gallery-grid" id="effectGrid"></div><aside class="effect-preview"><span class="preview-label">LIVE PREVIEW</span><div class="preview-stage"><span id="effectPreviewText">Stories deserve to be seen.</span></div><strong id="effectPreviewName">Choose an effect</strong><p id="effectPreviewNote">Your caption treatment will be previewed here.</p><button type="button" class="action" id="applyEffectAll" disabled>Apply to all captions</button><p class="apply-note">Effects are shared with every caption and the exported subtitle track.</p></aside></div>';
  document.body.append(gallery);
  const catalog = window.CAPTION_EFFECT_CATALOG || [];
  const grid = $('#effectGrid', gallery), effectSearch = $('#effectSearch', gallery), effectCount = $('#effectCount', gallery), effectCategory = $('#effectCategory', gallery);
  let pendingEffect = null;
  const family = motion => ['karaoke', 'pop'].includes(motion) ? 'words' : ['fade', 'slide', 'bounce', 'zoom', 'blur'].includes(motion) ? 'entrance' : motion === 'wipe' || motion === 'typewriter' ? 'reveal' : 'clean';
  function populateGallery(query = '') {
    const normalized = query.trim().toLowerCase();
    const filtered = catalog.filter(item => (effectCategory.value === 'all' || family(item.motion) === effectCategory.value) && `${item.name} ${item.note}`.toLowerCase().includes(normalized));
    effectCount.textContent = `${filtered.length} of ${catalog.length} combinations`;
    grid.replaceChildren(...filtered.map(item => {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'effect-card';
      button.dataset.motion = item.motion; button.dataset.accent = item.accent; button.setAttribute('aria-pressed', String(pendingEffect?.id === item.id));
      const accentClass = `fx-word current emphasis-${item.accent}${item.accent === 'marker' ? ' marker' : ''}${item.accent === 'underline' ? ' underline' : ''}${item.accent === 'color-scale' ? ' scale' : ''}`;
      button.innerHTML = `<span class="effect-card-swatch" style="--caption-highlight:#9bdcf4" aria-hidden="true"><i class="effect-swatch-word ${accentClass}">Caption</i></span><strong>${safeText(item.name)}</strong><small>${safeText(item.note)}</small>`;
      return button;
    }));
  }
  populateGallery();
  function previewEffect(item) {
    pendingEffect = item;
    populateGallery(effectSearch.value);
    $('#effectPreviewName').textContent = item.name; $('#effectPreviewNote').textContent = item.note;
    const preview = $('#effectPreviewText'); preview.className = `fx-${item.motion}`; preview.dataset.emphasis = item.accent;
    preview.style.setProperty('--caption-highlight', style.highlight);
    $('#applyEffectAll').disabled = false;
  }
  $('#openEffectGallery').addEventListener('click', () => {
    const activeEffect = catalog.find(item => item.motion === (style.effect || 'static') && item.accent === (style.emphasis || 'color'));
    if (activeEffect) previewEffect(activeEffect);
    gallery.showModal();
  });
  $('#closeEffectGallery').addEventListener('click', () => gallery.close());
  effectSearch.addEventListener('input', () => populateGallery(effectSearch.value));
  effectCategory.addEventListener('change', () => populateGallery(effectSearch.value));
  grid.addEventListener('click', event => {
    const button = event.target.closest('.effect-card'); if (!button) return;
    const selectedEffect = catalog.find(item => item.motion === button.dataset.motion && item.accent === button.dataset.accent);
    if (selectedEffect) previewEffect(selectedEffect);
  });
  $('#applyEffectAll').addEventListener('click', () => {
    if (!pendingEffect) return;
    $('#captionEffect').value = pendingEffect.motion; $('#wordEmphasis').value = pendingEffect.accent;
    $('#captionEffect').dispatchEvent(new Event('change', { bubbles: true }));
    $('#wordEmphasis').dispatchEvent(new Event('change', { bubbles: true }));
    gallery.close(); toast(`${pendingEffect.name} applied to all captions`);
  });
  const inspectorToggle = $('#inspectorToggle');
  const inspectorBreakpoint = window.matchMedia('(max-width: 940px)');
  function syncInspectorMotion() {
    if (!inspectorBreakpoint.matches) {
      inspector.inert = false;
      window.gsap?.set(inspector, { clearProps: 'transform,opacity,visibility' });
      return;
    }
    const open = inspector.classList.contains('v2-open');
    inspector.inert = !open;
    window.gsap?.set(inspector, { xPercent: open ? 0 : 104, autoAlpha: open ? 1 : 0 });
  }
  function setInspectorOpen(open) {
    inspector.classList.toggle('v2-open', open);
    inspectorToggle.setAttribute('aria-expanded', String(open));
    if (!inspectorBreakpoint.matches) { inspector.inert = false; return; }
    if (open) inspector.inert = false;
    if (window.gsap) {
      const duration = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : open ? .34 : .22;
      window.gsap.to(inspector, {
        xPercent: open ? 0 : 104, autoAlpha: open ? 1 : 0, duration,
        ease: open ? 'power3.out' : 'power2.in', overwrite: 'auto',
        onComplete: () => { if (!open) inspector.inert = true; }
      });
    } else {
      inspector.inert = !open;
    }
  }
  syncInspectorMotion();
  inspectorBreakpoint.addEventListener('change', syncInspectorMotion);
  inspectorToggle.addEventListener('click', () => setInspectorOpen(!inspector.classList.contains('v2-open')));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && inspector.classList.contains('v2-open')) {
      setInspectorOpen(false); inspectorToggle.focus();
    }
  });
  const translation = document.createElement('section');
  translation.className = 'translation-panel';
  translation.innerHTML = `<h2>Translate captions</h2><p class="motion-note">Translation runs locally. Download a model once; caption text stays on this computer.</p><label>Translation model<select id="translationProvider"><option value="ollama">Natural language · local LLM</option><option value="argos">Compact language pack · Argos</option></select></label><div class="v2-style-grid"><label>From<select id="translateSource"><option value="en">English</option><option value="de">German</option><option value="es">Spanish</option><option value="fr">French</option></select></label><label>To<select id="translateTarget"><option value="de">German</option><option value="en">English</option><option value="es">Spanish</option><option value="fr">French</option></select></label></div><label id="llmModelRow">Local LLM<select id="translationModel"><option value="qwen3.5:4b">Qwen 3.5 · 4B · 3.4 GB</option><option value="qwen3.5:9b">Qwen 3.5 · 9B · 6.6 GB</option><option value="qwen3.5:2b">Qwen 3.5 · 2B · 1.9 GB</option><option value="gemma3:4b">Gemma 3 · 4B · 3.3 GB</option></select></label><button id="downloadTranslationModel" class="wide ghost">Check local model</button><button id="translateCaptions" class="wide action">Translate naturally</button><button id="restoreSource" class="wide ghost" hidden>Restore source text</button><p id="translationStatus" class="motion-note" aria-live="polite"></p>`;
  const modelPanel = $('#modelPanel');
  inspector.insertBefore(translation, modelPanel || inspector.children[1] || null);
  $('#translateTarget').addEventListener('change', event => { if (!dubLanguageWasPicked) $('#dubLanguage').value = event.target.value; });

  function foldSection(section, expanded = false) {
    if (!section || section.classList.contains('job-panel') || section.dataset.foldReady) return;
    const heading = section.querySelector(':scope > h2');
    if (!heading) return;
    const title = heading.textContent.trim();
    const content = document.createElement('div'); content.className = 'section-fold-content';
    for (const child of [...section.children]) if (child !== heading) content.append(child);
    const toggle = document.createElement('button'); toggle.type = 'button'; toggle.className = 'section-fold-toggle';
    toggle.textContent = title; toggle.setAttribute('aria-expanded', String(expanded));
    toggle.setAttribute('aria-label', `${expanded ? 'Collapse' : 'Expand'} ${title}`);
    section.replaceChildren(toggle, content); section.dataset.foldReady = 'true';
    section.classList.toggle('is-collapsed', !expanded);
    toggle.addEventListener('click', () => {
      const open = section.classList.contains('is-collapsed');
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', `${open ? 'Collapse' : 'Expand'} ${title}`);
      if (!window.gsap || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        section.classList.toggle('is-collapsed', !open);
        return;
      }
      if (open) {
        section.classList.remove('is-collapsed');
        window.gsap.fromTo(content, { height: 0, autoAlpha: 0 }, {
          height: 'auto', autoAlpha: 1, duration: .24, ease: 'power3.out', overwrite: 'auto',
          clearProps: 'height,opacity,visibility'
        });
      } else {
        window.gsap.to(content, {
          height: 0, autoAlpha: 0, duration: .17, ease: 'power2.in', overwrite: 'auto',
          onComplete: () => { section.classList.add('is-collapsed'); window.gsap.set(content, { clearProps: 'height,opacity,visibility' }); }
        });
      }
    });
  }
  const foldSections = () => [...inspector.children].forEach((section, index) => foldSection(section, ['Selected caption','Video look'].includes(section.querySelector(':scope > h2')?.textContent.trim())));
  foldSections();
  new MutationObserver(foldSections).observe(inspector, { childList: true });
  function expandSection(section) {
    const toggle = section?.querySelector(':scope > .section-fold-toggle');
    if (toggle?.getAttribute('aria-expanded') !== 'true') toggle?.click();
  }

  let lastPreviewId = null;
  const setRange = (id, key, output, suffix = '') => {
    const input = $('#' + id), label = $('#' + output);
    if (!input) return;
    input.value = style[key];
    const apply = () => { style[key] = id === 'letterSpacing' ? Number(input.value) : Number(input.value); if (label) label.textContent = `${input.value}${suffix}`; paint(); renderPreview(); };
    input.addEventListener('input', apply);
    apply();
  };
  setRange('outlineWidth', 'outlineWidth', 'outlineValue');
  setRange('shadowDepth', 'shadow', 'shadowValue');
  setRange('panelRadius', 'radius', 'radiusValue', 'px');
  setRange('letterSpacing', 'letterSpacing', 'spacingValue', 'px');
  const outlinePicker = $('#outlineColor');
  const highlightPicker = $('#highlightColor');
  outlinePicker.value = style.outlineColor;
  highlightPicker.value = style.highlight;
  outlinePicker.addEventListener('input', () => { style.outlineColor = outlinePicker.value; renderPreview(); });
  highlightPicker.addEventListener('input', () => { style.highlight = highlightPicker.value; renderPreview(); });
  $('#captionEffect').addEventListener('change', e => { style.effect = e.target.value; renderPreview(true); });
  $('#effectSpeed').addEventListener('change', e => { style.speed = e.target.value; renderPreview(true); });
  $('#wordEmphasis').addEventListener('change', e => { style.emphasis = e.target.value; renderPreview(); });
  $('#wordsPerBeat').addEventListener('change', e => { style.wordsPerBeat = Math.max(1, Math.min(12, Number(e.target.value) || 5)); e.target.value = style.wordsPerBeat; });
  $('#captionAlign').addEventListener('change', e => { style.alignment = e.target.value; paint(); });
  $('#captionCase').addEventListener('change', e => { style.transform = e.target.value; paint(); });
  $('#lineHeight').addEventListener('input', e => { style.lineHeight = Number(e.target.value); $('#lineHeightValue').textContent = style.lineHeight.toFixed(2); paint(); });
  $('#paddingX').addEventListener('input', e => { style.paddingX = Number(e.target.value); paint(); });
  $('#paddingY').addEventListener('input', e => { style.paddingY = Number(e.target.value); paint(); });
  style.lineHeight = 1.18; style.paddingX = 12; style.paddingY = 6;
  document.querySelectorAll('[data-effect-preset]').forEach(button => button.addEventListener('click', () => {
    const presets = {
      cinematic: { effect: 'fade', speed: 'gentle', size: 42, weight: 600, color: '#ffffff', bg: '#111827', opacity: 72, outlineWidth: 1, shadow: 8, radius: 7, emphasis: 'none' },
      creator: { effect: 'pop', speed: 'snappy', size: 54, weight: 800, color: '#ffffff', bg: '#111827', opacity: 0, outlineWidth: 4, shadow: 12, radius: 0, emphasis: 'color-scale' },
      karaoke: { effect: 'karaoke', speed: 'snappy', size: 48, weight: 800, color: '#ffffff', bg: '#111827', opacity: 0, outlineWidth: 3, shadow: 10, radius: 0, emphasis: 'color' },
    };
    Object.assign(style, presets[button.dataset.effectPreset]);
    const ids = { fontSize: 'size', fontWeight: 'weight', textColor: 'color', backgroundColor: 'bg', backgroundOpacity: 'opacity', captionEffect: 'effect', effectSpeed: 'speed', wordEmphasis: 'emphasis' };
    for (const [id, key] of Object.entries(ids)) { const input = $('#' + id); if (input) input.value = style[key]; }
    outlinePicker.value = style.outlineColor; highlightPicker.value = style.highlight;
    $('#fontSizeValue').textContent = style.size; $('#opacityValue').textContent = `${style.opacity}%`;
    $('#outlineWidth').value = style.outlineWidth; $('#shadowDepth').value = style.shadow; $('#panelRadius').value = style.radius; $('#letterSpacing').value = style.letterSpacing;
    $('#outlineValue').textContent = style.outlineWidth; $('#shadowValue').textContent = style.shadow; $('#radiusValue').textContent = style.radius; $('#spacingValue').textContent = style.letterSpacing;
    paint(); renderPreview(true); toast(`${button.textContent} style applied`);
  }));

  function renderPreview(restart = false) {
    const caption = active();
    const effect = style.effect || 'static';
    if (caption?.id !== lastPreviewId) { restart = true; lastPreviewId = caption?.id ?? null; }
    const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    overlay.classList.remove('fx-static', 'fx-pop', 'fx-typewriter', 'fx-fade', 'fx-slide', 'fx-bounce', 'fx-karaoke', 'fx-zoom', 'fx-blur', 'fx-wipe');
    overlay.style.setProperty('--caption-outline', `${style.outlineWidth}px ${style.outlineColor}`);
    overlay.style.setProperty('--caption-shadow', `${style.shadow}px`);
    overlay.style.setProperty('--caption-radius', `${style.radius}px`);
    overlay.style.setProperty('--caption-highlight', style.highlight);
    overlay.style.setProperty('--effect-duration', style.speed === 'snappy' ? '180ms' : style.speed === 'gentle' ? '560ms' : '320ms');
    overlay.style.letterSpacing = `${style.letterSpacing}px`;
    if (!caption) { overlay.textContent = 'Your caption will appear here'; return; }
    const words = caption.words || [];
    const now = Number(video.currentTime) || 0;
    const current = words.findIndex(word => now >= Number(word.start) && now <= Number(word.end));
    if (effect === 'typewriter' && !reduced) {
      if (words.length) {
        overlay.innerHTML = words.map(word => now >= Number(word.start) ? safeText(word.word || word.text || '') : '').filter(Boolean).join(' ');
        overlay.classList.toggle('has-spoken-word', current >= 0);
      } else {
        const fraction = Math.max(0, Math.min(1, (now - caption.start) / Math.max(.1, caption.end - caption.start)));
        const count = Math.ceil(caption.text.length * fraction);
        overlay.textContent = caption.text.slice(0, count);
      }
    } else if (words.length > 0 && !reduced) {
      overlay.innerHTML = words.map((word, index) => `<span class="fx-word${index === current ? ` current emphasis-${style.emphasis}` : ''}${style.emphasis === 'marker' && index === current ? ' marker' : ''}${style.emphasis === 'underline' && index === current ? ' underline' : ''}${style.emphasis === 'color-scale' && index === current ? ' scale' : ''}">${safeText(word.word || word.text || '')}</span>`).join(' ');
    } else overlay.textContent = caption.text;
    if (!reduced) {
      overlay.classList.add(`fx-${effect === 'pop' && !words.length ? 'bounce' : effect}`);
    }
    if (restart && !reduced) { overlay.style.animation = 'none'; void overlay.offsetWidth; overlay.style.animation = ''; }
  }
  video.addEventListener('timeupdate', () => renderPreview());
  const originalPaint = paint;
  window.addEventListener('resize', renderPreview);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) renderPreview(); });
  void originalPaint;
  renderPreview();

  let languageCatalog = null;
  let ollamaCatalog = null;
  function fillLanguageChoices(catalog) {
    const labels = new Map();
    [...catalog.available, ...catalog.installed].forEach(pair => { labels.set(pair.from, pair.from_name || pair.from); labels.set(pair.to, pair.to_name || pair.to); });
    const sources = $('#translateSource'), targets = $('#translateTarget');
    const currentSource = sources.value, currentTarget = targets.value;
    const options = [...labels].sort((a, b) => a[1].localeCompare(b[1]));
    for (const select of [sources, targets]) {
      select.replaceChildren(...options.map(([code, name]) => { const option = document.createElement('option'); option.value = code; option.textContent = name; return option; }));
    }
    if (labels.has(currentSource)) sources.value = currentSource;
    if (labels.has(currentTarget)) targets.value = currentTarget;
  }
  const providerSelect = $('#translationProvider');
  const modelRow = $('#llmModelRow');
  const downloadModelButton = $('#downloadTranslationModel');
  let speechLanguages = [];
  function configureTranslationProvider() {
    const useOllama = providerSelect.value === 'ollama';
    modelRow.hidden = !useOllama;
    downloadModelButton.hidden = !useOllama;
    $('#translateCaptions').textContent = useOllama ? 'Translate naturally' : 'Translate with Argos';
    $('#translationStatus').textContent = useOllama ? 'Ollama must be installed and running locally for the natural language model.' : 'Argos language packs are compact and work offline after download.';
    fillLLMLanguages();
  }
  function fillLLMLanguages() {
    const names = speechLanguages.length ? speechLanguages.map(({code, name}) => [code, name]) : [['en','English'],['de','German'],['es','Spanish'],['fr','French']];
    const current = [$('#translateSource').value, $('#translateTarget').value];
    for (const select of [$('#translateSource'), $('#translateTarget')]) {
      select.replaceChildren(...names.map(([code, name]) => { const option = document.createElement('option'); option.value = code; option.textContent = name; return option; }));
    }
    $('#translateSource').value = current[0]; $('#translateTarget').value = current[1];
  }
  providerSelect.addEventListener('change', configureTranslationProvider);
  configureTranslationProvider();
  api('/api/languages').then(catalog => {
    speechLanguages = catalog.languages || [];
    if (!speechLanguages.length) return;
    const language = $('#language'), selected = language.value;
    language.replaceChildren(new Option('Auto-detect', ''), ...speechLanguages.map(item => new Option(item.name, item.code)));
    if (speechLanguages.some(item => item.code === selected)) language.value = selected;
    fillLLMLanguages();
  }).catch(() => {});
  $('#translationModel').addEventListener('change', () => { ollamaCatalog = null; });
  downloadModelButton.addEventListener('click', async () => {
    const button = downloadModelButton, status = $('#translationStatus'), model = $('#translationModel').value;
    button.disabled = true;
    try {
      ollamaCatalog = await api('/api/translation/models');
      if (!ollamaCatalog.available) throw new Error('Ollama is not running. Install Ollama, then reopen this panel.');
      const installed = ollamaCatalog.installed.some(name => name === model || name.startsWith(`${model}-`));
      if (installed) { status.textContent = `${model} is ready locally. GPU ${ollamaCatalog.gpu_vram_gb || '?'} GB VRAM detected.`; button.textContent = 'Model ready'; button.disabled = false; return; }
      status.textContent = `Downloading ${model} (${ollamaCatalog.catalogue[model].size}). This is a one-time local download.`;
      button.textContent = 'Downloading…';
      const { job_id } = await api('/api/translation/models/pull', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ model }) });
      const poll = async () => {
        const job = await api(`/api/jobs/${job_id}`);
        status.textContent = job.detail ? `${job.stage}: ${job.detail}` : job.stage;
        button.textContent = `${job.progress || 0}%`;
        if (job.status === 'done') { ollamaCatalog = null; button.textContent = 'Model ready'; status.textContent = `${model} is ready for local translation.`; button.disabled = false; }
        else if (job.status === 'error') { button.disabled = false; button.textContent = 'Retry download'; status.textContent = job.detail || job.stage; }
        else setTimeout(poll, 1000);
      };
      poll();
    } catch (error) { button.disabled = false; button.textContent = 'Check local model'; status.textContent = error.message; }
  });
  $('#translateCaptions').addEventListener('click', async () => {
    const button = $('#translateCaptions'), status = $('#translationStatus');
    const source = $('#translateSource').value, target = $('#translateTarget').value;
    if (!state.captions.length) { status.textContent = 'Add or import captions first.'; return; }
    if (source === target) { status.textContent = 'Choose two different languages.'; return; }
    button.disabled = true;
    try {
      const provider = providerSelect.value;
      if (provider === 'argos') {
        status.textContent = 'Checking local language models…';
        languageCatalog ||= await api('/api/translation/languages');
        fillLanguageChoices(languageCatalog);
        const installed = languageCatalog.installed.some(pair => pair.from === source && pair.to === target);
        if (!installed) {
          const available = languageCatalog.available.some(pair => pair.from === source && pair.to === target);
          if (!available) throw new Error('This language pair is not listed in the local model catalog.');
          status.textContent = 'Downloading this language pair once…';
          await api('/api/translation/install', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ source, target }) });
          languageCatalog = null;
        }
      } else {
        status.textContent = 'Checking local LLM…';
        ollamaCatalog ||= await api('/api/translation/models');
        if (!ollamaCatalog.available) throw new Error('Start Ollama and download a model first.');
        const model = $('#translationModel').value;
        if (!ollamaCatalog.installed.some(name => name === model || name.startsWith(`${model}-`))) throw new Error(`Download ${model} first using the model button above.`);
      }
      status.textContent = provider === 'ollama' ? 'Translating with the local language model…' : 'Translating locally…';
      const model = $('#translationModel').value;
      const result = await api('/api/translation/translate', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ captions: state.captions, source, target, provider, model, source_name: $('#translateSource').selectedOptions[0].text, target_name: $('#translateTarget').selectedOptions[0].text }) });
      state.captions = result.captions.map((caption, index) => ({ ...caption, translationSource: state.captions[index]?.translationSource || state.captions[index]?.text }));
      render(); renderPreview(true);
      status.textContent = `Translated ${result.captions.length} captions to ${target.toUpperCase()}.`;
      $('#restoreSource').hidden = false;
    } catch (error) { status.textContent = error.message; }
    finally { button.disabled = false; }
  });
  $('#restoreSource').addEventListener('click', () => {
    state.captions = state.captions.map(caption => { const { translationSource, ...rest } = caption; return translationSource == null ? rest : { ...rest, text: translationSource }; });
    render(); renderPreview(true); $('#restoreSource').hidden = true; $('#translationStatus').textContent = 'Source text restored.';
  });

  const formatMenu = document.createElement('select');
  formatMenu.id = 'subtitleExportFormat';
  formatMenu.setAttribute('aria-label', 'Subtitle file format');
  formatMenu.innerHTML = '<option value="srt">SRT · universal</option><option value="vtt">WebVTT · web</option><option value="ass">ASS · styled + motion</option>';
  const exportButton = $('#exportSrt');
  exportButton.before(formatMenu);
  exportButton.textContent = 'Download subtitles';
  exportButton.addEventListener('click', async event => {
    event.stopImmediatePropagation();
    if (!state.captions.length) return toast('Add or import captions before exporting');
    try {
      const result = await api('/api/export/subtitles', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ captions: state.captions, style, format: formatMenu.value }) });
      location.href = result.download; toast(`${result.format.toUpperCase()} subtitle file downloaded`);
    } catch (error) { toast(error.message); }
  }, true);
  const installTrackExport = () => {
    const deliveryActions = $('.delivery-actions');
    if (!deliveryActions) { setTimeout(installTrackExport, 50); return; }
    const containerSelect = document.createElement('select');
    containerSelect.id = 'subtitleTrackContainer'; containerSelect.setAttribute('aria-label', 'Subtitle track container');
    containerSelect.innerHTML = '<option value="mkv">MKV · styled track</option><option value="mp4">MP4 · portable text track</option>';
    const trackButton = document.createElement('button');
    trackButton.id = 'exportTrack'; trackButton.className = 'delivery-secondary'; trackButton.textContent = 'Add selectable subtitle track';
    deliveryActions.append(containerSelect, trackButton);
    trackButton.addEventListener('click', async () => {
      if (!state.file) return toast('Choose a video before adding a subtitle track');
      if (!state.captions.length) return toast('Add or import captions before adding a track');
      const chosen = containerSelect.value;
      const form = new FormData(); form.append('video', state.file); form.append('captions_json', JSON.stringify(state.captions)); form.append('style_json', JSON.stringify(style)); form.append('container', chosen);
      trackButton.disabled = true; trackButton.textContent = 'Preparing track…';
      try {
        const { job_id } = await fetch('/api/export/mux', { method: 'POST', body: form }).then(async response => { const value = await response.json(); if (!response.ok) throw new Error(value.detail || response.statusText); return value; });
        const poll = async () => {
          const job = await api(`/api/jobs/${job_id}`);
          trackButton.textContent = job.status === 'working' ? `${job.stage} · ${job.progress}%` : job.stage;
          if (job.status === 'done') { location.href = job.download; toast(`${chosen.toUpperCase()} subtitle track downloaded`); trackButton.disabled = false; trackButton.textContent = 'Add selectable subtitle track'; }
          else if (job.status === 'error') { trackButton.disabled = false; trackButton.textContent = 'Add selectable subtitle track'; toast(job.detail || job.stage); }
          else setTimeout(poll, 900);
        };
        poll();
      } catch (error) { trackButton.disabled = false; trackButton.textContent = 'Add selectable subtitle track'; toast(error.message); }
    });
  };
  installTrackExport();

  setTimeout(async () => {
    try {
      const health = await api('/api/health');
      const select = $('#modelChoice');
      if (select) {
        const memory = Number(health.gpu_vram_gb) || 0;
        const best = memory >= 20 ? 'large-v3' : memory >= 8 ? 'turbo' : memory >= 5 ? 'medium' : memory >= 2 ? 'small' : 'base';
        select.value = best;
        const status = $('#whisperStatus');
        if (status) status.textContent = `GPU ${memory ? `${memory} GB VRAM` : 'not detected'} · ${best} recommended`;
      }
    } catch {}
  }, 1100);
})();
