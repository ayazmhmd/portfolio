// Click any .zoomable figure to open it full size with its caption and description.
(function () {
  var box = document.getElementById('lightbox');
  if (!box) return;
  var items = Array.prototype.slice.call(document.querySelectorAll('.zoomable'));
  if (!items.length) return;
  var media = box.querySelector('.lb-media');
  var cap = box.querySelector('.lb-caption');
  var desc = box.querySelector('.lb-desc');
  var count = box.querySelector('.lb-count');
  var current = 0, lastFocus = null;

  function paragraphs(text) {
    var out = document.createDocumentFragment();
    text.split(/\n\s*\n/).forEach(function (t) {
      if (!t.trim()) return;
      var p = document.createElement('p');
      p.textContent = t.trim();
      out.appendChild(p);
    });
    return out;
  }

  function show(i) {
    current = (i + items.length) % items.length;
    var el = items[current];
    media.innerHTML = '';
    if (el.dataset.full) {
      var img = document.createElement('img');
      img.src = el.dataset.full;
      img.alt = el.dataset.caption || '';
      media.appendChild(img);
    } else {
      var svg = el.querySelector('svg');
      var wrap = document.createElement('div');
      wrap.className = 'svgwrap';
      if (svg) wrap.appendChild(svg.cloneNode(true));
      media.appendChild(wrap);
    }
    cap.textContent = el.dataset.caption || '';
    desc.innerHTML = '';
    if (el.dataset.desc) desc.appendChild(paragraphs(el.dataset.desc));
    count.textContent = items.length > 1 ? (current + 1) + ' of ' + items.length + ' · use ← → keys' : '';
    box.querySelector('.lb-prev').hidden = box.querySelector('.lb-next').hidden = items.length < 2;
  }

  function open(i) {
    lastFocus = document.activeElement;
    show(i);
    box.hidden = false;
    document.body.style.overflow = 'hidden';
    box.querySelector('.lb-close').focus();
  }

  function close() {
    box.hidden = true;
    document.body.style.overflow = '';
    if (lastFocus) lastFocus.focus();
  }

  items.forEach(function (el, i) {
    el.addEventListener('click', function () { open(i); });
    el.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(i); }
    });
  });
  box.querySelector('.lb-close').addEventListener('click', close);
  box.querySelector('.lb-prev').addEventListener('click', function () { show(current - 1); });
  box.querySelector('.lb-next').addEventListener('click', function () { show(current + 1); });
  box.addEventListener('click', function (e) { if (e.target === box) close(); });
  document.addEventListener('keydown', function (e) {
    if (box.hidden) return;
    if (e.key === 'Escape') close();
    if (e.key === 'ArrowLeft') show(current - 1);
    if (e.key === 'ArrowRight') show(current + 1);
  });
})();
