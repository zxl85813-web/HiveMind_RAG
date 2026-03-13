# File Versioning Design

We need a table for files and a table for versions. 
When a user saves, create a new row in the version table.
To revert, just copy the data back.

Service will be in `versioning.py`.
UI will have a list of versions.
