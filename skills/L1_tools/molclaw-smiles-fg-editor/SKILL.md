---
name: molclaw-smiles-fg-editor
description: Edit molecular structures in SMILES notation by adding, deleting, or replacing functional groups. Use this skill whenever the user asks to modify a molecule's SMILES by manipulating functional groups (e.g., "delete hydroxyl", "add nitrile", "replace amine with carboxyl"). This skill prevents the most common error: treating the same atom pattern (like -OH) as one functional group when it actually represents different groups depending on chemical context.
license: MIT license
metadata:
    skill-author: PJLab
---

# SMILES Functional Group Editor

Note: 
- Local files are not directly accessible by the server. Please upload them to the server using `molclaw-file-transfer` before execution. 
- For PDB file inputs, it is recommended to preprocess them using `molclaw-pdbfixer` before execution.
- Please refer to skill `molclaw-scp-server` to complete tool invocation.

## Core Rule: Context Determines Identity

Never match functional groups by SMILES substring alone. The same pattern represents different
groups depending on what it's bonded to. Always classify from **most-specific to least-specific** —
first match wins.

## Functional Group Hierarchy

### Oxygen-containing (check top-down)

| Priority | Group            | Pattern                     | Key Test                          |
|----------|------------------|-----------------------------|-----------------------------------|
| 1        | Carboxylic acid  | `C(=O)O` (terminal OH)     | C=O adjacent to OH                |
| 2        | Ester            | `C(=O)OC`                  | C=O adjacent to O-C               |
| 3        | Phenol           | `c-O` (aromatic carbon-OH) | Lowercase `c` bonded to O         |
| 4        | Enol             | `C=C-O`                    | Vinyl carbon bonded to OH         |
| 5        | Ketone           | `CC(=O)C` (non-terminal)   | Internal C=O, no adjacent N or OC |
| 6        | Aldehyde         | terminal `C=O`             | Terminal C=O                       |
| 7        | Ether            | `C-O-C` (aliphatic)        | Not part of ester                 |
| 8        | Alcohol/Hydroxyl | `C-O` (aliphatic C-OH)     | Aliphatic C — **lowest priority** |

### Nitrogen-containing

| Priority | Group          | Pattern             | Key Test                        |
|----------|----------------|---------------------|---------------------------------|
| 1        | Nitro          | `[N+](=O)[O-]`     | Charged N with two oxygens      |
| 2        | Amide          | `C(=O)N`           | N adjacent to C=O               |
| 3        | Nitrile        | `C#N`              | Triple bond                     |
| 4        | Imine          | `C=N`              | Double bond                     |
| 5        | Heterocyclic N | `n` in ring        | Ring member — not an amine      |
| 6        | Amine          | `C-N` (aliphatic)  | Not in amide/ring — **lowest**  |

## User Term → Target Mapping

| User says    | Target only                  | Do NOT touch                        |
|--------------|------------------------------|-------------------------------------|
| "hydroxyl"   | Alcohol (aliphatic C-OH)     | Phenol, enol, carboxyl OH           |
| "amine"      | Aliphatic amine              | Amide N, ring N                     |
| "carbonyl"   | Ketone/Aldehyde C=O          | Ester/amide/carboxyl C=O            |
| "nitrile"    | C≡N                          | Isocyanide                          |
| "carboxyl"   | -COOH                        | Ester                               |

## Workflow

1. **Inventory**: list all candidate groups in the molecule
2. **Classify**: walk the hierarchy top-down for each candidate, first match wins
3. **Filter**: keep only groups matching the user's term per the mapping table above
4. **Modify**: delete/add/replace at the matched positions; preserve `@`/`@@` stereochemistry
5. **Validate**: check parentheses balanced, ring closures matched, stereo preserved

## Output Format

```json
{
    "output": "Modified Molecule SMILES"
}
```
