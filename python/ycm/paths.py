# Copyright (C) 2015-2017 YouCompleteMe contributors.
#
# This file is part of YouCompleteMe.
#
# YouCompleteMe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# YouCompleteMe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

import os
import sys
import vim
import re

from ycm.vimsupport import ReadFile, OnWindows

DIR_OF_CURRENT_SCRIPT = os.path.dirname( os.path.abspath( __file__ ) )
DIR_OF_YCMD = os.path.join( DIR_OF_CURRENT_SCRIPT, '..', '..', 'third_party',
                            'ycmd' )
WIN_PYTHON_PATH = os.path.join( sys.exec_prefix, 'python.exe' )
PYTHON_BINARY_REGEX = re.compile(
  r'python((2(\.[67])?)|(3(\.[3-9])?))?(.exe)?$', re.IGNORECASE )
EXECUTABLE_FILE_MASK = os.F_OK | os.X_OK


def PathToFirstExistingExecutable( executable_name_list ):
  for executable_name in executable_name_list:
    path = FindExecutable( executable_name )
    if path:
      return path
  return None


def _GetWindowsExecutable( filename ):
  def _GetPossibleWindowsExecutable( filename ):
    pathext = [ ext.lower() for ext in
                os.environ.get( 'PATHEXT', '' ).split( os.pathsep ) ]
    base, extension = os.path.splitext( filename )
    if extension.lower() in pathext:
      return [ filename ]
    else:
      return [ base + ext for ext in pathext ]

  for exe in _GetPossibleWindowsExecutable( filename ):
    if os.path.isfile( exe ):
      return exe
  return None


# Check that a given file can be accessed as an executable file, so controlling
# the access mask on Unix and if has a valid extension on Windows. It returns
# the path to the executable or None if no executable was found.
def GetExecutable( filename ):
  if OnWindows():
    return _GetWindowsExecutable( filename )

  if ( os.path.isfile( filename )
       and os.access( filename, EXECUTABLE_FILE_MASK ) ):
    return filename
  return None


# Adapted from https://hg.python.org/cpython/file/3.5/Lib/shutil.py#l1081
# to be backward compatible with Python2 and more consistent to our codebase.
def FindExecutable( executable ):
  # If we're given a path with a directory part, look it up directly rather
  # than referring to PATH directories. This includes checking relative to the
  # current directory, e.g. ./script
  if os.path.dirname( executable ):
    return GetExecutable( executable )

  paths = os.environ[ 'PATH' ].split( os.pathsep )

  if OnWindows():
    # The current directory takes precedence on Windows.
    curdir = os.path.abspath( os.curdir )
    if curdir not in paths:
      paths.insert( 0, curdir )

  for path in paths:
    exe = GetExecutable( os.path.join( path, executable ) )
    if exe:
      return exe
  return None


# Not caching the result of this function; users shouldn't have to restart Vim
# after running the install script or setting the
# `g:ycm_server_python_interpreter` option.
def PathToPythonInterpreter():
  # Not calling the Python interpreter to check its version as it significantly
  # impacts startup time.
  python_interpreter = vim.eval( 'g:ycm_server_python_interpreter' )
  if python_interpreter:
    python_interpreter = FindExecutable( python_interpreter )
    if python_interpreter:
      return python_interpreter

    raise RuntimeError( "Path in 'g:ycm_server_python_interpreter' option "
                        "does not point to a valid Python 2.7 or 3.4+." )

  python_interpreter = _PathToPythonUsedDuringBuild()
  if python_interpreter and GetExecutable( python_interpreter ):
    return python_interpreter

  # On UNIX platforms, we use sys.executable as the Python interpreter path.
  # We cannot use sys.executable on Windows because for unknown reasons, it
  # returns the Vim executable. Instead, we use sys.exec_prefix to deduce the
  # interpreter path.
  python_interpreter = WIN_PYTHON_PATH if OnWindows() else sys.executable
  if _EndsWithPython( python_interpreter ):
    return python_interpreter

  # As a last resort, we search python in the PATH. We prefer Python 2 over 3
  # for the sake of backwards compatibility with ycm_extra_conf.py files out
  # there; few people wrote theirs to work on py3.
  # So we check 'python2' before 'python' because on some distributions (Arch
  # Linux for example), python refers to python3.
  python_interpreter = PathToFirstExistingExecutable( [ 'python2',
                                                        'python',
                                                        'python3' ] )
  if python_interpreter:
    return python_interpreter

  raise RuntimeError( "Cannot find Python 2.7 or 3.4+. "
                      "Set the 'g:ycm_server_python_interpreter' option "
                      "to a Python interpreter path." )


def _PathToPythonUsedDuringBuild():
  try:
    filepath = os.path.join( DIR_OF_YCMD, 'PYTHON_USED_DURING_BUILDING' )
    return ReadFile( filepath ).strip()
  # We need to check for IOError for Python2 and OSError for Python3
  except ( IOError, OSError ):
    return None


def _EndsWithPython( path ):
  """Check if given path ends with a python 2.7 or 3.4+ name."""
  return path and PYTHON_BINARY_REGEX.search( path ) is not None


def PathToServerScript():
  return os.path.join( DIR_OF_YCMD, 'ycmd' )
