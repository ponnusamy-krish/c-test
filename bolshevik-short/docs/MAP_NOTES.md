# Map notes: what is measured, what is approximate

## 1. Whole-empire outline (opening, civil war, ending)

* **Data:** Natural Earth 1:50m admin-0 countries (public domain), projected with a Lambert conformal conic projection (parallels 45°N and 65°N, central meridian 75°E).
* **The 1914 empire is assembled from modern countries** (Russia, Finland, Estonia, Latvia, Lithuania, Belarus, Ukraine, Moldova, Georgia, Armenia, Azerbaijan, Kazakhstan, Uzbekistan, Turkmenistan, Tajikistan, Kyrgyzstan, plus Poland clipped to a hand-drawn polygon for Congress Poland).
* **Two corrections** to avoid showing modern borders as historical ones: Kaliningrad oblast (German East Prussia in 1914) and southern Sakhalin (Japanese 1905–45) are cut out.
* **Not modelled:** Kars/Batum (held by Russia 1878–1918), the Tannu Uriankhai protectorate (1914), the Bukhara and Khiva protectorate borders (shown as part of the modern Central Asian states).
* The outline is therefore **a faithful general shape, not a surveyed 1914 boundary**.

## 2. Territory phases A–E and the front lines

Hand-drawn polygons in `src/territory.py`, simplified from general histories of the war and labelled on screen **"FRONT LINES: APPROXIMATE, SIMPLIFIED"**.

| Phase | Shown with | What it depicts |
|---|---|---|
| A | start of the civil-war scene | Petrograd and Moscow with the railway between them: where the Bolsheviks actually held power right after October |
| B | "1918" | The Soviet heartland after Brest-Litovsk, the Czech Legion revolt, the Don/Kuban Volunteer Army and the Allied landings in the North |
| C | "1919" | High-water mark of the White offensives (Denikin at Orel, Yudenich near Petrograd; Kolchak already pushed back toward Omsk) |
| D | "1920/1921" | Whites reduced to Crimea; Georgia and the Far East (Japanese occupation / Far Eastern Republic) still outside; the western borderlands under Poland |
| E | "1922" | The Red area as the USSR forms. **Poland, Finland, the Baltic states, Bessarabia and the Polish-held borderlands stay outside**: the Bolsheviks did not recover the whole empire. |

Phases are rasterised on a 6 km grid, converted to signed-distance fields and interpolated, so the front line flows between phases. The arrows (Denikin, Kolchak, Yudenich) are schematic axes of the 1919 offensives, not surveyed lines. Their end points are documented in `docs/FACT_CHECK.md` (Denikin to Orel, Yudenich to the Petrograd outskirts, Kolchak's Omsk base).

## 3. The 1914 Petrograd plan (October scene)

* **Source:** Baedeker's *Russia* (1914), fold-out "St. Petersburg I", 1:36,200, scanned by the Internet Archive (`russiawithtehera00baed`, leaf n179). The plan prints the name "St. Petersburg" (the city was renamed Petrograd in 1914). It shows the *Dvortzovi (Palace) Bridge* as temporary / in construction; the permanent bridge opened in 1916, so it existed in October 1917.
* **Georeferencing.** An affine transform from local kilometres (equirectangular around 59.93°N, 30.30°E) to plan pixels was fitted by least squares to four landmarks identified on the plan at native resolution:

| Anchor | lon, lat | plan px (x, y) |
|---|---|---|
| Nikolaevsky ("Nicholas") Station | 30.3622, 59.9308 | 2072, 1535 |
| Finland Station | 30.3566, 59.9556 | 2000, 885 |
| Baltic Station | 30.2991, 59.9072 | 1225, 2130 |
| Cathedral of St Peter & St Paul | 30.3167, 59.9500 | 1479, 1029 |

  Residuals: 4.1, 5.8, 2.6 and 4.3 px (≈ 4.26 m per pixel, so ≈ 15–25 m). The transform is stored in `assets/petrograd_pins.json`.
* **Pin positions** are computed from modern coordinates of the buildings, then checked visually against the printed labels on the plan: Winter Palace (on the "Hermitage / Winter Pal." block), Palace Bridge ("Dvortzovi Br."), Post & Telegraph ("Gen. Post Off." / "Gen. Tel. Off."), State Bank (Catherine Canal near Kazan Cathedral), Nikolaevsky and Baltic stations (station labels), Smolny (east bank, grid square K4 in the plan's index).
* **Which places were seized:** railway stations, the Palace Bridge, the telegraph agency / post office, the State Bank (and others) on 24–25 October O.S., per the accounts listed in `docs/FACT_CHECK.md`. The film names five of them; it does not claim to list all.
