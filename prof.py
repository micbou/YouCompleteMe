#!/usr/bin/env python

import argparse
import pstats
import os
import subprocess
import sys
import tempfile
from distutils.spawn import find_executable


DIR_OF_THIS_SCRIPT = os.path.dirname( os.path.abspath( __file__ ) )


def PathToFirstExistingExecutable( executable_name_list ):
  for executable_name in executable_name_list:
    path = find_executable( executable_name )
    if path:
      return path
  return None


def CreateStatsFile():
  with tempfile.NamedTemporaryFile( prefix = 'ycm_stats_',
                                    suffix = '.pyc',
                                    delete = False ) as stats_file:
    return stats_file.name


def FormatOption( name, value ):
  value = value.replace( '\\', '\\\\' )
  return [ '-c', 'let g:{0} = "{1}"'.format( name, value ) ]


def Run():
  stats_file = CreateStatsFile()
  vim_executable = PathToFirstExistingExecutable( [ 'gvim', 'vim', 'mvim' ] )
  vim_command = [ vim_executable,
                  '-u', 'NONE' ]
  vim_command.extend( FormatOption( 'ycm_profile_stats_file', stats_file ) )
  vim_command.extend( FormatOption(
    'ycm_profile_python_interpreter',
    'python{0}'.format( '3' if sys.version_info[ 0 ] == 3 else '' ) ) )
  vim_command.extend( [ '-c', 'source prof/diagnostics.vim' ] )
  subprocess.call( vim_command )
  return stats_file


def RemoveBytecode():
  for root, dirs, files in os.walk( DIR_OF_THIS_SCRIPT ):
    for name in files:
      _, extension = os.path.splitext( name )
      if extension == '.pyc':
        os.remove( os.path.join( root, name ) )


def ParseArguments():
  parser = argparse.ArgumentParser()
  parser.add_argument( '--runs', type = int, default = 10,
                       help = 'Number of runs.' )
  parser.add_argument( '--visualize', action = 'store_true',
                       help = 'Visualize profiling data.' )
  return parser.parse_args()


def Main():
  args = ParseArguments()

  # Warmup
  Run()

  # Without bytecode
  stats_files = []
  for _ in range( args.runs ):
    RemoveBytecode()
    stats_files.append( Run() )
  stats = pstats.Stats( *stats_files )
  stats.sort_stats( 'cumulative' )
  average_startup_time_without_bytecode = int(
      stats.total_tt * 1000 / args.runs )

  for stats_file in stats_files:
    os.remove( stats_file )

  # With bytecode
  stats_files = []
  for _ in range( args.runs ):
    stats_files.append( Run() )
  stats = pstats.Stats( *stats_files )
  stats.sort_stats( 'cumulative' )
  average_startup_time_with_bytecode = int(
      stats.total_tt * 1000 / args.runs )

  for stats_file in stats_files:
    os.remove( stats_file )

  print( 'Average startup time on {0} runs:\n'
         '  without bytecode: {1}ms\n'
         '  with bytecode:    {2}ms'.format(
             args.runs,
             average_startup_time_without_bytecode,
             average_startup_time_with_bytecode ) )

  if args.visualize:
    from pyprof2calltree import visualize
    visualize( stats )


if __name__ == "__main__":
  Main()
