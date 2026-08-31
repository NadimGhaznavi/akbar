# Writing Experiment Proposals

Free-form text is part of the scientific record. Write it so that a future reader can understand the decision without reconstructing the planning conversation.

The automatic first experiment is a special baseline. Its synthetic rationale
states that the default configuration establishes the initial reference
population, and its success criterion and conclusion concern complete usable
coverage rather than improvement over evidence that did not yet exist.

## Experiment Rationale

A useful rationale identifies the evidence reviewed, states the interpretation, names the proposed change, and explains what the experiment is intended to reveal.

Rationales, success criteria, and conclusions should each be no more than one
paragraph. Summarize distributions, aggregates, comparisons, and coverage; do
not turn prose into a list of individual simulation values or data points.

- Include the experiment IDs or clearly defined population examined.
- Include row counts and relevant status, seed, and configuration coverage.
- State the observed pattern without claiming more than the data supports.
- Name the proposed baseline values and how they differ from prior experiments.
- State the question, comparison, or prediction the new experiment addresses.
- Mention important uncertainty, incomplete coverage, or competing explanations.

### Strong Rationale Example

Across completed experiments 4744dcb9 and 5ea305dc, I analyzed all 54 completed simulation rows, covering all 27 configurations with seed 1970 in each experiment. Configurations near learning rate 0.0008 scored higher than nearby 0.001 configurations, while epsilon settings were unchanged, so the learning-rate effect is the clearest distinction available within this single-seed methodology. I propose a 0.00085 learning-rate baseline with epsilon start 1.0 and epsilon decay 0.995. This experiment tests whether the apparent improvement persists between the two previously tested learning-rate centers while preserving direct comparability on exploration settings. Because only one seed is used, the result will not establish robustness across random initializations.

### Weak Rationale Example

The lower learning rate looked better, so I will try something nearby.

The weak example does not identify its evidence population, coverage, observed measurements, exact proposal, uncertainty, or intended comparison.

## Success Criterion

State before execution what observable population-level outcome would support
the rationale. The criterion must be specific enough to distinguish `pass`
from `fail`; use `inconclusive` when completed evidence cannot make that
distinction. Execution failure, cancellation, interruption, or incomplete
coverage is `not_evaluable`, not a scientific failure.

## Experiment Conclusion

After a completed experiment, compare the complete 27-simulation population
with the predeclared rationale and success criterion. Record `pass` when the
criterion is met, `fail` when complete evidence contradicts it, and
`inconclusive` when the evidence cannot distinguish the proposed outcomes. The
conclusion must be one concise paragraph describing coverage, the aggregate
comparison, the verdict, limitations, and the implication for subsequent work;
do not enumerate individual simulation results.

## Duplicate Experiment Reason

An exact deterministic duplicate is normally redundant. A duplicate experiment reason must explain what new knowledge the repetition can produce despite identical hyperparameters, seeds, epochs, methodology, and execution.

- Identify the completed experiment being repeated.
- Explain why its existing simulation rows are insufficient for the stated purpose.
- Identify a meaningful changed condition outside the stored experiment configuration.
- State how the repeated result will be compared and what outcome would matter.
- Do not use convenience, uncertainty without a source, or a desire for more data as the sole reason.

### Strong Duplicate Reason Example

Repeat experiment 4744dcb9 after upgrading the numerical runtime to verify that the environment change did not alter deterministic outcomes. I will compare every simulation by configuration against the original 27 rows for seed 1970. Exact agreement supports continuity across the runtime upgrade; any disagreement indicates an environmental reproducibility problem that must be investigated before combining old and new results.

### Weak Duplicate Reason Example

Run it again to make sure and get more confidence.

The weak example does not identify a changed condition, explain why deterministic stored results are insufficient, or define a comparison that can produce new knowledge.

## General Free-Form Writing

- Prefer specific observations and identifiers over adjectives such as good, bad, better, or promising.
- Distinguish observation from interpretation and prediction.
- Include enough context to stand alone, but do not paste schemas, raw result sets, tool histories, or complete evidence JSON.
- Never place instructions to future tool callers inside a scientific rationale.
- Keep operational errors and debugging notes out of the rationale unless they affect the scientific interpretation.

- [Planning workflow](/experiments/workflow)
- [Data discipline](/data/discipline)
- [Return to experiments](/experiments/)
