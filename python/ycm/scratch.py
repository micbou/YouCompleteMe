# Copyright (C) 2018 YouCompleteMe contributors
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

import json
import vim


YCM_BUFFER_NAME = 'YouCompleteMe'


class Scratch( object ):

  def __init__( self ):
    vim.command( 'silent new {0}'.format( YCM_BUFFER_NAME ) )
    buffer_number = vim.current.buffer.number
    self._buffer = vim.buffers[ buffer_number ]
    self._buffer.options[ 'textwidth' ]  = 0
    self._buffer.options[ 'buftype' ]    = 'nofile'
    self._buffer.options[ 'bufhidden' ]  = 'hide'
    self._buffer.options[ 'buflisted' ]  = False
    self._buffer.options[ 'modifiable' ] = False
    self._buffer.options[ 'readonly' ]   = False
    vim.command( 'close' )

    self._latest_message = ''
    self._saved_view = None


  def _GetWindow( self ):
    for window in vim.windows:
      if window.buffer.number == self._buffer.number:
        return window
    return None


  def _SaveView( self ):
    self._saved_view = vim.eval( 'winsaveview()' )


  def _RestoreView( self ):
    vim.eval( 'winrestview( {view} )'.format(
      view = json.dumps( self._saved_view ) ) )


  def Toggle( self ):
    self._SaveView()
    try:
      window = self._GetWindow()
      if window:
        vim.command( '{0}wincmd c'.format( window.number ) )
        return

      saved_window = vim.current.window

      vim.command( 'silent botright split {0}'.format( YCM_BUFFER_NAME ) )
      window = vim.current.window
      window.options[ 'winfixheight' ] = True
      window.options[ 'winfixwidth' ]  = True
      window.options[ 'number' ]       = False
      window.options[ 'cursorline' ]   = False
      window.options[ 'cursorcolumn' ] = False
      window.options[ 'list' ]         = False

      self._SetMessage( self._latest_message, window )

      vim.current.window = saved_window
    finally:
      self._RestoreView()


  def OnWindowEnter( self ):
    # Anchor the scratch window to the bottom.
    window = self._GetWindow()
    if window and window != vim.windows[ -1 ]:
      vim.command( '{0}wincmd w'.format( window.number ) )
      vim.command( 'wincmd J' )
      # vim.eval( '{0}wincmd _'.format( window.number ) )
      vim.command( 'wincmd p' )


  def _SetMessage( self, message, window ):
    self._buffer.options[ 'modifiable' ] = True
    self._buffer.options[ 'readonly' ]   = False

    self._buffer[:] = message.splitlines()

    self._buffer.options[ 'modifiable' ]     = False
    self._buffer.options[ 'readonly' ]       = True
    self._buffer.options[ 'modified' ]       = False

    window_width = window.width
    fitting_height = 0
    for line in self._buffer:
      fitting_height += len( line ) // ( window_width - 1 ) + 1
    window.height = fitting_height


  def DisplayMessage( self, message ):
    self._latest_message = message

    window = self._GetWindow()
    if not window:
      self.Toggle()
      return

    self._SaveView()
    self._SetMessage( message, window )
    self._RestoreView()


  def UpdateMessage( self, message ):
    self._latest_message = message

    window = self._GetWindow()
    if not window:
      return

    self._SaveView()
    self._SetMessage( message, window )
    self._RestoreView()


scratch = Scratch()
