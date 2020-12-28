import * as vscode from 'vscode';
import cp = require('child_process');

function getFormatterExecutablePath(config: vscode.WorkspaceConfiguration): string | undefined {
    var execPath = config.get<string>('cairo.cairoFormatPath');

    if (!execPath) {
        return undefined;
    }

    // Replace placeholders, if present.
    if (vscode.workspace.rootPath) {
        execPath = execPath.replace(/\${workspaceFolder}/g, vscode.workspace.rootPath);
    }
    return execPath.replace(/\${cwd}/g, process.cwd());
}

export function activate(context: vscode.ExtensionContext) {
    const config = vscode.workspace.getConfiguration();
    vscode.languages.registerDocumentFormattingEditProvider('cairo', {
        provideDocumentFormattingEdits(document: vscode.TextDocument): vscode.TextEdit[] {
            const execPath = getFormatterExecutablePath(config);
            if (!execPath) {
                vscode.window.showInformationMessage('Unable to read cairo.cairoFormatPath.');
                return [];
            }

            const opts = {
                input: document.getText(),
                encoding: 'utf-8',
            };
            try {
                var replacementText = cp.execFileSync(execPath, ['-'], opts);
            } catch (e) {
                if ((<any>e).code === 'ENOENT') {
                    vscode.window.showInformationMessage(
                        'Formatting failed. Executable ' + execPath + ' not found. ' +
                        'Please check your cairo.cairoFormatPath user setting and ensure ' +
                        'it is installed.');
                    return [];
                }
                vscode.window.showInformationMessage('Formatting failed: ' + e.stderr.toString());
                return [];
            }

            var firstLine = document.lineAt(0);
            var lastLine = document.lineAt(document.lineCount - 1);
            var wholeRange = new vscode.Range(0,
                firstLine.range.start.character,
                document.lineCount - 1,
                lastLine.range.end.character);
            return [vscode.TextEdit.replace(wholeRange, replacementText.toString())];
        }
    });
}
