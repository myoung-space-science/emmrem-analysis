# Developing eprempy-analysis

This document contains notes for those who wish to contribute to `eprempy-analysis` by modifying the code base. In order to develop `eprempy-analysis`, you should fork the respository, edit your forked copy, and submit a pull request for integration with the original repository.

Note that this is a living document and is subject to change without notice.

## Committing to the Repository

### Messages

Each commit message must have a subject line, which may be followed by an optional body. If the commit message has a body, a blank line must separate the subject line from the body. Subject lines need not follow the `<type>(<scope>): <subject>` format. In fact, we will prefer a plain-subject format, which allows more space for descriptive text and which is sufficient for a repository of this nature.

For example, a concise commit message may apply to a simple update
```
Fixed bug in plot-script.py
```
or a complex update
```
Improved path parsing in plot-script.py
```
in cases when the change(s) are self-explanatory in a code diff.

However, a commit message may warrant a body when the change(s) are not self-explanatory in a code diff or when the update touches multiple files.
```
Update plotting and refactor

* create plot_tools.py
* move make_plot function to plot_tools.py
* define create_panel function in plot_tools.py
* refactor main function in plot-script.py
```
or
```
Fix plotting loop

There was a subtle bug in the inner loop of plot_tools.make_plot
that was causing the flimp-florb to refuncsticate.
```

## Conventions

Top-level scripts should have names like `plot-script.py` and must have a CLI that passes arguments to a function, typically `main`. These scripts are not meant for import. All sharable code should live in modules that follow [standard Python style guidelines](https://peps.python.org/pep-0008/).

