#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import logging
import traceback

class BaseDecorate:
    def exception_capture(self,func):
        def wrapper(self, *args, **kwargs):
            try:
                func(self, *args, **kwargs)
            except Exception as e:
                logging.error('run error {}'.format(e))
                logging.error(traceback.format_exc())
        return wrapper

    def exception_capture_close_datebase(self,func):
        def wrapper(self, *args, **kwargs):
            try:
                func(self, *args, **kwargs)
            except Exception as e:
                logging.error('run error {}'.format(e))
                logging.error(traceback.format_exc())
            finally:
                self.close()
                logging.info('close databases ok!')
        return wrapper

decorate=BaseDecorate()