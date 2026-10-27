# Narration script and timing

Voice: Kokoro-82M (ONNX, `kokoro-onnx`), voice `bm_george` (British male), speed 1.07, narration length 63.20 s; video length 64.50 s (1.30 s silent hold after the last word).

Text is written for the speech engine: **"Nicholas II" is spelled "Nicholas the Second"** because espeak reads the numeral as "Nicholas Roman two". Numerals 1917 / 1922 are read as "nineteen seventeen" / "nineteen twenty-two".

| Segment | Start (s) | End (s) | Text |
|---|---:|---:|---|
| hook | 0.00 | 12.41 | Russia was one of the world's largest empires. In 1917, a revolutionary party seized its capital in hours. But taking control of Russia itself was a much longer struggle. |
| crisis | 12.76 | 17.26 | World War One drained the empire. Millions died, and bread ran short. |
| tsar | 17.61 | 27.02 | In February 1917, strikes and mutinies in Petrograd forced Nicholas the Second to abdicate. A Provisional Government took over. |
| lenin | 27.36 | 34.30 | It kept fighting the war. Lenin's Bolsheviks promised peace, land, and bread, and workers and soldiers listened. |
| october | 34.65 | 45.66 | On October twenty-fifth, by the old Russian calendar, Bolsheviks seized Petrograd's key points and toppled the Provisional Government. November seventh, in the Gregorian calendar. |
| civil_war | 46.06 | 52.49 | But holding the capital was not holding Russia. Civil war split the empire between Reds and Whites. |
| consolidation | 52.89 | 58.79 | By 1922, through war and tight centralised control, the Bolsheviks had won. |
| end | 59.29 | 63.20 | The capital fell in hours. Consolidating power took years. |

## Pronunciation check

Phonemes produced by the engine's front end (espeak-ng, en-GB), checked for the four terms the brief names:

| Term | Phonemes (IPA) | Result |
|---|---|---|
| Bolsheviks | `bˈɒlʃɪvˌɪks` | ✔ standard English pronunciation |
| Petrograd | `pˈɛtɹəɡɹˌad` | ✔ |
| Lenin | `lˈɛnɪn` | ✔ |
| Nicholas II | `nˈɪkələs ɹˌəʊmən tˈuː` ("Nicholas Roman two") | ✘ wrong, so the script says "Nicholas the Second" → `nˈɪkələs ðə sˈɛkənd` ✔ |

As an independent intelligibility test, the finished narration was transcribed by a separate speech recogniser (sherpa-onnx streaming zipformer). It returned the script almost word for word, including "Petrograd", "Lenin's", "Nicholas the second", "Provisional Government" and "Gregorian" (it normalised "Bolsheviks" to "Bolshevik(s)" and read 1917 as "nineteen hundred and seventeen"). Nobody has *listened* to the audio: this is a machine check, so a human listen before publication is still recommended.

## Word timings (used for captions and on-screen cues)

Method: asr-timestamps; the recogniser's token timestamps were calibrated against pauses measured in the audio (median lag 0.216 s). Accuracy is about ±0.15 s.

**hook**: Russia`0.03` was`0.51` one`0.71` of`0.87` the`0.99` world's`1.15` largest`1.63` empires.`2.15` In`3.19` 1917,`3.43` a`5.35` revolutionary`5.51` party`6.31` seized`6.71` its`7.03` capital`7.27` in`7.87` hours.`8.03` But`8.83` taking`9.03` control`9.47` of`9.83` Russia`9.99` itself`10.43` was`11.11` a`11.39` much`11.47` longer`11.67` struggle.`12.07`

**crisis**: World`12.79` War`13.11` One`13.43` drained`13.67` the`13.99` empire.`14.15` Millions`14.91` died,`15.63` and`16.19` bread`16.35` ran`16.67` short.`16.99`

**tsar**: In`17.61` February`17.79` 1917,`18.27` strikes`20.35` and`20.75` mutinies`20.91` in`21.51` Petrograd`21.67` forced`22.59` Nicholas`22.95` the`23.47` Second`23.67` to`24.03` abdicate.`24.23` A`25.23` Provisional`25.39` Government`25.95` took`26.51` over.`26.83`

**lenin**: It`27.39` kept`27.51` fighting`27.83` the`28.23` war.`28.51` Lenin's`29.07` Bolsheviks`29.55` promised`30.15` peace,`30.71` land,`31.31` and`31.67` bread,`31.91` and`32.51` workers`32.67` and`33.19` soldiers`33.47` listened.`33.95`

**october**: On`34.65` October`34.79` twenty-fifth,`35.27` by`36.19` the`36.35` old`36.59` Russian`36.79` calendar,`37.23` Bolsheviks`37.95` seized`38.67` Petrograd's`39.07` key`39.91` points`40.19` and`40.71` toppled`40.91` the`41.31` Provisional`41.47` Government.`42.03` November`43.07` seventh,`43.59` in`44.27` the`44.43` Gregorian`44.55` calendar.`45.31`

**civil_war**: But`46.06` holding`46.27` the`46.63` capital`46.83` was`47.55` not`47.75` holding`47.99` Russia.`48.43` Civil`49.27` war`49.67` split`49.95` the`50.27` empire`50.47` between`51.07` Reds`51.39` and`51.91` Whites.`52.11`

**consolidation**: By`52.89` 1922,`53.03` through`54.95` war`55.27` and`55.55` tight`55.63` centralised`56.17` control,`56.71` the`57.47` Bolsheviks`57.63` had`58.35` won.`58.63`

**end**: The`59.29` capital`59.43` fell`59.95` in`60.35` hours.`60.47` Consolidating`61.19` power`62.15` took`62.59` years.`62.95`
