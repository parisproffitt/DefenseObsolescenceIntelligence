# Ontology as built (mirror)

Created through the Palantir MCP on global branch `continuum-ontology`
(`ri.branch..branch.f7823b55-60b9-4fb2-b5cf-13fe46b023a8`) of the CONTINUUM Ontology
(`ri.ontology.main.ontology.f96d0a93-c559-4094-843c-ed770b5c83a0`). Foundry prefixes
every id with the namespace `one4jwoo.`. The branch reaches the main Ontology when its
proposal is approved (`docs/MANUAL_STEPS.md`, step 1).

Property ids equal the dataset column names; API names are their camelCase form.

## Object types (12)

| Object type (id) | API name | Backing dataset | Primary key | Title |
|---|---|---|---|---|
| Program (`one4jwoo.program`) | `Program` | `clean/programs` | `program_id` | `name` |
| Assembly (`one4jwoo.assembly`) | `Assembly` | `clean/assemblies` | `assembly_id` | `name` |
| Part (`one4jwoo.part`) | `Part` | `clean/parts` | `part_number` | `part_number` |
| BOM Line (`one4jwoo.bom-line`) | `BomLine` | `clean/bom_lines` | `bom_line_id` | `part_number` |
| Inventory Position (`one4jwoo.inventory-position`) | `InventoryPosition` | `clean/inventory` | `inventory_id` | `inventory_id` |
| Notice (`one4jwoo.notice`) | `Notice` | `clean/notices` | `notice_id` | `notice_id` |
| Notice Line (`one4jwoo.notice-line`) | `NoticeLine` | `clean/notice_lines` | `notice_line_id` | `part_number` |
| Impact Case (`one4jwoo.impact-case`) | `ImpactCase` | `analysis/impact_cases` | `case_id` | `title` |
| Review Flag (`one4jwoo.review-flag`) | `ReviewFlag` | `analysis/review_flags` | `flag_id` | `flag_type` |
| Course of Action (`one4jwoo.course-of-action`) | `CourseOfAction` | `analysis/coas` | `coa_key` | `name` |
| Procurement Request | `ProcurementRequest` | `ontology/procurement_requests` | `request_id` | `request_id` |
| Engineering Review | `EngineeringReview` | `ontology/engineering_reviews` | `review_id` | `review_id` |

The last two are written only by the *Approve course of action* action (D-18).

## Link types (all one-to-many; foreign key on the "many" side)

| Link (id) | One | Many | Key |
|---|---|---|---|
| `one4jwoo.program-to-assembly` | Program | Assembly | `program_id` |
| `one4jwoo.assembly-to-bom-line` | Assembly | BOM Line | `assembly_id` |
| `one4jwoo.part-to-bom-line` | Part | BOM Line | `part_number` |
| `one4jwoo.program-to-inventory-position` | Program | Inventory Position | `program_id` |
| `one4jwoo.part-to-inventory-position` | Part | Inventory Position | `part_number` |
| `one4jwoo.notice-to-notice-line` | Notice | Notice Line | `notice_id` |
| `one4jwoo.program-to-impact-case` | Program | Impact Case | `program_id` |
| `one4jwoo.notice-to-impact-case` | Notice | Impact Case | `notice_id` |
| `one4jwoo.part-to-impact-case` | Part | Impact Case | `part_number` |
| `one4jwoo.notice-to-review-flag` | Notice | Review Flag | `notice_id` |
| `one4jwoo.program-to-review-flag` | Program | Review Flag | `program_id` |
| `one4jwoo.part-to-review-flag` | Part | Review Flag | `part_number` |
| `one4jwoo.impact-case-to-course-of-action` | Impact Case | Course of Action | `case_id` |
