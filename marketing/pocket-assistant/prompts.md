# Art brief and generation prompts — PhoneKit "Pocket Assistant"

This file records the exact creative intent and prompts for any future
image-generation pass. The rendered SVG artwork in `artwork/` is the current
approved editorial direction; these prompts describe the *photoreal* scene the
same brief would call for when a capable generator is available. A generated
image is never evidence that a product capability exists.

## Vibe (approved)

**Art direction #2 — "Everyday companion / warm human."** A lived-in evening
scene, a warm reading light, an e-ink reading device held in a hand. Calm and
grounded, not futuristic. Warm low light, soft shadows, believable hands and
posture, natural adult proportions.

## Core metaphor

The e-ink reader is already the calm object people curl up with at night.
The scene shows that same calm object now doing a little useful work: a page
of a pocket assistant on the e-ink screen, next to a warm lamp, held by a
relaxed hand. The copy reserves the negative space.

## Palette

- Warm evening neutrals: deep charcoal, warm taupe, soft cream.
- A single warm accent: warm amber lamp glow (approx `#E8A95B`) against cool
  e-ink grey (approx `#9AA0A6` on `#F2EFEA`).
- Background dusk-to-lamp gradient, dark enough for the light to read.

## Composition for each format

- **Hero (1600x900):** wide. Reader + hand on a desk to the right of center,
  lamp glow from upper left, generous negative space top-left for the tagline.
- **Feed (1080x1350):** portrait. Reader and hand centered in the lower two
  thirds, lamp glow above, tagline across the wide top band.
- **Story (1080x1920):** tall. Vertical layout, reader + hand lower, lamp and
  dusk across the top, tagline near the middle with thumb-zone-safe margins.
- **README banner (1600x400):** short and wide. A single warm strip, small
  reader glyph + lamp on the left, the tagline on the right, nothing full-bleed.

## Not to include (guardrail)

- No marketing text baked into the raster art (the SVG adds text
  deterministically; a generated master must ship text-free).
- No visible logo, no fake interface chrome, no readable fake UI.
- No children, no extreme styling, no sci-fi, no phone-in-hand confusion.
  If any device is shown, the silhouette reads e-ink (paper-white screen,
  no backlight), not a smartphone.
- No people who look like they are being surveilled, and nothing that implies
  private credentials.

## Photoreal generation prompts (for a capable raster generator)

### Hero (landscape 1600x900)
> A calm editorial photograph-style image. A person's relaxed hand holds a
> slim white e-ink reading device over a wooden desk in the evening. A warm
> amber reading lamp on the left casts soft light onto the screen and the
> desk. Deep dusk-blue window light on the right. The device screen shows a
> simple monochrome list, softly blurred. Warm taupe and charcoal palette,
> cream highlights, shallow depth of field, genuine gentle mood, natural hand
> anatomy, no text, no logos, no phones. Editorial, understated.

### Feed (portrait 1080x1350)
> A warm editorial image. Close crop of the same scene: an e-ink reader held
> in a calm hand, warm lamp glow from above, dusk settling outside a window.
> Monochrome e-ink screen softly blurred. Soft focus, warm amber and charcoal
> tones, natural believable hand, no text, no logos, no phone, serene mood.

### Story (vertical 1080x1920)
> A vertical editorial image. From the top: a dusky window with warm lamp
> glow, descending to a desk where a relaxed hand holds a slim white e-ink
> reader. Generous clean space near the vertical center. Warm, calm, dim,
> natural hand, no text, no logos, no phone, no face visible.

### README banner (wide 1600x400, short strip)
> A very wide, short editorial strip. Left: a small e-ink reader glyph and a
> warm lamp on the edge of a desk. Right: calm empty space for a one-line
> tagline. Warm charcoal and cream, one amber glow. Simple, quiet, no text,
> no logos.

## Current rendered deliverable

Because no raster generator is available in this environment, the shipped kit
uses **hand-composed SVG** of the same brief in `artwork/`. These prompts are
kept for a future photoreal pass and are explicitly marked as non-final in the
manifest.