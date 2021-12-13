from typing import Any, Dict, List

import json
import logging
import os.path
from functools import partial
from importlib.resources import path

import click as click
import yaml
from click import BadOptionUsage, Choice, Path
from tqdm.contrib.concurrent import process_map

import telescope.util
from telescope.functions.astronomer_enterprise import precheck, verify
from telescope.functions.cluster_info import cluster_info
from telescope.getter_util import gather_getters, get_from_getter
from telescope.getters.kubernetes import KubernetesGetter
from telescope.getters.local import LocalGetter
from telescope.reporters.report import REPORT_TYPES, assemble, assemble_from_file

log = logging.getLogger(__name__)


d = {"show_default": True, "show_envvar": True}
fd = {"show_default": True, "show_envvar": True, "is_flag": True}


@click.command()
@click.version_option()
@click.option("--local", "use_local", **fd, help="checks versions of locally installed tools")
@click.option("--docker", "use_docker", **fd, help="autodiscovery and airflow reporting for local docker")
@click.option("--kubernetes", "use_kubernetes", **fd, help="autodiscovery and airflow reporting for kubernetes")
@click.option(
    "-l", "--label-selector", **d, default="component=scheduler", help="Label selector for Kubernetes Autodiscovery"
)
@click.option("--cluster-info", "should_cluster_info", **fd, help="get cluster size and allocation in kubernetes")
@click.option("--verify", "should_verify", **fd, help="adds helm installations to report")
@click.option(
    "--precheck", "should_precheck", **fd, help="runs Astronomer Enterprise pre-install sanity-checks in the report"
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
    "--report/--no-report", "should_report", **fd, default=True, help="Generate report summary of gathered data"
)
@click.option("--report-type", type=Choice(REPORT_TYPES.keys()), default="xlsx", help="What report type to generate")
def cli(
    use_local: bool,
    use_docker: bool,
    use_kubernetes: bool,
    label_selector: str,
    should_verify: bool,
    should_precheck: bool,
    should_cluster_info: bool,
    hosts_file: str,
    output_file: str,
    parallelism: int,
    should_gather: bool,
    should_report: bool,
    report_type: str,
) -> None:
    """Telescope - A tool to observe distant (or local!) Airflow installations, and gather usage metadata"""
    # noinspection PyTypeChecker
    with path(telescope, "config.yaml") as config_file_path, open(config_file_path.resolve()) as config_file:
        report = {}

        if should_gather:
            with click.open_file(output_file, "w") as output:
                log.info(f"Gathering data and saving to {output_file} ...")
                config_inputs = yaml.safe_load(config_file)

                # Add special method calls, don't know a better way to do this
                if should_cluster_info:
                    report["cluster_info"] = cluster_info(KubernetesGetter())

                if should_precheck:
                    report["precheck"] = precheck(KubernetesGetter())

                if should_verify:
                    report["verify"] = verify(LocalGetter())

                # flatten getters - for multiproc
                all_getters = [
                    getter
                    for (_, getters) in gather_getters(
                        use_local, use_docker, use_kubernetes, hosts_file, label_selector
                    ).items()
                    for getter in getters
                ]

                # get evverrryttthinngggg all at once
                results: List[Dict[Any, Any]] = process_map(
                    partial(get_from_getter, config_inputs=config_inputs), all_getters, max_workers=parallelism
                )

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

                assemble_from_file(output_file, output_filepath=report_output_file, report_type=report_type)
            else:
                if not len(report):
                    raise BadOptionUsage(
                        "--report", "There is no data to generate a report on without --gather, failing to report"
                    )
                assemble(report, output_filepath=report_output_file, report_type=report_type)


if __name__ == "__main__":
    cli(auto_envvar_prefix="TELESCOPE")
