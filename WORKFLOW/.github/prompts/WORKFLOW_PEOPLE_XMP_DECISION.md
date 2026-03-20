# WORKFLOW People Metadata Decision Summary

Date: 2026-03-16

## Purpose

This document summarizes the decisions discussed for representing people metadata in image files for WORKFLOW and Immich synchronization.

## Key Decisions

### 1) Can XMP be embedded in image files?

Yes. XMP can be embedded in many image formats (commonly JPEG and TIFF, and often PNG/HEIF/DNG depending on tooling).

For workflows that should avoid modifying originals (or where tooling/formats require it), sidecar .xmp files remain a valid option.

### 2) Can XMP map more than one person to an image?

Yes. XMP supports multiple people per image.

Recommended IPTC XMP fields:

- Iptc4xmpExt:PersonInImage (flat list of person names)
- Iptc4xmpExt:PersonInImageWDetails (structured list of person entries)

### 3) Should Immich IDs be stored in PersonInImageWDetails?

Yes, with a portability constraint:

- Use PersonInImageWDetails as the canonical structured field.
- For each person entry, store:
  - PersonName: readable display name
  - PersonId: one or more identifiers
- Keep PersonInImage synchronized from PersonName values for compatibility with simpler tools.

Immich person IDs are local system IDs, not globally universal identities. If stored in PersonId, encode them as namespaced URI/URN strings so they remain unambiguous.

Recommended format:

- urn:immich:<instance-id>:person:<person-id>

## WORKFLOW Guidance

For cache and CSV design:

- Preserve people as a list of objects, not a single delimited string.
- Include both name and identifier(s) in cache.
- Treat names as user-facing labels and IDs as stable linkage keys.
- Support entries with name only when ID is unknown.
- When writing back to metadata, emit both PersonInImageWDetails and PersonInImage where possible.

## Example Data Shape

Example conceptual person record:

- name: Jane Doe
- ids:
  - urn:immich:home-server:person:12345

This keeps interoperability with IPTC/XMP while preserving reliable round-trip mapping to Immich.
