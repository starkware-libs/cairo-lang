# CairoZero for Visual Studio Code

This extension provides support for the older version of Cairo, known as CairoZero. For the new language, install the [Cairo 1.0](https://marketplace.visualstudio.com/items?itemName=starkware.cairo1) extension.
Note that the CairoZero compiler and extension are no longer maintained. This extension should only be used by projects that still rely on CairoZero code.

## Installation

From the directory of this file, run:
```
sudo npm install -g vsce
npm install
vsce package
code --install-extension cairo*.vsix
```

## Configuration

If you have `cairo-format` installed globally (available in PATH), the value of
`cairo.cairoFormatPath` should be `cairo-format` (the default).

If you're working inside a StarkWare repository, and want the most up-to-date version,
set the value of `cairo.cairoFormatPath` to
```
${workspaceFolder}/src/starkware/cairo/lang/scripts/cairo-format
```

## Run the extension (for development)

1. Open VSCode in the directory of the extension.
2. Run:
   ```
   npm install
   npm run compile
   ```
3. Reload VSCode.
4. Press F5.
