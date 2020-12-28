" Show existing tab with 4 spaces width.
setlocal tabstop=4
" When indenting with '>', use 4 spaces width.
setlocal shiftwidth=4

command -buffer Format !.tox/dev/bin/python cairo-format -i %
