# Scripts for efficiency statistics of SLURM jobs

The scripts base on the output of `sacct` and `seff` and print the low efficiency jobs in STDOUT.
So make sure the `sacct` and `seff` work fine in your shell.
And the scipts is Python 2/3 compatible without dependency.

## Usage

You can find help info with `python seff-statistics.py -h`. And here is an example:

```shell
$ python seff-statistics.py -A acct-hpc -u hpccsg,hpc-jianwen -S 2020-03-20T11:00:00 -E 2020-03-24
```

You can control the threshold of the efficiency jobs with two variable:

```python
low_cpu = 25     # Below 25% will be treated as low cpu efficiency
low_memory = 25  # Below 25% will be treated as low memery efficiency
```
