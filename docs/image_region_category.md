# Category-scoped image-region search

## Behaviour

The detector returns a stable `categoryID` for each region in addition to its label, score and normalized bounding box: phone 1, laptop 2, tablet 3, headphones 4, smartwatch 5. Selecting a region updates both its crop coordinates and the `Loại sản phẩm trong ảnh` control. The user can correct that category without changing the crop.

The submitted image-search snapshot carries `imageCategoryID` separately from the general catalogue `categoryID` filter. SearchService validates the selection and reconciles it with explicit text/filter conditions before image encoding. A conflict returns a readable error rather than silently substituting a category. When the category agrees, it becomes a mandatory SearchCriteria constraint, so only that category's candidates reach ranking. CandidateRetriever also checks this boundary independently of DAO filtering. A higher cosine from headphones or a watch cannot outrank a tablet because it is not eligible for the selected tablet search.

No eligible matches returns an empty list; the system does not fill it with another category. Unknown selected-region category requires the user to choose a type before searching. Manual API crops must likewise resolve a category through `imageCategoryID`, the normal category filter or explicit text. Full-image search remains available without a declared category and then uses the existing automatic retrieval heuristic; it does not guarantee a single object type.

Exactly one detected region is selected automatically. For multiple detections no arbitrary first object is selected: the interface shows that the full image is active and asks the user to select the intended region. The full-image option clears the prior region category. A manual whole-image category is also supported.

## Overlapping boxes

Boxes are visual outlines and their numbered labels are interactive buttons. The overlays do not intercept pointer events inside other boxes; visible labels can be clicked, and every region remains accessible through the region dropdown even when labels overlap. The active outline is highlighted. Keyboard users can use either labelled buttons or the dropdown.

## Data and architecture

View → SearchRoutesService → SearchService → CandidateRetriever/ProductDAO → SoftReranker. Category mapping belongs to the model AI adapter, query validation to SearchService and product filtering to retrieval/data access. No new entity or table was added. SearchQuery.searchCriteria stores the resolved category; ImageQuery.selectedRegion stores the crop. Responses expose imageSelection with the resolved category and selection source, and show the restricted group in the search message.

Inference caches stay keyed by image/model/crop. Changing only the category can reuse the same embedding, but candidates are fetched and filtered again; previous results are not cached. Existing ranking weights, product metadata/embeddings and recommendation behaviour were not changed.

## Verification

- Full Python suite: 124 passed, including all five label mappings, three-object detection responses, adversarial high-cosine products from wrong categories, manual category correction, no cross-category fallback, invalid categories, text/filter conflicts, unresolved crop rejection and image-vector reuse.
- Real MySQL/HTTP integration verifies category transmission, response filtering and persisted category/crop in an isolated retained database.
- Frontend TypeScript/Vite production build passed. Edge E2E uses three overlapping fixture boxes, selects tablet, corrects to phone, checks multipart category/crop, and confirms the full-image option clears both. The first browser run exposed overlay interception; the UI was corrected and rerun successfully.
- Real-model smoke uses a controlled composite of known catalogue phone/tablet/headphone photos with known crop coordinates. Each crop must return only its selected category and include its source in the top five. Detector responses are separately checked for category IDs. This is a pipeline consistency test, not a guarantee that OWL-ViT labels every new customer photo correctly.

Backend restart and browser refresh are required to load the change. If the detector mislabels a phone as a tablet, the manual category correction remains necessary; this fix enforces the chosen type rather than claiming improved detector accuracy.
