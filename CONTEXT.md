# aircraft-taxonomy-db

A data pipeline that classifies aircraft by role and configuration (not by operator or nationality), and serves the result as CSV files and a REST API.

## Language

**Aircraft record**:
One row in an aircraft database CSV — one physical aircraft, identified by its ICAO hex code, carrying Registration, Operator, Type, ICAO Type, CMPG, Category, and Tag 1/2/3, in a fixed column order.

**Category**:
The primary taxonomy classification of an aircraft record — what it *is* (e.g. "Fighter / Interceptor", "Cargo Freighter"), drawn from a fixed allowlist.
_Avoid_: Type (that's the manufacturer's model designation, a different field).

**Tag 1 / Tag 2 / Tag 3**:
Three secondary classification facets layered on top of Category — mission role, configuration, and airframe/engine characteristics respectively. Each has its own fixed allowlist.

**Type / ICAO Type**:
The manufacturer's model designation for an aircraft record. Type is the free-text name (e.g. "A320-200"); ICAO Type is its short designator code (e.g. "A320").
_Avoid_: Category (Type describes the airframe model; Category describes its taxonomy role).

**Match key**:
The canonical identifier used to join a raw Type/ICAO Type string to its taxonomy classification in the lookup table. Always uppercase, 2-5 alphanumeric characters, e.g. "A320".
_Avoid_: Lookup key (a related but distinct concept — see below).

**Lookup key**:
The case-insensitive form of a raw Type/ICAO Type string, used only to search the lookup table in memory. Never stored or written to a file — a match key is what gets written.
_Avoid_: Match key.

**Lookup table**:
The reference dataset mapping a match key to its canonical Category, Tag 1, Tag 2, Tag 3, and normalized Type name.

**Alias**:
A mapping from a raw, messy Type string (e.g. "A320-200", "Airbus A320") to the match key it should resolve to.

**Normalization**:
The process of resolving an aircraft record's raw Type/ICAO Type against the lookup table and aliases to fill in its Category and Tags. A record that can't be resolved is routed to a review queue instead.

**Review queue**:
The holding area (a `review/*.csv` file) for aircraft records or reference rows that failed normalization or validation and need manual triage before they can be trusted.

**Promotion**:
Moving a row out of a review queue and into the canonical lookup table or alias list, either by manual review or because it scored above a confidence threshold.
