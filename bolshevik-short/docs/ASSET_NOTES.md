# Asset vetting notes

Rules applied to every image: (1) the item is an authentic archival original, not a
reconstruction, painting, film still or modern artwork passed off as a photograph; (2) its date and
subject match what the film says about it; (3) the source states a reuse status that permits use.
Anything that failed a rule is listed below and is **not** in the film.

## Rejected

| Candidate | Source | Why it was rejected |
|---|---|---|
| "Stormningen av vinterpalatset.jpg" | Wikimedia Commons | Widely circulated "storming of the Winter Palace" image; it is a still from Eisenstein's staged 1928 film *October*, not a 1917 photograph. No genuine photograph of the storming exists. The film uses a map instead. |
| Soviet 1947 stamps "Winter Palace storming" | Wikimedia Commons | Postage-stamp illustrations (1947), not photographs. |
| Brodsky, "Lenin in the Smolny" | Wikimedia Commons | 1930 painting. |
| "[V.I. Lenin talking before a group of people, 1917]" | Library of Congress 2002723954 | Record states "Repro. of painting" and rights "not evaluated". |
| "Mit diesem Passbild reiste Lenin 1917 nach Petersburg" | Library of Congress | 1965 publication reproduction; not used. |
| Gen. Denikin portrait | Library of Congress 2018661595 | Record flags its caption as "unverified, old data from caption card". A dated, captioned photograph of Denikin's army was used instead (American Red Cross, 1919). |
| "Bolshevik troops in Petrograd, November 1917" | Wikimedia Commons | Credited to Popperfoto/ENA; the "public domain" label on Commons is doubtful for a press-agency print. Not used. |
| Grigory Goldstein, "Guard detachment of the Red Army, 1918" | Wikimedia Commons | Photographer died 1960; the public-domain basis for use is unclear. Not used. |
| "Lenin… talking" and other 1950s–60s Soviet reproductions in LoC | Library of Congress | Later reproductions of paintings/retouched images, not period photographs. |
| "[Vladimir Ilʹich Lenin, head-and-shoulders portrait]" (Soyuzfoto) | Library of Congress 90714584 | Record says "Copy of an earlier photograph or painting(?)"; provenance too uncertain. Replaced by a Bain News Service negative of Lenin at his desk. |
| Items with LoC rights "not evaluated" | Library of Congress | Left out unless the rights statement was "No known restrictions". |

## Accepted, with caveats

| Item | Caveat |
|---|---|
| Photographs from the LoC "Days of Revolution" series (LOT 2398) | Period photographs / postcards (1917) with Russian captions. LoC: "No known restrictions on publication in the U.S. Use elsewhere may be restricted by other countries' laws." |
| American Red Cross photographs, 1919 (LoC) | Scanned from glass negatives; plate borders cropped. Captions are the ARC's own (Volunteer Army cavalry in Kharkov; Bolshevik prisoners at Omsk). LoC: "No known restrictions". Because the ARC worked on the White side, the framing of these photographs reflects that viewpoint. |
| "Soldiers of the Russian Army, WWI era" (LoC / World Digital Library) | LoC: "unaware of any copyright or other restrictions". Original held by the Kemerovo Oblast Museum of Regional History. |
| "Lenine [i.e. Lenin]" (Bain News Service negative) | Library of Congress 2014713397. A genuine glass-plate negative of a photograph of Lenin at his desk, signed on the print. LoC dates the item 1920 (publication); the exposure date is not given, so the film captions it **"published 1920"** and never presents it as a 1917 image. LoC: "No known restrictions on publication." |
| Newspaper front-page crops (Chronicling America) | Real front pages of the Daily Kennebec Journal (16 Mar 1917) and the Seattle Star (8 Nov 1917). The Library of Congress "believes that the newspapers in Chronicling America are in the public domain or have no known copyright restrictions." Only headline regions are cropped; the film applies a monochrome grade and nothing else. |
| Bread queue, Petrograd, early 1917 (Wikimedia Commons) | The only Commons file in the film. Commons marks it public domain, dated "before 8 March 1917", with no photographer named; its stated source is a histclo.com essay. Provenance is therefore weaker than the LoC items. |
| 1914 plan of St Petersburg (Internet Archive, Baedeker) | Published 1914, public domain by age. See `docs/MAP_NOTES.md`. |

## Dates used in captions

* "Bread queue, Petrograd, early 1917": Commons description "before 8 March 1917".
* 1917 street scenes carry the photographers' original Russian captions; the film's credit lines translate only place and subject.
* Lenin portrait: shown while the narrator names Lenin; the caption states it is a Bain News Service item published in 1920.
* The 1917 street scenes and the 1 May 1917 demonstration photographs are anonymous period photographs; the LoC record gives the year but not the photographer.

## Candidates that could not be obtained

During production the shared egress IP of the cloud session was throttled by Wikimedia (HTTP 429 with a 10-minute Retry-After on `upload.wikimedia.org`; one download in roughly 12 minutes succeeded). These vetted Commons items were therefore **not** downloaded and are not in the film: the 8 March 1917 Women's Day march, the 4 July 1917 Nevsky Prospect photograph, Lenin in disguise (August 1917), two Red Guard photographs, the typed abdication manifesto, a 1918 NARA Red Guard photograph, and the Mayak 1917 plan of Petrograd. Each was replaced by a verified Library of Congress / Chronicling America / Internet Archive item (see `docs/SOURCES.md`), or, for the Lenin portrait, a Bain News Service photograph. If you can download them, `src/scenes.py` prefers `womens_day` and `july_days` when `assets/raw/womens_day.jpg` / `july_days.jpg` exist (see `PICKS`).
