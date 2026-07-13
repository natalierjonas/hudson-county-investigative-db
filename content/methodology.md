## Why this data? What's the issue?

Hudson County is the smallest and most densely populated county In New Jersey, home to ¾ of a million people. In Jersey City — referred to as "Wall Street West" by some and home to 3% of the state's population — more than 50% of renters are cost-burdened. New developments now dot the waterfront and are spreading inward into once-undesirable neighborhoods, which are pricing out long-time residents and largely affecting communities of color. Homelessness in Hudson County increased by 24% in 2024, compared to the year prior, the same year a number of new developments opened in Hudson County. Many of these developments allocate around 20% as affordable units.

With Jersey City's Mayor Fulop at the helm, housing development has boomed — even inspiring New York's Mayor Mamdani to follow Fulop's lead. But, for low- or middle-income residents, rising rents and a dearth of available affordable housing/loan approvals have pushed long-term residents out.

Bipartisan bills attempting to slow corporate ownership of single-family homes have been circulating on the federal and statewide level, some even being signed into law. Still yet, the 21st Century Road to Housing Act, which has been hailed as one of the biggest pieces of housing legislation to be heard by Congress in decades, passed in June but hasn't been signed by President Trump. The law would restrict corporate and institutional ownership of single-family homes in many cases, but does not address most of the types of residential buildings being bought up in Hudson County (and, the law remains stalled).

According to an analysis of 2024 HMDA data alone, nearly half of all loans in Hudson County are in a census tract that has at least one subsidized property. The average loan in a low-income tract in Hudson County hovered around $360,000 to $527,000, but Black applicants are denied mortgages at double the rate of White applicants in the same tracts (30.9% versus 19%). Many — mostly people of color — are unable to receive loans because of systemic racism in mortgage dealings. The income requirements for receiving such a loan are upwards of $175,000, which then isn't "low-income," inherently freezing out such applicants. Low-income renters don't earn enough nor can they borrow enough to get a loan, despite affordable housing supposedly being made available to such prospective renters.

Similarly, many large private creditors, investors and lenders — such as Kiavi Funding, LendingOne, and ABL RPC — exclusively report "Race Not Available," thereby shielding loanees from regulatory considerations regarding racial disparity in lending. Potentially, this is just a pitfall of HDMA data, or it hints at a larger, gameable loophole in mandatory ethnographic and racial data reporting.

Cursory analysis using the database shows that tracts with majority-private ownership of subsidized housing have a median family income of $86,520, which is well below the $125,337 average in tracts with no subsidized housing. Similarly, all "majority privately owned" tracts are in low, moderate, or middle income brackets. Applicants who are people of color and who reside in lower-income tracts are consistently denied loans, particularly in private-owned yet subsidized housing tracts.

Ownership structures listed as "Profit Motivated," "For Profit," and "Limited Dividend" (originating from NHPD data) control nearly half of all NHPD-tracked subsidized units in Hudson County, whereas "Public Entity" (housing authorities) control just 35% and non-profits own just 5%. Just 21 addresses (0.2% of all addresses) control 726 parcels in the county, nearly one in twelve of all dwelling units — and nearly 34% of all apartment parcels have an out-of-state mailing address.

Private owners control half of all subsidized units in Hudson County and mortgage applicants who are low-income or people of color are disproportionately denied loans for such properties as the county gentrifies. "Wall Street West" is the site of a lot of the most drastic change, as white male applicants receive loans easier and move into town. So, the influx of institutional investors into Hudson County seems to be contributing to redlining on the New Jersey Waterfront, forcing Black and Hispanic residents out of their homes while denying mortgage applications.

As I researched and wondered about the state of affordable housing in Hudson County and the mortgage lending crisis, I decided to create a database to explore the issue and draw some real, concrete conclusions.

A few questions this database intends to answer: Who owns Hudson County's affordable housing? Are low-income residents getting affordable units? Is redlining at play? Which investors and private creditors are most interested in this county? Who is being displaced?

## Where is the data from? Why this data?

To create this database, I merged 2024 Home Mortgage Disclosure Act (HMDA) data, Federal Financial Institutions Examination Council (FFIEC) data, New Jersey MOD IV records with National Housing Preservation Database (NHPD) data, all segmented to Hudson County (county code 34017).

The data was retrieved from requests to relevant agencies, via APIs and by downloading the static datasets from the site, if possible. The time frame of data aggregated varies, including all tax-year info for some properties to illustrate ownership changes, but datasets such as HMDA and FFIEC are dated to 2024. This is because that data was most complete, and that year a number of housing developments across Hudson County opened and began accepting rental applications.

