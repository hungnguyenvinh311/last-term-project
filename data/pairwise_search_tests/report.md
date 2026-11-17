# Pairwise image search experiment

{
  "pairs": 10,
  "targets": 20,
  "strongestLabelCorrect": 8,
  "correctLabelAvailable": 9,
  "endToEndPassed": 8,
  "knownRegionPassed": 20,
  "detectedSearchAttempts": 18,
  "selectedCategoryBoundaryFailures": 0,
  "seconds": 51.78262460000042
}

| Pair | Source ID | Strongest label correct | Correct label available | Detected-region search | Known-region control |
|---|---:|---|---|---|---|
| phone__laptop | 1 | True | True | passed | passed |
| phone__laptop | 21 | True | True | passed | passed |
| phone__tablet | 1 | True | True | passed | passed |
| phone__tablet | 41 | False | False | failed | passed |
| phone__headphones | 1 | True | True | passed | passed |
| phone__headphones | 61 | False | False | skipped_no_located_detection | passed |
| phone__watch | 1 | True | True | passed | passed |
| phone__watch | 81 | False | False | failed | passed |
| laptop__tablet | 21 | True | True | passed | passed |
| laptop__tablet | 41 | False | True | failed | passed |
| laptop__headphones | 21 | True | True | passed | passed |
| laptop__headphones | 61 | False | False | failed | passed |
| laptop__watch | 21 | True | True | passed | passed |
| laptop__watch | 81 | False | False | failed | passed |
| tablet__headphones | 41 | False | False | failed | passed |
| tablet__headphones | 61 | False | False | failed | passed |
| tablet__watch | 41 | False | False | failed | passed |
| tablet__watch | 81 | False | False | failed | passed |
| headphones__watch | 61 | False | False | skipped_no_located_detection | passed |
| headphones__watch | 81 | False | False | failed | passed |

## Limits

- One product per category, one left/right layout; no claim of exhaustive product/angle/background coverage.
- Indexed catalogue images are reused; top-five source recovery is a consistency check, not independent retrieval accuracy.
- Panels and pasted-image rectangles are known; exact physical-object boxes are not manually annotated.
- Correct-label availability is separate from strongest-label correctness; duplicates/extra detections are retained.
- Known-region controls use the expected category explicitly and are reported separately from end-to-end detection.
- No Gemini API calls, live ranking changes, catalogue modifications or demo search-history writes. Test database is retained.
