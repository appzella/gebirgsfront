# Gebirgsfront 1915–1918

Interaktive Karte der Gebirgsfront zwischen Italien und Österreich-Ungarn im Ersten Weltkrieg, vom Stilfserjoch bis zum Isonzo.

- Zeitregler von Mai 1915 bis November 1918 mit 11 Frontphasen
- Schlachten und Kämpfe, Festungswerke beider Seiten
- Umschalter zwischen Karte und 3D-Relief

## Technik

Eine einzelne statische Seite (`index.html`), kein Build-Schritt.

- Kartenbibliothek: [MapLibre GL JS](https://maplibre.org) 4.7.1
- Vektorkarte: [OpenFreeMap](https://openfreemap.org) (OpenStreetMap-Daten), eigener heller Stil
- Relief und 3D: [AWS Terrain Tiles](https://registry.opendata.aws/terrain-tiles/) (Terrarium)

Frontlinien, Schlachten und Festungen stehen als Daten im Skript (`S`, `PHASES`, `BATTLES`, `FORTS`). Die Frontlinien sind historische Näherungen, keine Vermessung.

Lokal ansehen: `npx serve .` oder die Datei direkt im Browser öffnen.
