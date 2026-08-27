/* VS Code support for SHE.
 *
 * Highlighting and snippets are declarative (see package.json). This file wires
 * up the four commands and, when it is available, connects to SHE's own
 * language server for live diagnostics, completion and hover.
 */

const vscode = require("vscode");

let client = null;
let terminal = null;

function config() {
  return vscode.workspace.getConfiguration("she");
}

function sheCommand() {
  return config().get("command") || "she";
}

function runInTerminal(command) {
  if (!terminal || terminal.exitStatus !== undefined) {
    terminal = vscode.window.createTerminal("SHE");
  }
  terminal.show(true);
  terminal.sendText(command);
}

function activate(context) {
  const push = (name, handler) =>
    context.subscriptions.push(vscode.commands.registerCommand(name, handler));

  push("she.run", async () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document.languageId !== "she") {
      vscode.window.showWarningMessage("Open a .she file first.");
      return;
    }
    await editor.document.save();
    runInTerminal(`${sheCommand()} run "${editor.document.fileName}"`);
  });

  push("she.test", () => {
    const folder = vscode.workspace.workspaceFolders?.[0];
    runInTerminal(`${sheCommand()} test${folder ? ` "${folder.uri.fsPath}"` : ""}`);
  });

  push("she.format", async () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return;
    await editor.document.save();
    runInTerminal(`${sheCommand()} fmt "${editor.document.fileName}"`);
  });

  push("she.repl", () => runInTerminal(sheCommand()));

  if (config().get("languageServer")) {
    startLanguageServer(context);
  }
}

function startLanguageServer(context) {
  let languageclient;
  try {
    languageclient = require("vscode-languageclient/node");
  } catch (_) {
    // Highlighting and the commands still work without the LSP client.
    return;
  }

  const server = { command: sheCommand(), args: ["lsp"] };
  client = new languageclient.LanguageClient(
    "she",
    "SHE Language Server",
    { run: server, debug: server },
    {
      documentSelector: [{ scheme: "file", language: "she" }],
      synchronize: { fileEvents: vscode.workspace.createFileSystemWatcher("**/*.she") },
      outputChannelName: "SHE",
    }
  );

  client.start().catch(() => {
    vscode.window.showInformationMessage(
      "SHE: could not start the language server. Highlighting still works. " +
        "Install SHE with `pip install she-lang`, or set `she.command` in your settings."
    );
  });

  context.subscriptions.push({ dispose: () => client && client.stop() });
}

function deactivate() {
  return client ? client.stop() : undefined;
}

module.exports = { activate, deactivate };
