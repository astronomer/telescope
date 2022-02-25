from typing import Any, Dict, List

import json
import logging
import os.path

import click as click
from click import BadOptionUsage, Choice, Path
from tqdm.contrib.concurrent import process_map

from telescope.functions.astronomer_enterprise import verify, versions
from telescope.functions.cluster_info import cluster_info
from telescope.getter_util import gather_getters, get_from_getter
from telescope.reporters.report import (
    REPORT_TYPES,
    generate_charts,
    generate_output_reports,
    generate_report,
    generate_report_summary_text,
)
from telescope.upload import upload_to_gcs

log = logging.getLogger(__name__)

d = {"show_default": True, "show_envvar": True}
fd = {"show_default": True, "show_envvar": True, "is_flag": True}


@click.command()
@click.version_option()
@click.option("--local", "use_local", **fd, help="Airflow Reporting for local Airflow")
@click.option("--docker", "use_docker", **fd, help="Autodiscovery and Airflow reporting for local Docker")
@click.option("--kubernetes", "use_kubernetes", **fd, help="Autodiscovery and Airflow reporting for Kubernetes")
@click.option(
    "-l", "--label-selector", **d, default="component=scheduler", help="Label selector for Kubernetes Autodiscovery"
)
@click.option("--cluster-info", "should_cluster_info", **fd, help="Get cluster size and allocation in Kubernetes")
@click.option(
    "--verify",
    "should_verify",
    **fd,
    help="Introspect Helm installation information for Reporting and Verification purposes",
)
@click.option("--versions", "should_versions", **fd, help="checks versions of locally installed tools")
@click.option(
    "-f",
    "--hosts-file",
    **d,
    default=None,
    type=Path(exists=True, readable=True),
    help="Hosts file to pass in various types of hosts (ssh, kubernetes, docker) - See README.md for sample",
)
@click.option(
    "-p",
    "--parallelism",
    show_default="Number CPU",
    type=int,
    default=None,
    help="How many cores to use for multiprocessing",
)
@click.option(
    "--gather/--no-gather", "should_gather", **fd, default=True, help="Gather data about Airflow environments"
)
@click.option(
    "--report/--no-report", "should_report", **fd, default=False, help="Generate report summary of gathered data"
)
@click.option(
    "--charts/--no-charts", "should_charts", **fd, default=False, help="Generate charts of summary of gathered data"
)
@click.option(
    "--summary/--no-summary", "should_summary", **fd, default=False, help="Generate summary text file of gathered data"
)
@click.option(
    "--upload/--no-upload", "should_upload", **fd, default=False, help="Upload charts to get access to rich reporting"
)
@click.option(
    "-n",
    "--organization-name",
    "",
    **d,
    type=str,
    prompt=True,
    help="Denote who this report belongs to, e.g. a company name",
)
@click.option("--report-type", type=Choice(REPORT_TYPES.keys()), default="xlsx", help="What report type to generate")
def cli(
    use_local: bool,
    use_docker: bool,
    use_kubernetes: bool,
    label_selector: str,
    should_verify: bool,
    should_versions: bool,
    should_cluster_info: bool,
    hosts_file: str,
    parallelism: int,
    should_gather: bool,
    should_report: bool,
    should_charts: bool,
    should_summary: bool,
    should_upload: bool,
    organization_name: str,
    report_type: str,
) -> None:
    """Telescope - A tool to observe distant (or local!) Airflow installations, and gather usage metadata"""
    data = {}
    output_file = f"{organization_name}.data.json"

    if should_gather:
        with click.open_file(output_file, "w") as output:
            log.info(f"Gathering data and saving to {output_file} ...")

            # Add special method calls, don't know a better way to do this
            if should_cluster_info:
                data["cluster_info"] = cluster_info()

            if should_verify:
                data["verify"] = verify()

            if should_versions:
                data["versions"] = versions()

            # flatten getters - for multiproc
            all_getters = [
                getter
                for (_, getters) in gather_getters(
                    use_local, use_docker, use_kubernetes, hosts_file, label_selector
                ).items()
                for getter in getters
            ]

            # get all the Airflow Reports at once, in parallel
            results: List[Dict[Any, Any]] = process_map(get_from_getter, all_getters, max_workers=parallelism)

            # unflatten and assemble into report
            for result in results:
                for (host_type, getter_key, key), value in result.items():
                    if host_type not in data:
                        data[host_type] = {}

                    if getter_key not in data[host_type]:
                        data[host_type][getter_key] = {}

                    data[host_type][getter_key][key] = value

            log.info(f"Writing data to {output_file} ...")
            output.write(json.dumps(data, default=str))
    elif any([should_report, should_charts, should_summary, should_upload]):
        # We didn't have a "gather" step, so there's filled "report" object. Hope there's a file
        if not os.path.exists(output_file):
            raise BadOptionUsage("--report", f"There is no data to aggregate at {output_file}, failing to report")

        with open(output_file) as input_file:
            data = json.load(input_file)

    if any([should_report, should_charts, should_summary, should_upload]):
        if not len(data):
            raise BadOptionUsage(
                "--report",
                f"There is no data to aggregate without --gather, or an existing {output_file}, failing to report",
            )

        log.info(f"Aggregating Raw Data...")
        output_reports = generate_output_reports(data)

        if should_report:
            output_filepath = f"report.{report_type}"
            log.info(f"Generating Report of type {report_type} at {output_filepath} ...")
            generate_report(output_reports, report_type, output_filepath)

        if should_charts:
            try:
                log.info("Generating Charts at default filepath: [/charts] ...")
                generate_charts(output_reports)
            except ImportError as e:
                log.error(f"Attempted to generate charts but failed with error, skipping... - {e}")

        if should_summary:
            log.info("Generating Summary Report at default filepath: [report_summary.txt] ...")
            generate_report_summary_text(output_reports)

        if should_upload:
            output_reports["raw"] = data
            upload_to_gcs(output_reports=output_reports, organization_name=organization_name)


if __name__ == "__main__":
    cli(auto_envvar_prefix="TELESCOPE")
