#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.report_pdf.subtasks.gen_precipitation_analysis_report import GenPrecipitationAnalysisReport

def get_task_dic():
    task_dict = {
        "gen_precipitation_analysis_report": (lambda: GenPrecipitationAnalysisReport(), '报告=> 生成降水报告'),
    }
    return task_dict
