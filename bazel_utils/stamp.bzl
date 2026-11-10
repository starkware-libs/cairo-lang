"""
Makes the git commit of the workspace available to build actions as a file.

Build actions cannot run git: they execute in a sandbox (or on a remote executor) that holds
declared inputs only, with no .git directory. The commit is therefore read from the workspace
status command's output: when .bazelrc sets --workspace_status_command to a script that prints a
"STABLE_GIT_COMMIT <sha>" line, that commit is picked up here; without one the file is empty.
"""

def _git_commit_file_impl(ctx):
    out = ctx.actions.declare_file(ctx.attr.name + ".txt")

    # Extract the commit alone, rather than letting actions depend on the status file directly:
    # stable-status.txt also carries BUILD_USER and BUILD_HOST, which differ between developers,
    # so a direct dependency would make every action that embeds the commit user-specific and
    # cost us the shared remote cache. This file's content is identical for a given commit.
    ctx.actions.run_shell(
        command = "sed -n 's/^STABLE_GIT_COMMIT //p' {status} | head -1 > {out}".format(
            status = ctx.info_file.path,
            out = out.path,
        ),
        inputs = [ctx.info_file],
        outputs = [out],
        mnemonic = "GitCommit",
        progress_message = "Extracting the git commit from the workspace status",
    )
    return [DefaultInfo(files = depset([out]))]

git_commit_file = rule(
    implementation = _git_commit_file_impl,
    doc = (
        "Writes the git commit of the workspace to <name>.txt. The file is empty when the " +
        "commit is unavailable (no workspace status command, or not a git checkout)."
    ),
)
