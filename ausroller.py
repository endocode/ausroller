#!/usr/bin/env python2
# encoding: utf-8

from ausroller import Configuration
from ausroller import Ausroller
import logging


def main():
    # parse arguments from command line and
    # read configuration file

    c = Configuration()
    c.parse_args()
    logging.basicConfig(format='%(levelname)s:\t%(message)s',
                        level=c.log_level)
    c.read_config()

    a = Ausroller(c)
    resources = a.prepare_rollout()
    a.rollout(resources)

if __name__ == '__main__':
    main()
