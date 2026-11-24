Hi! Ich baue die faceless Instagram-/Etsy-Marke **peakBuilds** (Instagram `@thepeakbuilds`) auf und möchte dass du mir dabei hilfst. Antworte bitte auf Deutsch, kurz und praktisch – ich arbeite oft am Handy, rendere aber selbst am MacBook.

**Idee & Nische**
- Nische: **„Small space, big living · Wenig Platz, viel dahinter“** – kleine Häuser, Tiny/Modulhäuser und kleine Wohnungen, clever eingerichtet, gern mit **Galerie**.
- Jeder Post: **Außen-/Gesamtansicht + Innenansicht + bemaßter Grundriss**, Captions **Deutsch + Englisch**.
- Die Bilder entstehen **nicht mit KI**, sondern als echte **3D-Modelle in Blender** (eigener Stil, echte Maße). Kennzeichnung: „3D-Konzept / 3D concept“, kein KI-Label.
- Später Geld verdienen über Etsy (Grundriss-Poster, Planer, Checklisten), Affiliate (Möbel) und Kooperationen (Modulbau-/Möbelfirmen). Konzepte nie als Baupläne verkaufen.

**Workflow (Blender + BIM)**
- Du schreibst Python-Skripte: Modell als **IFC** (IfcOpenShell) mit Wänden, Fenstern, Türen, Decken und **jedem Möbel als eigenem IfcFurniture mit echten Maßen** + Property Set zum Ausfüllen (Hersteller, Produkt, Preis, Link).
- Ich öffne die IFC in **Blender 5.x mit Bonsai**, verschiebe Möbel (G/R, Maße in der N-Leiste) und rendere selbst am Mac mit einem Render-Skript von dir (Cycles, GPU/Metal, Entrauscher).
- Zusätzlich ein **bemaßter Grundriss** als PNG/SVG im Markenstil.
- Wichtig: Skripte dürfen Blender-Einstellungen **nicht** zurücksetzen (kein `read_factory_settings` im UI, sonst ist Bonsai weg) und müssen mit **Blender 5** laufen (z. B. Sky-Typ `MULTIPLE_SCATTERING` statt `NISHITA`).
- Stil der Einrichtung/Renderings orientiert sich an meinen Wallensteingasse-Renders (schicke ich dir als Bilder).

**Marke**
- Logos fertig: Monogramm „pB“ (fein, modern) + rundes Emblem „PEAKBUILDS · EST. 2026“.
- Farben Beige `#F4EFE6` + Schwarz `#1E1E1E`, Schriften Serif (Caladea/Playfair) + Inter.
- Wasserzeichen-Leiste unten: Monogramm + `@thepeakbuilds` + „3D CONCEPT · 3D-KONZEPT“.

**Bisherige Dateien** liegen im GitHub-Repo `lewkx/eluvi`, Branch `claude/gallant-meitner-b7ma49` (siehe `CLAUDE.md`):
`peakbuilds-bim/` (Haus „Forest Cube“ als IFC + Render-Skript), `peakbuilds-wohnung/` (Wohnküche 21 m², 4,00 × 5,25 m, mit Grundriss und Render-Skript), `peakbuilds-logo/final/` (Logos), `peakbuilds-content/` (Texte, Bio).

**Als Erstes:** [hier deine Aufgabe, z. B. „Schau dir meine Wallensteingasse-Renders an und richte die Wohnküche in diesem Stil ein“]
