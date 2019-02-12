# Copyright (C) 2019 YouCompleteMe contributors
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

import vim

from ycm import vimsupport
from ycm.vimsupport import GetVariableValue
from ycm.client.base_request import BaseRequest


class CompletionWindow( object ):

  def __init__( self, user_options ):
    self._completions = []
    self._sort_property = None
    self._confirm_callback = None
    self._filtered_completions = []
    self._first_index = 0
    self._last_index = 0
    self._selected_index = None
    self._buffer_number = None
    self._current_query = None


  def GetFirstWindow( self ):
    if not self._buffer_number:
      return None
    for window in vimsupport.GetWindowsForBufferNumber( self._buffer_number ):
      return window
    return None


  def Open( self ):
    first_window = self.GetFirstWindow()
    if first_window:
      vim.current.window = first_window
    else:
      window_height = 10
      vim.command( '{}new'.format( window_height ) )
      vim.current.buffer.options[ 'filetype' ] = 'ycm'
      vim.command( 'doautocmd User YcmCompletionWindowOpened' )
      vim.current.buffer.options[ 'buftype' ]  = 'nofile'
      vim.current.buffer.options[ 'swapfile' ] = False
      vim.current.window.options[ 'signcolumn' ] = 'no'
      self._buffer_number = vimsupport.GetCurrentBufferNumber()
    vim.command( 'startinsert' )
    vim.current.buffer[ : ] = []


  def Populate( self,
                completions,
                sort_property,
                confirm_callback,
                format_completions ):
    self._completions = completions
    self._sort_property = sort_property
    self._confirm_callback = confirm_callback
    self._format_completions = format_completions
    self._first_index = 0
    self._last_index = 0
    self._selected_index = None
    self._current_query = None
    self.Update()


  def Update( self ):
    window_height = vim.current.window.height
    query = vim.current.buffer[ 0 ]
    if self._current_query != query:
      self._current_query = query
      self._filtered_completions = self.FilterAndSortCandidates( query )
      print( len( self._filtered_completions ) )
      self._selected_index = None
      self._first_index = 0
      self._last_index = min( window_height - 1,
                              len( self._filtered_completions ) )
      self.UnhighlightLine()

    displayed_completions = self._filtered_completions[ self._first_index :
                                                        self._last_index ]
    vim.current.buffer[ : ] = (
      [ query ] +
      self._format_completions( displayed_completions,
                                vim.current.window.width ) +
      # Fill the remaining space with empty lines.
      [ '' ] * ( window_height - ( self._last_index - self._first_index + 1 ) )
    )


  def OnTextChanged( self ):
    self.Update()


  def OnInsertEnter( self ):
    line, _ = vimsupport.CurrentLineAndColumn()
    if line == 0:
      return
    vimsupport.SetCurrentLineAndColumn( 0, 0 )
    vim.command( 'startinsert!' )
    # Prevent Vim from restoring the cursor after the InsertEnter event.
    vimsupport.SetVariableValue( 'v:char', ' ' )


  def Select( self ):
    nb_filtered_completions = len( self._filtered_completions )
    if not nb_filtered_completions:
      return

    window_height = vim.current.window.height

    if self._selected_index is not None:
      self._selected_index += 1
      if self._selected_index >= nb_filtered_completions:
        self._selected_index = 0
        self._first_index = 0
        self._last_index = min( window_height - 1, nb_filtered_completions )
      elif self._selected_index >= self._last_index:
        self._first_index += 1
        self._last_index += 1
    else:
      self._selected_index = 0
      self._first_index = 0
      self._last_index = min( window_height - 1, nb_filtered_completions )

    self.Update()
    self.HighlightLine()


  def Previous( self ):
    nb_filtered_completions = len( self._filtered_completions )
    if not nb_filtered_completions:
      return

    window_height = vim.current.window.height

    if self._selected_index is not None:
      self._selected_index -= 1
      if self._selected_index < 0:
        self._selected_index = nb_filtered_completions - 1
        self._first_index = max( nb_filtered_completions - window_height + 1,
                                 0 )
        self._last_index = nb_filtered_completions
      elif self._selected_index < self._first_index:
        self._first_index -= 1
        self._last_index -= 1
    else:
      self._selected_index = nb_filtered_completions - 1
      self._first_index = max( nb_filtered_completions - window_height + 1, 0 )
      self._last_index = nb_filtered_completions

    self.Update()
    self.HighlightLine()


  def HighlightLine( self ):
    signs_to_unplace = vimsupport.GetSignsInBuffer( self._buffer_number )

    sign = vimsupport.CreateSign( self._selected_index - self._first_index + 2,
                                  'YcmCompletionSelection',
                                  self._buffer_number )
    try:
      signs_to_unplace.remove( sign )
    except ValueError:
      vimsupport.PlaceSign( sign )

    for sign in signs_to_unplace:
      vimsupport.UnplaceSign( sign )


  def UnhighlightLine( self ):
    for sign in vimsupport.GetSignsInBuffer( self._buffer_number ):
      vimsupport.UnplaceSign( sign )


  def Confirm( self ):
    self._confirm_callback(
      self._filtered_completions[ self._selected_index ] )


  def FilterAndSortCandidates( self, query ):
    request_data = {
      'candidates': self._completions,
      'sort_property': self._sort_property,
      'query': query
    }

    response = BaseRequest().PostDataToHandler( request_data,
                                                'filter_and_sort_candidates' )
    return response if response is not None else []
