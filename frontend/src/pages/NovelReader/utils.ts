export const focusReaderPosition = (position: number) => {
  const fid = requestAnimationFrame(() => {
    const el = document.getElementById('chapter-content');
    if (!el) return;

    const childEl = el.children[position];
    if (!childEl) return;

    childEl.scrollIntoView({
      behavior: 'smooth',
      inline: 'center',
      block: 'center',
    });
  });
  return () => cancelAnimationFrame(fid);
};
