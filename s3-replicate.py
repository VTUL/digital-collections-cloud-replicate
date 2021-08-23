#!/usr/bin/env python3

import argparse
import pathlib
import logging
from os.path import basename, normpath, exists, join
from datetime import datetime
from os import access, W_OK, R_OK
from sys import exit


def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--directory', dest='directory', type=pathlib.Path,
                        help='path to digital collections directory.  E.g., /some/path', required=True)
    parser.add_argument('-f', '--fixity', dest='fixity', default=False, action='store_true',
                        help='perform fixity validation against manifest')
    parser.add_argument('-m', '--manifest', dest='manifest', default='checksums-md5.txt',
                        help='name of manifest file if not "checksums-md5.txt"')
    parser.add_argument('-l', '--log', dest='log', default='/tmp',
                        help='directory to save logfile.  E.g., /some/path.  Default is /tmp')
    parser.add_argument('-c', '--config', dest='config', default='/tmp',
                        help='path to aws config file.  E.g., ~/.aws/config.  Default is ~/.aws/config')
    parser.add_argument('-p', '--profile', dest='profile', default='profile',
                        help='aws profile name.  E.g., default.  Default is default.')
    # parser.add_argument('-a', '--id', dest='id', help='AWS access key id', required=True)
    # parser.add_argument('-k', '--key', dest='key', help='AWS secret access key', required=True)
    parser.add_argument('-b', '--bucket', dest='bucket', help='AWS bucket or folder', required=True )
    arguments = parser.parse_args()
    return arguments


def instantiate_logger(logpath, directory, bucket):
    timestamp = '{:%Y-%m-%d-%H-%M-%S}'.format(datetime.now())
    dirname = basename(normpath(directory))
    bucketname= basename(normpath(bucket))
    logname = 's3-replicate_{}_{}_{}.log'.format(dirname, bucketname, timestamp)
    logging.basicConfig(filename=join(logpath, logname), encoding='utf-8', level=logging.INFO,
                        format='%(asctime)s - %(message)s')
    logging.info('s3-replicate %s to %s', directory, bucket)


def test_arguments(arguments):
    # test collections directory, test bucket, test manifest if passed
    error = False
    print(arguments)
    if not access(arguments.log, W_OK):
        print('Log file location: {} not writeable.'.format(arguments.log))
        error = True
    if arguments.fixity:
        manifest = join(arguments.directory, arguments.manifest)
        if not access(manifest, R_OK):
            print('Manifest file: {} is not readable.'.format(arguments.manifest))
            error = True
    if not access(arguments.config, R_OK):
        print('AWS configuration file {} not found or not readable.')
    # todo test AWS config file, aws bucket access
    if error:
        print('Exiting.')
        exit()


def ignore_file(path):
    ignorelist = ('Thumbs.db', '.DS_Store')
    ignore = False
    for ignorename in ignorelist:
        if ignorename in path:
            ignore = True
    if ignore:
        logging.info('Ignoring manifest entry matching ignore list: %s', path.strip())
        return True
    else:
        return False


def validate_fixity(manifest, directory):
    logging.info('Validating fixity using manifest file: %s', join(directory, manifest))
    manifestentries = {}
    files = {}
    manifestfile = open(join(directory, manifest))
    linecount = 0
    for line in manifestfile:
        linecount += 1
        checksum, filepath = line.split(',')
        if not ignore_file(filepath):
            manifestentries[filepath.strip()] = checksum.strip()
    logging.info('Found %s records in manifest file', str(linecount))
    logging.info('Using %s records from manifest file after matching ignored files', len(manifestentries))
    print(manifestentries)


if __name__ == "__main__":
    args = get_arguments()
    test_arguments(args)
    instantiate_logger(args.log, args.directory, args.bucket)
    if args.fixity:
        validate_fixity(args.manifest, args.directory)

