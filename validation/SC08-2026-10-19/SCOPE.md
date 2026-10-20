SC08 reruns the original defect against corrected infrastructure.
The task source is git archive7ef483a with only coding_cli.py restored from
17260d4; tests and reference expectations are unchanged. The exact five original
duplicate-field failures remain. This is an explicit regression fixture override,
not the current production code. The installed dev2 client uses a fresh coding
root, rather than carrying47Ktokens from unrelated earlier projects. The Q8
native profile is unchanged; RAMpool12GiB replaces the oversized96GiB setting
on this124GiB host. Diskpool48GiB and actual memory guard stay enabled.
No complete new GPU pass yet. Original failed workflow remains dev1 and its
pending original operation is preserved; this run does not claim recovery of it.
