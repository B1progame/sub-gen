/* 10 motion behaviors × 9 live-word treatments = 90 selectable combinations. */
(() => {
  const motions = [
    ['static', 'Pure', 'A clean, steady caption'],
    ['karaoke', 'Karaoke', 'Word-timed light sweep'],
    ['pop', 'Pop', 'Short scale accent'],
    ['typewriter', 'Type-on', 'Progressive text reveal'],
    ['fade', 'Dissolve', 'Soft opacity entrance'],
    ['slide', 'Lift', 'Rising entrance'],
    ['bounce', 'Spring settle', 'Soft spring entrance'],
    ['zoom', 'Focus', 'Cinematic scale and settle'],
    ['blur', 'Defocus', 'Sharpens into view'],
    ['wipe', 'Wipe', 'Clipped reveal from the edge'],
  ];
  const accents = [
    ['color', 'Luminous color'],
    ['color-scale', 'Color + scale'],
    ['marker', 'Marker sweep'],
    ['underline', 'Drawn underline'],
    ['outline', 'Outline pulse'],
    ['capsule', 'Glass capsule'],
    ['italic', 'Slanted focus'],
    ['tracking', 'Letter spread'],
    ['none', 'No word accent'],
  ];
  window.CAPTION_EFFECT_CATALOG = motions.flatMap(([motion, motionName, motionNote]) =>
    accents.map(([accent, accentName]) => ({
      id: `${motion}-${accent}`,
      motion,
      accent,
      name: `${motionName} · ${accentName}`,
      note: `${motionNote} with ${accentName.toLowerCase()}`,
    })),
  );
})();
