# Copyright (C) 2013-2018 YouCompleteMe contributors
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

import hashlib
import hmac
import json
import logging
import vim
from future.utils import native, PY2
from base64 import b64decode, b64encode
from ycm.vimsupport import ( Confirm,
                             CurrentLineAndColumn,
                             FiletypesForBuffer,
                             GetBufferFilepath,
                             GetCurrentDirectory,
                             GetUnsavedAndSpecifiedBufferData,
                             PostVimMessage,
                             ToBytes,
                             ToUnicode )

# Idiom to import urljoin and urlparse on Python 2 and 3.
if PY2:
  from urlparse import urljoin, urlparse
else:
  from urllib.parse import urljoin, urlparse  # noqa

_HEADERS = { 'content-type': 'application/json' }
_CONNECT_TIMEOUT_SEC = 0.01
# Setting this to None seems to screw up the Requests/urllib3 libs.
_READ_TIMEOUT_SEC = 30
_HMAC_HEADER = 'x-ycm-hmac'
_logger = logging.getLogger( __name__ )

CONFIRM_CONF_FILE_MESSAGE = ( 'Found {}. Load? \n\n(Question can be turned '
                              'off with options, see YCM docs)' )


class UnknownExtraConf( Exception ):
  def __init__( self, message, extra_conf_file ):
    super( UnknownExtraConf, self ).__init__( message )
    self.extra_conf_file = extra_conf_file


class BaseRequest( object ):

  def __init__( self ):
    self._should_resend = False


  def Start( self ):
    pass


  def Done( self ):
    return True


  def Response( self ):
    return {}


  def ShouldResend( self ):
    return self._should_resend


  def HandleFuture( self,
                    future,
                    display_message = True,
                    truncate_message = False ):
    """Get the server response from a |future| object and catch any exception
    while doing so. If an exception is raised because of a unknown
    .ycm_extra_conf.py file, load the file or ignore it after asking the user.
    An identical request should be sent again to the server. For other
    exceptions, log the exception and display its message to the user on the Vim
    status line. Unset the |display_message| parameter to hide the message from
    the user. Set the |truncate_message| parameter to avoid hit-enter prompts
    from this message."""
    try:
      try:
        return _JsonFromFuture( future )
      except UnknownExtraConf as e:
        if Confirm( str( e ) ):
          _LoadExtraConfFile( e.extra_conf_file )
        else:
          _IgnoreExtraConfFile( e.extra_conf_file )
        self._should_resend = True
    except BaseRequest.Requests().exceptions.ConnectionError as e:
      # We don't display this exception to the user since it is likely to happen
      # for each subsequent request (typically if the server crashed) and we
      # don't want to spam the user with it.
      _logger.error( e )
    except Exception as e:
      _logger.exception( 'Error while handling server response' )
      if display_message:
        DisplayServerException( e, truncate_message )

    return None


  # This method blocks
  # |timeout| is num seconds to tolerate no response from server before giving
  # up; see Requests docs for details (we just pass the param along).
  # See the HandleFuture method for the |display_message| and |truncate_message|
  # parameters.
  def GetDataFromHandler( self,
                          handler,
                          timeout = _READ_TIMEOUT_SEC,
                          display_message = True,
                          truncate_message = False ):
    return self.HandleFuture(
        BaseRequest._TalkToHandlerAsync( '', handler, 'GET', timeout ),
        display_message,
        truncate_message )


  # This is the blocking version of the method. See below for async.
  # |timeout| is num seconds to tolerate no response from server before giving
  # up; see Requests docs for details (we just pass the param along).
  # See the HandleFuture method for the |display_message| and |truncate_message|
  # parameters.
  def PostDataToHandler( self,
                         data,
                         handler,
                         timeout = _READ_TIMEOUT_SEC,
                         display_message = True,
                         truncate_message = False ):
    return self.HandleFuture(
        BaseRequest.PostDataToHandlerAsync( data, handler, timeout ),
        display_message,
        truncate_message )


  # This returns a future! Use HandleFuture to get the value.
  # |timeout| is num seconds to tolerate no response from server before giving
  # up; see Requests docs for details (we just pass the param along).
  @staticmethod
  def PostDataToHandlerAsync( data, handler, timeout = _READ_TIMEOUT_SEC ):
    return BaseRequest._TalkToHandlerAsync( data, handler, 'POST', timeout )


  # This returns a future! Use HandleFuture to get the value.
  # |method| is either 'POST' or 'GET'.
  # |timeout| is num seconds to tolerate no response from server before giving
  # up; see Requests docs for details (we just pass the param along).
  @staticmethod
  def _TalkToHandlerAsync( data,
                           handler,
                           method,
                           timeout = _READ_TIMEOUT_SEC ):
    request_uri = _BuildUri( handler )
    if method == 'POST':
      sent_data = _ToUtf8Json( data )
      return BaseRequest.Session().post(
          request_uri,
          data = sent_data,
          headers = BaseRequest._ExtraHeaders( method,
                                               request_uri,
                                               sent_data ),
          timeout = ( _CONNECT_TIMEOUT_SEC, timeout ) )
    return BaseRequest.Session().get(
        request_uri,
        headers = BaseRequest._ExtraHeaders( method, request_uri ),
        timeout = ( _CONNECT_TIMEOUT_SEC, timeout ) )


  @staticmethod
  def _ExtraHeaders( method, request_uri, request_body = None ):
    if not request_body:
      request_body = bytes( b'' )
    headers = dict( _HEADERS )
    headers[ _HMAC_HEADER ] = b64encode(
        CreateRequestHmac( ToBytes( method ),
                           ToBytes( urlparse( request_uri ).path ),
                           request_body,
                           BaseRequest.hmac_secret ) )
    return headers


  # These two methods exist to avoid importing the requests module at startup;
  # reducing loading time since this module is slow to import.
  @classmethod
  def Requests( cls ):
    try:
      return cls.requests
    except AttributeError:
      import requests
      cls.requests = requests
      return requests


  @classmethod
  def Session( cls ):
    try:
      return cls.session
    except AttributeError:
      from ycm.unsafe_thread_pool_executor import UnsafeThreadPoolExecutor
      from requests_futures.sessions import FuturesSession
      executor = UnsafeThreadPoolExecutor( max_workers = 30 )
      cls.session = FuturesSession( executor = executor )
      return cls.session


  server_location = ''
  hmac_secret = ''


