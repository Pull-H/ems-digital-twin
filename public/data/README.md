# NYC borough geometry

`nyc-boroughs.geojson` is a local copy of NYC Department of City Planning
**Borough Boundaries**, release 26b (water excluded), downloaded 2026-09-18 UTC.

- Catalog: https://data.cityofnewyork.us/City-Government/Borough-Boundaries/gthc-hcne
- Download: https://data.cityofnewyork.us/resource/gthc-hcne.geojson
- SHA-256: `7aa44d9fb611f2f518a226ff994a6516a261a8ce982ccf1e7b37d663687f443c`
- Five MultiPolygon features; longitude/latitude coordinates, CRS84.

This external source supplies display boundaries only. It does not supply
incident GPS, hospital locations, ambulance bases, road routes, or EMS resources.
The simulation retains its documented borough centroids and approximate coordinates.
The browser reads this local asset without querying Socrata or downloading map tiles.
