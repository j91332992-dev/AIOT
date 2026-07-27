---
name: LJU Smart Essence
colors:
  surface: '#ffffff'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#47464f'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#787680'
  outline-variant: '#c8c5d0'
  surface-tint: '#5b598c'
  primary: '#070235'
  on-primary: '#ffffff'
  primary-container: '#1e1b4b'
  on-primary-container: '#8683ba'
  inverse-primary: '#c4c1fb'
  secondary: '#006c4a'
  on-secondary: '#ffffff'
  secondary-container: '#82f5c1'
  on-secondary-container: '#00714e'
  tertiary: '#160700'
  on-tertiary: '#ffffff'
  tertiary-container: '#371a00'
  on-tertiary-container: '#ae7f59'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e3dfff'
  primary-fixed-dim: '#c4c1fb'
  on-primary-fixed: '#181445'
  on-primary-fixed-variant: '#444173'
  secondary-fixed: '#85f8c4'
  secondary-fixed-dim: '#68dba9'
  on-secondary-fixed: '#002114'
  on-secondary-fixed-variant: '#005137'
  tertiary-fixed: '#ffdcc2'
  tertiary-fixed-dim: '#f1bc91'
  on-tertiary-fixed: '#2e1500'
  on-tertiary-fixed-variant: '#633e1e'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#f1f5f9'
  on-surface-subtle: '#64748b'
  glass-bg: rgba(255, 255, 255, 0.7)
  accent-emerald: '#10b981'
  status-online: '#22c55e'
  status-offline: '#94a3b8'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  title-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-mono:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.05em
  display-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base-unit: 4px
  container-padding: 24px
  gutter: 16px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style

The design system is centered on a **Modern Minimalist** aesthetic, specifically tailored for a Smart Home Dashboard. It prioritizes clarity, sophistication, and effortless control. By moving away from heavy neumorphism and embracing **Clean Flat** principles with **Glassmorphism** accents, the UI achieves a high-end, architectural feel.

The emotional response should be one of "calm control"—the interface should feel invisible until needed, using generous whitespace and subtle motion to guide the user.

- **Primary Style:** Clean Modern Minimalism.
- **Visual Flourish:** Glassmorphic navigation bars and subtle depth through soft, tinted shadows.
- **Target Audience:** Tech-savvy users looking for a premium, non-cluttered home management experience.

## Colors

The palette is anchored in a **Deep Indigo** (`#1e1b4b`) primary color for high-contrast interactions and typography, paired with an **Emerald Green** (`#059669`) for status indicators and active states. 

The background utilizes a series of cool-toned neutrals to maintain a clinical yet inviting feel.
- **Primary:** Used for main actions, headers, and active navigation icons.
- **Secondary/Accent:** Used for toggle states (e.g., lights "on") and success confirmations.
- **Neutral Base:** A very light gray (`#f8fafc`) serves as the canvas, preventing the "starkness" of pure white while maintaining high legibility.
- **Glass Effects:** Used for fixed elements like the bottom navigation and top headers to provide a sense of layered depth.

## Typography

This design system uses **Plus Jakarta Sans** for all UI elements and headings to provide a modern, friendly, and highly legible experience. **JetBrains Mono** is reserved specifically for sensor data, terminal logs, and technical readouts to differentiate "data" from "interface."

- **Headlines:** Use tight letter-spacing and bold weights to create a strong hierarchy.
- **Body Text:** Optimized for readability with a standard 1.5x line height.
- **Data Display:** Numerical values (temperature, humidity, brightness) should use the Label-Mono style for a precise, "instrumented" appearance.

## Layout & Spacing

The layout follows a **Fixed Grid** approach optimized for mobile-first consumption, with a maximum width of **480px** to simulate a native app experience. 

- **Grid:** A simple 2-column grid is used for sensor cards to maximize vertical space. Larger controls (like the OLED preview or RGB controller) span the full width.
- **Rhythm:** An 8px-based spacing system ensures vertical rhythm. 
- **Safe Areas:** 24px horizontal margins provide "breathing room" for the content, preventing it from feeling cramped on mobile screens.
- **Reflow:** On desktop browsers, the dashboard remains centered with a max-width, maintaining the intimacy of a handheld controller.

## Elevation & Depth

Hierarchy is established through **Tonal Layers** and **Subtle Shadows** rather than borders.

1.  **Level 0 (Background):** Neutral base (`#f8fafc`).
2.  **Level 1 (Cards):** Pure white surface (`#ffffff`) with a very soft, diffused shadow (`box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04)`).
3.  **Level 2 (Active Elements):** Primary color surfaces or glassmorphic overlays.
4.  **Glassmorphism:** Applied to the Header and Bottom Navigation using `backdrop-filter: blur(12px)` and a semi-transparent white background (`rgba(255, 255, 255, 0.7)`). This creates a sense of the interface floating above the dashboard content.

## Shapes

The shape language is consistently **Rounded**, using a 16px (1rem) base for all cards and primary buttons to evoke a soft, consumer-friendly feel. 

- **Cards & Input Groups:** 16px radius (`rounded-lg`).
- **Interactive Badges/Small Buttons:** 8px radius (`rounded-md`).
- **Connection Status:** Pill-shaped (fully rounded) to indicate a distinct status object.

## Components

### Buttons
- **Primary Action:** Solid Primary Indigo background, white text, 16px rounded corners. Heavy weight typography.
- **Secondary Action:** Ghost style with a subtle 1px border (`#e2e8f0`) and Indigo text.
- **Control Toggles:** When "On," buttons transition to Emerald Green with a subtle inner glow.

### Sensor Cards
- Display a large mono-spaced value (JetBrains Mono) with a small descriptive label.
- Include a "Refresh" icon in the top right corner using a low-contrast outline.

### Input Fields / Terminal
- **Terminal Log:** Dark mode block (`#1e293b`) with green mono-spaced text to simulate a developer console.
- **Sliders:** Minimalist tracks with a large, easy-to-tap circular thumb.

### Navigation (Bottom Tab Bar)
- Fixed at the bottom.
- Uses Glassmorphism (blur) to allow content to scroll behind it.
- Active state is indicated by a Primary Indigo icon and a subtle 4px dot below the icon.

### Connection Overlay
- A full-screen blur over the dashboard.
- Uses a centered card with a high-contrast "Connect to BLE" button and a pulsating Bluetooth icon animation.
