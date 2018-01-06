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


def Run( args ):
  stats_file = CreateStatsFile()
  vim_executable = PathToFirstExistingExecutable( [ 'gvim', 'vim', 'mvim' ] )
  vim_command = [ vim_executable,
                  '-u', 'NONE' ]
  vim_command.extend( FormatOption( 'ycm_profile_stats_file', stats_file ) )
  vim_command.extend( FormatOption(
    'ycm_profile_python_interpreter',
    'python{0}'.format( '3' if sys.version_info[ 0 ] == 3 else '' ) ) )
  vim_command.extend( FormatOption( 'ycm_nb_buffers', str( args.nb_buffers ) ) )
  vim_command.extend( [ '-c', 'source prof/request.vim' ] )
  subprocess.call( vim_command )
  return stats_file


def ParseArguments():
  parser = argparse.ArgumentParser()
  parser.add_argument( '--runs', type = int, default = 10,
                       help = 'Number of runs.' )
  parser.add_argument( '--visualize', action = 'store_true',
                       help = 'Visualize profiling data.' )
  parser.add_argument( 'nb_buffers', type = int,
                       help = 'Number of buffers already open.' )
  return parser.parse_args()


def Main():
  args = ParseArguments()

  # Warmup
  Run( args )

  # With bytecode
  stats_files = []
  for _ in range( args.runs ):
    stats_files.append( Run( args ) )
  stats = pstats.Stats( *stats_files )
  stats.sort_stats( 'cumulative' )
  average_time_with_bytecode = round( stats.total_tt * 1000 / args.runs, 1 )

  for stats_file in stats_files:
    os.remove( stats_file )

  print( 'Average time to edit a new empty buffer on {0} runs: '
         '{1}ms\n'.format( args.runs, average_time_with_bytecode ) )

  if args.visualize:
    from pyprof2calltree import visualize
    visualize( stats )


if __name__ == "__main__":
  Main()
