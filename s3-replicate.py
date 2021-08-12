#!/usr/bin/env python3

import argparse
import pathlib
import logging


def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--directory', dest='directory', type=pathlib.Path,
                        help='path to digital collections directory', required=True)
    parser.add_argument('-m', '--manifest', dest='manifest', default='checksum-md5.txt',
                        help='name of manifest file if not "checksum-md5.txt"')
    parser.add_argument('-l', '--logfile', dest='logfile', default='/tmp',
                        help='location to save logfile')
    args = parser.parse_args()
    # add arguments for AWS credentials, AWS location

    return args


def instantiate_logger():
    pass


def test_arguments():
    # test collections directory, test bucket, test manifest if passed
    pass


if __name__ == "__main__":
    args = get_arguments()
    print(args)