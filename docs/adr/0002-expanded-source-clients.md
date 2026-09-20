# ADR 0002: Expanded set of source clients

Date: 2026-09-20
Status: accepted

## Context

The plan gave Find six source clients: OpenAlex, Semantic Scholar, arXiv, PubMed, Crossref and Unpaywall. The owner asked for wider coverage, naming IEEE, Springer, MICCAI and ResearchGate.

Three of the six are indexes rather than publishers. OpenAlex, Crossref and Semantic Scholar already carry IEEE, Springer, ACM, Elsevier and Nature records, and MICCAI proceedings are Springer LNCS with Crossref DOIs. Adding a publisher client for those venues would add a second path to records already in the store rather than new records, which makes the dedup step in Find harder without raising recall.

The real question is which sources hold records the three large indexes miss, or hold full text that Unpaywall does not reach. Section 14 names "scope creep in Find (more sources)" as the project's highest likelihood and highest impact risk, and rule 7 requires a tool to be evaluated before it is extended. Section 6.7 step 3 already specifies a per-channel recall ablation, which is the mechanism for deciding whether a source earns its place.

## Decision

Expand the source list to twelve, split across two phases.

Phase 0 builds eight clients: the original six, plus DBLP (free, no key, canonical computer science venue metadata) and Europe PMC (free, no key, superset of PubMed with open-access full text as XML). PubMed E-utilities is kept alongside Europe PMC for elink and for records Europe PMC mirrors late.

Phase 1 adds four more on a `tool/find-sources` branch, each admitted only if the recall ablation in section 6.7 shows it contributes: OpenReview (ML venue submissions and reviews before DOIs exist), CORE (open-access full text from institutional repositories, as a fallback when Unpaywall has no link), Springer Nature (free key, 100 requests per minute on the open access tier, the one publisher API worth having because MICCAI is Springer), and bioRxiv with medRxiv (one client, two servers, preprints arXiv does not carry).

Rejected: IEEE Xplore, whose API requires membership of a subscribing institution, breaking rule 9 and making `doctor` fail on a fresh machine, while its content is already in OpenAlex and Crossref. ResearchGate, which has no public API, forbids automated access in its terms, and hosts author uploads that are not licensed for redistribution. Google Scholar, which has no API and blocks automated access. Scopus and Web of Science, which are paid and institutional.

## Consequences

Easier: better computer science venue metadata for filtering and dedup, better full text for Read via Europe PMC XML and later CORE, and earlier coverage of ML venues via OpenReview.

Harder: Phase 0 Day 6 to 8 grows from six clients to eight, each needing a rate limiter, retries, a disk cache, field mapping and a cassette test. Expect Phase 0 to run one to three days long. Dedup carries more duplicate paths, so the merge log in section 6.5 matters more.

Plan sections changed: 2.1 and 5.2 client table and 5.3 checklist in the full plan and the Phase 0 plan, 6.3 step 2 channel sources, 15.1 data APIs.

## Alternatives considered

- All twelve clients in Phase 0: one consistent pass over the client layer, but roughly a week added to a two week phase and five clients whose value cannot yet be measured; rejected.
- Six clients in Phase 0 with every addition deferred to Phase 1: strictest reading of rule 7, but DBLP and Europe PMC are keyless and cheap and change what the store can reach from the first run; rejected as too conservative.
- Publisher clients for IEEE and Springer as the primary route to those venues: misreads indexes as gaps; the coverage is already there through OpenAlex and Crossref.