- HMDA - For understanding racial disparities in individual mortgage lending and who is trying to become property owners. Illuminates trends in unequal lending and denials, a gaping lack in reported racial data.
- FFIEC - For greater clarity on distressed and underserved tracts, identifying income level at the tract level and median family income. Provides socioeconomic context regarding where private ownership is concentrated to then layer with results gleaned from the other merged datasets.
- MOD-IV - For property tax assessment records from the county tax assessor. Provides information on owner name, sale price and date, property class per parcel and clarity on LLC/out-of-state ownership and buying trends. Extends possible analyses from subsidized housing ownership to the entire private rental stock/trend analysis. Also, adds in "naturally-occuring" affordable housing data that private investors can buy easier due to no subsidy existing and can be used to identify property flipping from individual/non-profit ownership to private/LLC ownership.
- NHPD - For tracking every federally or state-subsidized affordable housing unit in the county. Also, provides information on current ownership (with owner names) and when the subsidy expires, useful since the expiration of Section 8/LIHTC contracts are often when private investors swoop in and buy. Also, this data helps elucidate if/when affordable housing or subsidized housing is being sold off, and to who.

## Data cleaning, decisions and limitations:

I dropped all columns with "NULL" or "NO" for all, such as "distressed-remote-rural" or "distressed poverty," both of which Hudson County doesn't track or that don't apply to the area. I also removed rows with no tract data, which was a negligible number.

In order to best serve my research questions and the intended use cases for this database (private-credit's imposition into Hudson County/ private institutional acquisition of housing units/affordable housing units/racist lending and mortgage denials), I removed columns that didn't pertain. Notable columns I kept are: "tract_income_level," "tract_median_family_income," "nhpd_private_owned_properties/units," and "modiv_out_of_area_owner_parcels."

I also added in partial tract-located, parcel-level MOD-IV data to the "parcel ownership" table, which can be queried on the "Unmask ownership" page, to power mailing-address analyses — most useful in analyzing out-of-state ownership and LLC prevalence. The "Unmask ownership" database uses NHPD property-level data (not tract-aggregated) with owner names and classifications with MOD-IV data, which doesn't include owner names. So, this table provides the best approximation of those owners beyond tract-level aggregations by normalizing mailing addresses via "owner_mailing_key" to apartment parcels, a well-suited proxy for ownership identification. This secondary database, built into the main branch, also is searchable and filterable with a reverse-lookup capacity.

A limitation of this data is that the level in which information is tracked differs between datasets so the methodology needs to be read prior to using the database (a.k.a., the data has disclaimers). Loan level varies because that is the nature of HMDA data. All other merged data is at the census-tract or property-level, and was left-joined to the loan with census-tract.

Loan-level columns (race, ethnicity, sex, action, denial reason, income) describe one specific mortgage application.

Tract-level columns describe the census tract the loan is in — not the specific building or loan. The same tract-level value repeats across every loan application in that tract, so summing or averaging a tract-level column across rows will overcount it once per loan rather than once per tract. A tract with no matching NHPD or MOD-IV record will show no value or "No subsidized housing," (for example), rather than a dropped row to maintain database integrity.

Rows are tagged via "column-metadata" to show the level of analysis (loan- or tract-level) and ensure a user doesn't misinterpret or misaggregate the data.

Also, "Avg. parcels per owner" divides MOD-IV's apartment parcel count by the count of distinct owner mailing addresses for that same tract. A high value signifies relatively few owners (potentially a single LLC or holding company) control many parcels.

The database also has many "-" because of data missing from the merged databases themselves, which isn't a bug with this database. The accuracy of the data was verified with test runs with various addresses, owners and tract-types, but all conclusions drawn from the database would have to be individually verified or run by statisticians if statistical analysis is involved, particularly to account for dropped rows and in relation to any aggregate findings. Similarly, applicant income data, race, ethnicity, sex are all extracted from the HMDA database, which is self-reported or observed by a lender and subject to bias or misreporting.

## TLDR:

This database, for use by residents, researchers or journalistic investigations, can elucidate who is buying up subsidized affordable housing (Section 8, LIHTC, etc.) in a county hit hard by gentrification. A user can search and filter the database to explore ownership type, demographics, income levels as well as where high levels of LLC/private ownership is located. Future database-building and research can address some of the challenges inherent to the data, such as racial and ethnic makeup of census tracts, and finding either more individual-level data to avoid jumping from loan- to census-level.

Some findings after querying the database that could inspire future research or inquiry:

- An out-of-state address, a P.O. Box 351 in Cedarhurst, NY, is the ownership address for 62 apartment parcels with 872 total units, largely in Union City.
- This address is linked to two LLCs with past-due filings.
- One owner, whose address is also a P.O. box, bought 11 subsidized buildings in a Jersey City tract, owning 62 buildings total.
- This tract, 34017005801, lost a number of its affordable housing protections to lapsed regulations and subsidies. Now, there are only 5 subsidized properties. Now, this tract has many residents moving out (housing sales) and 32 parcels owned by out-of-area landlords.
- Ten tracts in the county (including the aforementioned) show a pattern of inactive subsidies leading to private ownership.
- Low-income tracts have the most inactive subsidies and the highest rate of out-of-area ownership of any other income tract (despite having the fewest apartment buildings overall) — as well as 2-3x the rate of lapsed subsidy contracts.
- Upper-income tracts had the lowest rate of out-of-area ownership, illustrating a gaping disparity in what areas are owned by out-of-state, institutional investors.
