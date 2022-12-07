# Queequeg

## Installing dependencies

    dnf install gcc js-d3-flame-graph perf qpid-proton-c-devel sysstat

## Drilling into the recorded data

    $ ./plano record
    $ perf report --no-children
