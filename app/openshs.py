#!/bin/env python

import subprocess
import csv
from repeater import Repeater
from datetime import datetime, timedelta
import click
import os
import shutil
from collections import OrderedDict
import itertools

SCENARIOS = OrderedDict()
SCENARIOS['morning'] = {'exe': 'blender/morning.blend',
                         'dataset_path': 'temp/morning/',
                         'start_dt': datetime.strptime("2016-04-01 08:00:00", "%Y-%m-%d %H:%M:%S")}
SCENARIOS['evening'] = {'exe': 'blender/evening.blend',
                         'dataset_path': 'temp/evening/',
                         'start_dt': datetime.strptime("2016-04-01 18:00:00", "%Y-%m-%d %H:%M:%S")}

def validate_dt(value):
    try:
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        return dt
    except ValueError:
        raise click.BadParameter("Please enter a valid datetime")

def get_file_names(path):
    files = os.listdir(path)
    return sorted([f.rstrip('.csv') for f in files], key=lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S"))

def parse_scenario_filenames(filenames):
    di = {}
    for f in filenames:
        x = f.split('_')
        di[x[0]] = x[1].rstrip('.csv')
    return di

def get_scenario_filenames(path):
    files = os.listdir(path)
    di = parse_scenario_filenames(files)
    return di

def get_scenarios_dict():
    result = {}
    for scenario in SCENARIOS:
        di = get_scenario_filenames(SCENARIOS[scenario]['dataset_path'])
        for k in di:
            result[k] = {'repeat': int(di[k]), \
                         'filename': SCENARIOS[scenario]['dataset_path'] + k + '_' + str(di[k]) + '.csv'}

    return result

def sort_scenarios_dict_by_day(scenarios_dict):
    sorted_dict = OrderedDict()
    sorted_keys = sorted(scenarios_dict, key=lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S"))
    for k in sorted_keys:
        sorted_dict[k] = scenarios_dict[k]
    return sorted_dict

@click.group()
def main():
    """OpenSHS: Open Smart Home Simulator"""
    pass

@main.command()
@click.option('--list-scenarios', '-ls', default=False, is_flag=True, help='Lists the available scenarios.')
@click.option('--recorded-scenarios', '-rs', default=False, is_flag=True, help='Shows the status of the recorded scenarios.')
def status(list_scenarios, recorded_scenarios):
    """Shows the current status of the experiment."""
    if list_scenarios:
        click.echo(", ".join([x for x in SCENARIOS.keys()]))

    if recorded_scenarios:
        for scenario in SCENARIOS:
            click.echo("For scenario " + click.style(scenario, bold=True) + ":")
            di = get_scenario_filenames(SCENARIOS[scenario]['dataset_path'])
            for k in sorted(di):
                click.echo("\t" + k + " repeated: " + di[k])

@main.command()
@click.option('--scenario', '-s', type=click.Choice(list(SCENARIOS.keys())), help='Which scenario to start.')
@click.option('--primusrun', '-p', default=False, is_flag=True, help='Start the scenario with primus support (Linux Only).')
def start(scenario, primusrun):
    """Start a scenario experiment."""
    click.echo('Starting the ' + click.style(scenario, bold=True) + ' scenario.')
    start_dt = click.prompt("What's the starting date/time?",
                            default=SCENARIOS[scenario]['start_dt'],
                            value_proc=validate_dt)
    SCENARIOS[scenario]['start_dt'] = start_dt
    if primusrun:
        subprocess.call(["primusrun", "blender", SCENARIOS[scenario]['exe']], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.call(["blender", SCENARIOS[scenario]['exe']], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    num_repeat = click.prompt("How many times you want to repeat this pattern?", default=1, type=int)

    if not os.path.exists(SCENARIOS[scenario]['dataset_path']):
        os.makedirs(SCENARIOS[scenario]['dataset_path'])
    shutil.move('temp/output.csv', SCENARIOS[scenario]['dataset_path'])
    os.rename(SCENARIOS[scenario]['dataset_path'] + 'output.csv', \
              SCENARIOS[scenario]['dataset_path'] + datetime.strftime(start_dt, "%Y-%m-%d %H:%M:%S" + "_" + str(num_repeat) + ".csv"))

@main.command()
@click.option('--alpha', '-a', type=float, default=0.0, help='How random the repeated patterns.', )
def compile(alpha):
    """Compiles the datasets."""

    s_dict = get_scenarios_dict()
    ss_dict = sort_scenarios_dict_by_day(s_dict)

    aday = timedelta(days=1)

    # The header row
    first_el = list(ss_dict.items())[0][0]
    with open(ss_dict[first_el]['filename'], 'r') as headfile:
        csv_reader = csv.reader(headfile)
        header = next(csv_reader)
    header.append('timestamp')

    with open('datasets/dataset.csv', 'w') as outf:
        csv_writer = csv.writer(outf)
        csv_writer.writerow(header)

        d_rows = []
        for s_key in ss_dict:
            with open(ss_dict[s_key]['filename'], 'r') as inf:
                csv_reader = csv.reader(inf)
                next(csv_reader)
                rows = [x for x in csv_reader]
                start_dt = datetime.strptime(s_key, "%Y-%m-%d %H:%M:%S")
                for _ in range(ss_dict[s_key]['repeat']):
                    repeater = Repeater(rows, alpha, hasheader=False)
                    rep_rows = repeater.consData()
                    d_rows.append(add_timestamp_field(rep_rows, start_dt))
                    start_dt += aday

        flatten_rows = list(itertools.chain(*d_rows))
        sorted_rows = sorted(flatten_rows, key=lambda x: datetime.strptime(x[-1], "%Y-%m-%d %H:%M:%S"))
        csv_writer.writerows(sorted_rows)

def add_timestamp_field(reader, start_dt):
    if type(start_dt) is str:
        start_dt = datetime.strptime(start_dt, "%Y-%m-%d %H:%M:%S")
    ts = start_dt
    asec = timedelta(seconds=1)
    result = []

    for i in reader:
        row = i + [ts.strftime("%Y-%m-%d %H:%M:%S")]
        result.append(row)
        ts += asec
    return result


if __name__ == '__main__':
    main()
