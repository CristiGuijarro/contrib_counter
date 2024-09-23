from datetime import datetime
from os import environ
from typing import Any, Dict, List

import click
import pandas as pd
import plotly.express as px
import requests


def get_contributions_query(username: str, from_date: str, cursor: str = None) -> str:
    """Constructs a GraphQL query to fetch contributions for a specific period.

    Args:
        username: The GitHub username.
        from_date: The start date for the query in ISO format (YYYY-MM-DD).
        cursor: A pagination cursor to fetch the next page of results.

    Returns:
        A formatted GraphQL query string.
    """
    after_clause = f', after: "{cursor}"' if cursor else ""
    return f"""
    {{
      user(login: "{username}") {{
        contributionsCollection(from: "{from_date}T00:00:00Z") {{
          commitContributionsByRepository(maxRepositories: 100) {{
            contributions(first: 100{after_clause}) {{
              nodes {{
                occurredAt
              }}
              pageInfo {{
                hasNextPage
                endCursor
              }}
            }}
          }}
          issueContributions(first: 100{after_clause}) {{
            nodes {{
              occurredAt
            }}
            pageInfo {{
              hasNextPage
              endCursor
            }}
          }}
          pullRequestContributions(first: 100{after_clause}) {{
            nodes {{
              occurredAt
            }}
            pageInfo {{
              hasNextPage
              endCursor
            }}
          }}
          pullRequestReviewContributions(first: 100{after_clause}) {{
            nodes {{
              occurredAt
            }}
            pageInfo {{
              hasNextPage
              endCursor
            }}
          }}
          repositoryContributions(first: 100{after_clause}) {{
            nodes {{
              occurredAt
            }}
            pageInfo {{
              hasNextPage
              endCursor
            }}
          }}
          restrictedContributionsCount  # Includes restricted contributions (e.g., private contributions)
          contributionCalendar {{
            totalContributions
            weeks {{
              contributionDays {{
                contributionCount
                date
              }}
            }}
          }}
        }}
      }}
    }}
    """


def fetch_contributions(
    username: str, header: dict, from_date: str
) -> List[Dict[str, Any]]:
    """Fetches contributions for a specified period, handling pagination.

    Args:
        username: The GitHub username.
        header: Authorisation header with token bearer.
        from_date: The start date for fetching contributions.

    Returns:
        A list of contributions with their associated dates.
    """
    contributions = []
    cursor = None

    while True:
        query = get_contributions_query(username, from_date, cursor)
        response = requests.post(
            "https://api.github.com/graphql", json={"query": query}, headers=header
        )
        data = response.json()

        if "errors" in data:
            print("GraphQL API returned errors:", data["errors"])
            break

        contributions_data = data["data"]["user"]["contributionsCollection"]
        contributions.extend(extract_contributions(contributions_data))

        # Checking for pagination
        page_info = get_page_info(contributions_data)
        if page_info["hasNextPage"]:
            cursor = page_info["endCursor"]
        else:
            break

    return contributions


