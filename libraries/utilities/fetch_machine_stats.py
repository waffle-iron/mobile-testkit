import os.path
import shutil
import sys
from optparse import OptionParser

from provision.ansible_runner import AnsibleRunner


def fetch_machine_stats(folder_name):

    ansible_runner = AnsibleRunner()

    print("\n")

    print("Pulling logs")
    # fetch logs from sync_gateway instances
    ansible_runner.run_ansible_playbook("fetch-machine-stats.yml")

    # zip logs and timestamp
    if os.path.isdir("/tmp/perf_logs"):

        # Move perf logs to performance_results
        shutil.move("/tmp/perf_logs", "testsuites/syncgateway/performance/results/{}/".format(folder_name))

    print("\n")


if __name__ == "__main__":
    usage = """usage: fetch_machine_stats.py
    --test-id=<test-id>
    """

    parser = OptionParser(usage=usage)

    parser.add_option("", "--test-id",
                      action="store", type="string", dest="test_id", default=None,
                      help="Test id to generate graphs for")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    if opts.test_id is None:
        print("You must provide a test identifier to run the test")
        sys.exit(1)

    fetch_machine_stats(opts.test_id)
