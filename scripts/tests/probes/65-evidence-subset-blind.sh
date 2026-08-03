#!/usr/bin/env bash
# Blind-spot probe for 65-evidence-subset.sh. Contract: 0 = blind spot real.
#
# Declared: the check is TEXTUAL. A path merely named in a command's argv
# counts as read, even when the output does not depend on it.
# Probed by: a command that names a file whose content cannot affect the
# output must still be judged "read". If the checker ever becomes semantic,
# this flips and the declaration must be rewritten.
set -u
cd "$(git rev-parse --show-toplevel)"
python3 - <<'PY'
import sys, importlib.util
spec = importlib.util.spec_from_file_location("es", "scripts/evidence-subset.py")
es = importlib.util.module_from_spec(spec); spec.loader.exec_module(es)
# `head -1 a.py` cannot be affected by b.py, yet b.py is named in the argv.
blind = es.path_is_read("head -1 a.py b.py", "b.py")
if not blind:
    print("probe-65: the checker no longer counts a merely-named path as read "
          "-- the declared blind spot is CLOSED; update 65-evidence-subset.sh")
    sys.exit(1)
print("probe-65: blind spot intact -- a path named in argv counts as read "
      "regardless of whether the output depends on it")
PY
