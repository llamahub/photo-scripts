# Immich API Findings: People and Albums Per Asset

Date: 2026-02-15

## Summary
The API responses and server source indicate there is no single bulk endpoint that returns both people and album membership per asset in one call. To enrich a cache with per-asset people and albums, you need separate calls: faces per asset for people, and album enumeration for albums.

## Live API Probes (from this workspace)
- POST /api/search/metadata with withExif true returned assets with a people field present but empty. No albums field was present.
- GET /api/assets/{asset_id} returned people field present but empty. No albums field was present.
- GET /api/albums returned album list; GET /api/albums/{album_id} returned assets in that album. Asset objects did not include an albums array.
- GET /api/people returned a list of people (name, id, isHidden, isFavorite, etc.).
- GET /api/people/{person_id}/assets returned 404, indicating this endpoint does not exist on the server.
- GET /api/faces without required query parameters returned 400.

## Source Scan Notes (immich-app/immich)
- The Faces controller exposes GET /faces and expects query params. The DTO implies the asset id is required for retrieving faces for an asset. This endpoint returns faces that include a person object when present.
- The People controller exposes GET /people, GET /people/{id}, and GET /people/{id}/statistics, but no /people/{id}/assets route exists.

## Practical Enrichment Strategy
1. People per asset
   - Call GET /faces?id=<assetId> for each asset.
   - Build people list as unique face.person values per asset.

2. Albums per asset
   - Call GET /albums once to list albums.
   - For each album, call GET /albums/{albumId} to get assets in that album.
   - Build a map of assetId -> [albumId, albumName, ...].

## Notes and Limitations
- There is no bulk endpoint discovered that returns people and albums per asset in one response.
- People data is not populated in search or asset detail responses unless you query faces for each asset.
- Album membership is only derivable by traversing albums and their asset lists.
