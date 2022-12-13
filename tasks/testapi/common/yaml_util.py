'''
Author: lisheng
Date: 2022-11-01 22:09:56
LastEditTime: 2022-11-02 13:25:34
LastEditors: lisheng
Description: 
FilePath: /go-ship-server/testapi/common/yaml_util.py
'''
import os
import yaml


def read_yaml(key):
    with open(os.getcwd()+"/extract.yaml", encoding="utf-8", mode="r") as f:
        value = yaml.load(f, yaml.FullLoader)
        return value[key]
  
  
def read_yaml_test_cases(yamlpath):
    with open(os.getcwd()+"/"+yamlpath, encoding="utf-8", mode="r") as f:
        value = yaml.load(f, yaml.FullLoader)
        return value

        
def write_yaml(data, yamlpath):
    with open(os.getcwd()+"/"+yamlpath, encoding="utf-8", mode="a+") as f:
        yaml.dump(data, stream=f, allow_unicode=True)