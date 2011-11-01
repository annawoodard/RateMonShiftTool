from RateMonitorShifterFunction import RateMon

from Page1Parser import Page1Parser
from GetRun import GetRun
import sys
import os
import cPickle as pickle
import getopt
import time
from ReadConfig import RateMonConfig
from colors import *

WBMPageTemplate = "http://cmswbm/cmsdb/servlet/RunSummary?RUN=%s&DB=cms_omds_lb"
WBMRunInfoPage = "https://cmswbm/cmsdb/runSummary/RunSummary_1.html"

RefRunNameTemplate = "RefRuns/Run_%s.pk"

selected_runs = []
runs_file = 'run_list.csv'
input_file = open(runs_file)
file_content = input_file.read()
for line in file_content.splitlines():
    if line.strip():
        [run, min_ls, max_ls] = [int(item) for item in line.split(',')]
        selected_runs.append(run)
BeginningLS = 10
for run in selected_runs:
    RateMon(run,BeginningLS)
