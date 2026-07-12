## Data sources

- **Mortgage applications:** 2024 HMDA Snapshot National Loan-Level Dataset (FFIEC), filtered to Hudson County, NJ (`county_code = '34017'`).
- **Tract income classification:** FFIEC census data, joined by census tract to attach each tract's income classification (low/moderate/middle/upper) and median family income.
- **Subsidized housing:** National Housing Preservation Database (NHPD), aggregated to the census-tract level — property counts, unit counts, and active/inactive subsidy counts.
- **Property ownership/sales:** NJ MOD-IV (Municipal Database of the Division of Taxation) property assessment records, aggregated to the census-tract level — parcel counts, recent sale prices, and out-of-area owner mailing addresses.

## Unmask ownership page — what it adds

The main search table only has tract-level aggregates, whereas the ["Unmask ownership"](/ownership) page reveals:

- **Subsidized housing owners:** NHPD-tracked properties in Hudson County, each with owner name, owner type (For Profit / Non-Profit / Public Entity / Limited Dividend), manager name/type, unit count, and subsidy status — extracted from the NHPD's full property-level file rather than the tract-aggregated counts used in Search.
- **Private housing ownership concentration:** Hudson County apartment parcels from NJ's MOD-IV tax assessment data, grouped by owner mailing address to show how many parcels are registered to a location, the standard proxy for one owner (often an LLC or a shared registered agent) controlling multiple properties under different names. The user can click through to see the individual parcels behind an address.

## Two levels of granularity — read before analyzing

This table mixes two kinds of data at different levels of detail due to the nature of the datasets that were joined:

- **Loan-level** columns (race, ethnicity, sex, action, denial reason, income) describe one specific mortgage application.
- **Tract-level** columns (everything from tract income level onward, including all NHPD and MOD-IV fields) describe the census tract the loan is in — not the specific building or loan. **The same tract-level value repeats across every loan application in that tract**, so summing or averaging a tract-level column across rows will overcount it once per loan rather than once per tract.

## Known limitations

- Applicant income data, race, ethniciy, sex are all extracted from the HMDA database, is self-reported or observed by a lender.
- NHPD and MOD-IV fields are aggregated at the tract level, so a tract with no matching NHPD or MOD-IV records will show blank/zero values rather than a dropped row.

## Necessary considerations

- **Ownership profile** groups each tract's subsidized housing by comparing NHPD's private, public, and nonprofit owned-property counts (whichever group has the most properties in that tract gets the relevant label; a tract with no NHPD-tracked properties is labeled "No subsidized housing").
- **Avg. parcels per owner** divides MOD-IV's apartment parcel count by its count of distinct owner mailing addresses for that tract. A high value means relatively few owners (potentially a single LLC or holding company) control many parcels — a signal worth checking against actual deed/owner names, not a confirmed finding on its own.
