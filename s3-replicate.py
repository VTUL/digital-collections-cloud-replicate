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
from base64 import b64encode
from tempfile import gettempdir
from urllib.parse import urlparse


def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', dest='config', default='/tmp',
                        help='path to aws credentials file.  E.g., /home/user/.aws/credentials.  '
                             'Default is ~/.aws/credentials')
    parser.add_argument('-d', '--directory', dest='directory', type=pathlib.Path,
                        help='path to digital collections directory.  E.g., /some/path', required=True)
    parser.add_argument('-f', '--fixity', dest='fixity', default=False, action='store_true',
                        help='perform fixity validation against manifest')
    parser.add_argument('-l', '--log', dest='log', default=gettempdir(),
                       help='directory to save logfile.  E.g., /some/path.  Default is POSIX temp directory')
    parser.add_argument('-m', '--manifest', dest='manifest', default='checksums-md5.txt',
                        help='name of manifest file if not "checksums-md5.txt"')
    parser.add_argument('-p', '--profile', dest='profile', default='profile',
                        help='aws profile name.  E.g., default.  Default is default.')

    parser.add_argument('-s', '--separator', dest='separator', nargs='?', const=',',
                        help='delimiter in manifest file.  Default is ",".')

    parser.add_argument('-u', '--uri', dest='uri', required=True,
                        help='S3 URI.  E.g. s3://vt-testbucket/SpecScans/IAWA3/JDW/')
    parser.add_argument('-v', '--verbose', dest='verbose', default=False, action='store_true',
                        help='print verbose output to console')
    arguments = parser.parse_args()
    return arguments


def instantiate_logger(logpath, directory, bucket, verbosity):
    timestamp = '{:%Y-%m-%d-%H-%M-%S}'.format(datetime.now())
    dirname = basename(normpath(directory))
    bucketname= basename(normpath(bucket))
    logname = 's3-replicate_{}_{}_{}.log'.format(dirname, bucketname, timestamp)
    logging.basicConfig(filename=join(logpath, logname), encoding='utf-8', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    print('Logging output to {}'.format(join(logpath, logname)))
    message = 'Replicating files from {} to {}'.format(directory, bucket)
    logging.info(message)
    if verbosity:
        print(message)


def test_arguments(arguments):
    error = False
    # Test log location is writeable
    if not access(arguments.log, W_OK):
        message = 'Log file location: {} not writeable.'.format(arguments.log)
        logging.error(message)
        print(message)
        error = True
    # Test manifest can be read
    if arguments.fixity:
        manifest = join(arguments.directory, arguments.manifest)
        if not access(manifest, R_OK):
            message = 'Manifest file: {} is not readable.'.format(arguments.manifest)
            logging.error(message)
            print(message)
            error = True
    # Test specified profile found in AWS credentials file
    if not access(arguments.config, R_OK):
        message = 'AWS configuration file {} not found or not readable.'
        logging.error(message)
        print(message)
    # test write access to bucket
    bucket, awspath = parse_uri(args.uri)
    s3 = boto3.client('s3')
    response = s3.get_bucket_acl(Bucket=bucket)
    if (response['Grants'][0]['Permission'] == 'WRITE') or (response['Grants'][0]['Permission'] == 'FULL_CONTROL'):
        message = 'User has write access to S3 bucket'
        logging.info(message)
        if arguments.verbose:
            print(message)
    else:
        message = 'User does not have write access to bucket'
        logging.error(message)
        print(message)
        error = True
    if error:
        message = 'Exiting due to error condition in passed arguments.'
        logging.error(message)
        print(message)
        exit()


def parse_uri(uri):
    bucket, awspath = uri.split('//')[1].split('/', 1)
    return bucket, awspath


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
    try:
        for line in manifestreader:
            linecount += 1
            checksum, filepath = line.split(args.separator)
            if not ignore_file(filepath, ignored):
                if filepath.startswith('./'):
                    manifestentries[filepath[2:].strip()] = checksum.strip()
                else:
                    manifestentries[filepath.strip()] = checksum.strip()
    except UnicodeDecodeError:
        message = 'The manifest file is not ASCII and must be converted to be used.'
        print(message)
        logging.error(message)
        exit()
    logging.info('Found %s records in manifest file', str(linecount))
    logging.info('Using %s manifest records after matching ignored files', len(manifestentries))
    return manifestentries


def calculate_hash(p):
    md5hash = md5()
    with open(p, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            md5hash.update(byte_block)
    return md5hash


def get_filesystem(workdir, verbosity, ignored):
    message = 'Scanning files at {}.'.format(workdir)
    fsrecordshex = {}
    fsrecords  = {}
    logging.info(message)
    if verbosity:
        print(message)
    ignoredfiles = 0
    for root, dirs, files in walk(workdir):
        for f in files:
            relativepath = str(join(root, f)).split(str(workdir))[1][1:]
            if f not in ignored:
                digest = calculate_hash(join(root, f))
                fsrecordshex[relativepath] = digest.hexdigest()
                fsrecords[relativepath] = digest.digest()
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
    return fsrecords, fsrecordshex


def validate_fixity(manifest, directory, verbosity, ignored):
    print("Checking fixity")
    manifestrecords = get_manifest(manifest, directory, ignored)
    fsrecords, fsrecordshex= get_filesystem(directory, verbosity, ignored)
    if manifestrecords == fsrecordshex:
        message = 'Filesystem and manifest match.'
        logging.info(message)
        if verbosity:
            print(message)
        return fsrecords, fsrecordshex
    else:
        diffs = diff(manifestrecords, fsrecordshex, ignore_order=True)
        message = 'Exiting due to mismatch.  The following differences exist between manifest' \
                  ' and filesystem: {}'.format(diffs)
        logging.error(message)
        print(message)
        exit()


def put_files(workdir, verbosity, uri, hashes, hexhashes, ignore):
    message = 'Initiating file replication to {}'.format(uri)
    logging.info(message)
    if verbosity:
        print(message)
    u = urlparse(uri)
    bucket = u.netloc
    keypath = u.path[1:]
    s3 = boto3.client('s3')
    for file, digest in hashes.items():
        if file not in ignore:
            key = join(keypath, file)
            hash64 = b64encode(digest).decode('ascii')
            response = s3.put_object(Body=open(join(workdir, file), 'rb'),
                                     Bucket=bucket,
                                     Key=key,
                                     ContentMD5=hash64,
                                     Metadata={'fixity-md5': hexhashes[file],
                                               'fixity-md5b64': hash64,
                                               },
                                     )
            logging.info(response)
            if verbosity:
                print(response)


if __name__ == "__main__":
    args = get_arguments()
    ignorelist = ('Thumbs.db', '.DS_Store', args.manifest)
    instantiate_logger(args.log, args.directory, args.uri, args.verbose)
    test_arguments(args)
    if args.fixity:
        filehashes, filehasheshex = validate_fixity(args.manifest, args.directory, args.verbose, ignorelist)
    else:
        filehashes, filehasheshex = get_filesystem(args.directory, args.verbose, ignorelist)
    put_files(args.directory, args.verbose, args.uri, filehashes, filehasheshex, ignorelist)

