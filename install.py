#!/usr/bin/env python

from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
from __future__ import absolute_import

import argparse
import glob
import os
import os.path as p
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

DIR_OF_THIS_SCRIPT = p.dirname( p.abspath( __file__ ) )
DIR_OF_THIRD_PARTY = p.join( DIR_OF_THIS_SCRIPT, 'third_party' )
YCMD_DIR = p.join( DIR_OF_THIRD_PARTY, 'ycmd' )

sys.path.insert( 0, p.join( DIR_OF_THIRD_PARTY, 'requests' ) )

import requests

DIR_OF_OLD_LIBS = p.join( DIR_OF_THIS_SCRIPT, 'python' )

PY_MAJOR, PY_MINOR, PY_PATCH = sys.version_info[ 0 : 3 ]
if not ( ( PY_MAJOR == 2 and PY_MINOR == 7 and PY_PATCH >= 1 ) or
         ( PY_MAJOR == 3 and PY_MINOR >= 4 ) or
         PY_MAJOR > 3 ):
  sys.exit( 'YouCompleteMe requires Python >= 2.7.1 or >= 3.4; '
            'your version of Python is ' + sys.version )


def CheckCall( args, **kwargs ):
  try:
    subprocess.check_call( args, **kwargs )
  except subprocess.CalledProcessError as error:
    sys.exit( error.returncode )


YCMD_DOWNLOAD_URL = ( 'https://github.com/micbou/ycmd/releases/download/'
                      '{version}/{package}' )


def OnLinux():
  return platform.system() == 'Linux'


def OnWindows():
  return platform.system() == 'Windows'


def Is64Bit():
  return platform.architecture()[ 0 ] == '64bit'


def ParseArguments():
  parser = argparse.ArgumentParser(
    description = 'Download and extract ycmd into the third-party folder' )
  parser.add_argument( '--dev',
                       action = 'store_true',
                       help   = 'Download the development version of ycmd' )
  return parser.parse_args()


def ExtractZip( archive, destination ):
  with zipfile.ZipFile( archive ) as archive_zip:
    archive_zip.extractall( destination )


def ExtractGzip( archive, destination ):
  with tarfile.TarFile( archive ) as archive_gzip:
    archive_gzip.extractall( destination )


def DownloadYcmd( package, version, destination ):
  url = YCMD_DOWNLOAD_URL.format( version = version, package = package )
  print( 'Downloading ycmd from {}...'.format( url ) )
  request = requests.get( url, stream = True )
  with open( destination, 'wb' ) as package_file:
    package_file.write( request.content )
  request.close()


def ExtractYcmd( source, destination ):
  print( 'Extracting ycmd to {}...'.format( destination ) )
  if os.path.splitext( source )[ 1 ] == '.zip':
    ExtractZip( source, destination )
  else:
    ExtractGzip( source, destination )


def Main():
  args = ParseArguments()
  if args.dev:
    ycmd_version = 'dev'
  else:
    raise NotImplementedError()

  print( 'Removing previous ycmd installation...' )
  if os.path.exists( os.path.join( YCMD_DIR, '.git' ) ):
    answer = input( "WARNING: {} is a Git repository and won't be removed "
                    "without your consent. Type 'yes' if you are sure you want "
                    "the script to remove it and proceed with the "
                    "installation: " )
    if answer != 'yes':
      sys.exit( 'ycmd has not been installed.' )
  try:
    shutil.rmtree( YCMD_DIR )
  except FileNotFoundError:
    pass

  if OnWindows():
    ycmd_package = 'ycmd-windows-64.zip' if Is64Bit() else 'ycmd-windows-32.zip'
  elif OnLinux():
    ycmd_package = 'ycmd-linux-64.tar.gz'

  temp_dir = tempfile.mkdtemp()
  try:
    ycmd_path = os.path.join( temp_dir, ycmd_package )
    DownloadYcmd( ycmd_package, ycmd_version, ycmd_path )
    ExtractYcmd( ycmd_path, DIR_OF_THIRD_PARTY )
    print( 'ycmd has been installed successfully.' )
  finally:
    shutil.rmtree( temp_dir )

  # build_file = p.join( DIR_OF_THIS_SCRIPT, 'third_party', 'ycmd', 'build.py' )

  # if not p.isfile( build_file ):
  #   sys.exit(
  #     'File {0} does not exist; you probably forgot to run:\n'
  #     '\tgit submodule update --init --recursive\n'.format( build_file ) )

  # CheckCall( [ sys.executable, build_file ] + sys.argv[ 1: ] )

  # Remove old YCM libs if present so that YCM can start.
  old_libs = (
    glob.glob( p.join( DIR_OF_OLD_LIBS, '*ycm_core.*' ) ) +
    glob.glob( p.join( DIR_OF_OLD_LIBS, '*ycm_client_support.*' ) ) +
    glob.glob( p.join( DIR_OF_OLD_LIBS, '*clang*.*' ) ) )
  for lib in old_libs:
    os.remove( lib )


if __name__ == "__main__":
  Main()
