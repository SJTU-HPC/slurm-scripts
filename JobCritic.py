import re
import os
import logging
import inspect
import traceback
import subprocess


class MailDeliver():

    def __init__(self):
        self.mail_backend = "smail"
        self.subject_tmp = "Mails from git.hpc.sjtu.edu.cn"
        self.content_tmp = "Empty mail"

    def send_email(self, recv_email, subject, content, logger):
        if not subject:
            logger.warning("Empty subject for email to {}".format(recv_email))
            subject = self.subject_tmp
        if not content:
            logger.warning("Empty content for email to {}".format(recv_email))
            content = self.content_tmp
        send_cmd = "echo \"{}\" | smail -s '{}' {}".format(content, subject, recv_email)
        return_code = os.system(send_cmd)
        if return_code != 0:
            logger.warning("Failer to deliver email to {}".format(recv_email))
        else:
            logger.info("Delivered email to {}".format(recv_email))


class JobCritic():

    def __init__(self,
                 starttime='`date +"%Y-%m-%dT%T" -d \'24 hour ago\'`',
                 endtime='`date +"%Y-%m-%dT%T"`',
                 acct=None,
                 user=None,
                 partition=['cpu'],
                 min_elapse=1,
                 low_cpu=25,
                 low_memory=25,
                 debug=False):
        self.starttime = starttime
        self.endtime = endtime
        self.acct = acct
        self.user = user
        self.partition = partition
        self.low_cpu = low_cpu
        self.low_memory = low_memory
        self.min_elapse = min_elapse
        self.logger = logging.getLogger(__name__)
        self.init_logger(debug)
        self.sacct_query = ['jobid', 'account', 'user', 'state', 'elapsed']
        self.mailman = MailDeliver()
        self.filters = [
            lambda job: job['jobid'] > 100000,  # for roll-history jobs
            lambda job: job['account'] != 'acct-hpc',
            lambda job: 'stu' not in job['user'],
            lambda job: 'COMPLETED' in job['state'],
            lambda job: job['elapsed'] > self.min_elapse  # job['elapsed'] large than 1 minute
        ]

        self.internal_email = "hpc@sjtu.edu.cn"

    def init_logger(self, debug):
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.logger.addHandler(ch)
        self.logger.setLevel(level=logging.WARN)
        if debug:
            self.logger.setLevel(level=logging.DEBUG)

    def print_filters(self):
        self.logger.debug("=" * 50)
        self.logger.debug("All filters:")
        self.logger.debug("-" * 50)
        for i_filter, filter in enumerate(self.filters):
            self.logger.debug("[{}]: {}".format(i_filter, inspect.getsource(filter).strip()))
        self.logger.debug("=" * 50)

    def get_sacct_command(self):
        parameter = ''
        parameter += '-A {} '.format(self.acct) if self.acct else ''
        parameter += '-u {} '.format(self.user) if self.user else ''
        parameter += '-S {} '.format(self.starttime) if self.starttime else ''
        parameter += '-E {} '.format(self.endtime) if self.endtime else ''
        sacct_command = "sacct --partition {} -a -o {} {}".format(','.join(self.partition),
                                                                  ','.join(self.sacct_query),
                                                                  parameter)
        return sacct_command

    def all_filters(self, x):
        final_results = True
        for filter in self.filters:
            final_results = final_results and filter(x)
        return final_results

    def get_valid_jobs(self, apply_filters=True):
        self.logger.info("Executing {}".format(self.get_sacct_command()))
        sacct_result = subprocess.check_output(self.get_sacct_command(), shell=True).decode()
        sacct_result = sacct_result.split('\n')[2:-1]

        all_jobs = {}
        for line in sacct_result:
            if len(line.split()) == len(self.sacct_query):
                jobid, account, user, state, elapsed = line.split()
                # for array jobs
                jobid = jobid.split('_')[0]
                hours, mins, _ = elapsed.split(':')
                if '-' in hours:
                    days, hours = hours.split('-')
                    hours = int(hours) + 24 * int(days)
                mins = 60 * int(hours) + int(mins)
                elapsed = elapsed.split('_')
                all_jobs[int(jobid)] = {
                    'jobid': int(jobid),
                    'account': account,
                    'user': user,
                    'state': state,
                    'elapsed': mins
                }

        self.logger.info("There are {} jobs before apply filters.".format(len(all_jobs)))
        if apply_filters:
            self.print_filters()
            all_jobs = {job: all_jobs[job] for job in all_jobs if self.all_filters(all_jobs[job])}
        self.logger.info("There are {} valid jobs.".format(len(all_jobs)))

        return all_jobs

    def ineffective_critic(self, job_id):
        command = "seff {}".format(job_id)
        seff_result = subprocess.check_output(command, shell=True).decode()
        try:
            cpu_efficiency = float(re.search(r'CPU Efficiency: (.*?)%', seff_result).group(1))
            mem_efficiency = float(re.search(r'Memory Efficiency: (.*?)%', seff_result).group(1))
        except Exception:
            logging.error(traceback.format_exc())
        return (cpu_efficiency < self.low_cpu and mem_efficiency < self.low_memory), seff_result

    def get_workdir(self, slurm_jobid):
        command = "sacct -j {} -p -o ACCOUNT,WorkDir,NNodes,NCPUS".format(slurm_jobid)
        sacct_result = subprocess.check_output(command, shell=True).decode()
        acct, workdir, nnodes, ncpus = sacct_result.split()[1].split('|')[:4]
        return acct, workdir, nnodes, ncpus

    def get_ineffective_jobs(self):
        all_jobs = self.get_valid_jobs()
        low_efficience_jobs = {}
        self.logger.info("Finding ineffective jobs with seff.")
        num_low_efficience_jobs = 0
        for job_id in all_jobs:
            flag, seff_result = self.ineffective_critic(job_id)
            if flag:
                acct, workdir, nnodes, ncpus = self.get_workdir(job_id)
                if acct not in low_efficience_jobs:
                    low_efficience_jobs[acct] = {}
                self.logger.debug("Find ineffective job [{}]: {}".format(job_id, acct))
                low_efficience_jobs[acct][job_id] = (workdir, seff_result, nnodes, ncpus)
                num_low_efficience_jobs += 1
        self.logger.info("There are {} inefficent jobs from {} user.".format(
            num_low_efficience_jobs, len(low_efficience_jobs)))
        return low_efficience_jobs

    def get_suggestion(self, nnodes, ncpus):
        str = "Suggestion:\n \
1. Use fewer nodes if your jobs are multi-node.\n \
2. Use fewer cores, and submit your job to partition **small**."

        return str

    def send_email_internal(self, low_efficience_jobs):
        email_subject = "Inefficiency Jobs Reports"
        email_header = "Inefficiency Jobs from {} to {}".format(self.starttime,
                                                                self.endtime) + '\n\n'
        email_content = '=' * 30 + '\n'
        for acct in low_efficience_jobs:
            email_content += acct + '\n'
            for jobid in low_efficience_jobs[acct]:
                workdir, seff_result, nnodes, ncpus = low_efficience_jobs[acct][jobid]
                email_content += '-' * 20 + '\n'
                email_content += seff_result.rstrip() + '\n'
                email_content += "WorkDir: {}".format(workdir) + '\n'
            email_content += '-' * 20 + '\n'
            email_content += self.get_suggestion(nnodes, ncpus) + '\n'
            email_content += '=' * 30 + '\n'
        self.mailman.send_email(self.internal_email, email_subject, email_header + email_content,
                                self.logger)

    def send_email_user(self, emails):
        pass
