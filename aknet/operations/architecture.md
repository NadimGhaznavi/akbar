# System Architecture

- The scheduler controls timing and gives Akbar bounded orientation and read-only analysis tools.
- Akbar chooses evidence queries and proposes the next experiment.
- Python validates and persists proposals before launch.
- The experiment service executes one sequential experiment at a time.
- MariaDB is authoritative for plans, lifecycle records, configurations, and results.
- ZMQ carries experiment control messages and transient telemetry.
- Models, game state, and replay memory remain in process memory during each simulation.

- [Operating Akbar](/operations/)
- [Return to the homepage](/)
