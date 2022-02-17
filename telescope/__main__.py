from typing import Any, Dict, List

import json
import logging
import multiprocessing
import os.path

import click as click
from click import BadOptionUsage, Choice, Path, echo
from tqdm.contrib.concurrent import process_map

import telescope
from telescope.functions.astronomer_enterprise import precheck, verify, versions
from telescope.functions.cluster_info import cluster_info
from telescope.getter_util import gather_getters, get_from_getter
from telescope.reporters.report import (
    REPORT_TYPES,
    generate_charts,
    generate_output_reports,
    generate_report,
    generate_report_summary_text,
)

log = logging.getLogger(__name__)

d = {"show_default": True, "show_envvar": True}
fd = {"show_default": True, "show_envvar": True, "is_flag": True}


def version(ctx, self, value):
    if not value or ctx.resilient_parsing:
        return
    echo(f"Telescope, version {telescope.version}")
    ctx.exit()


@click.command()
@click.version_option()
@click.option(
    "--version", is_flag=True, expose_value=False, is_eager=True, help="Show the version and exit.", callback=version
)
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
    "--precheck", "should_precheck", **fd, help="Runs Astronomer Enterprise pre-install sanity-checks in the report"
)
@click.option(
    "-f",
    "--hosts-file",
    **d,
    default=None,
    type=Path(exists=True, readable=True),
    help="Hosts file to pass in various types of hosts (ssh, kubernetes, docker) - See README.md for sample",
)
@click.option(
    "-o",
    "--output-file",
    **d,
    type=Path(),
    default="report.json",
    help="Output file to write intermediate gathered data json, and report (with report_type as file extension), can be '-' for stdout",
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
@click.option("--report-type", type=Choice(REPORT_TYPES.keys()), default="xlsx", help="What report type to generate")
def cli(
    use_local: bool,
    use_docker: bool,
    use_kubernetes: bool,
    label_selector: str,
    should_verify: bool,
    should_versions: bool,
    should_precheck: bool,
    should_cluster_info: bool,
    hosts_file: str,
    output_file: str,
    parallelism: int,
    should_gather: bool,
    should_charts: bool,
    should_report: bool,
    report_type: str,
) -> None:
    """Telescope - A tool to observe distant (or local!) Airflow installations, and gather usage metadata"""
    # noinspection PyTypeChecker
    report = {}

    if should_gather:
        with click.open_file(output_file, "w") as output:
            log.info(f"Gathering data and saving to {output_file} ...")

            # Add special method calls, don't know a better way to do this
            if should_cluster_info:
                report["cluster_info"] = cluster_info()

            if should_precheck:
                report["precheck"] = precheck()

            if should_verify:
                report["verify"] = verify()

            if should_versions:
                report["versions"] = versions()

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
                    if host_type not in report:
                        report[host_type] = {}

                    if getter_key not in report[host_type]:
                        report[host_type][getter_key] = {}

                    report[host_type][getter_key][key] = value

            log.info(f"Writing report to {output_file} ...")
            output.write(json.dumps(report, default=str))

    if should_report:
        report_output_file = output_file
        if ".json" in output_file:
            if report_type == "json":
                report_output_file = report_output_file.replace(".json", f"_output.json")
            else:
                report_output_file = report_output_file.replace(".json", f"_output.{report_type}")
        log.info(f"Generating report to {report_output_file} ...")

        if not should_gather:
            # We didn't have a "gather" step, so there's filled "report" object. Hope there's a file
            if not os.path.exists(output_file):
                raise BadOptionUsage(
                    "--report", f"There is no data generated to report on at {output_file}, failing to report"
                )

            with open(output_file) as input_file:
                report = json.load(input_file)
                generate_outputs(
                    report, output_filepath=report_output_file, report_type=report_type, should_charts=should_charts
                )
        else:
            if not len(report):
                raise BadOptionUsage(
                    "--report", "There is no data to generate a report on without --gather, failing to report"
                )
            generate_outputs(
                report, output_filepath=report_output_file, report_type=report_type, should_charts=should_charts
            )


def generate_outputs(report: dict, report_type: str, output_filepath: str, should_charts: bool):
    log.info(f"Aggregating Raw Data...")
    output_reports = generate_output_reports(report)

    log.info(f"Generating Report of type {report_type} at {output_filepath} ...")
    generate_report(output_reports, report_type, output_filepath)
    if should_charts:
        try:
            log.info("Generating Charts ...")
            generate_charts(output_reports)
        except ImportError as e:
            log.error(f"Attempted to generate charts but failed with error, skipping... - {e}")

    log.info("Generating Summary Report at default filepath [report_summary.txt] ...")
    generate_report_summary_text(output_reports)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    cli(auto_envvar_prefix="TELESCOPE")
