# Copyright (C) 2011, 2012, 2013  Google Inc.
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
from ycm.client.base_request import BaseRequest

OMNIFUNC_RETURNED_BAD_VALUE = 'Omnifunc returned bad value to YCM!'
OMNIFUNC_NOT_LIST = ( 'Omnifunc did not return a list or a dict with a "words" '
                     ' list when expected.' )


class OmniCompleter():
  def __init__( self, user_options ):
    self._should_use_cache = bool( user_options[ 'cache_omnifunc' ] )
    self._disabled_filetypes = user_options[
      'filetype_specific_completion_to_disable' ]
    self._omnifunc = None
    self._cached_start_column = None
    self._cached_query = ''
    self._cached_candidates = []


  def ShouldUseNow( self, request_data ):
    self._omnifunc = vimsupport.ToUnicode( vim.eval( '&omnifunc' ) )
    if not self._omnifunc:
      return False
    if request_data[ 'force_semantic' ]:
      return True
    if not vimsupport.CurrentFiletypesEnabled( self._disabled_filetypes ):
      return False
    return BaseRequest().PostDataToHandler( request_data, 'should_use_now' )


  def _ComputeQuery( self, start_column, column ):
    current_line_bytes = vimsupport.ToBytes( vim.current.line )
    return vimsupport.ToUnicode( current_line_bytes[ start_column : column ] )


  def _GetCandidates( self ):
    if self._should_use_cache and self._cached_start_column is not None:
      column = vimsupport.CurrentColumn()
      return ( self._cached_start_column,
               self._ComputeQuery( self._cached_start_column, column ),
               self._cached_candidates )

    # Calling directly the omnifunc may move the cursor position. This is the
    # case with the default Vim omnifunc for C-family languages
    # (ccomplete#Complete) which calls searchdecl to find a declaration. This
    # function is supposed to move the cursor to the found declaration but it
    # doesn't when called through the omni completion mapping (CTRL-X CTRL-O).
    # So, we restore the cursor position after the omnifunc calls.
    line, column = vimsupport.CurrentLineAndColumn()

    try:
      start_column = vimsupport.GetIntValue( self._omnifunc + '(1,"")' )

      # Vim only stops completion if the value returned by the omnifunc is -3 or
      # -2. In other cases, if the value is negative or greater than the current
      # column, the start column is set to the current column; otherwise, the
      # value is used as the start column.
      if start_column in ( -3, -2 ):
        return start_column, '', []
      if start_column < 0 or start_column > column:
        start_column = column

      # Vim internally moves the cursor to the start column before calling again
      # the omnifunc. Some omnifuncs like the one defined by the
      # LanguageClient-neovim plugin depend on this behavior to compute the list
      # of candidates.
      vimsupport.SetCurrentLineAndColumn( line, start_column )

      query = self._ComputeQuery( start_column, column )

      omnifunc_call = [ self._omnifunc,
                        "(0,'",
                        vimsupport.EscapeForVim( query ),
                        "')" ]
      candidates = vim.eval( ''.join( omnifunc_call ) )

      if isinstance( candidates, dict ) and 'words' in candidates:
        candidates = candidates[ 'words' ]

      if not hasattr( candidates, '__iter__' ):
        raise TypeError( OMNIFUNC_NOT_LIST )

      # Vim allows each item of the list to be either a string or a dictionary
      # but ycmd only supports lists where items are all strings or all
      # dictionaries. Convert all strings into dictionaries.
      for index, candidate in enumerate( candidates ):
        if not isinstance( candidate, dict ):
          candidates[ index ] = { 'word': candidate }

      self._cached_start_column = start_column
      self._cached_candidates = candidates
      return start_column, query, candidates
    except ( TypeError, ValueError, vim.error ) as error:
      vimsupport.PostVimMessage(
        OMNIFUNC_RETURNED_BAD_VALUE + ' ' + str( error ) )
      return column, '', []

    finally:
      vimsupport.SetCurrentLineAndColumn( line, column )


  def ComputeCandidates( self, request_data ):
    start_column, query, candidates = self._GetCandidates()
    if self._should_use_cache and candidates:
      candidates = self.FilterAndSortCandidates( candidates, query )
    return start_column, candidates


  def FilterAndSortCandidates( self, candidates, query ):
    request_data = {
      'candidates': candidates,
      'sort_property': 'word',
      'query': query
    }

    response = BaseRequest().PostDataToHandler( request_data,
                                                'filter_and_sort_candidates' )
    return response if response is not None else []


  def InvalidateCache( self ):
    self._cached_start_column = None