def BuildRequestData( buffer_number = None ):
  """Build request for the current buffer or the buffer with number
  |buffer_number| if specified."""
  working_dir = GetCurrentDirectory()
  current_buffer = vim.current.buffer

  if buffer_number and current_buffer.number != buffer_number:
    # Cursor position is irrelevant when filepath is not the current buffer.
    buffer_object = vim.buffers[ buffer_number ]
    filepath = GetBufferFilepath( buffer_object )
    return {
      'filepath': filepath,
      'line_num': 1,
      'column_num': 1,
      'working_dir': working_dir,
      'file_data': GetUnsavedAndSpecifiedBufferData( buffer_object, filepath )
    }

  current_filepath = GetBufferFilepath( current_buffer )
  line, column = CurrentLineAndColumn()

  return {
    'filepath': current_filepath,
    'line_num': line + 1,
    'column_num': column + 1,
    'working_dir': working_dir,
    'file_data': GetUnsavedAndSpecifiedBufferData( current_buffer,
                                                   current_filepath )
  }


def BuildLineRequestData():
  """Same as BuildRequestData but only for the current line. Used as the
  body of the /start_column request to reduce bandwidth."""
  current_buffer = vim.current.buffer
  current_filepath = GetBufferFilepath( current_buffer )
  line, column = CurrentLineAndColumn()
  return {
    'filepath': current_filepath,
    'line_num': 1,
    'column_num': column + 1,
    'file_data': {
      current_filepath: {
        'contents': ToUnicode( current_buffer[ line ] ),
        'filetypes': FiletypesForBuffer( current_buffer )
      }
    }
  }


