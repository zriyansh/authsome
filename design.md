---
version: beta
name: authsome
description: A cinematic dark design system for authsome, the local authentication layer for AI agents. It uses sharp glass surfaces, precise white ink, and a balanced signal field of copper, electric blue, steel, and darker falloff tones to express trustworthy credential orchestration.
colors:
  primary: "#FFFFFF"
  on-primary: "#09090B"
  secondary: "#B4B5BD"
  muted: "#71717A"
  neutral: "#09090B"
  neutral-soft: "#1F1F22"
  surface: "#000000"
  surface-raised: "#111318"
  surface-glass: "#FFFFFF08"
  surface-glass-strong: "#FFFFFF12"
  surface-border: "#FFFFFF26"
  copper: "#CC8066"
  copper-deep: "#4A241D"
  electric-blue: "#6D8FD6"
  blue-soft: "#3B5F9F"
  blue-deep: "#172A4A"
  steel: "#334155"
  steel-deep: "#162033"
  overlay-left: "#09090BE6"
  overlay-bottom: "#09090BFA"
  glow-cool: "#0B101D"
  glow-blue: "#5B7CBE"
  glow-copper: "#CC8066"
  success: "#8FD7A4"
  warning: "#E7B66A"
  danger: "#F18A8A"
typography:
  display-xl:
    fontFamily: Inter
    fontSize: 72px
    fontWeight: 500
    lineHeight: 1.05
    letterSpacing: -0.04em
  display-lg:
    fontFamily: Inter
    fontSize: 60px
    fontWeight: 500
    lineHeight: 1.05
    letterSpacing: -0.04em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: 500
    lineHeight: 1.18
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: 500
    lineHeight: 1.25
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: 500
    lineHeight: 1.25
    letterSpacing: 0
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: 0
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: 0
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: 0
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: 0
  label-caps:
    fontFamily: Inter
    fontSize: 10px
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: 0.24em
rounded:
  none: 0px
  sm: 2px
  md: 4px
  lg: 8px
  full: 9999px
spacing:
  unit: 8px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  2xl: 40px
  3xl: 64px
  4xl: 96px
  page-padding-sm: 24px
  page-padding-md: 40px
  page-padding-lg: 48px
  section-max-width: 1600px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label-md}"
    rounded: "{rounded.none}"
    padding: 6px 6px 6px 24px
  button-primary-icon:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.primary}"
    rounded: "{rounded.none}"
    size: 36px
  button-secondary:
    backgroundColor: transparent
    textColor: "{colors.secondary}"
    borderColor: "{colors.surface-border}"
    typography: "{typography.label-md}"
    rounded: "{rounded.sm}"
    padding: 10px 16px
  nav-link:
    textColor: "{colors.secondary}"
    textColorHover: "{colors.primary}"
    typography: "{typography.body-sm}"
  card-glass:
    backgroundColor: "{colors.surface-glass}"
    borderColor: "{colors.surface-border}"
    textColor: "{colors.primary}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    padding: 20px
  card-authsome-core:
    backgroundColor: "{colors.surface-glass-strong}"
    borderColor: "{colors.electric-blue}"
    accentColor: "{colors.copper}"
    textColor: "{colors.primary}"
    rounded: "{rounded.sm}"
    padding: 24px
  badge-provider:
    backgroundColor: "{colors.surface-glass}"
    textColor: "{colors.secondary}"
    borderColor: "{colors.surface-border}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.sm}"
    padding: 4px 8px
  hero-copy:
    textColor: "{colors.secondary}"
    typography: "{typography.body-lg}"
    maxWidth: 34rem
  signal-field:
    colors:
      - "{colors.electric-blue}"
      - "{colors.copper}"
      - "{colors.steel}"
      - "{colors.primary}"
      - "{colors.blue-deep}"
      - "{colors.copper-deep}"
      - "{colors.steel-deep}"
    blendMode: additive
    glow: mixed
    role: environmental-depth
---

# authsome

## Brand & Style

authsome is the local auth layer for AI agents, so the interface should feel like trusted infrastructure rather than a generic developer dashboard. The visual language is dark, precise, and cinematic: a near-black stage, sharp white ink, glassy technical panels, and a balanced signal field that suggests credentials moving through a controlled local path.

The emotional target is calm confidence. authsome handles sensitive access, encrypted storage, and request-time credential injection; the design should communicate that the system is powerful without being loud, secure without feeling bureaucratic, and advanced without drifting into neon sci-fi. The atmosphere can be dramatic, but the UI layer must remain crisp, legible, and operational.

