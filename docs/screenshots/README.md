# FireLens screenshots

These files are captures of the running application at 1440×900. They were taken from the local Vite server. They are not illustrations drawn for the repository.

Plots under `backend/reports/figures/` and `backend/experiments/` are analysis figures. They are not pictures of the interface.

| File | Screen | What it shows | Synthetic data visible |
| --- | --- | --- | --- |
| `01-global-fire-intelligence.png` | Global Fire Intelligence, 7 July 2024 | Cesium globe, selected demo hotspot, **Demo data** badges, and the verified archive total of 277,259 delivered rows | Yes. The map points and the detail panel are the seeded sample. The archive panel is the July 7 delivered-row table. |
| `02-global-sample-coverage-limit.png` | Global Fire Intelligence, 10 July 2024 | Empty globe for a date outside 1–7 July, the message that the interactive sample stops on 7 July, delivered-row counts, and the note that Suomi-NPP delivered no rows and that this is not zero fire activity | No map points. The empty state describes the synthetic sample limit. The counts are archive statistics. |
| `03-historical-fire-explorer.png` | Historical Fire Explorer, July 2024 | Activity calendar for 1–31 July and the delivered-row trend, including hollow marks where a file delivered no rows | No. The calendar and chart use the transcribed July archive. |
| `04-modis-viirs-comparison.png` | Sensor Comparison, full July 2024 | Nadir schematic of ~1 km MODIS pixels beside 375 m VIIRS pixels, and the separate confidence vocabularies: integer 0–100 versus low, nominal, and high | No satellite points. The grids are a schematic in the interface, labeled as not a scan-angle footprint. |
| `05-fire-propagation-simulation.png` | Fire Propagation Preview | Wind, temperature, humidity, and time controls, and the banner **DEMONSTRATION SIMULATION — NOT A VALIDATED FIRE FORECAST** | The drawing is a conceptual sketch. It does not show FIRMS coordinates or the globe sample. |

The README embeds these images with relative paths.
