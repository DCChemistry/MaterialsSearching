# MaterialsSearching
 A one-stop shop for searching materials databases. Currently this codebase is able to search Google's GNoME and the Materials Project databases. Hoping to add the ability to search more databases in the future.

## Installation and setup:
This code uses Poetry to set up the necessary dependencies. The documentation on how to install and use Poetry is available here: https://python-poetry.org/docs/

To install Poetry, you will first need pipx. If you do not have root permissions on the machine on which you want to run this code, then you may not be able to install pipx in the usual way (see https://github.com/pypa/pipx). Instead, you will need to install the zipapp (pipx.pyz file) from the Releases page on the pipx github repository (https://github.com/pypa/pipx/releases).

Assuming you are not running on Windows, run `wget` and the link to the pipx.pyz file, e.g.

```wget https://github.com/pypa/pipx/releases/download/1.4.3/pipx.pyz```

Then add execute permissions to the pipx.pyz file with
```chmod +x pipx.pyz```

followed by

```python pipx.pyz ensurepath```.

Typing the above command will provide you with a path to where you need to move the pipx.pyz file. Move the pipx.pyz file into that directory with `mv`.

You will likely need to also update your .bashrc file with

```source ~/.bashrc```

This may be a .zshrc file on MacOS instead of a .bashrc file.

Now you should have access to pipx and you should now be able to install poetry with the command

```pipx.pyz install poetry```

Afterwards, clone this directory into your directory of choice, i.e.

```git clone https://github.com/DCChemistry/MaterialsSearching```

Go into the newly made directory with

```cd MaterialsSearching```

Inside the cloned directory there is a `pyproject.toml` file present with which you will be able to install the necessary dependencies for this codebase.

For this codebase, you will need Python 3.11, which you can install using conda, for example:

```conda create -n py3.11 python=3.11```

and then activate using

```conda activate py3.11```

Then, using the command

```whereis python```

you need to locate the path to the Python 3.11 binary. Once you have this path, deactivate your conda environment with

```conda deactivate```

Then you will need to provide this binary to poetry by using

```poetry use env <PATH-TO-PYTHON3.11-BIN>```

Now you will be able to install the necessary dependencies by typing

```poetry install --no-root`

and subsequently activate the environment with

```poetry shell```

And now you have finally set up the necessary dependencies for this project!

To run the code from terminal, you will need to use

```poetry run python <PYTHON-SCRIPT>```

With a Python script that contains the necessary information to perform a database search.
