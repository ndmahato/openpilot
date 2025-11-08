# Project Change Log

This consolidated log aggregates prior standalone documentation files (HUD_INTERFACE_GUIDE.md, UI_IMPROVEMENTS.md, VOICE_ALERT_FIX.md) and will be incrementally updated instead of creating new .md files.

## Changelog

- [HUD Interface Guide (v2.0)](#entry-hud-interface-guide-version-20)
- [UI/UX Improvements Redesign (v2.0)](#entry-uiux-improvements-redesign-version-20)
- [Voice Alert Fix & Enhancement (v2.1)](#entry-voice-alert-fix--enhancement-version-21)
- [Stopped Vehicle Voice Suppression (v2.2)](#entry-stopped-vehicle-voice-suppression-version-22)

### Versioning Semantics

- MAJOR (X.0.0): Breaking behavior or large architectural/UI overhaul.
- MINOR (x.Y.0): Backward-compatible feature addition or enhancement.
- PATCH (x.y.Z): Bug fix or small tweak that doesn’t change public behavior/contracts.


---
## Entry: HUD Interface Guide (Version 2.0)
Source: HUD_INTERFACE_GUIDE.md (merged)
Date: November 7, 2024
Summary: Introduced full-screen HUD overlay with:
- Top status bar (device ID, connection, IST date/time, mode badge)
- Center speed panel (GPS speed + speed limit) with large typography
- Bottom alert banner (color-coded: CRITICAL/WARNING/CAUTION/SAFE)
- Metrics panel (uploads, processed, alerts)
- Bottom control bar (Stop, Voice, Fullscreen, Settings)
Design Principles: Safety, readability, glassmorphism, responsive layout.
Technical Highlights:
- IST time conversion updated every second
- GPS speed captured every 0.5s and sent to server
- HUD refresh at 500ms intervals
- Color system for rapid cognition

---
## Entry: UI/UX Improvements Redesign (Version 2.0)
Source: UI_IMPROVEMENTS.md (merged)
Date: November 7, 2024
Summary: Transition from scroll-based page to full overlay HUD.
Before Issues:
- Scrolling required to view video and alerts
- Fragmented information architecture
- Not full-screen friendly
After Improvements:
- Unified full-screen video with layered info
- Prioritized safety alerts and speed
- Responsive mobile/tablet/desktop adjustments
Metrics:
- Scrolls per session reduced: 15 → 0
- Time to see critical alert: 2–3s → <0.5s
- Visible screen usage: 60% → ~95%
Design Enhancements:
- Larger font scale (10–32px hierarchy)
- Color psychology for state mapping
- Glassmorphism, gradients, alert animations
Success Outcomes: Improved immediacy, lower cognitive load, professional automotive-grade UX.

---
## Entry: Voice Alert Fix & Enhancement (Version 2.1)
Source: VOICE_ALERT_FIX.md (merged)
Date: November 7, 2024
Summary: Restored continuous voice alert behavior after HUD refactor.
Problem:
- Voice alerts previously fired only once (except CRITICAL)
Solution:
- Implemented priority-based intervals:
  - CRITICAL: speakInterval = 0ms (every check ~500ms)
  - WARNING: 2000ms
  - CAUTION: 3000ms
Behavior:
- Alerts repeat until safe state reached
- System checks every 500ms
Testing Scenarios: Person (CRITICAL), car (WARNING), bicycle (CAUTION), safe distance exit.
Added Safety Rule (Post-Merge): Stopped vehicle suppression—see next entry below.

---
## Entry: Stopped Vehicle Voice Suppression (Version 2.2)
Date: November 8, 2025
Summary: Added logic to suppress voice alerts when the vehicle is fully stopped while retaining visual alerts (red box, banner).
Implementation Details:
- New constants: STOP_SPEED_THRESHOLD = 0.5 km/h, STOP_CONFIRM_SAMPLES = 3
- Per-device speed history (last 10 samples)
- If last N samples <= threshold, mark `suppressed` and clear `voice_message`
- Alert payload additions: `speed`, `suppressed`, `suppressed_reason`
Rationale:
- Prevent redundant verbal spam when vehicle is already stationary.
- Maintain situational awareness via visuals.
Resumption: Voice automatically resumes when movement detected (next speed sample above threshold).

---
## Current Alert System Summary
Levels:
- CRITICAL: Continuous voice (unless suppressed), red banner, pulsing animation
- WARNING: Voice every 2s, orange banner
- CAUTION: Voice every 3s, yellow banner
- SAFE: Silent, green state messaging
Suppression Conditions:
- Vehicle stopped (speed <= 0.5 km/h for 3 consecutive updates)
- User toggled voice OFF
Data Frequency:
- Alert polling: 500ms
- HUD refresh: 500ms
- Clock update: 1000ms
- GPS speed: ~500ms (watchPosition / calculation fallback)

---
## File Merge Notes
Retired Files (deleted after merge):
- HUD_INTERFACE_GUIDE.md
- UI_IMPROVEMENTS.md
- VOICE_ALERT_FIX.md
Future Policy:
- All subsequent documentation entries appended here.
Format Standard:
- Use chronological entries with heading "Entry: <Title> (Version X.Y)".
- Include date, summary, changes, rationale, metrics when applicable.

---
## Next Possible Enhancements (Backlog)
- User-configurable alert intervals via settings panel.
- Multi-language voice pack integration.
- HUD toggle for suppressed voice indicator (e.g., small icon).
- Persisting recent alert history panel.
- Configurable stop threshold and sample count via UI.

---
## Contribution Guidelines for Log Updates
When adding a new entry:
1. Increment version (patch if minor tweak, minor if feature, major if overhaul).
2. Provide: Date, Summary, Change Type, Motivation, Affected Components.
3. Keep previous entries immutable (historical record).
4. Avoid duplicating unchanged context.

---
End of consolidated log.
