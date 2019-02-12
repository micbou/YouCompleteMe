# Copyright (C) 2013  Google Inc.
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
from functools import partial

from ycm.client.base_request import BaseRequest, BuildRequestData
from ycm.completion_window import CompletionWindow
from ycm import vimsupport
from ycmd.utils import OnWindows, ToUnicode


def _EnsureBackwardsCompatibility( arguments ):
  if arguments and arguments[ 0 ] == 'GoToDefinitionElseDeclaration':
    arguments[ 0 ] = 'GoTo'
  return arguments


class CommandRequest( BaseRequest ):
  def __init__( self,
                arguments,
                buffer_command = 'same-buffer',
                extra_data = None ):
    super( CommandRequest, self ).__init__()
    self._arguments = _EnsureBackwardsCompatibility( arguments )
    self._command = arguments and arguments[ 0 ]
    self._buffer_command = buffer_command
    self._extra_data = extra_data
    self._response = None


  def Start( self ):
    request_data = BuildRequestData()
    if self._extra_data:
      request_data.update( self._extra_data )
    request_data.update( {
      'command_arguments': self._arguments
    } )
    self._response = self.PostDataToHandler( request_data,
                                             'run_completer_command' )


  def Response( self ):
    return self._response


  def RunPostCommandActionsIfNeeded( self, completion_window, modifiers ):
    if not self.Done() or self._response is None:
      return

    # If not a dictionary or a list, the response is necessarily a
    # scalar: boolean, number, string, etc. In this case, we print
    # it to the user.
    if not isinstance( self._response, ( dict, list ) ):
      return self._HandleBasicResponse()

    if 'fixits' in self._response:
      return self._HandleFixitResponse()

    if 'symbols' in self._response:
      return self._HandleSymbolResponse( completion_window, modifiers )

    if 'message' in self._response:
      return self._HandleMessageResponse()

    if 'detailed_info' in self._response:
      return self._HandleDetailedInfoResponse()

    # The only other type of response we understand is GoTo, and that is the
    # only one that we can't detect just by inspecting the response (it should
    # either be a single location or a list)
    return self._HandleGotoResponse( modifiers )


  def _HandleGotoResponse( self, modifiers ):
    if isinstance( self._response, list ):
      vimsupport.SetQuickFixList(
        [ _BuildQfListItem( x ) for x in self._response ] )
      vimsupport.OpenQuickFixList( focus = True, autoclose = True )
    else:
      vimsupport.JumpToLocation( self._response[ 'filepath' ],
                                 self._response[ 'line_num' ],
                                 self._response[ 'column_num' ],
                                 modifiers,
                                 self._buffer_command )


  def _HandleFixitResponse( self ):
    if not len( self._response[ 'fixits' ] ):
      vimsupport.PostVimMessage( 'No fixits found for current line',
                                 warning = False )
    else:
      try:
        fixit_index = 0

        # When there are multiple fixit suggestions, present them as a list to
        # the user hand have her choose which one to apply.
        if len( self._response[ 'fixits' ] ) > 1:
          fixit_index = vimsupport.SelectFromList(
            "Multiple FixIt suggestions are available at this location. "
            "Which one would you like to apply?",
            [ fixit[ 'text' ] for fixit in self._response[ 'fixits' ] ] )

        vimsupport.ReplaceChunks(
          self._response[ 'fixits' ][ fixit_index ][ 'chunks' ],
          silent = self._command == 'Format' )
      except RuntimeError as e:
        vimsupport.PostVimMessage( str( e ) )


  def _HandleSymbolResponse( self, completion_window, modifiers ):
    completion_window.Open()
    confirm_callback = partial( _OnConfirmSymbol,
                                modifiers = modifiers,
                                buffer_command = self._buffer_command )
    completion_window.Populate( self._response[ 'symbols' ],
                                'name',
                                confirm_callback,
                                _FormatSymbols )


  def _HandleBasicResponse( self ):
    vimsupport.PostVimMessage( self._response, warning = False )


  def _HandleMessageResponse( self ):
    vimsupport.PostVimMessage( self._response[ 'message' ], warning = False )


  def _HandleDetailedInfoResponse( self ):
    vimsupport.WriteToPreviewWindow( self._response[ 'detailed_info' ] )


