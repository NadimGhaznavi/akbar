# Read-Only SQL

- Discover tables and columns before querying unfamiliar data.
- Select only fields required for the question.
- Extract individual JSON properties instead of returning complete JSON documents.
- Use filtering, joins, grouping, aggregation, ordering, and window functions when useful.
- Use PyMySQL placeholders and pass values separately as parameters.
- Query results above the tool length limit are rejected with guidance for narrowing the result.
- Experiment rationales are stored in the rationale property of proposal JSON.
- Predeclared success criteria are stored in the `success_criterion` property of
  proposal JSON; final verdicts, conclusions, and evaluation evidence are stored
  in `experiment_evaluations`.
- Evidence JSON is planning provenance and should not be selected wholesale.

- [Data discipline](/data/discipline)
- [Experiment workflow](/experiments/workflow)