## Colors

Colors are roles, not decoration. The palette is anchored by black and white for trust and legibility, then animated by a balanced environmental mix of copper, electric blue, steel, and darker falloff tones. No single accent should dominate the brand. The signal field should read as secure credential routing: blue for data velocity and technical clarity, copper for authenticated warmth and active handoff, steel for infrastructure, and dark shades for encrypted depth.

- **Primary (#FFFFFF):** The main ink. Use for headlines, high-emphasis labels, key diagram text, icon strokes, and the white shell of primary controls. It carries confidence and should remain the sharpest foreground value.
- **On Primary (#09090B):** Text and icon color when placed inside a primary white control. It keeps CTA labels practical and high-contrast.
- **Secondary (#B4B5BD):** Supporting ink for explanatory copy, nav links, card descriptions, and lower-priority labels. It should stay readable over motion without competing with primary text.
- **Muted (#71717A):** Metadata, section labels, faint diagram labels, and secondary timestamps. Use sparingly so small text does not become muddy.
- **Neutral (#09090B):** The emotional canvas. It represents local control, secrecy, and the protected runtime where credentials stay grounded.
- **Neutral Soft (#1F1F22):** A lifted dark role for subtle panels, inactive fills, and tonal separation.
- **Surface (#000000):** Absolute depth for WebGL/canvas backgrounds, icon tiles, and the black inset module inside white CTAs.
- **Surface Glass (#FFFFFF08):** Standard frosted-card fill. Use for utility panels, provider cards, and diagram nodes that should float without becoming heavy.
- **Surface Glass Strong (#FFFFFF12):** Elevated glass fill for the authsome core zone or selected cards.
- **Surface Border (#FFFFFF26):** Hairline refraction edge for glass cards and diagram containers.
- **Copper (#CC8066):** The authenticated-handoff accent. Use for token exchange, active auth boundaries, vault warmth, and small highlights around the authsome core. It should punctuate, not flood.
- **Copper Deep (#4A241D):** Warm falloff for receding reflections, low-energy credential trails, and shadows around copper highlights.
- **Electric Blue (#6D8FD6):** The data-velocity accent. Use for moving signal lines, focus glints, technical connectors, selected strokes, and occasional provider-routing emphasis.
- **Blue Soft (#3B5F9F):** Secondary blue for atmospheric reflections, receding trails, and lower-intensity connection paths.
- **Blue Deep (#172A4A):** Dark blue depth for secure-network shadow, bloom falloff, and the background behind active proxy details.
- **Steel (#334155):** Infrastructure color for rails, structural trails, outlines, and subdued system depth.
- **Steel Deep (#162033):** Distant infrastructure shade for horizon shadow, inactive flow, and low-energy diagram structure.
- **Glow Blue (#5B7CBE) and Glow Copper (#CC8066):** Environmental bloom roles only. These belong in the signal field, not in broad foreground UI fills.
- **Success, Warning, Danger:** Semantic status colors for CLI output, validation results, and auth states. Keep them functional and less visually dominant than the main signal palette.

## Typography

Typography uses **Inter** because authsome needs a neutral, precise voice that works for product pages, diagrams, CLI-adjacent UI, and developer documentation. The type should feel engineered but not sterile.

- **Display:** Large, tightly spaced hero headlines for brand-level statements. Use medium weight rather than heavy bold so the page feels premium and controlled.
- **Headlines:** Compact medium-weight section and card titles. They should identify systems quickly: proxy, vault, provider, agent, token.
- **Body:** Relaxed line height for explanatory text about security and flows. Avoid dense paragraphs in visual surfaces.
- **Labels:** Small labels are functional and crisp. `label-caps` is reserved for diagram zones such as AI Agents, Authsome, External Services, and provider badges.

## Layout & Spacing

The default layout is a wide, cinematic technical composition. Content sits inside a broad frame capped around `1600px`, with generous outer padding and bottom-weighted visual gravity. Use the page as a stage; avoid placing the entire experience inside a decorative card.

For product heroes, lead with the authsome name or a literal offer, then arrange supporting cards and copy around the signal field. For architecture diagrams, preserve a clear vertical pipeline: agents at the top, authsome in the protected center, external services at the bottom. This mirrors the product promise that access passes through a local, controlled layer.

Spacing follows an 8px-derived rhythm. Internal component spacing should be compact and utilitarian, while section spacing can be wide and cinematic. On mobile, collapse diagrams and card groups into a single column without losing the flow order: actor, authsome, destination.

## Elevation & Depth

Depth comes from light, blur, transparency, and perspective rather than heavy shadows. Glass panels should feel like thin technical overlays floating above a black signal environment. Use `surface-glass` with a faint border for standard cards, and `surface-glass-strong` for the authsome core or selected state.

The signal field is the main depth device. It should mix electric blue, copper, steel, white highlights, and darker blue/copper/steel falloff. A good frame contains visible blue, visible copper, visible steel, a few white-hot highlights, and enough dark falloff that trails feel embedded in the scene. If the composition reads as one hue, rebalance by lowering that hue’s opacity and restoring the other signal roles before increasing white.

Use overlays deliberately. A dark left overlay protects hero copy; a bottom overlay grounds lower content and keeps the interface from floating away. Bloom belongs mainly to the environmental layer, while foreground components stay sharp.

## Shapes

The shape language is precise and nearly square. authsome should not feel soft, pill-shaped, or consumer-playful. Use sharp corners or `2px` radii for technical panels, `4px` for larger controlled surfaces, and `8px` only when a card needs a slightly calmer reading edge.

Primary CTAs use a white rectangular shell with a black square icon tile. Glass cards use thin borders and restrained radii. Diagram nodes should feel like system modules rather than rounded marketing chips.

## Components

**Buttons**

Primary buttons combine a white outer control, black text, and a black trailing icon tile. They communicate decisive action without introducing another accent fill. Secondary buttons are transparent with subtle borders and secondary text.

**Navigation**

Navigation is quiet and sparse. Use secondary text, wide gaps, and a white hover state. Avoid enclosing navigation in a heavy bar; the page stage and signal field provide the structure.

**Glass Cards**

Glass cards are thin, translucent slabs for features, provider nodes, and architecture modules. Use a compact title, one supporting line, and optional linear icon. Hover states can add a small horizontal drift or border lift, but should not compete with the signal motion.

**Authsome Core Card**

The authsome core card represents the local proxy, encrypted vault, or credential broker. It may use both blue and copper: blue for technical routing and copper for authenticated handoff. Keep the fill dark and transparent so the card feels protected rather than promotional.

**Provider Badges**

Provider badges are small, uppercase, and restrained. They identify services like GitHub, Google, Linear, OpenAI, or Okta without becoming colorful brand-logo clutter.

**Signal Field**

The signal field is the governing environmental component. It may be implemented in SVG, canvas, WebGL, or CSS gradients. It uses additive-looking trails, mixed bloom, and perspective lines to imply secure credential flow. It should remain behind content and never obstruct readability.

## Motion

Motion should feel like controlled credential routing. Background trails can move continuously and slowly, with occasional brighter packets or dots suggesting request-time injection. UI motion should be short and practical: `200ms` to `300ms` for hover, color, border, and small transform changes.

Hero text may use a masked stagger reveal when the page is cinematic. Product and docs UI should prefer quieter transitions. Avoid frantic movement; authsome should feel fast because it is precise, not because the interface is noisy.

## Diagram Guidance

Architecture diagrams should preserve role clarity:

- **Agents:** Top row, glass modules, white ink, muted section label.
- **Authsome:** Center protected zone, strongest glass border, balanced blue/copper accent, label in copper or primary depending on contrast.
- **Proxy:** Highlight with mixed blue/copper signal lines because it performs the active handoff.
- **Vault:** Dark glass with lock/security icon treatment; avoid making it glow more than the proxy.
- **External Services:** Bottom row, quiet modules, secondary emphasis.
- **Flows:** Thin white, steel, blue, or copper connector lines. Use arrows sparingly and keep them readable over the signal field.

## Do's and Don'ts

**Do**

- Use black and white as the trust foundation.
- Treat every color as a role with a reason.
- Balance copper, electric blue, steel, and darker falloff shades in the signal field.
- Keep foreground UI sharp, restrained, and legible.
- Use glass panels for modules, not as decorative nested cards.
- Let the authsome core read as protected local infrastructure.

**Don't**

- Don't let blue overpower copper and steel; authsome is a mixed signal field, not a blue-only brand.
- Don't let copper turn the system into an orange/brown palette; it should mark authenticated warmth and handoff moments.
- Don't use gradients across foreground text or buttons.
- Don't round controls into soft pills.
- Don't add decorative blobs or unrelated atmospheric effects.
- Don't use provider brand colors as the main system palette.
