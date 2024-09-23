# Contrib Counter

A command-line tool to collect GitHub contributions over a specified date range and generate a heatmap of contributions. The tool allows users to visualise their activity using a Plotly plotted heatmap.

## How to Develop/fit to your needs

To clone and work with your own version of this contributions counter:

```bash
git clone https://github.com/CristiGuijarro/contrib_counter.git
cd contrib-counter
```

Set up a virtual environment e.g.

```bash
python3 -m venv venv
source venv/bin/activate   # For Linux/Mac/preferred OS
venv\Scripts\activate      # For Windows - maybe, unsure
```

Install the required Python packages.

```bash
poetry install
```

Edit the commented region for job phases - requires some tweaks, this was a quick and dirty effort for a single use-case. I know it can be improved. Uncomment when it suits your job phases (or equivalent, who knows).

```bash
python contrib_counter.py --username your-username --start YYYY-MM-DD --end YYYY-MM-DD --output output_file.html
# Replace your-username, start, and end with the appropriate values.
```

## Installation

Clone the repository:

```bash
git clone https://github.com/your-username/contrib-counter.git
cd contrib-counter
```

And install...

```bash
poetry install
```

## Usage

Once installed, you can use the CLI tool contrib-counter to generate a heatmap from your GitHub contributions.

Requires GitHub personal access token (classic fine) with read permissions to access in an env variable. Private contributions are only viewable if private contributions are turned on in your GitHub profile.

```
export GITHUB_READ_TOKEN=XXXXXXXXXXX # Replace with an actual token
```

Example:

```bash
python contrib_counter.py --username CristiGuijarro --start 2022-01-01 --end 2023-01-01 --output contributions.html
```

You can access the help documentation by running:

```bash
$ contrib-counter --help

Usage: contrib-counter [OPTIONS]

  Main function to collect contributions and plot data to file.

Options:
  --username TEXT  Your GitHub username.
  --start TEXT     Start date for fetching contributions.
  --end TEXT       End date for fetching contributions.
  --output TEXT    Output file for the heatmap.
  --help           Show this message and exit.
```