def extract_contributions(contributions_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts contributions from commit, issue, and pull request data.

    Args:
        contributions_data: The raw contribution data from GitHub.

    Returns:
        A list of contribution occurrences.
    """
    contributions = []

    for repo_contrib in contributions_data["commitContributionsByRepository"]:
        contributions.extend(repo_contrib["contributions"]["nodes"])

    contributions.extend(contributions_data["issueContributions"]["nodes"])

    contributions.extend(contributions_data["pullRequestContributions"]["nodes"])

    return contributions


def get_page_info(contributions_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts pagination information from the GraphQL response.

    Args:
        contributions_data: The raw contribution data.

    Returns:
        A dictionary containing pagination information.
    """
    commit_page_info = contributions_data["commitContributionsByRepository"][0][
        "contributions"
    ]["pageInfo"]
    return {
        "hasNextPage": commit_page_info["hasNextPage"],
        "endCursor": commit_page_info["endCursor"],
    }


def fetch_all_contributions(
    username: str, header: dict, start_date: datetime, end_date: datetime
) -> List[Dict[str, Any]]:
    """Fetches all contributions within a specified date range.

    Args:
        username: The GitHub username.
        header: Authorisation header with token bearer.
        start_date: The start date for fetching contributions.
        end_date: The end date for fetching contributions.

    Returns:
        A list of all contributions made within the specified period.
    """
    contributions = []
    for year_offset in range(end_date.year - start_date.year):
        current_start = start_date.replace(year=start_date.year + year_offset)
        contributions.extend(
            fetch_contributions(username, header, current_start.strftime("%Y-%m-%d"))
        )

    return contributions


def process_contributions(contributions_data: List[Dict[str, Any]]) -> List[str]:
    """Processes raw contribution data and extracts the contribution dates.

    Args:
        contributions_data: A list of contribution occurrences.

    Returns:
        A list of contribution dates as strings.
    """
    return [contribution["occurredAt"] for contribution in contributions_data]


def generate_plotly_heatmap(dates: List[str], output_file: str) -> None:
    """Generates a heatmap from contribution dates using Plotly.

    Args:
        dates: A list of contribution dates.
        output_file: The output file path where the heatmap will be saved.
    """
    dates = pd.to_datetime(dates, utc=True)
    df = pd.DataFrame({"date": dates})
    df["count"] = 1

    # Grouping by date to count contributions on a per-day basis
    df = df.groupby("date").sum().reset_index()

    df["weekday"] = df["date"].dt.weekday
    df["week"] = df["date"].dt.isocalendar().week
    df["year"] = df["date"].dt.year

    df = df[
        df["weekday"] < 5
    ]  # Weekend are not meant for working. (Monday-FriYay only).

    # Pivots the table to mimic the GitHub/GitLab contributions graph layout
    heatmap_data = df.pivot_table(
        index="weekday", columns=["year", "week"], values="count", fill_value=0
    )

    heatmap_data.index = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    # Custom yellow-to-dark green color scale
    custom_colorscale = [
        [0, "#ffffcc"],  # 0 contributions
        [0.1, "#d9f0a3"],  # 1 contribution
        [0.2, "#addd8e"],  # 2 contributions
        [0.3, "#78c679"],  # 3 contributions
        [0.4, "#41ab5d"],  # 4 contributions
        [0.5, "#238443"],  # 5 contributions
        [0.6, "#006837"],  # 6 contributions
        [0.7, "#004529"],  # 7 contributions
        [0.8, "#003300"],  # 8 contributions
        [0.9, "#002200"],  # 9 contributions
        [1, "#001a00"],  # 10+ contributions - to work with cap later on
    ]

    # Cap the maximum at 10 because contributions can really vary!
    heatmap_data = heatmap_data.map(lambda x: min(x, 10))

    # Calculate total weeks based on the heatmap data for job phases later (e.g. current week)
    total_weeks = heatmap_data.shape[1]

    fig = px.imshow(
        heatmap_data.values,
        labels=dict(x="Year-Week", y="Weekday", color="Contributions"),
        aspect="equal",
        color_continuous_scale=custom_colorscale,
        zmin=-1,  # Minimum contributions hack - to lazy-improve contrast
        zmax=10,
    )

    fig.update_layout(
        title="GitHub Contributions Heatmap",
        coloraxis_showscale=False,  # Removing the colour scale bar because it is not helpful
        xaxis_title="Weeks",
        yaxis_title="Weekday",
        yaxis=dict(
            tickvals=[0, 1, 2, 3, 4],
            ticktext=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        ),
    )

    # Adds in x-axis ticks for the start of each year
    years = df["year"].unique()
    year_starts = df.groupby(df["year"])["week"].min()
    fig.update_xaxes(
        tickvals=[
            heatmap_data.columns.get_loc((year, start))
            for year, start in zip(years, year_starts)
        ],
        ticktext=[str(year) for year in years],
        tickangle=45,
    )

    # Edit below to suit needs
    # Adding in job phases as colour-specified gridlines/shapes around contribution points
    # job_phases = [
    #     {
    #         "name": "In-Office",
    #         "start": 0,
    #         "end": 16,
    #         "colour": "rgba(255, 255, 255, 0.5)",
    #     },  # White
    #     {
    #         "name": "Fully Remote",
    #         "start": 16,
    #         "end": 47,
    #         "colour": "rgba(150, 150, 150, 0.5)",
    #     },  # Medium Grey
    #     {
    #         "name": "Hybrid (3 days in office)",
    #         "start": 47,
    #         "end": 95,
    #         "colour": "rgba(255, 255, 255, 0.5)",
    #     },
    #     {
    #         "name": "Remote (2 days a week part time)",
    #         "start": 95,
    #         "end": 101,
    #         "colour": "rgba(150, 150, 150, 0.5)",
    #     },
    #     {
    #         "name": "Fully Remote Again",
    #         "start": 101,
    #         "end": 137,
    #         "colour": "rgba(255, 255, 255, 0.5)",
    #     },
    #     {
    #         "name": "Hybrid (2 days in office) ** Gitlab contributions",
    #         "start": 137,
    #         "end": total_weeks,
    #         "colour": "rgba(150, 150, 150, 0.5)",
    #     },
    # ]

    # for job in job_phases:
    #     # Loop through the weeks for the job phase and add vertical lines
    #     for i in range(job["start"], job["end"]):
    #         # Add vertical gridline between each tile in the job phase
    #         fig.add_shape(
    #             type="line",
    #             x0=i + 0.5,
    #             y0=-0.5,
    #             x1=i + 0.5,
    #             y1=4.5,
    #             line=dict(color=job["colour"], width=2),
    #             layer="above",
    #         )

    #     # Add horizontal lines between each weekday in the phase
    #     for j in range(5):  # Loop through weekdays
    #         fig.add_shape(
    #             type="line",
    #             x0=job["start"],
    #             x1=job["end"],
    #             y0=j + 0.5,
    #             y1=j + 0.5,
    #             line=dict(color=job["colour"], width=2),
    #             layer="above",
    #         )

    #     # Adds job label at the center of the phase section below plot
    #     fig.add_annotation(
    #         x=(job["start"] + job["end"]) / 2,
    #         y=5,
    #         text=job["name"],
    #         showarrow=False,
    #         font=dict(color="black", size=10),
    #         bgcolor=job["colour"],
    #     )

    fig.write_html(output_file)
    fig.show()


@click.command()
@click.option("--username", default="CristiGuijarro", help="Your GitHub username.")
@click.option(
    "--start", default="2019-09-15", help="Start date for fetching contributions."
)
@click.option(
    "--end",
    default=datetime.today().strftime("%Y-%m-%d"),
    help="End date for fetching contributions.",
)
@click.option(
    "--output",
    default="contributions_plotly_fig.html",
    help="Output file for the heatmap.",
)
def main(username: str, start: str, end: str, output: str) -> None:
    """Main function to collect contributions and plot data to file."""

    token = environ.get("GITHUB_READ_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}

    start_datetime = datetime.strptime(start, "%Y-%m-%d")
    end_datetime = datetime.strptime(end, "%Y-%m-%d")

    contributions_data = fetch_all_contributions(
        username, headers, start_datetime, end_datetime
    )

    contribution_dates = process_contributions(contributions_data)

    generate_plotly_heatmap(contribution_dates, output)


if __name__ == "__main__":

    main()
