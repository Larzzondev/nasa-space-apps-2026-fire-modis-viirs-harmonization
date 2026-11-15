# Screenshot inventory

The FireLens interface has no committed screenshots. This directory is the place for them. Do not add a generated or placeholder image. A file belongs here only after someone captures the running application.

Scientific plots under `backend/reports/figures/` and `backend/experiments/*/figures/` are analysis figures. They are not pictures of the website, and they should not be copied into this folder to stand in for the screens below.

Capture the default theme at a desktop width of at least 1280 pixels, after `npm run dev`, with no Cesium ion token unless a shot says otherwise. Leave the demo and archive badges readable.

## Still needed

| File | Screen | What the capture must show |
| --- | --- | --- |
| `01-global-fire-intelligence.png` | Global Fire Intelligence, 7 July 2024, all sensors, day/night All | The Cesium globe with synthetic points, the **Demo data** badge, the **Verified archive** count for that day, and the legend. The archive total and the on-screen sample count must both be visible, so a reader can see that they differ. |
| `02-global-outside-sample-window.png` | Global Fire Intelligence, any date from 8–31 July 2024 | The empty-map message that the interactive sample is 1–7 July, and the side panel still showing delivered-row counts for that July date. |
| `03-historical-fire-explorer.png` | Historical Fire Explorer, full July 2024, all sensors | The calendar, the delivered-row trend, a hollow mark or gap note for a Suomi-NPP date with no rows, and the sentence that missing rows are not zero detections. |
| `04-sensor-comparison.png` | Sensor Comparison, full July 2024 | The MODIS and VIIRS confidence panels on their own scales, the delivered-row bars, and the nadir pixel schematic. |
| `05-propagation-preview.png` | Fire Propagation Preview | The banner **DEMONSTRATION SIMULATION — NOT A VALIDATED FIRE FORECAST** and enough of the sketch to show that the control is wind, temperature, and humidity. |

## Optional

| File | When to add it |
| --- | --- |
| `06-global-cesium-ion.png` | Only after a local `VITE_CESIUM_ION_TOKEN` is set and the legend reads **Basemap: Cesium ion**. Do not commit the token. The default OpenStreetMap basemap is already the subject of `01-global-fire-intelligence.png`. |

Until these files exist, the README links to this inventory instead of to images.
