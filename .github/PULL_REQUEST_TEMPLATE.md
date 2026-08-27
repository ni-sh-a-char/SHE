## What this changes

<!-- One or two sentences. What problem does this solve? -->

## Before and after

<!-- If it changes behaviour, show it. Delete this section if it does not. -->

```she
# before

# after
```

## Checklist

- [ ] `pytest` passes
- [ ] `she test examples` passes
- [ ] `python tools/check_sandbox.py` passes
- [ ] `ruff check she tools` passes
- [ ] Added a test for this change
- [ ] Any new error message says what to *do*, not just what went wrong
- [ ] Anything reaching the filesystem, network, environment or another process
      calls `interp.sandbox.require(...)` first
