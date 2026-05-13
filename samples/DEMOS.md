# Paperwise Demo Screenshots

This document defines reusable public demo scenarios for Paperwise screenshots, website copy, and local product walkthroughs. Keep it updated when the UI changes so screenshots can be regenerated without re-inventing sample data or prompts.

## Sample PDFs

The sample PDF corpus is in `samples/pdfs/`.

- Source: official Federal Reserve FOMC statement PDFs
- Coverage: 2025-05-07 through 2025-12-10
- Intended use: grounded Q&A demos, document-list population, and realistic PDF preview screenshots.

Available PDFs:

- `samples/pdfs/monetary20250507a1.pdf`
- `samples/pdfs/monetary20250618a1.pdf`
- `samples/pdfs/monetary20250730a1.pdf`
- `samples/pdfs/monetary20250917a1.pdf`
- `samples/pdfs/monetary20251029a1.pdf`
- `samples/pdfs/monetary20251210a1.pdf`

For the single-document detail screenshot, use:

- `samples/pdfs/monetary20251210a1.pdf`

This gives the screenshot a real PDF source while avoiding any private user document.

## Website Screenshot Outputs

Generated public screenshots should live in `samples/screenshots/`.

Current screenshot set:

- `samples/screenshots/documents-library.png`: main document library view.
- `samples/screenshots/ask-your-docs-medical-bill.png`: grounded Q&A across EOB, clinic invoice, and HSA records.
- `samples/screenshots/ask-your-docs-utility-bills.png`: grounded Q&A that summarizes multiple utility bills into a table.
- `samples/screenshots/ask-your-docs-vendor-renewal.png`: grounded company Q&A across contract, security review, procurement policy, and usage export.
- `samples/screenshots/document-detail.png`: single-document detail view using a sample PDF.
- `samples/screenshots/processing-queue.png`: active processing queue with progress states.

The current document-library, Ask Your Docs, and processing screenshots are `1440x980`.
The single-document detail screenshot is `1440x1400` so the PDF preview can show the full first page.

## Demo Account Treatment

Screenshots should look like a real Paperwise account, but must not expose real user data.

Replace visible account identity with:

- Email: `demo@paperwise.app`
- Avatar initials: `DM`

Avoid showing:

- Real email addresses.
- Real document names.
- Real file names from private documents.
- Real addresses, parcel numbers, member IDs, claim IDs, policy IDs, account numbers, or dollar amounts from actual documents.

## Demo Document Library Data

Use a balanced household-document library for the document-list screenshot:

- `2026 Property Tax Notice`
  - Correspondent: `King County Treasury`
  - Tags: `Tax`, `Home`
  - Type: `Notice`
  - Date: `Apr 18, 2026`
  - Size: `412 KB`
- `Blue Shield Explanation of Benefits`
  - Correspondent: `Blue Shield of CA`
  - Tags: `Medical`, `Insurance`
  - Type: `EOB`
  - Date: `Apr 9, 2026`
  - Size: `1.2 MB`
- `Fidelity Brokerage Statement`
  - Correspondent: `Fidelity Investments`
  - Tags: `Finance`, `Investments`
  - Type: `Statement`
  - Date: `Mar 31, 2026`
  - Size: `824 KB`
- `Solar Installation Warranty`
  - Correspondent: `SunPeak Energy`
  - Tags: `Home`, `Warranty`
  - Type: `Contract`
  - Date: `Mar 22, 2026`
  - Size: `2.4 MB`
- `Kindergarten Enrollment Packet`
  - Correspondent: `Cedar Grove School`
  - Tags: `Family`, `School`
  - Type: `Form`
  - Date: `Mar 14, 2026`
  - Size: `668 KB`
- `Mortgage Interest Form 1098`
  - Correspondent: `Pacific Home Lending`
  - Tags: `Tax`, `Mortgage`
  - Type: `Tax Form`
  - Date: `Feb 1, 2026`
  - Size: `306 KB`
- `Annual Portfolio Summary`
  - Correspondent: `Vanguard`
  - Tags: `Finance`, `Investments`
  - Type: `Statement`
  - Date: `Jan 24, 2026`
  - Size: `948 KB`
- `Dental Claim Estimate`
  - Correspondent: `Delta Dental`
  - Tags: `Medical`, `Insurance`
  - Type: `Estimate`
  - Date: `Jan 12, 2026`
  - Size: `533 KB`
- `Appliance Repair Receipt`
  - Correspondent: `Maple Appliance Co.`
  - Tags: `Home`, `Receipt`
  - Type: `Receipt`
  - Date: `Dec 28, 2025`
  - Size: `1.8 MB`
- `Auto Policy Renewal`
  - Correspondent: `Northwest Mutual Auto`
  - Tags: `Insurance`, `Auto`
  - Type: `Policy`
  - Date: `Dec 14, 2025`
  - Size: `516 KB`

Suggested sidebar counts:

- All documents: `248`
- Starred: `18`
- Processing: `3`
- Needs attention: `2`
- Finance: `64`
- Medical: `31`
- Tax: `28`
- Home: `22`
- Statement: `72`
- Notice: `39`
- Contract: `16`

