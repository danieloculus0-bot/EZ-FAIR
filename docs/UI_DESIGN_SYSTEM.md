# EZ FAIR UI design system

## Direction

EZ FAIR must not resemble a generic chatbot, AI dashboard, or soft consumer SaaS application.

The interface should use the established VenvWin visual direction:

- dark mode only
- sharp rectangular geometry
- compact shop-floor spacing
- strong visual hierarchy
- restrained industrial typography
- high-contrast status states
- minimal animation
- no oversized rounded cards
- no gradient-heavy AI styling
- no conversational layout

The product should look like a serious manufacturing application built for inspectors, machinists, quality engineers, and production leads.

## Core visual language

### Surfaces

- application background: near-black charcoal
- primary panels: dark graphite
- secondary panels: slightly lighter graphite
- input surfaces: dark neutral with crisp border
- active selection: configurable accent color
- disabled surfaces: low-contrast neutral, never translucent blur

### Geometry

- corner radius: 0 to 3 px maximum
- buttons: rectangular, compact, clearly bordered
- tables: dense rows with strong column separation
- tabs: flat or underlined, not pill-shaped
- dialogs: hard-edged, structured, and resizable
- icons: line or solid industrial icons, not playful illustrations

### Typography

- use a clean system sans-serif for UI
- use monospaced text where coordinates, dimensions, tolerances, IDs, paths, or debug values are displayed
- emphasize hierarchy using weight and spacing rather than oversized headings

## Configurable color system

Dark mode remains mandatory, but the user may configure:

- primary accent
- primary button
- secondary button
- destructive action
- warning
- success
- selected table row
- balloon annotation color
- PDF highlight color
- focus border

Provide several presets:

- VenvWin Blue
- Machine Green
- Safety Orange
- Inspection Yellow
- Steel Gray
- Custom

Custom colors should be stored in a local theme profile. Enforce minimum contrast so text remains readable.

## Interaction principles

- primary actions must be visible without scrolling
- destructive actions must be visually distinct
- keyboard navigation is required
- common actions need shortcuts
- editable tables must support direct cell editing
- no hidden hover-only controls for critical functions
- status and confidence must use text plus color, never color alone
- shop-floor use assumes gloves, dirty screens, and imperfect lighting, so hit targets must remain practical even with compact spacing

## Application layout

### Left navigation

Use a narrow fixed navigation rail or compact tree with:

- Projects
- Drawings
- Characteristics
- GD&T Controls
- Results
- Forms
- Integrations
- Settings

### Main workspace

Use split panes where useful:

- drawing/PDF on the left
- characteristic or metadata table on the right
- resizable divider
- source crop and parsed requirement shown together

### Bottom status bar

Always show:

- active project
- drawing revision
- extraction mode
- unresolved count
- save state
- active form profile

## Review states

Use explicit state labels:

- DETECTED
- REVIEW NEEDED
- VERIFIED
- LINKED
- CONFLICT
- EXCLUDED

Do not use vague AI-style confidence prose. Show the confidence value and the exact reason for uncertainty.

## Form designer styling

The form designer should feel like a technical configuration screen:

- left pane: available fields
- center pane: active columns in order
- right pane: selected field properties
- drag or arrow controls for reordering
- visible add, remove, hide, duplicate, and reset buttons
- live preview below or in a separate preview tab

## Button behavior

Buttons may use configurable colors, but button roles remain consistent:

- primary: current accent
- secondary: neutral graphite
- confirm/success: success color
- warning: warning color
- destructive: destructive color

Never use random colors per screen.

## Accessibility and deployment

- dark mode cannot be disabled
- support Windows display scaling
- minimum contrast must remain acceptable
- avoid color-only pass/fail indicators
- support large-text mode without changing the overall industrial layout
- persist theme settings locally

## Non-goals

- chatbot panel
- assistant avatar
- floating AI sparkle button
- giant marketing cards
- glassmorphism
- excessive rounded corners
- animated gradients
- mobile-first layout
- web-app imitation

EZ FAIR should look like a purpose-built industrial quality application, not another generic ChatGPT wrapper.