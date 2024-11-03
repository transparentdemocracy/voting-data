# Visualizing voting in the Belgian federal parliament (chamber)

We believe that in a democracy, it should be transparent and easily understandable what politicians, who represent the people, voted for.

This project currently visualizes the voting behavior of the politicians in the Belgian federal parliament (Chamber), starting from [oct 1st, 202](https://nl.wikipedia.org/wiki/Regering-De_Croo).

## The data

We built [watdoetdepolitiek.be](http://watdoetdepolitiek.be) to let you browse the data we extracted freely, according to your interests.

You can also check out the data yourself in [data/output](https://github.com/transparentdemocracy/voting-data/tree/main/data/output).

## Convinced of this project's potential?

We are looking for software developers, designers, marketeers, translators, ...

To get an idea of the **ideas we have planned on a high-level**, have a look at [our board of planned ideas](https://github.com/orgs/transparentdemocracy/projects/1/views/1).

Of course, **concrete implementation ideas, details and discussions related to this voting-data project**, are
tracked in [this project's issues](https://github.com/transparentdemocracy/voting-data/issues).

If you are interested to work on a certain feature, let us know via the above links.
When done, and when needing to set up this project to run locally, check the [contributing.md](https://github.com/transparentdemocracy/voting-data/blob/main/contributing.md).

If you want to bring ideas too, welcome!

You can create [Github issues](https://github.com/transparentdemocracy/voting-data/issues) if they are relevant to this repository.
We also have a public [discussion channel](https://github.com/orgs/transparentdemocracy/discussions) here on Github and a private discussion channel on Slack.

## Local development

Execute these three steps to get started as a developer (details below):

- Create virtual environment
- Install requirements
- Install the project in developer mode

This will install the python modules so you can import them in your own projects and install command-line tools (see setup.py, look for td-...).

### Create virtual environment

Create a virtual environment and install the project in development mode. Note:
if you're familiar with it you can also use conda or other environment management tools.

    python -mvenv venv
    . venv/bin/activate

Note that you should run `. venv/bin/activate` (or equivalent) whenever you want to work in a new shell.

### Install requirements

    pip install -r requirements.txt
    pip install setuptools

### Install the project in developer mode

    pip install -e .

### Set up OpenAI

Sign up for the OpenAI API at https://openai.com/index/openai-api.

Create a new secret ket at https://platform.openai.com/api-keys

Set the OPENAI_API_KEY environment variable to the secret key you just created.

    export OPENAI_API_KEY=sk-...

## Testing

Run `./test.sh` to run unit tests.

Note: some of the tests are rather slow, you can skip these by setting the SKIP_SLOW environment variable: `SKIP_SLOW=1 ./test.sh`

## Downloading and generating data

First, run `./download-reports.sh` and `./download-actors.sh` to download plenary html reports and json information about politicians

Next, run  `./run-all.sh` to generate all the data used the downstream projects (data is written to `data/output/...`)

