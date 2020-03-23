import re
import argparse
import subprocess

low_cpu = 25
low_memory = 25


def get_all_cpu_jobs(acct=None, user=None, starttime=None, endtime=None):
    parameter = ''
    parameter += '-A {} '.format(acct) if acct else ''
    parameter += '-u {} '.format(user) if user else ''
    parameter += '-S {} '.format(starttime) if starttime else ''
    parameter += '-E {} '.format(endtime) if endtime else ''
    sacct_command = "sacct --partition cpu,small {}".format(parameter)
    seff_result = subprocess.check_output(sacct_command, shell=True).decode()
    # parser the output of sacct
    seff_result = seff_result.split('\n')[2:-1]
    all_cpu_jobs = []
    for line in seff_result:
        job = int(line.split()[0].split('.')[0])
        if job not in all_cpu_jobs:
            all_cpu_jobs.append(job)
    return all_cpu_jobs


def get_seff(slurm_jobid):
    command = "seff {}".format(slurm_jobid)
    seff_result = subprocess.check_output(command, shell=True).decode()
    cpu_efficiency = re.search(r'CPU Efficiency: (.*?)%', seff_result).group(1)
    mem_efficiency = re.search(r'Memory Efficiency: (.*?)%',
                               seff_result).group(1)
    return float(cpu_efficiency), float(mem_efficiency), seff_result


def get_low_efficience_jobs(all_cpu_jobs):
    low_efficience_jobs = {}
    for slurm_jobid in all_cpu_jobs:
        cpu_efficiency, mem_efficiency, seff_result = get_seff(slurm_jobid)
        # handle `WARNING: Efficiency statistics may be misleading for RUNNING jobs.`
        if cpu_efficiency < low_cpu and mem_efficiency < low_memory and (
                'misleading' not in seff_result):
            low_efficience_jobs[slurm_jobid] = seff_result
    return low_efficience_jobs


def main():
    parser = argparse.ArgumentParser(description='seff scripts')
    parser.add_argument('-S', '--starttime')
    parser.add_argument('-E', '--endtime')
    parser.add_argument('-A', '--accounts')
    parser.add_argument('-u', '--user')
    args = parser.parse_args()
    all_cpu_jobs = get_all_cpu_jobs(args.accounts, args.user, args.starttime,
                                    args.endtime)
    low_efficience_jobs = get_low_efficience_jobs(all_cpu_jobs)
    for jobid in low_efficience_jobs:
        print(low_efficience_jobs[jobid])
        print('-'*20)


if __name__ == "__main__":
    main()
