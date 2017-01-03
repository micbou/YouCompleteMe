set nocompatible

set encoding=utf-8

filetype plugin indent on

exe 'set rtp+=' . expand( '<sfile>:p:h:h' )
runtime plugin/youcompleteme.vim
" We don't want YCM to be automatically started at the VimEnter event.
autocmd! youcompletemeStart VimEnter

let s:python_until_eof = g:ycm_profile_python_interpreter . " << EOF"


function! s:ProfileStartup()
  " Open an arbitrary file with a filetype supported by YCM.
  e test.py

  exec s:python_until_eof

import cProfile

pr = cProfile.Profile()
pr.enable()
EOF

  " Manually start YCM.
  call youcompleteme#Enable()

  exec s:python_until_eof
pr.disable()
EOF

  exec s:python_until_eof
from __future__ import unicode_literals

from ycm.client.base_request import BaseRequest
import pstats
import requests
import time
import vim

ps = pstats.Stats( pr ).sort_stats( 'cumulative' )
ps.dump_stats( vim.eval( 'g:ycm_profile_stats_file' ) )

# Wait for server to be ready then exit
while True:
  try:
    if BaseRequest().GetDataFromHandler( 'ready' ):
      break
  except requests.exceptions.ConnectionError:
    pass
  finally:
    time.sleep( 0.1 )
EOF
  q
endfunction


call s:ProfileStartup()
