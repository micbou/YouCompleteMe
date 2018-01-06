set nocompatible

set encoding=utf-8

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

  execute ":argadd " . join( range( g:ycm_nb_buffers ), " " )

  call s:StartProfiling()

  e prof/test.py

  call s:EndProfiling()
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
  q!
endfunction


call s:ProfileDiagnostics()
