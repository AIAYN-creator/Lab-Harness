"""Domain modules. Each subpackage is independent and registered through the
``labharness.modules`` entry point group.

Every module exposes plain Python functions that:

1. never print, read ``sys.argv`` or call ``exit()`` (errors are typed exceptions);
2. receive style and paths as arguments (no global state);
3. write their outputs atomically;
4. are deterministic;
5. do not import other modules, and only use the public API of ``labharness.core``
   and ``labharness.style``;
6. import their heavy dependencies lazily via ``labharness.core.require``.
"""
