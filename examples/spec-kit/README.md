# Example: a `spec` kind for Spec Kit projects

taskrail's core kinds know nothing about GitHub Spec Kit. A project that uses it adds its own
`spec` kind and keeps its existing pipeline skills.

1. Copy `.taskrail/types/spec/kind.toml` into the repository.
2. Declare the routing column in `.taskrail/config.toml`:

   ```toml
   [columns]
   custom = ["Spec"]
   ```

3. Add a `Spec` column to the task tables: `—` for a new specification, the specification's
   directory for an amendment.
4. Replace `spec-new-pipeline` and `spec-amend-pipeline` with the names of the repository's
   own skills.

`taskrail show <ID>` then reports the right skill for each row, and `taskrail validate` warns if
the column is used without being declared.
