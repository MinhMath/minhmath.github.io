"""Accessible, self-contained map of places confirmed by the author."""
import json
import hashlib
from html import escape
from pathlib import Path


def meetings_map():
    root = Path(__file__).resolve().parents[1]
    places = json.loads((root / 'data/visited-places.json').read_text())
    markers, options = [], []
    for i, place in enumerate(places):
        x = (place['longitude'] + 180) * 1000 / 360
        y = (90 - place['latitude']) * 500 / 180
        label = place['name'] + (' (country-level marker)' if place.get('scope') == 'country' else '')
        markers.append(f'<g class="travel-pin" data-place="{i}" data-x="{x:.3f}" data-y="{y:.3f}" role="button" tabindex="0" aria-label="{escape(label)}" transform="translate({x:.3f} {y:.3f})"><title>{escape(label)}</title><circle class="travel-hit" r="9"/><circle class="travel-dot" r="3.2"/></g>')
        options.append(f'<option value="{i}">{escape(label)}</option>')
    revision = hashlib.sha256((root / 'docs/assets/travel-map.js').read_bytes()).hexdigest()[:12]
    return f'''<figure class="travel-map" aria-label="Places I have been">
 <div class="travel-map-toolbar">
  <div class="travel-map-views" role="group" aria-label="Map region">
   <button type="button" data-map-view="world" aria-pressed="true">World</button>
   <button type="button" data-map-view="europe" aria-pressed="false">Europe</button>
   <button type="button" data-map-view="asia" aria-pressed="false">East &amp; Southeast Asia</button>
   <button type="button" data-map-view="vietnam" aria-pressed="false">Vietnam</button>
  </div>
  <label class="visually-hidden" for="travel-place">Choose a place</label>
  <select id="travel-place"><option value="">Choose a place</option>{''.join(options)}</select>
 </div>
 <svg class="travel-map-canvas" viewBox="0 15 1000 450" role="group" aria-label="World map of visited places">
  <image href="assets/world-land.svg" width="1000" height="500"/>
  {''.join(markers)}
 </svg>
 <figcaption><span class="travel-map-caption" aria-live="polite">Places I’ve lived, studied or visited. Select a point to see the place.</span><a class="travel-map-credit" href="https://www.naturalearthdata.com/" target="_blank" rel="noopener">Map: Natural Earth</a></figcaption>
</figure><script defer src="assets/travel-map.js?v={revision}"></script>'''
