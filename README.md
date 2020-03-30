# Scripts for efficiency statistics of SLURM jobs

The scripts base on the output of `sacct` and `seff` and print the low efficiency jobs in STDOUT.
So make sure the `sacct` and `seff` work fine in your shell.
And the scipts is Python 2/3 compatible without dependency.

## Usage

You can find help info with `python seff-statistics.py -h`. And here is an example:

```shell
$ python seff-statistics.py -S `date +"%Y-%m-%dT%T" -d '4 hour ago'` -E `date +"%Y-%m-%dT%T"`
```

You can control the threshold of the efficiency jobs with two variable:

```python
low_cpu = 25     # Below 25% will be treated as low cpu efficiency
low_memory = 25  # Below 25% will be treated as low memery efficiency
```
