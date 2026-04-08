# Agnes PoC: Ingredient Consolidation + Quality Verification

## Concept

Build a small decision-support PoC that identifies promising ingredient consolidation opportunities and verifies whether alternative suppliers meet required quality standards using traceable evidence.

## Core Flow

### 1. Consolidation Opportunity Layer
Rank ingredients by a simple score based on:
- number of companies using the ingredient
- number of BOMs containing it
- supplier fragmentation

High score = strong consolidation candidate.

### 2. Requirements Layer

Tip: If a finished product has a requirement, usually the raw material has the same requirement 
For the top 3–4 ingredients, define:
- **hard constraints** that must be met
- **soft preferences** that improve attractiveness

Use benchmark references such as:
- USP
- FCC
- Ph. Eur.

Example fields:
- assay / purity
- heavy metals
- impurities
- particle size
- moisture / loss on drying
- pH
- shelf life
- certifications / grade claims

### 3. Competitor Layer
Find alternative suppliers for a selected ingredient.

For each candidate, also check evidence availability:
- TDS available
- COA available
- only marketing page available
- no useful public evidence found

### 4. Quality Verification Layer
Use agents to:
- find TDS / COA / technical documents
- extract structured quality measures
- compare them against requirements and standards

For each supplier, output:
- extracted quality fields
- pass/fail on hard constraints
- better/equal/worse on soft criteria
- missing evidence flags
- confidence score

### 5. Recommendation Layer
Generate an explainable recommendation:
- Accept
- Reject
- Conditional Accept

## Scope

### Do
- focus on 3–4 ingredients
- use transparent scoring
- show evidence sources
- separate hard constraints from soft preferences

### Do not
- attempt full regulatory automation
- claim perfect supplier quality truth
- build a full autonomous procurement system

## One-line Positioning

**Agnes identifies high-value consolidation targets and verifies whether alternative suppliers meet required quality standards using traceable evidence from public technical documents.**
