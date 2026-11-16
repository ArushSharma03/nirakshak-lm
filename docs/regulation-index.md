# Indian packaged goods regulation research index

**Research retrieved:** 12 November 2026. **Use:** source discovery and a cautious crosswalk for the draft food/grocery profile, not legal advice or a compliance decision.

Machine-readable source and rule mapping: [`rules/regulation-index.json`](../rules/regulation-index.json).

## Official sources reviewed

| Instrument | Official source | What was verified | Consolidation status |
|---|---|---|---|
| Legal Metrology (Packaged Commodities) Rules, 2011 (LMPC) | [Department of Consumer Affairs rules and amendments index](https://consumeraffairs.gov.in/pages/legal-metrology-act); [department compilation](https://consumeraffairs.gov.in/public/upload/admin/cmsfiles/whatsnews/Book_on_Legal_Metrology_Packaged_Commodities_Rules%2C2011_with_all_amendments_whatsnews.pdf) | Rules 6(1)(a)–(da), 6(2), 24 and 26 in the department compilation | The compilation cover says 9 May 2022. The Department page lists later amendments through 13 February 2026. It is not safe to treat the 2022 compilation as current consolidated law; amendment effects and commencement were not reconciled in full. |
| Food Safety and Standards (Labelling and Display) Regulations, 2020 | [FSSAI amendments index](https://www.fssai.gov.in/food-law/regulations/amendments/labelling-display); [FSSAI Version VIII compilation](https://www.fssai.gov.in/docs/food-law/regulations/Comp_Labelling%20Display_Version%20VIII_09_09_2025.pdf) | Regulations 1, 2(r), 4(1)–(8), and the opening requirements of Regulation 5 | The compilation is Version VIII, dated 9 September 2025. The official amendment index surfaced an amendment dated 24 March 2026. Its full effect and a later consolidated text were not reconciled here. |

## Key verified scope points

- LMPC Rule 6 provides general packaged-commodity declarations, but the text itself contains food-specific interactions with the Food Safety and Standards Act and rules. Rule 6(1)(d) and Rule 6(da) include food-specific provisos. Do not apply a generic LMPC field literally without checking those clauses and current amendments.
- LMPC Rule 24 separately addresses wholesale packages. Rule 26 contains exemptions. Exemptions depend on the package and product facts and the currently effective text.
- FSSAI Regulation 1 says the regulations prescribe labelling requirements for pre-packaged foods and display of essential information at premises where food is manufactured, processed, served and stored. Regulation 2(r) defines pre-packaged food.
- FSSAI Regulation 4 governs general label presentation and online pre-sale disclosure, with express exceptions. Regulation 5 and its sub-regulations/schedules provide detailed food declarations; product category and applicable exceptions matter.
- The existing `rules/food_grocery.json` profile is an MVP draft. It has Legal Metrology fields but does not encode FSSAI-specific declarations or amendment history. The mapping in the JSON is therefore marked partial, not an approval of the profile's legal accuracy.

## Unknown / not established

- The in-force effect and commencement of every post-compilation amendment as of the retrieval date.
- A Gazette-reconciled current consolidated text for either instrument.
- Applicability to any particular SKU, package size, import, retail/wholesale channel, online listing or food subcategory.
- Whether the profile's field wording and effective dates correctly cover every relevant exception, product-specific regulation, or later amendment.

Before using these data for enforcement or packaging decisions, reconcile the applicable Gazette notifications and FSSAI directions against the product facts and obtain qualified legal review. No numeric threshold or exception beyond what appears in the cited text is inferred by this index.

## Browser verification and document lookup

The parent agent checked both official indexes in the T3 browser on 12 November 2026. The JSON includes 36 LMPC-related links and five FSSAI amendment links with exact official titles and URLs. These include advisories and corrigenda, not just amendments. Their status is `listed_on_official_index`; notification contents and commencement are not implied. Earlier research claims of LMPC amendments on 29 May and 21 September 2026 were not confirmed on that page and were removed.

`GET /profiles/regulations?q=consumer` searches the checked-in index without depending on live websites. Omitting `q` returns the full index. The response always retains retrieval date, source limitations and draft-profile coverage. This lookup does not change the compliance profile or determine law in force.
