# Fix a small contact directory

This example starts with a real bug: searching for `ann` misses the saved name
`Ann`. It has five existing tests. BW repaired it in an executed Q4/FP16-KV
client/server trial, including a new instruction sent while it was working.

## Try it

From your cloned BranchWrite folder, copy the example into a new project:

```sh
cp -a examples/repair-contact-directory/project ~/my-contact-directory
cd ~/my-contact-directory
~/.local/bin/bw
```

Use the server address and API key your operator gave you. Paste the text from
`01-fix-search.txt` at `You>`. While BW is working, paste
`02-live-followup.txt` and press Enter. That adds the Unicode requirement.
Do not paste the file name as the request; paste its contents.

When BW finishes, review `directory.py` and `tests/test_directory.py`. You can
also run the project checks yourself:

```sh
python3 -m unittest discover -s tests -v
python3 contacts.py CAFÉ
python3 contacts.py STRASSE
```

The last two commands should print `Café` and `Straße`. Saved names must stay
unchanged. A new run may take a different route or have a different outcome.

## What was checked

The observed run took about 5 minutes 42 seconds, including the live interruption,
model thinking, commands and saved-state work. The model added four tests; all
five original test methods remained unchanged. All nine tests passed. A separate
checker, unavailable inside the model's project, passed eleven checks on the
published files, including names, matching, order, saved bytes and final newline.
This is a bounded coding workflow, not numerical model or full release certification.
See `validation/real-project-loop-20261020`.
