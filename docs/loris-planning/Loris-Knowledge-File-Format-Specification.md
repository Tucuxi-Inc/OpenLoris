# **Loris Knowledge File Format Specification**

**Version:** 1.0 **Last Updated:** January 2026

This document defines the standard format for knowledge files exported by Loris Web App to the `/Loris-Knowledge` Google Drive folder for consumption by MoltenLoris.

---

## **File Naming Convention**

\[Category\]-\[Subcategory\].md

**Examples:**

* `Contracts-Vendor-Agreements.md`  
* `HR-Leave-Policies.md`  
* `Legal-NDA-Guidelines.md`  
* `IT-Security-Procedures.md`  
* `FAQ-General.md`

**Rules:**

* Use Title-Case with hyphens (no spaces, no underscores)  
* Keep names under 50 characters  
* Category should match Loris subdomain/category names  
* One file per topic area (don't create too many small files)

---

## **File Structure**

Every knowledge file follows this structure:

\---  
loris\_version: 1.0  
category: \[Category Name\]  
subcategory: \[Subcategory Name\]  
organization\_id: \[UUID\]  
subdomain\_id: \[UUID\]  
exported\_at: \[ISO 8601 timestamp\]  
exported\_by: loris-web-app  
fact\_count: \[number\]  
qa\_count: \[number\]  
rule\_count: \[number\]  
checksum: \[MD5 hash of content below frontmatter\]  
\---

\# \[Category Name\]: \[Subcategory Name\]

\> \*\*Last Updated:\*\* \[Human-readable date\]  
\> \*\*Source:\*\* Loris Knowledge Base  
\> \*\*Confidence Level:\*\* This document contains verified organizational knowledge.

\---

\#\# Quick Facts

\[Bullet list of core facts \- highest confidence items\]

\---

\#\# Detailed Knowledge

\[Longer-form content organized by topic\]

\---

\#\# Frequently Asked Questions

\[Q\&A pairs from automation rules and captured expert answers\]

\---

\#\# Procedures

\[Step-by-step processes, if applicable\]

\---

\#\# Related Topics

\[Links to other knowledge files\]

\---

\<\!-- LORIS\_METADATA\_START  
\[JSON blob with full metadata for each fact/rule\]  
LORIS\_METADATA\_END \--\>

---

## **Section Specifications**

### **Frontmatter (YAML)**

Required metadata at the top of every file:

\---  
loris\_version: 1.0  
category: "Contracts"  
subcategory: "Vendor Agreements"  
organization\_id: "550e8400-e29b-41d4-a716-446655440000"  
subdomain\_id: "7c9e6679-7425-40de-944b-e07fc1f90ae7"  
exported\_at: "2026-01-28T14:32:00Z"  
exported\_by: "loris-web-app"  
fact\_count: 12  
qa\_count: 5  
rule\_count: 3  
checksum: "a1b2c3d4e5f6789012345678"  
\---

| Field | Type | Description |
| ----- | ----- | ----- |
| `loris_version` | string | Format version (currently "1.0") |
| `category` | string | Primary category name |
| `subcategory` | string | Subcategory (optional, use "General" if none) |
| `organization_id` | UUID | Loris organization identifier |
| `subdomain_id` | UUID | Loris subdomain identifier |
| `exported_at` | ISO 8601 | When this file was generated |
| `exported_by` | string | Always "loris-web-app" |
| `fact_count` | integer | Number of facts in this file |
| `qa_count` | integer | Number of Q\&A pairs |
| `rule_count` | integer | Number of automation rules |
| `checksum` | string | MD5 of content (for change detection) |

---

### **Header Block**

Human-readable summary after frontmatter:

\# Contracts: Vendor Agreements

\> \*\*Last Updated:\*\* January 28, 2026 at 2:32 PM UTC  
\> \*\*Source:\*\* Loris Knowledge Base  
\> \*\*Confidence Level:\*\* This document contains verified organizational knowledge.

---

### **Quick Facts Section**

High-confidence facts in scannable bullet format. These are Tier 0a and 0b facts.

\#\# Quick Facts

\- Standard vendor contract term is 12 months with automatic renewal  
\- Cancellation requires 30 days written notice before renewal date  
\- All contracts over $50,000 require Legal review  
\- Vendor contracts must include our standard data protection addendum  
\- Payment terms are Net 30 unless otherwise negotiated

**Format rules:**

* One fact per bullet  
* Keep each fact under 150 characters  
* Most important/common facts first  
* No nested bullets in this section

---

### **Detailed Knowledge Section**

Longer explanations organized by subtopic. Include Tier 0c facts here.

\#\# Detailed Knowledge

\#\#\# Contract Terms and Duration

Standard vendor contracts have a 12-month term beginning on the execution date.   
Contracts automatically renew for successive 12-month periods unless either party   
provides written cancellation notice at least 30 days before the renewal date.

For strategic vendors or large engagements, we may negotiate:  
\- Multi-year terms (typically 2-3 years) with annual pricing reviews  
\- Early termination clauses with 90-day notice  
\- Performance-based renewal conditions

\#\#\# Approval Thresholds

| Contract Value | Required Approval |  
|----------------|-------------------|  
| Under $10,000 | Department Manager |  
| $10,000 \- $50,000 | Director \+ Procurement |  
| $50,000 \- $250,000 | VP \+ Legal Review |  
| Over $250,000 | CFO \+ Legal \+ Board notification |

\#\#\# Data Protection Requirements

All vendor contracts involving access to company data must include our Standard   
Data Protection Addendum (DPA). This applies to:  
\- SaaS providers with access to employee or customer data  
\- Consultants with system access  
\- Any vendor processing personal information on our behalf

The DPA template is available in the Legal Templates folder.

**Format rules:**

* Use \#\#\# for subtopics within this section  
* Tables are allowed for structured information  
* Keep paragraphs focused (3-5 sentences)  
* Include practical examples where helpful

---

### **FAQ Section**

Question-and-answer pairs from automation rules and captured expert answers.

\#\# Frequently Asked Questions

\*\*Q: What is the standard contract term for vendor agreements?\*\*

A: Standard vendor contracts have a 12-month term with automatic renewal.   
Cancellation requires 30 days written notice before the renewal date.

\_Source: Automation Rule AR-2024-0142 | Confidence: 95%\_

\---

\*\*Q: Do I need Legal review for my vendor contract?\*\*

A: Legal review is required for all contracts over $50,000. For contracts under   
$50,000, Legal review is recommended but not required unless the contract involves   
sensitive data, intellectual property, or non-standard terms.

\_Source: Expert answer by @sarah.chen on 2026-01-15 | Confidence: 90%\_

\---

\*\*Q: Where can I find the vendor contract template?\*\*

A: The standard vendor contract template is in Google Drive at:  
\`/Legal/Templates/Vendor-Agreement-Template-v3.docx\`

Make a copy before editing. Contact Legal if you need modifications to standard terms.

\_Source: WisdomFact WF-2025-0891 | Confidence: 98%\_

**Format rules:**

* Bold the question with `**Q: ...**`  
* Answer starts with `A:` on next line  
* Include source attribution in italics  
* Separate Q\&A pairs with `---`  
* Keep answers concise (1-3 paragraphs)

---

### **Procedures Section**

Step-by-step processes when applicable.

\#\# Procedures

\#\#\# How to Submit a Vendor Contract for Review

1\. \*\*Prepare the contract package:\*\*  
   \- Completed vendor contract (draft or vendor's paper)  
   \- Vendor due diligence questionnaire (for new vendors)  
   \- Business justification memo (for contracts over $50,000)

2\. \*\*Submit via the Contract Portal:\*\*  
   \- Go to contracts.company.com  
   \- Click "New Contract Review Request"  
   \- Upload documents and complete the intake form  
   \- Select urgency level (Standard: 5 days, Expedited: 2 days)

3\. \*\*Track progress:\*\*  
   \- You'll receive email updates at each stage  
   \- Average turnaround is 3 business days for standard requests  
   \- Check the portal dashboard for real-time status

4\. \*\*After approval:\*\*  
   \- Legal will route for signature via DocuSign  
   \- Fully executed copy will be filed automatically  
   \- You'll receive confirmation with the contract ID

\_Last verified: January 2026 by @legal.team\_

**Format rules:**

* Use numbered steps for sequential processes  
* Bold the step title, then details below  
* Include links/paths where relevant  
* Note who verified and when

---

### **Related Topics Section**

Cross-references to other knowledge files.

\#\# Related Topics

\- \*\*\[NDA Guidelines\](./Legal-NDA-Guidelines.md)\*\* — Confidentiality terms for vendor relationships  
\- \*\*\[Procurement Process\](./Procurement-Vendor-Onboarding.md)\*\* — How to onboard new vendors  
\- \*\*\[Data Protection\](./Legal-Data-Protection.md)\*\* — DPA requirements and templates

**Format rules:**

* Use relative links to other .md files in the same folder  
* Brief description of what each related file covers  
* Limit to 3-5 most relevant links

---

### **Hidden Metadata Section**

Full structured metadata for programmatic access. MoltenLoris can parse this for detailed source information.

\<\!-- LORIS\_METADATA\_START  
{  
  "facts": \[  
    {  
      "id": "wf-550e8400-e29b-41d4-a716-446655440001",  
      "content": "Standard vendor contract term is 12 months with automatic renewal",  
      "tier": "tier\_0a",  
      "confidence": 0.98,  
      "category": "contracts",  
      "created\_by": "sarah.chen@company.com",  
      "created\_at": "2025-06-15T10:30:00Z",  
      "last\_verified": "2026-01-10T14:00:00Z",  
      "source\_type": "expert\_knowledge"  
    },  
    {  
      "id": "wf-550e8400-e29b-41d4-a716-446655440002",  
      "content": "Cancellation requires 30 days written notice before renewal date",  
      "tier": "tier\_0b",  
      "confidence": 0.95,  
      "category": "contracts",  
      "created\_by": "bob.legal@company.com",  
      "created\_at": "2025-07-20T09:15:00Z",  
      "last\_verified": "2026-01-10T14:00:00Z",  
      "source\_type": "policy\_document"  
    }  
  \],  
  "qa\_pairs": \[  
    {  
      "id": "ar-7c9e6679-7425-40de-944b-e07fc1f90ae7",  
      "question\_pattern": "What is the standard contract term",  
      "answer\_template": "Standard vendor contracts have a 12-month term with automatic renewal. Cancellation requires 30 days written notice before the renewal date.",  
      "confidence": 0.95,  
      "created\_by": "sarah.chen@company.com",  
      "created\_at": "2025-08-01T11:00:00Z",  
      "source\_type": "automation\_rule",  
      "times\_used": 47  
    }  
  \],  
  "procedures": \[  
    {  
      "id": "proc-8f14e45f-ceea-467f-a4f8-2c9e0b8a9d1c",  
      "title": "How to Submit a Vendor Contract for Review",  
      "steps": 4,  
      "last\_verified": "2026-01-15T09:00:00Z",  
      "verified\_by": "legal.team@company.com"  
    }  
  \]  
}  
LORIS\_METADATA\_END \--\>

**This section is:**

* Hidden from human readers (HTML comment)  
* Parseable by MoltenLoris for detailed attribution  
* Contains full provenance for every piece of content  
* Useful for confidence scoring and source citation

---

## **Complete Example File**

\---  
loris\_version: 1.0  
category: "Contracts"  
subcategory: "Vendor Agreements"  
organization\_id: "550e8400-e29b-41d4-a716-446655440000"  
subdomain\_id: "7c9e6679-7425-40de-944b-e07fc1f90ae7"  
exported\_at: "2026-01-28T14:32:00Z"  
exported\_by: "loris-web-app"  
fact\_count: 5  
qa\_count: 3  
rule\_count: 2  
checksum: "a1b2c3d4e5f6789012345678"  
\---

\# Contracts: Vendor Agreements

\> \*\*Last Updated:\*\* January 28, 2026 at 2:32 PM UTC  
\> \*\*Source:\*\* Loris Knowledge Base  
\> \*\*Confidence Level:\*\* This document contains verified organizational knowledge.

\---

\#\# Quick Facts

\- Standard vendor contract term is 12 months with automatic renewal  
\- Cancellation requires 30 days written notice before renewal date  
\- All contracts over $50,000 require Legal review  
\- Vendor contracts must include our standard data protection addendum  
\- Payment terms are Net 30 unless otherwise negotiated

\---

\#\# Detailed Knowledge

\#\#\# Contract Terms and Duration

Standard vendor contracts have a 12-month term beginning on the execution date.   
Contracts automatically renew for successive 12-month periods unless either party   
provides written cancellation notice at least 30 days before the renewal date.

\#\#\# Approval Thresholds

| Contract Value | Required Approval |  
|----------------|-------------------|  
| Under $10,000 | Department Manager |  
| $10,000 \- $50,000 | Director \+ Procurement |  
| $50,000 \- $250,000 | VP \+ Legal Review |  
| Over $250,000 | CFO \+ Legal \+ Board notification |

\---

\#\# Frequently Asked Questions

\*\*Q: What is the standard contract term for vendor agreements?\*\*

A: Standard vendor contracts have a 12-month term with automatic renewal.   
Cancellation requires 30 days written notice before the renewal date.

\_Source: Automation Rule AR-2024-0142 | Confidence: 95%\_

\---

\*\*Q: Do I need Legal review for my vendor contract?\*\*

A: Legal review is required for all contracts over $50,000. For contracts under   
$50,000, Legal review is recommended but not required unless the contract involves   
sensitive data, intellectual property, or non-standard terms.

\_Source: Expert answer by @sarah.chen on 2026-01-15 | Confidence: 90%\_

\---

\#\# Procedures

\#\#\# How to Submit a Vendor Contract for Review

1\. \*\*Prepare the contract package:\*\*  
   \- Completed vendor contract (draft or vendor's paper)  
   \- Vendor due diligence questionnaire (for new vendors)

2\. \*\*Submit via the Contract Portal:\*\*  
   \- Go to contracts.company.com  
   \- Click "New Contract Review Request"

3\. \*\*Track progress:\*\*  
   \- Average turnaround is 3 business days

\_Last verified: January 2026 by @legal.team\_

\---

\#\# Related Topics

\- \*\*\[NDA Guidelines\](./Legal-NDA-Guidelines.md)\*\* — Confidentiality terms  
\- \*\*\[Procurement Process\](./Procurement-Vendor-Onboarding.md)\*\* — Vendor onboarding

\---

\<\!-- LORIS\_METADATA\_START  
{  
  "facts": \[  
    {  
      "id": "wf-001",  
      "content": "Standard vendor contract term is 12 months with automatic renewal",  
      "tier": "tier\_0a",  
      "confidence": 0.98  
    }  
  \],  
  "qa\_pairs": \[  
    {  
      "id": "ar-001",  
      "question\_pattern": "What is the standard contract term",  
      "confidence": 0.95  
    }  
  \]  
}  
LORIS\_METADATA\_END \--\>

---

## **Implementation Notes for Loris Web App**

### **KnowledgeExportService Updates**

The `KnowledgeExportService` should generate files following this format:

def \_generate\_knowledge\_file(  
    self,  
    category: str,  
    subcategory: str,  
    facts: List\[WisdomFact\],  
    qa\_pairs: List\[AutomationRule\],  
    procedures: List\[Procedure\]  
) \-\> str:  
    """Generate a knowledge file in Loris format."""  
      
    \# Build frontmatter  
    frontmatter \= {  
        "loris\_version": "1.0",  
        "category": category,  
        "subcategory": subcategory or "General",  
        "organization\_id": str(self.org\_id),  
        "subdomain\_id": str(self.subdomain\_id),  
        "exported\_at": datetime.utcnow().isoformat() \+ "Z",  
        "exported\_by": "loris-web-app",  
        "fact\_count": len(facts),  
        "qa\_count": len(qa\_pairs),  
        "rule\_count": len(procedures),  
    }  
      
    \# Build content sections  
    content \= \[\]  
    content.append(self.\_build\_frontmatter(frontmatter))  
    content.append(self.\_build\_header(category, subcategory))  
    content.append(self.\_build\_quick\_facts(facts))  
    content.append(self.\_build\_detailed\_knowledge(facts))  
    content.append(self.\_build\_faq(qa\_pairs))  
    content.append(self.\_build\_procedures(procedures))  
    content.append(self.\_build\_related\_topics(category))  
    content.append(self.\_build\_metadata\_block(facts, qa\_pairs, procedures))  
      
    file\_content \= "\\n".join(content)  
      
    \# Calculate checksum and update frontmatter  
    checksum \= hashlib.md5(file\_content.encode()).hexdigest()\[:24\]  
    frontmatter\["checksum"\] \= checksum  
      
    \# Rebuild with checksum  
    content\[0\] \= self.\_build\_frontmatter(frontmatter)  
      
    return "\\n".join(content)

### **Export Trigger Points**

Export should happen:

1. **On fact approval** — When a fact is promoted to Tier 0a/0b/0c  
2. **On automation rule creation** — When expert creates a new rule  
3. **On scheduled sync** — Hourly full export of all categories  
4. **On manual trigger** — Admin can force export via API

### **Change Detection**

Use the checksum to avoid unnecessary writes:

1. Before writing, fetch current file from Google Drive  
2. Compare checksums  
3. Only write if content has changed

---

## **MoltenLoris Parsing Notes**

MoltenLoris should:

1. **Parse frontmatter** for metadata (use a YAML parser)  
2. **Search the human-readable sections** for semantic matching  
3. **Use the hidden metadata** for attribution when citing sources  
4. **Check `loris_version`** to ensure compatibility

def parse\_knowledge\_file(content: str) \-\> dict:  
    """Parse a Loris knowledge file."""  
      
    \# Extract frontmatter  
    frontmatter\_match \= re.match(r'^---\\n(.\*?)\\n---', content, re.DOTALL)  
    frontmatter \= yaml.safe\_load(frontmatter\_match.group(1))  
      
    \# Extract hidden metadata  
    metadata\_match \= re.search(  
        r'\<\!-- LORIS\_METADATA\_START\\n(.\*?)\\nLORIS\_METADATA\_END \--\>',  
        content,  
        re.DOTALL  
    )  
    metadata \= json.loads(metadata\_match.group(1)) if metadata\_match else {}  
      
    \# Extract searchable content (everything between \--- and \<\!-- LORIS)  
    body\_start \= content.find('---', 4\) \+ 4  
    body\_end \= content.find('\<\!-- LORIS\_METADATA\_START')  
    searchable\_content \= content\[body\_start:body\_end\].strip()  
      
    return {  
        "frontmatter": frontmatter,  
        "metadata": metadata,  
        "searchable\_content": searchable\_content  
    }

---

*This specification is part of the Loris Knowledge Platform documentation.*

