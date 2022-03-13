" Vim syntax file
"
" Language: CAIRO

if exists("b:current_syntax")
  finish
endif

syntax include @python syntax/python.vim

let b:current_syntax = "cairo"

hi def link statement Statement
hi def link register Identifier
hi def link comment Comment
hi def link funcDef Statement
hi def link funcName Function
hi def link num Constant
hi def link specialIdentifier Special

syn keyword statement call jmp ret abs rel if const let end from import static_assert local tempvar
  \ felt return assert member cast else alloc_locals as with with_attr nondet dw codeoffset new
  \ using
syn keyword register ap fp
syn keyword specialIdentifier SIZEOF_LOCALS SIZE
syn match comment '#[^\n]*\n'
syn keyword funcDef func namespace struct nextgroup=funcName skipwhite
syn match funcName '[a-zA-Z_][a-zA-Z0-9_]*' display contained
syn match num '[+-]\?\d\+'
syn region cairoHint matchgroup=SpecialComment start="%{" keepend end="%}" contains=@python
syn region pythonLiteral matchgroup=SpecialComment start="%\[" keepend end="%\]" contains=@python
