import argparse
from JobCritic import JobCritic


def main():
    parser = argparse.ArgumentParser(description='seff scripts')
    parser.add_argument('-S', '--starttime', default='`date +"%Y-%m-%dT%T" -d \'4 hour ago\'`')
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

    acct_info_path = "./account_info.csv"

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
    watcher.valid_filters.append(
        lambda job: 'phyzpj-jxwang' not in job.user
    )
    watcher.valid_filters.append(
        lambda job: 'user' not in job.user
    )
    watcher.valid_filters.append(
        lambda job: 'esechzh-air4' not in job.user
    )
    watcher.valid_filters.append(
        lambda job: 'medhjy' not in job.user
    )
    ineffective_jobs = watcher.get_ineffective_jobs()
    watcher.send_email_user(ineffective_jobs, acct_info_path)


if __name__ == "__main__":
    main()
