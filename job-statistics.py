import argparse
from JobCritic import JobCritic


def main():
    parser = argparse.ArgumentParser(description='seff scripts')
    parser.add_argument('-S', '--starttime', default='`date +"%Y-%m-%dT%T" -d \'24 hour ago\'`')
    parser.add_argument('-E', '--endtime', default='`date +"%Y-%m-%dT%T"`')
    parser.add_argument('-A', '--accounts')
    parser.add_argument('-u', '--user')
    parser.add_argument('-d',
                        '--debug',
                        default=False,
                        action='store_true',
                        help="turn on the STD output")
    args = parser.parse_args()

    min_elapse = 1  # filter jobs less than 1 minute

    low_cpu = 25
    low_memory = 25

    # set debug=False to quiet STD output
    watcher = JobCritic(starttime=args.starttime,
                        endtime=args.endtime,
                        acct=args.accounts,
                        user=args.user,
                        min_elapse=min_elapse,
                        low_cpu=low_cpu,
                        low_memory=low_memory,
                        debug=args.debug)

    # you can add or modefy filters diretly
    # watcher.filters.append(lambda job: job['xxx'] > xxx)
    ineffective_jobs = watcher.get_ineffective_jobs()
    watcher.send_email_internal(ineffective_jobs)


if __name__ == "__main__":
    main()
