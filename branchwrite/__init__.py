"""BranchWrite integration boundaries."""
import sys

# A second CLI (including --help) must not populate bytecode inside a Python
# environment already pinned by another workflow. Do this before importing
# command modules, not only when PDF execution is admitted. Initial setup
# compiles the bootstrap cache before any runtime is admitted; real source or
# cache mutations remain integrity errors and are never ignored by the guard.
sys.dont_write_bytecode = True