class CommandRequestSender( object ):
  def __init__( self, completion_window ):
    self._completion_window = completion_window


  def Send( self, arguments, modifiers, buffer_command, extra_data = None ):
    request = CommandRequest( arguments, buffer_command, extra_data )
    # This is a blocking call.
    request.Start()
    request.RunPostCommandActionsIfNeeded( self._completion_window, modifiers )
    return request.Response()


def _BuildQfListItem( goto_data_item ):
  qf_item = {}
  if 'filepath' in goto_data_item:
    qf_item[ 'filename' ] = ToUnicode( goto_data_item[ 'filepath' ] )
  if 'description' in goto_data_item:
    qf_item[ 'text' ] = ToUnicode( goto_data_item[ 'description' ] )
  if 'line_num' in goto_data_item:
    qf_item[ 'lnum' ] = goto_data_item[ 'line_num' ]
  if 'column_num' in goto_data_item:
    # ycmd returns columns 1-based, and QuickFix lists require "byte offsets".
    # See :help getqflist and equivalent comment in
    # vimsupport.ConvertDiagnosticsToQfList.
    #
    # When the Vim help says "byte index", it really means "1-based column
    # number" (which is somewhat confusing). :help getqflist states "first
    # column is 1".
    qf_item[ 'col' ] = goto_data_item[ 'column_num' ]

  return qf_item


def _OnConfirmSymbol( symbol, modifiers, buffer_command ):
  start = symbol[ 'range' ][ 'start' ]
  vimsupport.JumpToLocation( start[ 'filepath' ],
                             start[ 'line_num' ],
                             start[ 'column_num' ],
                             modifiers,
                             buffer_command )
  # Leave insert mode with the cursor on the current character.
  vimsupport.SendKeys( "\<ESC>" )
  column = vimsupport.CurrentColumn()
  if column != 0:
    vimsupport.SendKeys( "l" )


# Based on the implementation of os.path.expanduser.
def _GetHomeDirectory():
  if 'HOME' in os.environ:
    return os.environ[ 'HOME' ]

  if OnWindows():
    if 'USERPROFILE' in os.environ:
      return os.environ[ 'USERPROFILE' ]
    if 'HOMEPATH' in os.environ:
      try:
        drive = os.environ[ 'HOMEDRIVE' ]
      except KeyError:
        drive = ''
      return os.path.join( drive, os.environ[ 'HOMEPATH' ] )
    return None

  import pwd
  try:
    return pwd.getpwuid( os.getuid() ).pw_dir
  except KeyError:
    return None


def _GetShortestPath( filepath, current_dir, home_dir ):
  path_relative_to_current_dir = os.path.relpath( filepath, current_dir )
  if filepath.startswith( home_dir ):
    filepath = '~' + filepath[ len( home_dir ) : ]
  if len( filepath ) < len( path_relative_to_current_dir ):
    return filepath
  return path_relative_to_current_dir


def _ShortenString( string, max_length ):
  return (
    string[ : max_length - 1 ] + '…' if len( string ) > max_length else string )


def _FormatSymbols( symbols, window_width ):
  name_length = round( window_width * 0.4 )
  location_length = round( window_width * 0.2 )
  description_length = window_width - ( name_length + location_length + 4 )

  current_dir = vimsupport.GetCurrentDirectory()
  home_dir = _GetHomeDirectory()

  line_format = (
    '{name:<' + str( name_length ) + '} ' +
    '{location:<' + str( location_length ) + '} ' +
    '{kind} ' +
    '{description:<' + str( description_length ) + '}' )
  symbols_format = []
  for symbol in symbols:
    name = _ShortenString( symbol[ 'name' ], name_length )
    kind = symbol[ 'kind' ][ 0 ].lower()
    start = symbol[ 'range' ][ 'start' ]
    filepath = _GetShortestPath( start[ 'filepath' ], current_dir, home_dir )
    location = (
      ':' + str( start[ 'line_num' ] ) + ':' + str( start[ 'column_num' ] ) )
    filepath = _ShortenString( filepath, location_length - len( location ) )
    location = filepath + location
    description = _ShortenString( symbol[ 'description' ], description_length )
    symbols_format.append( line_format.format( name = name,
                                               location = location,
                                               kind = kind,
                                               description = description ) )
  return symbols_format
