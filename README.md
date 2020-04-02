# JobCritic

`JobCritic` contain core fuctions of job efficiency analysis for SLURM.

* Job efficiency analysis based on `sacct` and `seff`
* Deliver email for Internal or User use `smail`

And the scipts is Python 2/3 compatible without dependency.

## Usage

You can find help info with `python job-statistics.py -h`. And here is an example:

```shell
$ python job-statistics.py -S `date +"%Y-%m-%dT%T" -d '4 hour ago'` -E `date +"%Y-%m-%dT%T"`
```

You can control the threshold of the efficiency jobs with two variable:

```python
low_cpu = 25     # Below 25% will be treated as low cpu efficiency
low_memory = 25  # Below 25% will be treated as low memery efficiency
```