## Single Document Screenshot

Use `samples/pdfs/monetary20251210a1.pdf` as the source document for the single-document screenshot.

Recommended demo metadata:

- Title: `FOMC Statement - December 2025`
- Status: `READY`
- Correspondent: `Federal Reserve`
- Date: `2025-12-10`
- Type: `Statement`
- Tags: `Finance`, `Policy`, `Federal Reserve`
- File meta: `application/pdf`

Reason: it is a real public PDF, visually credible, and safe to show.

## Ask Your Docs Screenshots

Use grounded Q&A scenarios that require information from multiple private or internal documents.

### Medical Bill Follow-Up

Thread title:

- `Pediatric visit bill follow-up`

Conversation:

- User: `Why did we still get a bill after insurance processed the pediatric visit?`
- Assistant: `The EOB says the visit was covered, but $186.40 was applied to the deductible. The pediatric clinic invoice shows the same patient responsibility due May 18. The HSA activity statement does not show a matching payment yet; it only shows an earlier $42.15 lab payment, so this office-visit balance likely still needs to be paid.`
- Sources:
  - `Blue Shield Explanation of Benefits · p. 1`
  - `Pediatric Clinic Invoice · p. 1`
  - `HSA Activity Statement · p. 2`
- User: `What should I pay from the HSA?`
- Assistant: `Pay the $186.40 clinic invoice from the HSA, assuming the visit details match your records. Keep the EOB and invoice together for your records.`
- Sources:
  - `Blue Shield Explanation of Benefits · p. 1`
  - `Pediatric Clinic Invoice · p. 1`
  - `HSA Activity Statement · p. 2`

Use fake sidebar threads:

- `Pediatric visit bill follow-up`
- `PG&E bill comparison`
- `Vendor renewal review`

Screenshot output:

- `samples/screenshots/ask-your-docs-medical-bill.png`

### Utility Bill Table

Thread title:

- `PG&E bill comparison`

Conversation:

- User: `Compare our PG&E bills for January through April and show the trend in a table.`
- Assistant: `I found four monthly PG&E statements and summarized the total due, electricity usage, and gas usage in a table. The total bill rose from $214.38 in January to $268.91 in April, mainly because electricity usage increased in March and April.`
- Sources:
  - `PG&E Statement - Jan 2026 · p. 1`
  - `PG&E Statement - Feb 2026 · p. 1`
  - `PG&E Statement - Mar 2026 · p. 1`
  - `PG&E Statement - Apr 2026 · p. 1`
- Composer follow-up: `Which month should I look at first if I want to reduce usage?`

Screenshot output:

- `samples/screenshots/ask-your-docs-utility-bills.png`

### Vendor Renewal Review

Thread title:

- `Vendor renewal review`

Conversation:

- User: `Are we okay to renew Acme Analytics for another year, or is there a contract issue?`
- Assistant: `There are two items to resolve before renewal. The order form renews on June 30 for 25 seats at $18,000 annually, but the vendor security review expires June 15. The procurement policy requires an active security review before renewal.`
- Sources:
  - `Acme Analytics Order Form · p. 1`
  - `Vendor Security Review · p. 3`
  - `Procurement Policy · p. 2`
- User: `Can we reduce the renewal before signing?`
- Assistant: `Likely yes. The latest usage export shows only 14 active users, so you can ask procurement to quote fewer seats before signing, as long as the security review is refreshed first.`
- Sources:
  - `SaaS Usage Export · p. 1`
  - `Acme Analytics Order Form · p. 1`
  - `Procurement Policy · p. 2`

Screenshot output:

- `samples/screenshots/ask-your-docs-vendor-renewal.png`

## Processing Queue Screenshot

Use three fake active jobs:

- `Solar Installation Warranty`
  - Status: `PROCESSING`
  - Stage: `Classifying`
  - Progress: `72%`
  - File: `application/pdf`
- `Receipt Photo - Appliance Repair`
  - Status: `PROCESSING`
  - Stage: `OCR`
  - Progress: `38%`
  - File: `image/jpeg`
- `2026 Auto Policy Renewal`
  - Status: `RECEIVED`
  - Stage: `Queued`
  - Progress: `12%`
  - File: `application/pdf`

This screenshot is useful for showing that Paperwise exposes OCR and metadata-processing progress without requiring page refreshes.

## Capture Workflow

1. Log into the local Paperwise app with the local demo or development account.
2. Import the PDFs under `samples/pdfs/` if the local account does not already have them.
3. For the single-document screenshot, open the document created from `samples/pdfs/monetary20251210a1.pdf`.
4. Navigate to the target page in the running app.
5. If needed, inject demo labels/counts into the browser DOM only.
6. Replace visible account identity with `demo@paperwise.app`.
7. Capture screenshots to `samples/screenshots/`.
8. Visually inspect every screenshot for:
   - Real email addresses.
   - Real names or private document titles.
   - Real IDs, addresses, account numbers, or medical/financial details.
   - Overlapping UI text.
   - Empty states where a populated demo state is expected.

Do not save demo-only labels back through the UI. Browser DOM replacement should be transient unless the imported source files are already public samples.
