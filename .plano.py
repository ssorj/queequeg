#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

from plano import *

standard_args = (
    CommandArgument("duration", default=5, positional=False,
                    help="The time to run (excluding warmup) in seconds"),
    CommandArgument("warmup", default=5, positional=False,
                    help="Warmup time in seconds"),
)

@command
def check():
    """
    Check for required programs and system configuration
    """
    check_program("gcc", "I can't find gcc.  Run 'dnf install gcc'.")
    check_program("perf", "I can't find the perf tools.  Run 'dnf install perf'.")
    check_program("pidstat", "I can't find pidstat.  Run 'dnf install sysstat'.")

    perf_event_paranoid = read("/proc/sys/kernel/perf_event_paranoid")

    if perf_event_paranoid != "-1\n":
        exit("Perf events are not enabled.  Run 'echo -1 > /proc/sys/kernel/perf_event_paranoid' as root.")

@command
def clean():
    """
    Remove build artifacts and output files
    """
    remove("perf.data")
    remove("perf.data.old")
    remove("flamegraph.html")
    remove("flamegraph.html.old")
    remove("transfers.csv")
    remove("transfers.csv.old")

@command
def build():
    """
    Compile the load generator
    """
    check()

    run("gcc queequeg.c -o queequeg -g -O2 -std=c99 -fno-omit-frame-pointer -lqpid-proton -lqpid-proton-proactor")

def run_outer(inner, warmup):
    procs = list()
    output_files = list()

    if exists("transfers.csv"):
        move("transfers.csv", "transfers.csv.old")

    procs.append(start("./queequeg receive", stdout="transfers.csv"))
    procs.append(start("./queequeg send"))

    # XXX
    pids = ",".join([str(x.pid) for x in procs])

    try:
        with start(f"pidstat 2 --human -p {pids}"):
            sleep(warmup)
            inner(pids)
    finally:
        for proc in procs:
            kill(proc)

def print_transfers(duration):
    count = int(call(f"wc -l transfers.csv").split()[0])

    print()
    print(">> {:,} messages per second <<".format(count // duration))
    print()

@command(args=standard_args)
def stat(duration, warmup):
    """
    Run the workload and capture 'perf stat' output
    """
    build()

    with temp_file() as output:
        def inner(pids):
            run(f"perf stat --detailed --pid {','.join(pids)} sleep {duration}", output=output)

        try:
            run_outer(inner, warmup)
        finally:
            print_transfers(duration + warmup)

        print(read(output))

@command(args=standard_args)
def flamegraph(duration, warmup):
    """
    Run the workload and generate a flamegraph
    """
    try:
        check_exists("/usr/share/d3-flame-graph")
    except:
        fail("I can't find d3-flame-graph.  Run 'dnf install js-d3-flame-graph'.")

    build()

    with temp_file() as output:
        def inner(pids):
            if exists("flamegraph.html"):
                move("flamegraph.html", "flamegraph.html.old")

            # run(f"perf script flamegraph --freq 997 --call-graph lbr --pid {pids} sleep {duration}", stdout=output)
            run(f"perf script flamegraph --freq 997 --call-graph dwarf --pid {pids} sleep {duration}", stdout=output)

        try:
            run_outer(inner, warmup)
        finally:
            print_transfers(duration + warmup)

        print(read(output))

@command(args=standard_args)
def record(duration, warmup):
    """
    Run the workload and capture perf events using 'perf record'
    """
    build()

    with temp_file() as output:
        def inner(pids):
            # run(f"perf record --freq 997 --call-graph lbr --pid {pids} sleep {duration}", output=output)
            run(f"perf record --freq 997 --call-graph dwarf --pid {pids} sleep {duration}", output=output)

        try:
            run_outer(inner, warmup)
        finally:
            print_transfers(duration + warmup)

        print(read(output))

# @command
# def self_test():
#     """
#     Test Flimflam
#     """
#     flamegraph(duration=1, warmup=0.1)
#     stat(duration=1, warmup=0.1)
#     record(duration=1, warmup=0.1)
#     clean()
