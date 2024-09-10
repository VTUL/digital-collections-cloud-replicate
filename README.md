
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]



  <h3 align="center">Digital Collections Cloud Replicate</h3>
  <p align="center">
    <br />
    <a href="https://github.com/VTUL/digital-collections-cloud-replicate/issues">Report Bug</a> |
    <a href="https://github.com/VTUL/digital-collections-cloud-replicate/issues">Request Feature</a>
  </p>



<!-- TABLE OF CONTENTS -->
<details open="open">
  <summary><h2 style="display: inline-block">Table of Contents</h2></summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgements">Acknowledgements</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

This tool aims to introduce some digital preservation transparency into the process of copying digital collections 
files from local storage to S3.  Amazon's awcli provides high-level tools like
[sync](https://awscli.amazonaws.com/v2/documentation/api/latest/reference/s3/sync.html) and low-level tools like 
[put-object](https://awscli.amazonaws.com/v2/documentation/api/latest/reference/s3api/put-object.html) claim to validate
fixity on uploaded objects behind the scenes, but this isn't transparent.  

In our digital collections processes, we generate fixity using 
[md5deep](http://md5deep.sourceforge.net/start-md5deep.html) as soon after file capture or creation as possible.  We 
use that fixity digest to verify files on each move.  This tool does the following:
<ul>
<li>Verify that all files in the fixity manifest exist in the filesystem</li>
<li>Verify that all files in the filesystem are explicated in the manifest</li>
<li>Ignore some files like Thumbs.db</li>
<li>Verify the MD5 fixity for each file matches the fixity recorded in the manifest</li>
<li>Replicates files from local storage to AWS S3</li>
<li>Request that AWS validates the MD5 to ensure file in S3 is accurate</li>
<li>Configure metadata on the S3 object with the MD5 of the file</li>
<li>Log all of these actions to a log file for review</li>
</ul>



### Built With

* [boto3](https://pypi.org/project/boto3/)
* [botocore](https://pypi.org/project/botocore/)
* [deepdiff](https://pypi.org/project/deepdiff/)
* [jmespath](https://pypi.org/project/jmespath/)

<!-- GETTING STARTED -->
## Getting Started

To get a local copy up and running follow these simple steps.

### Installation

1. Clone the repo
   ```sh
   git clone https://github.com/VTUL/digital-collections-cloud-replicate.git
   ```
2. Install libraries
   ```sh
   pip install boto3 botocore deepdiff jmespath   
   ```


<!-- USAGE EXAMPLES -->
## Usage

See options using -h
```sh
$ ./s3-replicate.py -h
usage: s3-replicate.py [-h] [-c CONFIG] -d DIRECTORY [-f] [-l LOG] [-m MANIFEST] [-p PROFILE] -u URI [-v]

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        path to aws credentials file. E.g., /home/user/.aws/credentials. Default is ~/.aws/credentials
  -d DIRECTORY, --directory DIRECTORY
                        path to digital collections directory. E.g., /some/path
  -f, --fixity          perform fixity validation against manifest
  -l LOG, --log LOG     directory to save logfile. E.g., /some/path. Default is POSIX temp directory
  -m MANIFEST, --manifest MANIFEST
                        name of manifest file if not "checksums-md5.txt"
  -p PROFILE, --profile PROFILE
                        aws profile name. E.g., default. Default is default.
  -u URI, --uri URI     S3 URI. E.g. s3://vt-testbucket/SpecScans/IAWA3/JDW/
  -v, --verbose         print verbose output to console
```
Run with options
```sh 
$ ./s3-replicate.py -u s3://imgagestore/SpecScans/IAWA/JDW/ -d /home/jjt/Downloads/ingest_test/in_jdw/ -m checksums-md5-jdw.txt -f -v
```
Review logfile
```sh 
$ cat /tmp/s3-replicate_in_jdw_JDW_2021-09-20-12-44-04.log
2021-09-20 14:43:43,092 - INFO - Replicating files from /home/jjt/Downloads/ingest_test/in_jdw to s3://imagestore/SpecScans/IAWA/JDW/
2021-09-20 14:43:43,102 - INFO - Found credentials in shared credentials file: ~/.aws/credentials
2021-09-20 14:43:43,380 - INFO - User has write access to S3 bucket
2021-09-20 14:43:43,384 - INFO - Ignoring manifest entry matching ignore list: ./jdwst001001/Thumbs.db
2021-09-20 14:43:43,385 - INFO - Found 5 records in manifest file
2021-09-20 14:43:43,385 - INFO - Using 4 manifest records after matching ignored files
2021-09-20 14:43:43,385 - INFO - Scanning files at /home/jjt/Downloads/ingest_test/in_jdw.  Generating fixity will take time
2021-09-20 14:43:43,386 - INFO - Ignoring file checksums-md5-jdw.txt
2021-09-20 14:43:43,675 - INFO - Found 4 files in /home/jjt/Downloads/ingest_test/in_jdw after ignoring 1 files
2021-09-20 14:43:43,675 - INFO - Filesystem and manifest match.
2021-09-20 14:43:43,675 - INFO - Initiating file replication to s3://imgagestore/SpecScans/IAWA/JDW/
2021-09-20 14:43:46,191 - INFO - {'ResponseMetadata': {'RequestId': '3M752071KR8DS1YW', 'HostId': 'ueyoxW3Wkdff6SJan2S1zv6Mkm1wbMQb/lfy9hq97m4AlGRQFFe4DMDFUuqSdrqR+6dvl03QgNk=', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amz-id-2': 'ueyoxW3Wkdfe6SJan2S1zv6Mkm1wbMQb/lfy9hq97m4AlGRQFFe4DMDFUuqSdjqR+6xvl03QgNk=', 'x-amz-request-id': '3M752971KK8DS1YW', 'date': 'Mon, 20 Sep 2021 18:43:44 GMT', 'etag': '"7034b2e690d2e04bc50a6ce8a8be392e"', 'server': 'AmazonS3', 'content-length': '0'}, 'RetryAttempts': 0}, 'ETag': '"7034b2e690d2e04bc50a6ce8a8be392e"'}
...
```
<!-- ROADMAP -->
## Roadmap

See the [open issues](https://github.com/VTUL/digital-collections-cloud-replicate/issues) for a list of proposed features (and known issues).



<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request



<!-- LICENSE -->
## License

Distributed under the Apache 2.0 License. See `LICENSE` for more information.



<!-- CONTACT -->
## Contact
[summer@braggtown.com](mailto:summer@braggtown.com?subject=[GitHub]%20Sdigital-collections-cloud-replicate)




Project Link: [https://github.com/VTUL/digital-collections-cloud-replicate](https://github.com/VTUL/digital-collections-cloud-replicate)



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/jimtuttle/repo.svg?style=for-the-badge
[contributors-url]: https://github.com/VTUL/digital-collections-cloud-replicate/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/jimtuttle/repo.svg?style=for-the-badge
[forks-url]: https://github.com/VTUL/digital-collections-cloud-replicate/network/members
[stars-shield]: https://img.shields.io/github/stars/jimtuttle/repo.svg?style=for-the-badge
[stars-url]: https://github.com/VTUL/digital-collections-cloud-replicate/stargazers
[issues-shield]: https://img.shields.io/github/issues/jimtuttle/repo.svg?style=for-the-badge
[issues-url]: https://github.com/VTUL/digital-collections-cloud-replicate/issues
[license-shield]: https://img.shields.io/github/license/jimtuttle/repo.svg?style=for-the-badge
[license-url]: https://github.com/VTUL/digital-collections-cloud-replicate/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/jjtuttle