def _JsonFromFuture( future ):
  response = future.result()
  _ValidateResponseObject( response )
  if response.status_code == BaseRequest.Requests().codes.server_error:
    raise MakeServerException( response.json() )

  # We let Requests handle the other status types, we only handle the 500
  # error code.
  response.raise_for_status()

  if response.text:
    return response.json()
  return None


def _LoadExtraConfFile( filepath ):
  BaseRequest().PostDataToHandler( { 'filepath': filepath },
                                   'load_extra_conf_file' )


def _IgnoreExtraConfFile( filepath ):
  BaseRequest().PostDataToHandler( { 'filepath': filepath },
                                   'ignore_extra_conf_file' )


def DisplayServerException( exception, truncate_message = False ):
  serialized_exception = str( exception )

  # We ignore the exception about the file already being parsed since it comes
  # up often and isn't something that's actionable by the user.
  if 'already being parsed' in serialized_exception:
    return
  PostVimMessage( serialized_exception, truncate = truncate_message )


def _ToUtf8Json( data ):
  return ToBytes( json.dumps( data ) if data else None )


def _ValidateResponseObject( response ):
  our_hmac = CreateHmac( response.content, BaseRequest.hmac_secret )
  their_hmac = ToBytes( b64decode( response.headers[ _HMAC_HEADER ] ) )
  if not SecureBytesEqual( our_hmac, their_hmac ):
    raise RuntimeError( 'Received invalid HMAC for response!' )
  return True


def _BuildUri( handler ):
  return native( ToBytes( urljoin( BaseRequest.server_location, handler ) ) )


def MakeServerException( data ):
  exception_name = data[ 'exception' ][ 'TYPE' ]
  message = data[ 'message' ]
  if exception_name == 'UnknownExtraConf':
    return UnknownExtraConf( message, data[ 'exception' ][ 'extra_conf_file' ] )
  return type( exception_name, ( Exception, ), {} )( message )


def CreateHmac( content, hmac_secret ):
  # Note that py2's str type passes this check (and that's ok)
  if not isinstance( content, bytes ):
    raise TypeError( 'content was not of bytes type; you have a bug!' )
  if not isinstance( hmac_secret, bytes ):
    raise TypeError( 'hmac_secret was not of bytes type; you have a bug!' )

  return bytes( hmac.new( hmac_secret,
                          msg = content,
                          digestmod = hashlib.sha256 ).digest() )


def CreateRequestHmac( method, path, body, hmac_secret ):
  # Note that py2's str type passes this check (and that's ok)
  if not isinstance( body, bytes ):
    raise TypeError( 'body was not of bytes type; you have a bug!' )
  if not isinstance( hmac_secret, bytes ):
    raise TypeError( 'hmac_secret was not of bytes type; you have a bug!' )
  if not isinstance( method, bytes ):
    raise TypeError( 'method was not of bytes type; you have a bug!' )
  if not isinstance( path, bytes ):
    raise TypeError( 'path was not of bytes type; you have a bug!' )

  method_hmac = CreateHmac( method, hmac_secret )
  path_hmac = CreateHmac( path, hmac_secret )
  body_hmac = CreateHmac( body, hmac_secret )

  joined_hmac_input = bytes().join( ( method_hmac, path_hmac, body_hmac ) )
  return CreateHmac( joined_hmac_input, hmac_secret )


# This is the compare_digest function from python 3.4
#   http://hg.python.org/cpython/file/460407f35aa9/Lib/hmac.py#l16
def SecureBytesEqual( a, b ):
  """Returns the equivalent of 'a == b', but avoids content based short
  circuiting to reduce the vulnerability to timing attacks."""
  # Consistent timing matters more here than data type flexibility
  # We do NOT want to support py2's str type because iterating over them
  # (below) produces different results.
  if type( a ) != bytes or type( b ) != bytes:
    raise TypeError( "inputs must be bytes instances" )

  # We assume the length of the expected digest is public knowledge,
  # thus this early return isn't leaking anything an attacker wouldn't
  # already know
  if len( a ) != len( b ):
    return False

  # We assume that integers in the bytes range are all cached,
  # thus timing shouldn't vary much due to integer object creation
  result = 0
  for x, y in zip( a, b ):
    result |= x ^ y
  return result == 0
