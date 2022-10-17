#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import threading

class MultiThread:
    def __init__(self, handlers={}):
        self.handlers = handlers
        self.threads = []

    def run_handler(self,handler):
        t = threading.Thread(target=handler)
        t.setDaemon(True)
        t.start()
        self.threads.append(t)
        logging.info('start thread,threads num: {}'.format(len(self.threads)))

    def run_arg_handler(self,handler,task_dict,task_type):
        t = threading.Thread(target=handler, kwargs={"task_dict":task_dict,"task_type":task_type})
        t.setDaemon(True)
        t.start()
        self.threads.append(t)
        logging.info('start rds listening thread,threads num: {}'.format(len(self.threads)))

    def run(self):
        for task_type, handler in self.handlers.items():
            t = threading.Thread(target=handler, name=task_type)
            t.setDaemon(True)
            t.start()
            self.threads.append(t)
            logging.info('start thread {}, threads num: {}'.format(task_type, len(self.threads)))

    def close(self):
        for t in self.threads:
            t.join()
            logging.info('{0} exit now'.format(t.getName()))