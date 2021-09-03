#!/usr/bin/env python3

import argparse
import pathlib
import logging
from os.path import basename, normpath, join
from datetime import datetime
from os import access, W_OK, R_OK, walk
from sys import exit
from hashlib import md5
from deepdiff import DeepDiff as diff
import boto3
from botocore.exceptions import ClientError
from pathlib import Path

def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--bucket', dest='bucket', help='AWS bucket or folder', required=True )
    parser.add_argument('-c', '--config', dest='config', default='/tmp',
                        help='path to aws credentials file.  E.g., /home/user/.aws/credentials.  '
                             'Default is ~/.aws/credentials')
    parser.add_argument('-d', '--directory', dest='directory', type=pathlib.Path,
                        help='path to digital collections directory.  E.g., /some/path', required=True)
    parser.add_argument('-f', '--fixity', dest='fixity', default=False, action='store_true',
                        help='perform fixity validation against manifest')
    parser.add_argument('-i', '--id', dest='id', help='AWS access key id', required=True)
    parser.add_argument('-k', '--key', dest='key', help='AWS secret access key', required=True)
    parser.add_argument('-l', '--log', dest='log', default='/tmp',
                        help='directory to save logfile.  E.g., /some/path.  Default is /tmp')
    parser.add_argument('-m', '--manifest', dest='manifest', default='checksums-md5.txt',
                        help='name of manifest file if not "checksums-md5.txt"')
    parser.add_argument('-p', '--profile', dest='profile', default='profile',
                        help='aws profile name.  E.g., default.  Default is default.')
    parser.add_argument('-v', '--verbose', dest='verbose', default=False, action='store_true',
                        help='print verbose output to console')
    arguments = parser.parse_args()
    return arguments


def instantiate_logger(logpath, directory, bucket, verbosity):
    timestamp = '{:%Y-%m-%d-%H-%M-%S}'.format(datetime.now())
    dirname = basename(normpath(directory))
    bucketname= basename(normpath(bucket))
    logname = 's3-replicate_{}_{}_{}.log'.format(dirname, bucketname, timestamp)
    logging.basicConfig(filename=join(logpath, logname), encoding='utf-8', level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    print('Logging output to {}'.format(join(logpath, logname)))
    message = 'Replicating files from {} to {}'.format(directory, bucket)
    logging.info(message)
    if verbosity:
        print(message)


def test_arguments(arguments):
    # test collections directory, test bucket, test manifest if passed
    error = False
    if not access(arguments.log, W_OK):
        message = 'Log file location: {} not writeable.'.format(arguments.log)
        logging.error(message)
        print(message)
        error = True
    if arguments.fixity:
        manifest = join(arguments.directory, arguments.manifest)
        if not access(manifest, R_OK):
            message = 'Manifest file: {} is not readable.'.format(arguments.manifest)
            logging.error(message)
            print(message)
            error = True
    if not access(arguments.config, R_OK):
        message = 'AWS configuration file {} not found or not readable.'
        logging.error(message)
        print(message)
    # todo test AWS config file, aws bucket access
    if error:
        message = 'Exiting due to error condition in passed arguments.'
        logging.error(message)
        print(message)
        exit()


def ignore_file(path, ignored):
    ignore = False
    for ignorename in ignored:
        if ignorename in path:
            ignore = True
    if ignore:
        logging.info('Ignoring manifest entry matching ignore list: %s', path.strip())
        return True
    else:
        return False


def get_manifest(manifestfile, workdir, ignored):
    manifestentries = {}
    manifestreader = open(join(workdir, manifestfile))
    linecount = 0
    for line in manifestreader:
        linecount += 1
        checksum, filepath = line.split(',')
        if not ignore_file(filepath, ignored):
            manifestentries[filepath.strip()] = checksum.strip()
    logging.info('Found %s records in manifest file', str(linecount))
    logging.info('Using %s manifest records after matching ignored files', len(manifestentries))
    return manifestentries


def calculate_hash(p):
    md5hash = md5()
    with open(p, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            md5hash .update(byte_block)
    return md5hash.hexdigest()


def get_filesystem(workdir, verbosity, ignored):
    message = 'Scanning files at {}'.format(workdir)
    fsrecords = {}
    logging.info(message)
    if verbosity:
        print(message)
    ignoredfiles = 0
    for root, dirs, files in walk(workdir):
        for f in files:
            relativepath = str(join(root, f)).split(str(workdir))[1][1:]
            if f not in ignored:
                digest = calculate_hash(join(root, f))
                fsrecords[relativepath] = digest
            else:
                ignoredfiles += 1
                message = 'Ignoring file {}'.format(relativepath)
                logging.info(message)
                if verbosity:
                    print(message)
    message = 'Found {} files in {} after ignoring {} files'.format(len(fsrecords.keys()), workdir, str(ignoredfiles))
    logging.info(message)
    if verbosity:
        print(message)
    return fsrecords


def validate_fixity(manifest, directory, verbosity, ignored):
    manifestrecords = get_manifest(manifest, directory, ignored)
    fsrecords = get_filesystem(directory, verbosity, ignored)
    if manifestrecords == fsrecords:
        message = 'Filesystem and manifest match.'
        logging.info(message)
        if verbosity:
            print(message)
        return
    else:
        diffs = diff(manifestrecords, fsrecords, ignore_order=True)
        message = 'Exiting due to mismatch.  The following differences exist between manifest' \
                  ' and filesystem: {}'.format(diffs)
        logging.error(message)
        print(message)
        exit()


def put_files(awsid, awskey, workdir, verbosity, bucket):
    message = 'Initiating file replication to {} as user {}'.format(awsid, bucket)
    logging.info(message)
    if verbosity:
        print(message)
    set_aws_config(awsid, awskey)


def set_aws_config(awsid, awskey):
    # Documentation on creating credentials: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html
    home = str(Path.home())
    client = boto3.client('s3', aws_access_key_id=awsid, aws_secret_access_key=awskey)



if __name__ == "__main__":
    args = get_arguments()
    ignorelist = ('Thumbs.db', '.DS_Store', args.manifest)
    instantiate_logger(args.log, args.directory, args.bucket, args.verbose)
    test_arguments(args)
    if args.fixity:
        validate_fixity(args.manifest, args.directory, args.verbose, ignorelist)
    put_files(args.id, args.key, args.directory, args.verbose, args.bucket)

