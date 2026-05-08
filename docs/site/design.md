---
version: alpha
name: CortexSync Signal Flow
description: A cinematic dark landing-page system for authsome site experiments, inspired by the CortexSync / NeuroSync hero treatment.
colors:
  primary: "#FFFFFF"
  secondary: "#B4B5BD"
  tertiary: "#CC8066"
  neutral: "#09090B"
  neutral-soft: "#1F1F22"
  neutral-steel: "#334155"
  surface-glass: "#FFFFFF08"
  surface-border: "#FFFFFF26"
  overlay-left: "#09090BE6"
  overlay-mid: "#09090B66"
  glow-cool: "#0B101D"
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 72px
    fontWeight: 500
    lineHeight: 1.05
    letterSpacing: -0.04em
  display-md:
    fontFamily: Inter
    fontSize: 60px
    fontWeight: 500
    lineHeight: 1.05
    letterSpacing: -0.04em
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: -0.02em
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: -0.01em
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: -0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: -0.01em
  nav-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.2
    letterSpacing: -0.01em
rounded:
  sm: 0px
  md: 4px
  lg: 8px
  xl: 12px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  2xl: 40px
  3xl: 64px
  4xl: 96px
  gutter: 32px
  section-max-width: 1600px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.neutral}"
    rounded: "{rounded.sm}"
    paddingInline: 20px
    paddingBlock: 6px
  button-primary-icon:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.primary}"
    rounded: "{rounded.sm}"
    size: 36px
  card-feature:
    backgroundColor: "{colors.surface-glass}"
    borderColor: "{colors.surface-border}"
    rounded: "{rounded.lg}"
    backdropBlur: 12px
    padding: 20px
  nav-link:
    textColor: "{colors.secondary}"
    textColorHover: "{colors.primary}"
  hero-copy:
    textColor: "{colors.secondary}"
    maxWidth: 32rem
---

# CortexSync Signal Flow

## Overview

This system is built for high-drama product marketing pages that should feel cerebral, precise, and slightly futuristic without drifting into neon sci-fi camp. The visual mood is dark and immersive: a black architectural stage, fast streaks of light, frosted utility cards, and oversized editorial typography that feels confident rather than flashy.

The intended emotional response is focused acceleration. The interface should suggest that the product turns complexity into clarity, so the page needs to feel technically advanced, premium, and calm under pressure. Copy and layout should avoid clutter. Every element must support the sense that the product is already moving faster than the user.

## Colors

The palette is anchored in deep near-black neutrals with white as the main contrast driver. Warm copper and cool steel highlights provide the motion signature inside the background trails and accent moments. Glass panels should feel atmospheric, not decorative.

- **Primary (#FFFFFF):** Pure white for key text, buttons, icon strokes, and the brightest points of emphasis.
- **Secondary (#B4B5BD):** Soft cool gray for supporting copy, navigation, and reduced-emphasis text.
- **Tertiary (#CC8066):** Warm copper accent used inside glow trails or small highlight moments, not as a broad UI fill.
- **Neutral (#09090B):** The page foundation. It should dominate the canvas and create a theatrical stage for the lighter content.
- **Neutral Soft (#1F1F22):** A lifted dark surface for subtle depth transitions and inactive dark fills.
- **Neutral Steel (#334155):** A cool structural tone used inside the motion layer and for restrained atmospheric contrast.
- **Surface Glass (#FFFFFF08):** Transparent white wash for frosted cards and subtle layered surfaces.
- **Surface Border (#FFFFFF26):** Hairline border tone for glass cards and restrained separators.

## Typography

Typography is intentionally spare. The system relies on one sans family, **Inter**, and extracts hierarchy through scale, weight, and tracking rather than mixing many typefaces. Headlines should feel monumental and smooth. Supporting text should remain crisp and understated.

- **Display:** Large, tightly tracked, two-line headlines with a mix of regular and medium weights. The first line may be slightly softer in tone than the second to create visual sequencing.
- **Headline:** Short card titles and section anchors should be compact, medium-weight, and clean.
- **Body:** Product explanation copy should be airy and readable, never dense.
- **Navigation and labels:** Small and neutral, with just enough contrast to stay legible over a complex background.

## Layout

The layout is a single-screen hero composition with a cinematic horizon line. Content sits inside a wide desktop frame with generous outer padding and strong left-right tension: large headline and stacked feature cards on one side, explanatory copy and CTA on the other.

Use a simple responsive rule set:

- On desktop, favor a wide container capped around `{spacing.section-max-width}` with large top breathing room and a bottom-aligned content cluster.
- On tablet and mobile, collapse into a single-column flow while preserving the dramatic headline and glass-card stack.
- Maintain a clear foreground-versus-background split. The motion layer is environmental; the content layer must remain readable at all times through dark gradients and tonal overlays.

Spacing should feel architectural rather than soft. Use the 8px-derived scale with larger jumps for hero spacing. Large negative space is part of the brand voice.

## Elevation & Depth

Depth comes from contrast, blur, bloom, and atmospheric layering instead of heavy drop shadows. The background should feel like a tunnel of light receding into darkness. Foreground surfaces float above it through translucent fills, faint borders, and soft blur.

When adding depth:

- Prefer backdrop blur and tonal separation over large opaque panels.
- Let the brightest whites appear in text and call-to-action surfaces.
- Use glow and bloom in the environment layer, not as a default treatment on UI components.

## Shapes

The shape language is disciplined and nearly square. Containers and buttons should feel engineered, not bubbly. Most corners are sharp or only lightly softened.

- Primary controls should use square or near-square corners.
- Feature cards may use a slightly larger radius to support the frosted-glass treatment.
- Icon containers inside CTAs should read like inset modules: compact black squares nested inside white buttons.

## Components

**Buttons**

Primary buttons are white capsules with black text and a separate dark icon tile on the trailing edge. They should feel like compact control modules rather than pill-shaped SaaS buttons. Keep padding restrained and the silhouette crisp.

**Navigation**

Navigation is lightweight and quiet. Links should sit near the top center or top right, using secondary text until hover elevates them to white.

**Feature cards**

Feature cards are translucent dark-glass slabs with thin luminous borders. They use a left-aligned icon, a concise title, and one line of supporting text. Hover movement should be minimal, such as a slight horizontal drift or opacity lift.

**Hero copy**

Longer explanatory text should stay in a narrow measure and use secondary contrast so the headline remains dominant.

**Background motion**

The signature visual is a field of linear light trails and bloom moving through a black 3D space. Motion should feel smooth and continuous, not noisy. Any animation added elsewhere should defer to this primary environmental effect.

## Do's and Don'ts

**Do**

- Use deep blacks and restrained grays as the structural base.
- Let white typography do most of the persuasive work.
- Preserve the cinematic contrast between the atmospheric background and the sharp foreground UI.
- Keep CTA styling modular: bright outer shell, dark inset icon block.
- Favor minimal, meaningful motion such as line reveals, slow drift, and ambient light travel.

**Don't**

- Don’t introduce colorful gradients across buttons, cards, or text.
- Don’t round everything into soft consumer-SaaS shapes.
- Don’t fill the page with multiple competing accent colors.
- Don’t use dense paragraphs or crowded grids that weaken the hero composition.
- Don’t make glass panels too opaque; they should feel spectral, not solid.
