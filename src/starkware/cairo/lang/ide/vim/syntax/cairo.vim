" Vim syntax file
" Language: Cairo
" Author: Zolmeister
" Last Change: Feb 11, 2021

if exists("b:current_syntax")
  finish
endif

syn keyword cairoConditional if else end
syn keyword cairoKeyword func nextgroup=cairoFuncName skipwhite skipempty
syn keyword cairoKeyword struct namespace nextgroup=cairoIdentifier skipwhite skipempty
syn keyword cairoKeyword call jmp ret abs rel
syn keyword cairoRegister ap fp
syn keyword cairoKeyword const let local tempvar as from import static_assert return assert member cast alloc_locals 
syn keyword cairoType felt
syn keyword cairoItalic SIZEOF_LOCALS SIZE
syn keyword cairoTodo contained TODO FIXME XXX NB NOTE SAFETY

syn region cairoCommentLine start="#" end="$" contains=cairoTodo,@Spell

syn match cairoIdentifier "\%([^[:cntrl:][:space:][:punct:][:digit:]]\|_\)\%([^[:cntrl:][:punct:][:space:]]\|_\)*" display contained
syn match cairoFuncName "\%(r#\)\=\%([^[:cntrl:][:space:][:punct:][:digit:]]\|_\)\%([^[:cntrl:][:punct:][:space:]]\|_\)*" display contained
syn match cairoFuncCall "\w\(\w\)*("he=e-1,me=e-1
syn match cairoDecNumber display "\<\d\+\>"
syn match cairoOperator display "\%(+\|-\|/\|*\|=\|\^\|&\||\|!\|>\|<\|%\)=\?"

" embedded python
syn include @python syntax/python.vim
unlet b:current_syntax
syn region pythonStyle matchgroup=cairoEmbed start=+%{+ keepend end=+%}+ contains=@python
syn region pythonStyle matchgroup=cairoEmbed start=+%\[+ keepend end=+%\]+ contains=@python

hi def link cairoKeyword Keyword
hi def link cairoRegister Identifier
hi def link cairoIdentifier Identifier
hi def link cairoFuncName Function
hi def link cairoFuncCall Function
hi def link cairoType Type
hi def link cairoConditional Conditional
hi def link cairoItalic Special
hi def link cairoCommentLine Comment
hi def link cairoTodo Todo
hi def link cairoDecNumber Number
hi def link cairoOperator Operator
hi def link cairoEmbed SpecialComment

let b:current_syntax = "cairo"

