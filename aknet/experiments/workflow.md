# Planning and Execution Workflow

- On a fresh installation, launch one baseline experiment from the service's
  default configuration without asking the language model to choose values.
- After baseline evidence exists, begin each planning conversation at the Aknet
  homepage and consult the relevant orientation pages.
- Confirm that no experiment is queued or running.
- Discover the database schema before writing analytical SQL.
- Establish complete experiment, status, seed, and configuration coverage.
- Investigate all relevant observations with read-only SQL.
- Propose learning rate, initial epsilon, epsilon decay, and an evidence-based rationale.
- State a success criterion before execution so the result can be judged without
  inventing a threshold after observing it.
- Reconsider an exact completed duplicate when Python challenges it.
- Let Python validate, persist, and launch the experiment.
- Monitor status and simulation progress without launching overlapping work.
- After completion, verify full coverage and evaluate the experiment against its
  rationale and success criterion before proposing another experiment.
- Persist a `pass`, `fail`, or `inconclusive` verdict and a concise conclusion.

- [SQL guide](/data/sql)
- [Writing rationales and free-form text](/experiments/writing)
- [Experiment methodology](/experiments/methodology)
