import re
import argparse
import subprocess

low_cpu = 25
low_memory = 25
partition = 'cpu' # 'cpu,small'

def get_all_cpu_jobs(acct=None, user=None, starttime=None, endtime=None):
    parameter = ''
    parameter += '-A {} '.format(acct) if acct else ''
    parameter += '-u {} '.format(user) if user else ''
    parameter += '-S {} '.format(starttime) if starttime else ''
    parameter += '-E {} '.format(endtime) if endtime else ''
    sacct_command = "sacct --partition {} -a {}".format(partition, parameter)
    seff_result = subprocess.check_output(sacct_command, shell=True).decode()
    # parser the output of sacct
    seff_result = seff_result.split('\n')[2:-1]
    all_cpu_jobs = []
    for line in seff_result:
        # handle array job
        job = int(line.split()[0].split('.')[0].split('_')[0])
        if job not in all_cpu_jobs:
            all_cpu_jobs.append(job)
    return all_cpu_jobs


def get_seff(slurm_jobid):
    command = "seff {}".format(slurm_jobid)
    seff_result = subprocess.check_output(command, shell=True).decode()
    command = "sacct -j {} -p -o ACCOUNT,WorkDir".format(slurm_jobid)
    sacct_result = subprocess.check_output(command, shell=True).decode()
    acct, workdir = sacct_result.split()[1].split('|')[:2]
    if 'PENDING' not in seff_result:
        cpu_efficiency = re.search(r'CPU Efficiency: (.*?)%', seff_result).group(1)
        mem_efficiency = re.search(r'Memory Efficiency: (.*?)%',
                                   seff_result).group(1)
    else:
        cpu_efficiency, mem_efficiency = 0, 0
    state = re.search(r'State: (.*?)\n', seff_result).group(1)
    return acct, workdir, state, float(cpu_efficiency), float(mem_efficiency), seff_result


def get_low_efficience_jobs(all_cpu_jobs):
    low_efficience_jobs = {}
    for slurm_jobid in all_cpu_jobs:
        if slurm_jobid < 100000:
            continue
        acct, workdir, status, cpu_efficiency, mem_efficiency, seff_result = get_seff(slurm_jobid)
        # handle `WARNING: Efficiency statistics may be misleading for RUNNING jobs.`
        if ('COMPLETED' in status) and cpu_efficiency < low_cpu and mem_efficiency < low_memory and (
                'misleading' not in seff_result):
            if acct in low_efficience_jobs:
                low_efficience_jobs[acct][slurm_jobid] = (workdir, seff_result)
            else:
                low_efficience_jobs[acct] = {}
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
    for acct in low_efficience_jobs:
        print(acct)
        for jobid in low_efficience_jobs[acct]:
            workdir, seff_result = low_efficience_jobs[acct][jobid]
            print(seff_result)
            print("WorkDir: {}".format(workdir))
            print('-'*20)
        print('='*30)


if __name__ == "__main__":
    main()
