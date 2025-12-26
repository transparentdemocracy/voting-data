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

## Testing

Run `./test.sh` to run unit tests, or configure and save a Run configuration in Pycharm to run all tests in the 
transparentdemocracy package folder (you can create this easily by right clicking that folder, then selecting "Run 
python tests in...").

Both ways of running the tests will require that you set some secrets in OS environment variables first, either directly
from the command terminal, or in the created Pycharm run configuration's settings.

The environment variables we currently use are: WDDP_STORAGE_SERVICE_ACCOUNT_CREDENTIALS=...;WDDP_PROD_ES_AUTH=...; SKIP_SLOW=1

WDDP_STORAGE_SERVICE_ACCOUNT_CREDENTIALS is a JSON object.
WDDP_PROD_ES_AUTH is a username:password pair.
Copy the actual secrets from our password manager.
SKIP_SLOW is currently set to 1, because some of the tests are rather slow, we usually skip them.

## Running the Data Processing Pipeline

The data processing pipeline has been redesigned with clear phases and improved logging. You can control the behavior using environment variables:

### Environment Variables

- `LOG_LEVEL`: Controls logging verbosity (DEBUG, INFO, WARNING, ERROR) - default: INFO
- `INTERACTIVE`: Whether to prompt between phases (true/false) - default: true  
- `WDDP_ENVIRONMENT`: Environment to run in (test/local/dev/prod) - default: dev
- `LEGISLATURE`: Legislature number to process - default: 56
- `DOWNLOAD_ACTORS`: Whether to download actor data (true/false) - default: false
- `UPDATE_POLITICIANS`: Whether to update politician data (true/false) - default: false

### Processing Phases

The pipeline runs through 7 clear phases:

1. **DETERMINE PLENARIES** - Identify which plenary sessions need processing
2. **DOWNLOAD REPORTS** - Download HTML plenary reports from dekamer.be
3. **ANALYZE DOCUMENTS** - Extract voting data and identify referenced documents
4. **PLAN DOCUMENT WORK** - Determine which documents need downloading/summarizing
5. **DOWNLOAD DOCUMENTS** - Download PDF documents that need processing
6. **SUMMARIZE DOCUMENTS** - Generate AI summaries for documents
7. **PUBLISH RESULTS** - Publish processed data to ElasticSearch backend

### Usage Examples

```bash
# Run with minimal logging, no prompts (good for CI/CD)
LOG_LEVEL=WARNING INTERACTIVE=false python -m transparentdemocracy.main

# Run with debug logging and prompts (good for development)
LOG_LEVEL=DEBUG INTERACTIVE=true python -m transparentdemocracy.main

# Run in production mode
WDDP_ENVIRONMENT=prod LOG_LEVEL=INFO python -m transparentdemocracy.main

# Use the convenience script
python run_processing.py
```

### Logging Improvements

- **Phase-based logging**: Clear separation of processing phases with progress indicators
- **Appropriate log levels**: Important information at INFO level, detailed operations at DEBUG level
- **Progress tracking**: Shows progress for long-running operations like document processing
- **Reduced noise**: Third-party library logging is suppressed to focus on relevant information

## Downloading and generating data


Set up the .env file. See `.env.example` to get started.
You don't need to use the keepass configuration mechanism, but it's generally a good idea not to store secrets in plain text.

Run:

    python -m transparentdemocracy.main


New orchestration: application.py, ES_AUTH=username:password (see our password database) and LEGISLATURE=56 env vars to set.
