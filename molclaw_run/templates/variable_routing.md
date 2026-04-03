Variable routing rules (high-throughput):
- Every successful tool result is registered as reusable context for the current sample.
- Prefer variable symbols over pasting large payloads: use `@var_name` or `{tool_name.field}`.
- For list outputs from list-of-dict results, subfields can be referenced directly, for example `{calculate_mol_basic_info.metrics.smiles}`.
- Use `read_variable` when you need to inspect the full content of a registered variable.
- Use `aggregate_variables` when you need to join or filter multiple variable tables by a shared key such as `smiles`.
- When a downstream tool needs a list or scalar that already exists in prior results, pass the variable reference instead of rewriting the data.

