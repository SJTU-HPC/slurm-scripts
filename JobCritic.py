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


class SlurmJob():
    def __init__(self, jobid, account, user, state, elapsed):
        self.jobid = jobid
        self.account = account
        self.user = user
        self.state = state
        self.elapsed = elapsed

    def seff(self):
        command = "seff {}".format(self.jobid)
        self.seff_result = subprocess.check_output(command, shell=True).decode()
        try:
            self.cpu_efficiency = float(re.search(r'CPU Efficiency: (.*?)%', self.seff_result).group(1))
            self.mem_efficiency = float(re.search(r'Memory Efficiency: (.*?)%', self.seff_result).group(1))
        except Exception:
            logging.error(traceback.format_exc())

    def sacct(self):
        command = "sacct -j {} -p -o ACCOUNT,WorkDir,NNodes,NCPUS".format(self.jobid)
        sacct_result = subprocess.check_output(command, shell=True).decode()
        self.account, self.workdir, self.nnodes, self.ncpus = sacct_result.split()[1].split('|')[:4]


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
        self.valid_filters = [
            lambda job: job.jobid > 100000,  # for roll-history jobs
            lambda job: job.account != 'acct-hpc',
            lambda job: 'stu' not in job.user,
            lambda job: 'COMPLETED' in job.state,
            lambda job: job.elapsed > self.min_elapse  # job.elapsed large than 1 minute
        ]

        self.efficiency_filters = [
            lambda job: job.cpu_efficiency < 25,
            lambda job: job.mem_efficiency < 25,
        ]

        self.internal_email = "hpc@sjtu.edu.cn"

    def init_logger(self, debug):
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.logger.addHandler(ch)
        self.logger.setLevel(level=logging.WARN)
        if debug:
            self.logger.setLevel(level=logging.DEBUG)

    def print_filters(self, filters):
        self.logger.debug("=" * 50)
        self.logger.debug("Apply filters:")
        self.logger.debug("-" * 50)
        for i_filter, filter in enumerate(filters):
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

    def applyfilters(self, filters, obj):
        final_results = True
        for filter in filters:
            final_results = final_results and filter(obj)
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
                all_jobs[int(jobid)] = SlurmJob(int(jobid), account, user, state, mins)

        self.logger.info("There are {} jobs before apply filters.".format(len(all_jobs)))
        if apply_filters:
            self.print_filters(self.valid_filters)
            all_jobs = {job: all_jobs[job] for job in all_jobs if self.applyfilters(self.valid_filters, all_jobs[job])}
        self.logger.info("There are {} valid jobs.".format(len(all_jobs)))

        return all_jobs

    def get_ineffective_jobs(self):
        all_jobs = self.get_valid_jobs()
        low_efficience_jobs = {}
        self.logger.info("Finding ineffective jobs with seff.")
        self.print_filters(self.efficiency_filters)
        num_low_efficience_jobs = 0
        for job_id in all_jobs:
            this_job = all_jobs[job_id]
            this_job.seff()
            if self.applyfilters(self.efficiency_filters, this_job):
                this_job.sacct()
                if this_job.account not in low_efficience_jobs:
                    low_efficience_jobs[this_job.account] = {}
                self.logger.debug("Find ineffective job [{}]: {}".format(job_id, this_job.account))
                low_efficience_jobs[this_job.account][job_id] = this_job
                num_low_efficience_jobs += 1
        self.logger.info("There are {} inefficent jobs from {} user.".format(
            num_low_efficience_jobs, len(low_efficience_jobs)))
        return low_efficience_jobs

    def get_suggestion(self):
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
                this_job = low_efficience_jobs[acct][jobid]
                email_content += '-' * 20 + '\n'
                email_content += this_job.seff_result.rstrip() + '\n'
                email_content += "WorkDir: {}".format(this_job.workdir) + '\n'
            email_content += '-' * 20 + '\n'
            email_content += self.get_suggestion() + '\n'
            email_content += '=' * 30 + '\n'
        self.mailman.send_email(self.internal_email, email_subject, email_header + email_content,
                                self.logger)

    def send_email_user(self, emails):
        pass
