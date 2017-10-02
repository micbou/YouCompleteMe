set nocompatible

set encoding=utf-8


let s:count = 0


function! s:GoDown( ... )
  if s:count == 10
    call s:EndProfiling()
    return
  endif
  call feedkeys( "j" )
  let s:count = s:count + 1
  call timer_start( 100, function( 's:GoDown' ) )
endfunction

filetype plugin indent on

exe 'set rtp+=' . expand( '<sfile>:p:h:h' )
runtime plugin/youcompleteme.vim
" We don't want YCM to be automatically started at the VimEnter event.
autocmd! youcompletemeStart VimEnter

let s:python_until_eof = g:ycm_profile_python_interpreter . " << EOF"


function! s:ProfileDiagnostics()
  let g:ycm_confirm_extra_conf = 0
  let g:ycm_echo_current_diagnostic = 1

  " Manually start YCM.
  call youcompleteme#Enable()

  exec s:python_until_eof
from __future__ import unicode_literals
from ycm.client.base_request import BaseRequest

import cProfile
import pstats
import requests
import time
import vim

# Wait for server to be ready then exit
while True:
  try:
    if BaseRequest.GetDataFromHandler( 'ready' ):
      break
  except requests.exceptions.ConnectionError:
    pass
  finally:
    time.sleep( 0.1 )
EOF

  e prof/test.cpp

  call s:StartProfiling()

  call timer_start( 100, function( 's:GoDown' ) )
endfunction


function! s:StartProfiling()
  exec s:python_until_eof
pr = cProfile.Profile()
pr.enable()
EOF
endfunction


function! s:EndProfiling()
  exec s:python_until_eof
pr.disable()

ps = pstats.Stats( pr ).sort_stats( 'cumulative' )
ps.dump_stats( vim.eval( 'g:ycm_profile_stats_file' ) )

EOF
  q
endfunction


call s:ProfileDiagnostics()
